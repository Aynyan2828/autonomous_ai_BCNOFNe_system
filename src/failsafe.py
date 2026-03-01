<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自己修復・自動復旧エンジン（フェイルセーフ）
"""

import os
import sys
import glob
import gzip
import shutil
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any


class FailSafe:
    """自己修復エンジン"""
    
    BASE_DIR = "/home/pi/autonomous_ai"
    LOG_DIR = "/home/pi/autonomous_ai/logs"
    MEMORY_DIR = "/home/pi/autonomous_ai/memory"
    FALLBACK_DIR = "/tmp/ai_fallback"
    RECOVERY_LOG = "/home/pi/autonomous_ai/state/recovery.jsonl"
    
    def __init__(self):
        os.makedirs(os.path.dirname(self.RECOVERY_LOG), exist_ok=True)
    
    def check_and_recover(self) -> List[Dict[str, Any]]:
        """全チェック＆自動修復"""
        actions = []
        actions.extend(self._check_ai_service())
        actions.extend(self._check_log_size())
        actions.extend(self._check_memory_integrity())
        actions.extend(self._check_storage_writable())
        return actions
    
    # ===== AIサービス復旧 =====
    
    def _check_ai_service(self) -> List[Dict]:
        """AIプロセス停止時の自動再起動"""
        actions = []
        try:
            r = subprocess.run(
                ["systemctl", "is-active", "autonomous-ai.service"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip() != "active":
                actions.append(self._restart_ai_service())
        except Exception as e:
            actions.append({"action": "ai_check", "success": False, "error": str(e)})
        return actions
    
    def _restart_ai_service(self) -> Dict:
        """AIサービスを再起動"""
        try:
            subprocess.run(
                ["systemctl", "restart", "autonomous-ai.service"],
                timeout=30
            )
            self._log_recovery("ai_restart", "AIサービスを自動再起動しました")
            return {"action": "ai_restart", "success": True, "message": "AI自動再起動完了"}
        except Exception as e:
            self._log_recovery("ai_restart_fail", str(e))
            return {"action": "ai_restart", "success": False, "error": str(e)}
    
    # ===== ログ自動圧縮 =====
    
    def _check_log_size(self) -> List[Dict]:
        """7日超ログを自動圧縮"""
        actions = []
        cutoff = datetime.now() - timedelta(days=7)
        
        try:
            for log_file in glob.glob(os.path.join(self.LOG_DIR, "*.log")):
                path = Path(log_file)
                if path.name == "agent.log":
                    # 現行ログはサイズチェックのみ
                    if path.stat().st_size > 50 * 1024 * 1024:  # 50MB超
                        actions.append(self._rotate_log(path))
                    continue
                
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    actions.append(self._compress_log(path))
        except Exception as e:
            actions.append({"action": "log_check", "success": False, "error": str(e)})
        
        return actions
    
    def _compress_log(self, path: Path) -> Dict:
        """ログファイルをgz圧縮"""
        try:
            gz_path = str(path) + ".gz"
            with open(path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(path)
            self._log_recovery("log_compress", f"圧縮: {path.name}")
            return {"action": "log_compress", "success": True, "file": path.name}
        except Exception as e:
            return {"action": "log_compress", "success": False, "error": str(e)}
    
    def _rotate_log(self, path: Path) -> Dict:
        """ログローテーション"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated = path.parent / f"{path.stem}_{ts}.log"
            shutil.move(str(path), str(rotated))
            path.touch()  # 空ファイル再作成
            self._compress_log(rotated)
            self._log_recovery("log_rotate", f"ローテーション: {path.name}")
            return {"action": "log_rotate", "success": True, "file": path.name}
        except Exception as e:
            return {"action": "log_rotate", "success": False, "error": str(e)}
    
    # ===== Memory整合性 =====
    
    def _check_memory_integrity(self) -> List[Dict]:
        """memory破損チェック＆再生成"""
        actions = []
        memory_dir = Path(self.MEMORY_DIR)
        
        if not memory_dir.exists():
            memory_dir.mkdir(parents=True, exist_ok=True)
            actions.append({"action": "memory_dir_create", "success": True})
        
        # index.json チェック
        index_path = memory_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except (json.JSONDecodeError, ValueError):
                # 破損 → 再生成
                actions.append(self._regenerate_index(index_path, memory_dir))
        
        # 0バイトファイル検出
        for f in memory_dir.rglob("*"):
            if f.is_file() and f.stat().st_size == 0 and f.suffix in ('.json', '.txt', '.jsonl'):
                actions.append({
                    "action": "zero_byte_detected",
                    "file": str(f),
                    "success": True,
                    "message": f"0バイトファイル検出: {f.name}"
                })
                self._log_recovery("zero_byte", f"検出: {f}")
        
        return actions
    
    def _regenerate_index(self, index_path: Path, memory_dir: Path) -> Dict:
        """インデックスを再生成"""
        try:
            topics_dir = memory_dir / "topics"
            index = {"topics": {}, "total_memories": 0}
            
            if topics_dir.exists():
                for topic_file in topics_dir.glob("*.txt"):
                    topic = topic_file.stem
                    index["topics"][topic] = {
                        "filename": topic_file.name,
                        "updated": datetime.fromtimestamp(topic_file.stat().st_mtime).isoformat(),
                        "size": topic_file.stat().st_size
                    }
                    index["total_memories"] += 1
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
            
            self._log_recovery("index_regen", f"インデックス再生成: {index['total_memories']}件")
            return {"action": "index_regen", "success": True}
        except Exception as e:
            return {"action": "index_regen", "success": False, "error": str(e)}
    
    # ===== ストレージ書込み隔離 =====
    
    def _check_storage_writable(self) -> List[Dict]:
        """書込みテスト＆隔離"""
        actions = []
        test_file = os.path.join(self.BASE_DIR, ".write_test")
        
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception:
            # 書込み不可 → フォールバック隔離
            os.makedirs(self.FALLBACK_DIR, exist_ok=True)
            self._log_recovery("storage_isolate", f"書込み隔離: {self.FALLBACK_DIR}")
            actions.append({
                "action": "storage_isolate",
                "success": True,
                "message": f"メインストレージ書込み不可。{self.FALLBACK_DIR}に隔離。"
            })
        
        return actions
    
    def _log_recovery(self, action: str, detail: str):
        """復旧ログ"""
        try:
            with open(self.RECOVERY_LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "action": action,
                    "detail": detail,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


def main():
    """Watchdogとして常駐"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchdog", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    
    fs = FailSafe()
    
    if args.watchdog:
        print("FailSafe Watchdog 起動")
        while True:
            actions = fs.check_and_recover()
            for a in actions:
                print(f"[FailSafe] {a}")
            time.sleep(args.interval)
    else:
        actions = fs.check_and_recover()
        for a in actions:
            print(f"[FailSafe] {a}")


if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自己修復・自動復旧エンジン（フェイルセーフ）
"""

import os
import sys
import glob
import gzip
import shutil
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any


class FailSafe:
    """自己修復エンジン"""
    
    BASE_DIR = "/home/pi/autonomous_ai"
    LOG_DIR = "/home/pi/autonomous_ai/logs"
    MEMORY_DIR = "/home/pi/autonomous_ai/memory"
    FALLBACK_DIR = "/tmp/ai_fallback"
    RECOVERY_LOG = "/home/pi/autonomous_ai/state/recovery.jsonl"
    
    def __init__(self):
        os.makedirs(os.path.dirname(self.RECOVERY_LOG), exist_ok=True)
    
    def check_and_recover(self) -> List[Dict[str, Any]]:
        """全チェック＆自動修復"""
        actions = []
        actions.extend(self._check_ai_service())
        actions.extend(self._check_log_size())
        actions.extend(self._check_memory_integrity())
        actions.extend(self._check_storage_writable())
        return actions
    
    # ===== AIサービス復旧 =====
    
    def _check_ai_service(self) -> List[Dict]:
        """AIプロセス停止時の自動再起動"""
        actions = []
        try:
            r = subprocess.run(
                ["systemctl", "is-active", "autonomous-ai.service"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout.strip() != "active":
                actions.append(self._restart_ai_service())
        except Exception as e:
            actions.append({"action": "ai_check", "success": False, "error": str(e)})
        return actions
    
    def _restart_ai_service(self) -> Dict:
        """AIサービスを再起動"""
        try:
            subprocess.run(
                ["systemctl", "restart", "autonomous-ai.service"],
                timeout=30
            )
            self._log_recovery("ai_restart", "AIサービスを自動再起動しました")
            return {"action": "ai_restart", "success": True, "message": "AI自動再起動完了"}
        except Exception as e:
            self._log_recovery("ai_restart_fail", str(e))
            return {"action": "ai_restart", "success": False, "error": str(e)}
    
    # ===== ログ自動圧縮 =====
    
    def _check_log_size(self) -> List[Dict]:
        """7日超ログを自動圧縮"""
        actions = []
        cutoff = datetime.now() - timedelta(days=7)
        
        try:
            for log_file in glob.glob(os.path.join(self.LOG_DIR, "*.log")):
                path = Path(log_file)
                if path.name == "agent.log":
                    # 現行ログはサイズチェックのみ
                    if path.stat().st_size > 50 * 1024 * 1024:  # 50MB超
                        actions.append(self._rotate_log(path))
                    continue
                
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    actions.append(self._compress_log(path))
        except Exception as e:
            actions.append({"action": "log_check", "success": False, "error": str(e)})
        
        return actions
    
    def _compress_log(self, path: Path) -> Dict:
        """ログファイルをgz圧縮"""
        try:
            gz_path = str(path) + ".gz"
            with open(path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(path)
            self._log_recovery("log_compress", f"圧縮: {path.name}")
            return {"action": "log_compress", "success": True, "file": path.name}
        except Exception as e:
            return {"action": "log_compress", "success": False, "error": str(e)}
    
    def _rotate_log(self, path: Path) -> Dict:
        """ログローテーション"""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated = path.parent / f"{path.stem}_{ts}.log"
            shutil.move(str(path), str(rotated))
            path.touch()  # 空ファイル再作成
            self._compress_log(rotated)
            self._log_recovery("log_rotate", f"ローテーション: {path.name}")
            return {"action": "log_rotate", "success": True, "file": path.name}
        except Exception as e:
            return {"action": "log_rotate", "success": False, "error": str(e)}
    
    # ===== Memory整合性 =====
    
    def _check_memory_integrity(self) -> List[Dict]:
        """memory破損チェック＆再生成"""
        actions = []
        memory_dir = Path(self.MEMORY_DIR)
        
        if not memory_dir.exists():
            memory_dir.mkdir(parents=True, exist_ok=True)
            actions.append({"action": "memory_dir_create", "success": True})
        
        # index.json チェック
        index_path = memory_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except (json.JSONDecodeError, ValueError):
                # 破損 → 再生成
                actions.append(self._regenerate_index(index_path, memory_dir))
        
        # 0バイトファイル検出
        for f in memory_dir.rglob("*"):
            if f.is_file() and f.stat().st_size == 0 and f.suffix in ('.json', '.txt', '.jsonl'):
                actions.append({
                    "action": "zero_byte_detected",
                    "file": str(f),
                    "success": True,
                    "message": f"0バイトファイル検出: {f.name}"
                })
                self._log_recovery("zero_byte", f"検出: {f}")
        
        return actions
    
    def _regenerate_index(self, index_path: Path, memory_dir: Path) -> Dict:
        """インデックスを再生成"""
        try:
            topics_dir = memory_dir / "topics"
            index = {"topics": {}, "total_memories": 0}
            
            if topics_dir.exists():
                for topic_file in topics_dir.glob("*.txt"):
                    topic = topic_file.stem
                    index["topics"][topic] = {
                        "filename": topic_file.name,
                        "updated": datetime.fromtimestamp(topic_file.stat().st_mtime).isoformat(),
                        "size": topic_file.stat().st_size
                    }
                    index["total_memories"] += 1
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
            
            self._log_recovery("index_regen", f"インデックス再生成: {index['total_memories']}件")
            return {"action": "index_regen", "success": True}
        except Exception as e:
            return {"action": "index_regen", "success": False, "error": str(e)}
    
    # ===== ストレージ書込み隔離 =====
    
    def _check_storage_writable(self) -> List[Dict]:
        """書込みテスト＆隔離"""
        actions = []
        test_file = os.path.join(self.BASE_DIR, ".write_test")
        
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception:
            # 書込み不可 → フォールバック隔離
            os.makedirs(self.FALLBACK_DIR, exist_ok=True)
            self._log_recovery("storage_isolate", f"書込み隔離: {self.FALLBACK_DIR}")
            actions.append({
                "action": "storage_isolate",
                "success": True,
                "message": f"メインストレージ書込み不可。{self.FALLBACK_DIR}に隔離。"
            })
        
        return actions
    
    def _log_recovery(self, action: str, detail: str):
        """復旧ログ"""
        try:
            with open(self.RECOVERY_LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "action": action,
                    "detail": detail,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


def main():
    """Watchdogとして常駐"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchdog", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    
    fs = FailSafe()
    
    if args.watchdog:
        print("FailSafe Watchdog 起動")
        while True:
            actions = fs.check_and_recover()
            for a in actions:
                print(f"[FailSafe] {a}")
            time.sleep(args.interval)
    else:
        actions = fs.check_and_recover()
        for a in actions:
            print(f"[FailSafe] {a}")


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
