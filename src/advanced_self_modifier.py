#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高度な自己進化モジュール
複数ファイルにまたがる修正、Git連携、自動テスト実行
"""

import os
import json
import logging
import subprocess
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from openai import OpenAI


class AdvancedSelfModifier:
    """高度な自己進化クラス"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        project_dir: str = "/home/pi/autonomous_ai",
        backup_dir: str = "/home/pi/autonomous_ai/backups",
        git_enabled: bool = True
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            project_dir: プロジェクトディレクトリ
            backup_dir: バックアップディレクトリ
            git_enabled: Git連携を有効にするか
        """
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.project_dir = Path(project_dir)
        self.backup_dir = Path(backup_dir)
        self.git_enabled = git_enabled
        
        # ディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Git初期化
        if self.git_enabled:
            self._init_git()
        
        # 修正履歴
        self.history_file = self.project_dir / "self_modification_history.json"
        self.history = self._load_history()
        
        self.logger.info("高度な自己進化システムを初期化しました")
    
    def _init_git(self):
        """Git初期化"""
        try:
            # Gitリポジトリが存在するか確認
            git_dir = self.project_dir / ".git"
            
            if not git_dir.exists():
                self.logger.info("Gitリポジトリを初期化します")
                subprocess.run(
                    ["git", "init"],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
                
                # .gitignoreを作成
                gitignore_path = self.project_dir / ".gitignore"
                if not gitignore_path.exists():
                    with open(gitignore_path, 'w') as f:
                        f.write("__pycache__/\n*.pyc\n*.log\n.env\nbackups/\nvector_db/\n")
                
                # 初回コミット
                subprocess.run(["git", "add", "."], cwd=self.project_dir, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
            
            self.logger.info("Gitリポジトリが利用可能です")
        
        except Exception as e:
            self.logger.error(f"Git初期化エラー: {e}")
            self.git_enabled = False
    
    def _load_history(self) -> List[Dict]:
        """修正履歴を読み込み"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"履歴読み込みエラー: {e}")
        
        return []
    
    def _save_history(self):
        """修正履歴を保存"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"履歴保存エラー: {e}")
    
    def analyze_codebase(self, target_files: Optional[List[Path]] = None) -> Dict:
        """
        コードベース全体を解析
        
        Args:
            target_files: 対象ファイルリスト（Noneの場合は全ファイル）
            
        Returns:
            解析結果
        """
        if target_files is None:
            target_files = list(self.project_dir.rglob("*.py"))
        
        codebase_info = {
            "files": [],
            "total_lines": 0,
            "dependencies": {}
        }
        
        for file_path in target_files:
            if "__pycache__" in str(file_path) or "test_" in file_path.name:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    lines = len(code.split('\n'))
                
                codebase_info["files"].append({
                    "path": str(file_path.relative_to(self.project_dir)),
                    "lines": lines,
                    "code": code[:1000]  # 最初の1000文字のみ
                })
                
                codebase_info["total_lines"] += lines
            
            except Exception as e:
                self.logger.error(f"ファイル読み込みエラー: {file_path}: {e}")
        
        return codebase_info
    
    def plan_modifications(
        self,
        request: str,
        codebase_info: Dict
    ) -> Optional[Dict]:
        """
        修正計画を立案
        
        Args:
            request: 修正リクエスト
            codebase_info: コードベース情報
            
        Returns:
            修正計画
        """
        prompt = f"""あなたはPythonプロジェクトのリファクタリング専門家です。
以下のリクエストに基づいて、複数ファイルにまたがる修正計画を立案してください。

# リクエスト
{request}

# コードベース情報
総ファイル数: {len(codebase_info['files'])}
総行数: {codebase_info['total_lines']}

ファイル一覧:
{json.dumps([f['path'] for f in codebase_info['files']], indent=2, ensure_ascii=False)}

