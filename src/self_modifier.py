#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自己コード修正モジュール
AIが自身のソースコードを読み込み、バグ修正や機能追加を行う
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from openai import OpenAI


class SelfModifier:
    """自己コード修正クラス"""
    
    SYSTEM_PROMPT = """あなたはPythonコードの専門家であり、自律型AIシステムの自己改善エージェントです。

# あなたの役割
1. 既存のソースコードを読み込み、理解する
2. バグを発見し、修正する
3. 新しい機能を追加する
4. コードの品質を向上させる

# 重要なルール
1. 既存の機能を壊さないこと
2. 変更前に必ずバックアップを作成すること
3. 変更内容を詳細にログに記録すること
4. テストコードも同時に作成すること
5. セキュリティリスクを生じさせないこと

# 出力JSONスキーマ
{
  "analysis": "コードの分析結果（日本語）",
  "issues": ["発見した問題点のリスト"],
  "improvements": ["改善提案のリスト"],
  "modifications": [
    {
      "file": "修正対象ファイル名",
      "reason": "修正理由",
      "original_code": "元のコード（該当部分のみ）",
      "modified_code": "修正後のコード",
      "line_start": 開始行番号,
      "line_end": 終了行番号
    }
  ],
  "risk_level": "low/medium/high",
  "recommendation": "実行推奨度（実行推奨/要確認/非推奨）"
}

必ずJSON形式で応答してください。
"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        source_dir: str = "/home/pi/autonomous_ai/src",
        backup_dir: str = "/home/pi/autonomous_ai/backups",
        log_dir: str = "/home/pi/autonomous_ai/logs"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            source_dir: ソースコードディレクトリ
            backup_dir: バックアップディレクトリ
            log_dir: ログディレクトリ
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(backup_dir)
        self.log_dir = Path(log_dir)
        
        # ディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.modification_log = self.log_dir / "self_modifications.jsonl"
    
    def log(self, message: str, level: str = "INFO"):
        """
        ログを記録
        
        Args:
            message: ログメッセージ
            level: ログレベル
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        log_file = self.log_dir / "self_modifier.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def get_source_files(self) -> List[Path]:
        """
        ソースファイル一覧を取得
        
        Returns:
            Pythonファイルのリスト
        """
        return list(self.source_dir.glob("*.py"))
    
    def read_source_code(self, file_path: Path) -> Optional[str]:
        """
        ソースコードを読み込み
        
        Args:
            file_path: ファイルパス
            
        Returns:
            ソースコード（失敗時はNone）
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.log(f"ファイル読み込みエラー: {file_path} - {e}", "ERROR")
            return None
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        ファイルのバックアップを作成
        
        Args:
            file_path: バックアップ対象ファイル
            
        Returns:
            バックアップファイルのパス（失敗時はNone）
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            self.log(f"バックアップ作成: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            self.log(f"バックアップ作成エラー: {e}", "ERROR")
            return None
    
    def analyze_code(self, file_path: Path, specific_request: Optional[str] = None) -> Optional[Dict]:
        """
        コードを分析
        
        Args:
            file_path: 分析対象ファイル
            specific_request: 特定のリクエスト（例: 「バグを探して」「パフォーマンスを改善して」）
            
        Returns:
            分析結果（失敗時はNone）
        """
        try:
            code = self.read_source_code(file_path)
            if not code:
                return None
            
            # コンテキスト構築
            context = f"""# ファイル名
{file_path.name}

# ソースコード
```python
{code}
```

