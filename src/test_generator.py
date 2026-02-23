#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動テスト生成モジュール
Pythonコードから自動的にユニットテストを生成
"""

import os
import ast
import logging
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI


class TestGenerator:
    """自動テスト生成クラス"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        test_dir: str = "/home/pi/autonomous_ai/tests"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            test_dir: テストディレクトリ
        """
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.test_dir = Path(test_dir)
        
        # テストディレクトリ作成
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("自動テスト生成システムを初期化しました")
    
    def analyze_code(self, file_path: Path) -> Dict:
        """
        Pythonコードを解析
        
        Args:
            file_path: ファイルパス
            
        Returns:
            解析結果
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # ASTでパース
            tree = ast.parse(code)
            
            # 関数とクラスを抽出
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "lineno": node.lineno
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                "name": item.name,
                                "args": [arg.arg for arg in item.args.args]
                            })
                    
                    classes.append({
                        "name": node.name,
                        "methods": methods,
                        "lineno": node.lineno
                    })
            
            return {
                "file_path": str(file_path),
                "functions": functions,
                "classes": classes,
                "code": code
            }
        
        except Exception as e:
            self.logger.error(f"コード解析エラー: {e}")
            return {}
    
    def generate_test(self, code_info: Dict) -> Optional[str]:
        """
        テストコードを生成
        
        Args:
            code_info: コード情報
            
        Returns:
            テストコード
        """
        if not code_info:
            return None
        
        # プロンプト構築
        prompt = self._build_prompt(code_info)
        
        try:
            self.logger.info("GPT-4を使ってテストコードを生成中...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはPythonのユニットテスト生成の専門家です。pytestを使った高品質なテストコードを生成してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            test_code = response.choices[0].message.content
            
            # コードブロックから抽出
            if "```python" in test_code:
                test_code = test_code.split("```python")[1].split("```")[0].strip()
            elif "```" in test_code:
                test_code = test_code.split("```")[1].split("```")[0].strip()
            
            self.logger.info("テストコードを生成しました")
            return test_code
        
        except Exception as e:
            self.logger.error(f"テスト生成エラー: {e}")
            return None
    
    def _build_prompt(self, code_info: Dict) -> str:
        """
        プロンプトを構築
        
        Args:
            code_info: コード情報
            
        Returns:
            プロンプト
        """
        prompt = f"""以下のPythonコードに対して、pytestを使った包括的なユニットテストを生成してください。

# 元のコード
```python
{code_info['code']}
```

# 要件
1. すべての関数とメソッドに対してテストを作成
2. 正常系と異常系の両方をテスト
3. エッジケースも考慮
4. モックが必要な場合は unittest.mock を使用
5. テストは独立して実行可能にする
6. docstringで各テストの目的を説明

# 出力形式
完全なPythonテストコードのみを出力してください。説明は不要です。
"""
        return prompt
    
    def save_test(self, test_code: str, original_file: Path) -> Optional[Path]:
        """
        テストコードを保存
        
        Args:
            test_code: テストコード
            original_file: 元のファイル
            
        Returns:
            保存先パス
        """
        try:
            # テストファイル名を生成
            test_filename = f"test_{original_file.stem}.py"
            test_path = self.test_dir / test_filename
            
            # テストコードを保存
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            self.logger.info(f"テストコードを保存しました: {test_path}")
            return test_path
        
        except Exception as e:
            self.logger.error(f"テスト保存エラー: {e}")
            return None
    
    def generate_test_for_file(self, file_path: Path) -> Optional[Path]:
        """
        ファイルに対してテストを生成
        
        Args:
            file_path: ファイルパス
            
        Returns:
            テストファイルパス
        """
        self.logger.info(f"テスト生成開始: {file_path}")
        
        # コード解析
        code_info = self.analyze_code(file_path)
        if not code_info:
            return None
        
        # テスト生成
        test_code = self.generate_test(code_info)
        if not test_code:
            return None
        
        # テスト保存
        test_path = self.save_test(test_code, file_path)
        return test_path
    
    def generate_tests_for_directory(
        self,
        src_dir: Path,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Path]:
        """
        ディレクトリ内のすべてのPythonファイルに対してテストを生成
        
        Args:
            src_dir: ソースディレクトリ
            exclude_patterns: 除外パターン
            
        Returns:
            生成されたテストファイルのリスト
        """
        if not exclude_patterns:
            exclude_patterns = ["__init__.py", "test_*.py"]
        
        generated_tests = []
        
        # Pythonファイルを検索
        for py_file in src_dir.rglob("*.py"):
            # 除外パターンチェック
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue
            
            # テスト生成
            test_path = self.generate_test_for_file(py_file)
            if test_path:
                generated_tests.append(test_path)
        
        self.logger.info(f"{len(generated_tests)}個のテストファイルを生成しました")
        return generated_tests
    
    def run_tests(self) -> Dict:
        """
        生成されたテストを実行
        
        Returns:
            実行結果
        """
        import subprocess
        
        try:
            self.logger.info("テストを実行中...")
            
            result = subprocess.run(
                ["pytest", str(self.test_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        
        except Exception as e:
            self.logger.error(f"テスト実行エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }


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
    
    generator = TestGenerator(api_key=api_key)
    
    # テスト対象ファイル
    test_file = Path("/home/pi/autonomous_ai/src/memory.py")
    
    if test_file.exists():
        # テスト生成
        test_path = generator.generate_test_for_file(test_file)
        
        if test_path:
            print(f"テストを生成しました: {test_path}")
            
            # テスト実行
            result = generator.run_tests()
            print(f"\nテスト実行結果: {'成功' if result['success'] else '失敗'}")
            print(result.get('stdout', ''))
    else:
        print(f"ファイルが見つかりません: {test_file}")


if __name__ == "__main__":
    main()