# 出力形式
以下のJSON形式で修正計画を出力してください:
{{
  "summary": "修正の概要",
  "risk_level": "low/medium/high",
  "files_to_modify": [
    {{
      "path": "src/example.py",
      "reason": "修正理由",
      "changes": "具体的な変更内容"
    }}
  ],
  "dependencies": ["必要な依存関係"],
  "test_required": true/false
}}
"""
        
        try:
            self.logger.info("修正計画を立案中...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたはPythonプロジェクトのリファクタリング専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            plan_text = response.choices[0].message.content
            
            # JSONを抽出
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
            
            plan = json.loads(plan_text)
            self.logger.info(f"修正計画を立案しました: {plan['summary']}")
            
            return plan
        
        except Exception as e:
            self.logger.error(f"修正計画立案エラー: {e}")
            return None
    
    def execute_modifications(self, plan: Dict) -> bool:
        """
        修正計画を実行
        
        Args:
            plan: 修正計画
            
        Returns:
            成功したかどうか
        """
        # リスクレベルチェック
        if plan.get("risk_level") == "high":
            self.logger.warning("高リスクの修正です。実行を中止します。")
            return False
        
        # Gitコミット（修正前）
        if self.git_enabled:
            self._git_commit("Before self-modification")
        
        # バックアップ作成
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        modified_files = []
        
        try:
            # 各ファイルを修正
            for file_info in plan.get("files_to_modify", []):
                file_path = self.project_dir / file_info["path"]
                
                if not file_path.exists():
                    self.logger.warning(f"ファイルが見つかりません: {file_path}")
                    continue
                
                # バックアップ
                backup_file = backup_path / file_info["path"]
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_code = f.read()
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(original_code)
                
                # 修正コードを生成
                modified_code = self._generate_modified_code(
                    original_code,
                    file_info["changes"]
                )
                
                if modified_code:
                    # ファイルに書き込み
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(modified_code)
                    
                    modified_files.append(str(file_path))
                    self.logger.info(f"ファイルを修正しました: {file_path}")
            
            # テスト実行
            if plan.get("test_required", False):
                test_result = self._run_tests()
                if not test_result:
                    self.logger.error("テストが失敗しました。ロールバックします。")
                    self._rollback(backup_path)
                    return False
            
            # Gitコミット（修正後）
            if self.git_enabled:
                self._git_commit(f"Self-modification: {plan['summary']}")
            
            # 履歴に記録
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "summary": plan["summary"],
                "risk_level": plan["risk_level"],
                "modified_files": modified_files,
                "backup_path": str(backup_path),
                "success": True
            })
            self._save_history()
            
            self.logger.info("修正が完了しました")
            return True
        
        except Exception as e:
            self.logger.error(f"修正実行エラー: {e}")
            self._rollback(backup_path)
            return False
    
    def _generate_modified_code(self, original_code: str, changes: str) -> Optional[str]:
        """
        修正コードを生成
        
        Args:
            original_code: 元のコード
            changes: 変更内容
            
        Returns:
            修正されたコード
        """
        prompt = f"""以下のPythonコードを修正してください。

# 元のコード
```python
{original_code}
```

# 変更内容
{changes}

# 要件
1. 元のコードの機能を維持する
2. コードスタイルを統一する
3. コメントとdocstringを適切に更新する
4. 完全なコードのみを出力（説明不要）
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたはPythonコード修正の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            modified_code = response.choices[0].message.content
            
            # コードブロックから抽出
            if "```python" in modified_code:
                modified_code = modified_code.split("```python")[1].split("```")[0].strip()
            elif "```" in modified_code:
                modified_code = modified_code.split("```")[1].split("```")[0].strip()
            
            return modified_code
        
        except Exception as e:
            self.logger.error(f"コード生成エラー: {e}")
            return None
    
    def _run_tests(self) -> bool:
        """テストを実行"""
        try:
            result = subprocess.run(
                ["pytest", str(self.project_dir / "tests"), "-v"],
                capture_output=True,
                timeout=300
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"テスト実行エラー: {e}")
            return False
    
    def _rollback(self, backup_path: Path):
        """ロールバック"""
        try:
            self.logger.info("ロールバック中...")
            
            for backup_file in backup_path.rglob("*"):
                if backup_file.is_file():
                    relative_path = backup_file.relative_to(backup_path)
                    target_file = self.project_dir / relative_path
                    
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        original_code = f.read()
                    
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(original_code)
            
            self.logger.info("ロールバックが完了しました")
        
        except Exception as e:
            self.logger.error(f"ロールバックエラー: {e}")
    
    def _git_commit(self, message: str):
        """Gitコミット"""
        try:
            subprocess.run(["git", "add", "."], cwd=self.project_dir, check=True)
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )
            self.logger.info(f"Gitコミット: {message}")
        except Exception as e:
            self.logger.warning(f"Gitコミットエラー: {e}")
    
    def self_improve(self, request: str) -> bool:
        """
        自己改善を実行
        
        Args:
            request: 改善リクエスト
            
        Returns:
            成功したかどうか
        """
        self.logger.info(f"自己改善を開始: {request}")
        
        # コードベース解析
        codebase_info = self.analyze_codebase()
        
        # 修正計画立案
        plan = self.plan_modifications(request, codebase_info)
        if not plan:
            return False
        
        # 修正実行
        return self.execute_modifications(plan)


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEYが設定されていません")
        return
    
    modifier = AdvancedSelfModifier(api_key=api_key)
    
    # 自己改善テスト
    success = modifier.self_improve("すべてのログメッセージを日本語に統一してください")
    
    if success:
        print("自己改善が成功しました")
    else:
        print("自己改善が失敗しました")


if __name__ == "__main__":
    main()