# 分析リクエスト
"""
            if specific_request:
                context += f"{specific_request}\n"
            else:
                context += "このコードを分析し、バグや改善点を見つけてください。\n"
            
            context += "\n上記のコードを分析し、JSON形式で結果を出力してください。"
            
            self.log(f"コード分析開始: {file_path.name}")
            
            # GPT呼び出し
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                temperature=0.3,  # より正確な分析のため低めに設定
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            
            # JSON解析
            analysis = self._parse_json_response(content)
            
            if analysis:
                self.log(f"分析完了: {len(analysis.get('issues', []))}個の問題、{len(analysis.get('improvements', []))}個の改善提案")
                return analysis
            else:
                self.log("分析結果のパースに失敗", "ERROR")
                return None
            
        except Exception as e:
            self.log(f"コード分析エラー: {e}", "ERROR")
            return None
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        GPTの応答をJSONとしてパース
        
        Args:
            response: GPTの応答
            
        Returns:
            パースされたJSON（失敗時はNone）
        """
        try:
            # JSON部分を抽出
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            self.log(f"JSON解析エラー: {e}", "ERROR")
            return None
    
    def apply_modifications(
        self,
        file_path: Path,
        modifications: List[Dict],
        create_backup: bool = True
    ) -> bool:
        """
        修正を適用
        
        Args:
            file_path: 修正対象ファイル
            modifications: 修正内容のリスト
            create_backup: バックアップを作成するか
            
        Returns:
            成功したらTrue
        """
        try:
            # バックアップ作成
            if create_backup:
                backup_path = self.create_backup(file_path)
                if not backup_path:
                    self.log("バックアップ作成に失敗したため、修正を中止します", "ERROR")
                    return False
            
            # ファイル読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 修正を適用（後ろから適用して行番号のズレを防ぐ）
            sorted_mods = sorted(modifications, key=lambda x: x.get('line_start', 0), reverse=True)
            
            for mod in sorted_mods:
                line_start = mod.get('line_start', 0) - 1  # 0-indexed
                line_end = mod.get('line_end', 0)
                modified_code = mod.get('modified_code', '')
                
                if line_start < 0 or line_end > len(lines):
                    self.log(f"無効な行番号: {line_start+1}-{line_end}", "WARNING")
                    continue
                
                # 修正を適用
                lines[line_start:line_end] = [modified_code + '\n']
                
                self.log(f"修正適用: 行 {line_start+1}-{line_end}")
            
            # ファイルに書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            self.log(f"修正完了: {file_path.name}")
            
            # 修正ログを記録
            self._log_modification(file_path, modifications)
            
            return True
            
        except Exception as e:
            self.log(f"修正適用エラー: {e}", "ERROR")
            return False
    
    def _log_modification(self, file_path: Path, modifications: List[Dict]):
        """
        修正履歴を記録
        
        Args:
            file_path: 修正したファイル
            modifications: 修正内容
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "file": str(file_path),
                "modifications": modifications
            }
            
            with open(self.modification_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            self.log(f"修正履歴記録エラー: {e}", "ERROR")
    
    def self_improve(
        self,
        target_file: Optional[str] = None,
        specific_request: Optional[str] = None,
        auto_apply: bool = False
    ) -> Dict:
        """
        自己改善を実行
        
        Args:
            target_file: 対象ファイル名（指定しない場合は全ファイル）
            specific_request: 特定のリクエスト
            auto_apply: 自動で修正を適用するか（Falseの場合は分析のみ）
            
        Returns:
            実行結果
        """
        result = {
            "analyzed_files": 0,
            "issues_found": 0,
            "improvements_suggested": 0,
            "modifications_applied": 0,
            "files_modified": []
        }
        
        try:
            # 対象ファイルを決定
            if target_file:
                files = [self.source_dir / target_file]
            else:
                files = self.get_source_files()
            
            for file_path in files:
                if not file_path.exists():
                    self.log(f"ファイルが見つかりません: {file_path}", "WARNING")
                    continue
                
                # コード分析
                analysis = self.analyze_code(file_path, specific_request)
                
                if not analysis:
                    continue
                
                result["analyzed_files"] += 1
                result["issues_found"] += len(analysis.get("issues", []))
                result["improvements_suggested"] += len(analysis.get("improvements", []))
                
                # リスクレベルをチェック
                risk_level = analysis.get("risk_level", "high")
                recommendation = analysis.get("recommendation", "非推奨")
                
                self.log(f"リスクレベル: {risk_level}, 推奨: {recommendation}")
                
                # 修正を適用するか判断
                modifications = analysis.get("modifications", [])
                
                if modifications and auto_apply:
                    if risk_level == "low" and "実行推奨" in recommendation:
                        # 安全と判断された場合のみ自動適用
                        if self.apply_modifications(file_path, modifications):
                            result["modifications_applied"] += len(modifications)
                            result["files_modified"].append(str(file_path))
                    else:
                        self.log(f"リスクが高いため自動適用をスキップ: {file_path.name}", "WARNING")
                
            return result
            
        except Exception as e:
            self.log(f"自己改善実行エラー: {e}", "ERROR")
            return result
    
    def rollback(self, backup_path: Path, target_path: Path) -> bool:
        """
        バックアップからロールバック
        
        Args:
            backup_path: バックアップファイル
            target_path: 復元先ファイル
            
        Returns:
            成功したらTrue
        """
        try:
            shutil.copy2(backup_path, target_path)
            self.log(f"ロールバック完了: {target_path.name}")
            return True
            
        except Exception as e:
            self.log(f"ロールバックエラー: {e}", "ERROR")
            return False


# テスト用
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    modifier = SelfModifier(
        api_key=os.getenv("OPENAI_API_KEY"),
        source_dir="/tmp/test_src",
        backup_dir="/tmp/test_backup"
    )
    
    # テストファイルを作成
    os.makedirs("/tmp/test_src", exist_ok=True)
    test_file = Path("/tmp/test_src/test.py")
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""def add(a, b):
    # バグ: 引数の型チェックがない
    return a + b

def divide(a, b):
    # バグ: ゼロ除算のチェックがない
    return a / b
""")
    
    print("=== 自己改善テスト ===")
    result = modifier.self_improve(
        target_file="test.py",
        specific_request="バグを見つけて修正してください",
        auto_apply=False  # テストなので自動適用はしない
    )
    
    print(f"\n結果: {result}")
