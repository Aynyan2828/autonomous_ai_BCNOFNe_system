#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コマンド実行エンジン（強化版：方針B）
- shell=False でシェル注入を封じる
- 許可ディレクトリ配下のパス操作のみ許可（rm/mv/cp/chmod/chown等）
- systemctl/journalctl 等は許可サブコマンド制限
"""

import subprocess
import shlex
from typing import Dict, List, Tuple, Optional
import re
import os
from pathlib import Path
from datetime import datetime
import json


class CommandExecutor:
    """コマンド実行クラス（安全強化）"""

    # ====== 設定 ======
    DEFAULT_CWD = "/home/pi/autonomous_ai"  # 作業ディレクトリ固定（必要なら変更）

    # パス操作を許可するルート（方針B：この配下だけ触ってOK）
    # ※あなたのプロジェクト実体に合わせて必要なら増やしてOK
    ALLOWED_ROOTS = [
        "/home/pi/autonomous_ai",
        "/home/pi/autonomous_ai_BCNOFNe_system",
        "/mnt/hdd",  # エンジンデータ保存先が /mnt/hdd 配下ならここ
    ]

    # 危険なコマンドのブラックリスト（文字列ベースで“補助”）
    # ※shell=False でほぼ無効化できるが、念のため残す
    DANGEROUS_PATTERNS = [
        r':\(\)\{.*\};:',  # fork bomb
        r'\brm\b.*\b-rf\b.*\b/\b',
        r'\bmkfs\b',
        r'\bdd\b.*\bof=/dev/',
        r'\bchmod\b.*\b-R\b.*\b/\b',
        r'\bchown\b.*\b-R\b.*\b/\b',
        r'\bcurl\b.*\|\s*\b(bash|sh)\b',
        r'\bwget\b.*\|\s*\b(bash|sh)\b',
        r'\b>\s*/dev/sd[a-z]\b',
    ]

    # 許可コマンド（完全一致）
    ALLOWED_COMMANDS = {
        "ls", "cat", "echo", "pwd", "mkdir", "touch",
        "grep", "find", "wc", "head", "tail", "sort", "uniq",
        "date", "whoami", "hostname", "uname", "df", "du",
        "ps", "top", "free", "uptime", "which", "whereis",
        "git", "python3", "pip3", "node", "npm",
        "systemctl", "journalctl",
        "cp", "mv", "rm",
        "chmod", "chown",
    }

    # ファイルパス制限が必要なコマンド
    PATH_SENSITIVE = {"cp", "mv", "rm", "chmod", "chown", "touch", "mkdir", "cat", "grep", "find", "ls", "head", "tail"}

    # systemctl の許可サブコマンド（必要に応じて追加）
    ALLOWED_SYSTEMCTL_ACTIONS = {
        "status", "restart", "start", "stop", "is-active", "is-enabled", "daemon-reload"
    }

    # journalctl の許可オプション（緩め。危険は少ないが、巨大出力対策に -n 推奨）
    # ここは“禁止”というより、実行前にガードで出力制限する感じ
    # ====== /設定 ======

    def __init__(self, timeout: int = 30, max_output_size: int = 10000, audit_log_path: Optional[str] = None):
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.audit_log_path = audit_log_path or os.path.join(self.DEFAULT_CWD, "logs", "command_audit.jsonl")
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

    # ---------- パス検査 ----------
    def _is_under_allowed_roots(self, p: Path) -> bool:
        """実パスが許可ルート配下か判定"""
        try:
            rp = p.expanduser().resolve()
        except Exception:
            return False

        for root in self.ALLOWED_ROOTS:
            try:
                rr = Path(root).resolve()
                # python3.9+ の is_relative_to が使えない環境もあるので手動
                if str(rp).startswith(str(rr) + os.sep) or str(rp) == str(rr):
                    return True
            except Exception:
                continue
        return False

    def _extract_pathlike_args(self, args: List[str]) -> List[Path]:
        """
        引数から“パスっぽいもの”を抽出。
        - オプション（-x / --xxx）は除外
        - 明らかにURLっぽいのも除外
        """
        paths: List[Path] = []
        for a in args[1:]:
            if not a:
                continue
            if a.startswith("-"):
                continue
            if re.match(r"^[a-zA-Z]+://", a):  # URL
                continue
            # systemctl unit 名みたいなの（foo.service）をパス扱いしない
            if a.endswith(".service") and "/" not in a:
                continue
            # それ以外はパス候補
            if "/" in a or a.startswith(".") or a.startswith("~"):
                paths.append(Path(a))
        return paths

    # ---------- 安全性チェック ----------
    def is_safe_command(self, command: str) -> Tuple[bool, str, List[str]]:
        """
        コマンドが安全かチェック

        Returns:
            (安全かどうか, エラーメッセージ, パース済みargs)
        """
        if not command or not command.strip():
            return False, "空のコマンドです", []

        # ざっくり危険パターン（補助）
        for pat in self.DANGEROUS_PATTERNS:
            if re.search(pat, command, re.IGNORECASE):
                return False, f"危険パターン検出: {pat}", []

        # シェル演算子っぽいのを明示拒否（shell=Falseでも一応）
        if any(x in command for x in [";", "&&", "||", "|", "`", "$("]):
            return False, "シェル演算子（;,&&,||,|,`,$()）は禁止です", []

        # パース
        try:
            args = shlex.split(command)
        except Exception as e:
            return False, f"コマンドの解析に失敗: {e}", []

        if not args:
            return False, "空のコマンドです", []

        base = Path(args[0]).name

        # sudo禁止
        if base == "sudo":
            return False, "sudoは禁止です", []

        # ホワイトリスト
        if base not in self.ALLOWED_COMMANDS:
            return False, f"許可されていないコマンド: {base}", []

        # systemctl 制限
        if base == "systemctl":
            if len(args) < 2:
                return False, "systemctl はサブコマンドが必要です", []
            action = args[1]
            if action not in self.ALLOWED_SYSTEMCTL_ACTIONS:
                return False, f"許可されていない systemctl 操作: {action}", []

        # ファイルパス制限（方針Bの肝）
        if base in self.PATH_SENSITIVE:
            # パスっぽい引数を抽出して全部検査
            path_args = self._extract_pathlike_args(args)
            for p in path_args:
                if not self._is_under_allowed_roots(p):
                    return False, f"許可ディレクトリ外のパス操作は禁止: {p}", []

        # rm の追加制限（より堅く）
        if base == "rm":
            # ルートや親ディレクトリっぽいの禁止
            for a in args[1:]:
                if a in ["/", "/*", "..", "../", "~", "~/", ".*"]:
                    return False, f"危険な rm 対象: {a}", []
            # -rf の乱用を弱める（必要なら -r だけ許可にしてもOK）
            # ここは運用で調整可

        return True, "", args

    # ---------- 実行 ----------
    def _truncate(self, s: str) -> str:
        if len(s) <= self.max_output_size:
            return s
        return s[:self.max_output_size] + f"\n... (出力が{self.max_output_size}文字を超えたため切り詰め)"

    def _audit(self, record: Dict) -> None:
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # 監査ログ失敗は実行結果に影響させない
            pass

    def execute(self, command: str) -> Dict:
        is_safe, error_msg, args = self.is_safe_command(command)
        if not is_safe:
            rec = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "command": command,
                "allowed": False,
                "reason": error_msg,
            }
            self._audit(rec)
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"安全性チェック失敗: {error_msg}"
            }

        try:
            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.DEFAULT_CWD,
            )

            stdout = self._truncate(result.stdout or "")
            stderr = self._truncate(result.stderr or "")

            rec = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "command": command,
                "args": args,
                "allowed": True,
                "returncode": result.returncode,
            }
            self._audit(rec)

            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            rec = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "command": command,
                "args": args,
                "allowed": True,
                "returncode": -1,
                "error": f"timeout({self.timeout}s)",
            }
            self._audit(rec)
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"タイムアウト: コマンドが{self.timeout}秒以内に完了しませんでした"
            }

        except Exception as e:
            rec = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "command": command,
                "args": args,
                "allowed": True,
                "returncode": -1,
                "error": str(e),
            }
            self._audit(rec)
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"実行エラー: {str(e)}"
            }

    def execute_multiple(self, commands: List[str]) -> List[Dict]:
        results = []
        for cmd in commands:
            res = self.execute(cmd)
            results.append({"command": cmd, "result": res})
        return results

    def get_safe_command_list(self) -> List[str]:
        return sorted(list(self.ALLOWED_COMMANDS))


if __name__ == "__main__":
    executor = CommandExecutor()

    print("=== 安全なコマンドのテスト ===")
    safe_commands = [
        "echo 'Hello, World!'",
        "ls -la",
        "pwd",
        "date",
        "uname -a",
        "systemctl status autonomous-ai.service",
        "journalctl -u autonomous-ai.service -n 50 --no-pager",
    ]
    for cmd in safe_commands:
        print(f"\n実行: {cmd}")
        r = executor.execute(cmd)
        print("成功:", r["success"])
        print("stdout:", r["stdout"])
        if r.get("error"):
            print("error:", r["error"])

    print("\n=== 危険/拒否されるコマンドのテスト ===")
    bad_commands = [
        "rm -rf /",
        "ls; rm -rf /home/pi",
        "sudo reboot",
        "chmod -R 777 /",
        "rm -rf ../",
        "rm -rf /etc",
        "systemctl enable ssh",
    ]
    for cmd in bad_commands:
        print(f"\n実行: {cmd}")
        r = executor.execute(cmd)
        print("成功:", r["success"])
        if r.get("error"):
            print("error:", r["error"])
