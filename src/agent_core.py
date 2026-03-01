<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIコアエージェント
自律的な思考・判断・実行ループを管理
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Optional
from openai import OpenAI

from memory import MemoryManager
from executor import CommandExecutor


class AutonomousAgent:
    """自律型AIエージェント"""
    
    SYSTEM_PROMPT = """あなたはUbuntu/Linux上で動作する自律型リサーチエージェントです。

# 重要なルール
1. 思考は内部で行い、出力は常に単一のJSONオブジェクトのみ
2. JSONスキーマに厳密に従うこと
3. コマンドは必要最小限のみ実行
4. 危険な操作は絶対に禁止
5. エラー時は自己修正して次ステップへ
6. 長期的に有益な成果を優先

# 出力JSONスキーマ
{
  "say": "オペレーターへの短いメッセージ(日本語)",
  "cmd": ["実行するシェルコマンドの配列"],
  "memory_write": [{"filename": "topic_yyyymmdd_hhmmss.txt", "content": "保存する内容"}],
  "diary_append": "日誌への追記内容",
  "next_goal": "次ターンの目標",
  "self_improve": {"enabled": false, "target_file": "", "request": ""}
}

# 自己コード修正機能
- self_improveフィールドを使用して、自身のソースコードを改善できます
- enabled: trueにすると自己改善を実行します
- target_file: 修正対象ファイル名（例: "memory.py"）、空の場合は全ファイル
- request: 具体的なリクエスト（例: "バグを修正して」「パフォーマンスを改善して"）
- 自己改善は慎重に行い、リスクが高い場合は実行を控えてください

# 行動指針
- 常に目標達成に向けて行動する
- 情報収集と分析を重視する
- 実行前に計画を立てる
- 結果を記録し、学習する
- 無駄な繰り返しを避ける

# 禁止事項
- ファイルシステムの破壊
- 無限ループ
- 大量のネットワークトラフィック
- 個人情報の不正取得
- システムの不安定化

必ずJSON形式で応答してください。それ以外の出力は禁止です。
"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        memory_dir: str = "/home/pi/autonomous_ai/memory",
        log_dir: str = "/home/pi/autonomous_ai/logs"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            memory_dir: メモリディレクトリ
            log_dir: ログディレクトリ
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        self.memory = MemoryManager(base_dir=memory_dir)
        self.executor = CommandExecutor()
        
        # ログディレクトリ作成
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "agent.log")
        
        # 状態管理
        self.current_goal = "システムの状態を確認し、有益なタスクを見つける"
        self.iteration_count = 0
        self.last_execution_time = None
        
        # ユーザー目標の優先制御
        self._user_goal_active = False  # ユーザーが設定した目標が有効か
        self._goal_history_path = os.path.join(memory_dir, "goal_history.jsonl")
        
        # 実行履歴（通知用）
        self.last_commands = []
        self.last_results = []
        self.last_thinking = ""
        self.last_action = {}
    
    def update_goal(self, new_goal: str, source: str = "user"):
        """
        外部から目標を更新する
        
        Args:
            new_goal: 新しい目標
            source: 更新元（"user" or "system"）
        """
        old_goal = self.current_goal
        
        if source == "user":
            # 旧目標を履歴に退避
            try:
                os.makedirs(os.path.dirname(self._goal_history_path), exist_ok=True)
                with open(self._goal_history_path, 'a', encoding='utf-8') as f:
                    import json as _json
                    f.write(_json.dumps({
                        "old_goal": old_goal,
                        "new_goal": new_goal,
                        "reason": "REPLACED_BY_USER",
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False) + "\n")
            except Exception as e:
                self.log(f"目標履歴の保存に失敗: {e}", "WARNING")
            
            # 内部状態リセット
            self.last_commands = []
            self.last_results = []
            self.last_action = {}
            self.last_thinking = ""
            
            # ユーザー目標フラグを有効化
            self._user_goal_active = True
        
        self.current_goal = new_goal
        self.log(f"目標更新 [{source}]: {old_goal} → {new_goal}", "INFO")
    
    def log(self, message: str, level: str = "INFO"):
        """
        ログを記録
        
        Args:
            message: ログメッセージ
            level: ログレベル
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # ファイルに書き込み
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # コンソールにも出力
        print(log_entry.strip())
    
    def build_context(self) -> str:
        """
        現在のコンテキストを構築
        
        Returns:
            GPTに送信するコンテキスト
        """
        context = f"""# 現在の状態

## 日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 現在の目標
{self.current_goal}

## 実行回数
{self.iteration_count}回目

## 最近の日誌
{self.memory.read_diary(lines=20)}

## メモリサマリー
{self.memory.get_summary()}

## 最近のメモリ
"""
        # 最近のメモリを追加
        recent_memories = self.memory.get_recent_memories(count=3)
        for mem in recent_memories:
            content = self.memory.get_memory_content(mem['filename'])
            if content:
                context += f"\n### {mem['filename']}\n{content[:300]}...\n"
        
        context += "\n# 指示\n上記の情報を基に、次に実行すべきアクションをJSON形式で出力してください。"
        
        return context
    
    def parse_gpt_response(self, response: str) -> Optional[Dict]:
        """
        GPTの応答をパース
        
        Args:
            response: GPTの応答テキスト
            
        Returns:
            パースされたJSON（失敗時はNone）
        """
        try:
            # JSON部分を抽出（```json ... ``` で囲まれている場合に対応）
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
            
            # JSONパース
            data = json.loads(json_str)
            
            # スキーマ検証
            required_keys = ["say", "cmd", "memory_write", "diary_append", "next_goal"]
            for key in required_keys:
                if key not in data:
                    self.log(f"JSON検証エラー: {key}が見つかりません", "ERROR")
                    return None
            
            return data
            
        except json.JSONDecodeError as e:
            self.log(f"JSON解析エラー: {e}", "ERROR")
            self.log(f"応答内容: {response}", "ERROR")
            return None
        except Exception as e:
            self.log(f"予期しないエラー: {e}", "ERROR")
            return None
    
    def call_gpt(self, context: str) -> Optional[Dict]:
        """
        GPTを呼び出し
        
        Args:
            context: コンテキスト
            
        Returns:
            パースされた応答（失敗時はNone）
        """
        try:
            self.log("GPT-4を呼び出し中...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            self.log(f"GPT応答を受信: {len(content)}文字")
            
            # 応答をパース
            parsed = self.parse_gpt_response(content)
            
            if parsed:
                self.log(f"GPT指示: {parsed['say']}")
                return parsed
            else:
                self.log("GPT応答のパースに失敗", "ERROR")
                return None
            
        except Exception as e:
            self.log(f"GPT呼び出しエラー: {e}", "ERROR")
            return None
    
    def execute_action(self, action: Dict) -> Dict:
        """
        アクションを実行
        
        Args:
            action: 実行するアクション
            
        Returns:
            実行結果
        """
        result = {
            "say": action.get("say", ""),
            "cmd_results": [],
            "memory_saved": False,
            "diary_saved": False
        }
        
        # コマンド実行
        commands = action.get("cmd", [])
        if commands:
            self.log(f"{len(commands)}個のコマンドを実行")
            for cmd in commands:
                self.log(f"実行: {cmd}")
                cmd_result = self.executor.execute(cmd)
                result["cmd_results"].append({
                    "command": cmd,
                    "success": cmd_result["success"],
                    "output": cmd_result.get("stdout", ""),
                    "error": cmd_result.get("stderr", "") or cmd_result.get("error", "")
                })
        
        # メモリ保存
        memory_writes = action.get("memory_write", [])
        if memory_writes:
            for mem in memory_writes:
                filename = mem.get("filename", "")
                content = mem.get("content", "")
                if filename and content:
                    success = self.memory.write_memory(filename, content)
                    result["memory_saved"] = success
                    self.log(f"メモリ保存: {filename} ({'成功' if success else '失敗'})")
        
        # 日誌追記
        diary_entry = action.get("diary_append", "")
        if diary_entry:
            success = self.memory.append_diary(diary_entry)
            result["diary_saved"] = success
            self.log(f"日誌追記: {'成功' if success else '失敗'}")
        
        # 次の目標を更新（ユーザー目標優先制御）
        next_goal = action.get("next_goal", "")
        if next_goal:
            if self._user_goal_active:
                # ユーザー目標が有効な間はGPTのnext_goalで上書きしない
                self.log(f"GPT提案の目標をスキップ（ユーザー目標優先）: {next_goal}")
                # ただしGPTが明らかに別の主題を提案 → ユーザー目標完了とみなす
                # （簡易判定: say に「完了」「達成」が含まれる場合）
                say_text = action.get("say", "")
                if any(kw in say_text for kw in ["完了", "達成", "終了", "完成", "done", "finished"]):
                    self.log("ユーザー目標完了を検出。GPT提案の目標に切替", "INFO")
                    self._user_goal_active = False
                    self.current_goal = next_goal
                    self.log(f"目標更新: {next_goal}")
            else:
                self.current_goal = next_goal
                self.log(f"目標更新: {next_goal}")
        
        # 自己改善機能
        self_improve = action.get("self_improve", {})
        if self_improve.get("enabled", False):
            self.log("自己改善機能を実行します", "WARNING")
            try:
                from self_modifier import SelfModifier
                
                modifier = SelfModifier(
                    api_key=self.client.api_key,
                    model=self.model
                )
                
                improve_result = modifier.self_improve(
                    target_file=self_improve.get("target_file") or None,
                    specific_request=self_improve.get("request") or None,
                    auto_apply=False  # 安全のため、分析のみ
                )
                
                result["self_improve_result"] = improve_result
                self.log(f"自己改善結果: {improve_result}")
                
            except Exception as e:
                self.log(f"自己改善エラー: {e}", "ERROR")
                result["self_improve_result"] = {"error": str(e)}
        
        return result
    
    def run_iteration(self) -> bool:
        """
        1回のイテレーションを実行
        
        Returns:
            成功したらTrue
        """
        self.iteration_count += 1
        self.log(f"=== イテレーション {self.iteration_count} 開始 ===")
        
        try:
            # コンテキスト構築
            context = self.build_context()
            
            # GPT呼び出し
            action = self.call_gpt(context)
            
            if not action:
                self.log("GPT呼び出しに失敗しました", "ERROR")
                return False
            
            # 実行履歴を保存（通知用）
            self.last_action = action
            self.last_thinking = action.get("say", "")
            self.last_commands = action.get("cmd", [])
            
            # アクション実行
            result = self.execute_action(action)
            
            # 実行結果を保存
            self.last_results = result.get("cmd_results", [])
            
            # 実行結果をログ
            self.log(f"実行結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            self.last_execution_time = datetime.now()
            
            return True
            
        except Exception as e:
            self.log(f"イテレーション実行エラー: {e}", "ERROR")
            return False
    
    def run_loop(self, interval: int = 30):
        """
        自律実行ループ
        
        Args:
            interval: イテレーション間隔（秒）
        """
        self.log("自律実行ループを開始します")
        self.memory.append_diary("エージェント起動")
        
        while True:
            try:
                # イテレーション実行
                success = self.run_iteration()
                
                if not success:
                    self.log("イテレーション失敗。リトライします。", "WARNING")
                
                # 待機
                self.log(f"{interval}秒待機中...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.log("ユーザーによる中断")
                self.memory.append_diary("エージェント停止（ユーザー中断）")
                break
            except Exception as e:
                self.log(f"予期しないエラー: {e}", "ERROR")
                self.memory.append_diary(f"エラー発生: {e}")
                time.sleep(interval)


# メイン実行
if __name__ == "__main__":
    # 環境変数からAPIキーを取得
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("エラー: OPENAI_API_KEYが設定されていません")
        exit(1)
    
    # エージェント起動
    agent = AutonomousAgent(
        api_key=api_key,
        model="gpt-4.1-mini",
        memory_dir="/home/pi/autonomous_ai/memory",
        log_dir="/home/pi/autonomous_ai/logs"
    )
    
    # 自律ループ開始
    agent.run_loop(interval=30)
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIコアエージェント
自律的な思考・判断・実行ループを管理
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Optional
from openai import OpenAI

from memory import MemoryManager
from executor import CommandExecutor


class AutonomousAgent:
    """自律型AIエージェント"""
    
    SYSTEM_PROMPT = """あなたはUbuntu/Linux上で動作する自律型リサーチエージェントです。

# 重要なルール
1. 思考は内部で行い、出力は常に単一のJSONオブジェクトのみ
2. JSONスキーマに厳密に従うこと
3. コマンドは必要最小限のみ実行
4. 危険な操作は絶対に禁止
5. エラー時は自己修正して次ステップへ
6. 長期的に有益な成果を優先

# 出力JSONスキーマ
{
  "say": "オペレーターへの短いメッセージ(日本語)",
  "cmd": ["実行するシェルコマンドの配列"],
  "memory_write": [{"filename": "topic_yyyymmdd_hhmmss.txt", "content": "保存する内容"}],
  "diary_append": "日誌への追記内容",
  "next_goal": "次ターンの目標",
  "self_improve": {"enabled": false, "target_file": "", "request": ""}
}

# 自己コード修正機能
- self_improveフィールドを使用して、自身のソースコードを改善できます
- enabled: trueにすると自己改善を実行します
- target_file: 修正対象ファイル名（例: "memory.py"）、空の場合は全ファイル
- request: 具体的なリクエスト（例: "バグを修正して」「パフォーマンスを改善して"）
- 自己改善は慎重に行い、リスクが高い場合は実行を控えてください

# 行動指針
- 常に目標達成に向けて行動する
- 情報収集と分析を重視する
- 実行前に計画を立てる
- 結果を記録し、学習する
- 無駄な繰り返しを避ける

# 禁止事項
- ファイルシステムの破壊
- 無限ループ
- 大量のネットワークトラフィック
- 個人情報の不正取得
- システムの不安定化

必ずJSON形式で応答してください。それ以外の出力は禁止です。
"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        memory_dir: str = "/home/pi/autonomous_ai/memory",
        log_dir: str = "/home/pi/autonomous_ai/logs"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            memory_dir: メモリディレクトリ
            log_dir: ログディレクトリ
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        self.memory = MemoryManager(base_dir=memory_dir)
        self.executor = CommandExecutor()
        
        # ログディレクトリ作成
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "agent.log")
        
        # 状態管理
        self.current_goal = "システムの状態を確認し、有益なタスクを見つける"
        self.iteration_count = 0
        self.last_execution_time = None
        
        # ユーザー目標の優先制御
        self._user_goal_active = False  # ユーザーが設定した目標が有効か
        self._goal_history_path = os.path.join(memory_dir, "goal_history.jsonl")
        
        # 実行履歴（通知用）
        self.last_commands = []
        self.last_results = []
        self.last_thinking = ""
        self.last_action = {}
    
    def update_goal(self, new_goal: str, source: str = "user"):
        """
        外部から目標を更新する
        
        Args:
            new_goal: 新しい目標
            source: 更新元（"user" or "system"）
        """
        old_goal = self.current_goal
        
        if source == "user":
            # 旧目標を履歴に退避
            try:
                os.makedirs(os.path.dirname(self._goal_history_path), exist_ok=True)
                with open(self._goal_history_path, 'a', encoding='utf-8') as f:
                    import json as _json
                    f.write(_json.dumps({
                        "old_goal": old_goal,
                        "new_goal": new_goal,
                        "reason": "REPLACED_BY_USER",
                        "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False) + "\n")
            except Exception as e:
                self.log(f"目標履歴の保存に失敗: {e}", "WARNING")
            
            # 内部状態リセット
            self.last_commands = []
            self.last_results = []
            self.last_action = {}
            self.last_thinking = ""
            
            # ユーザー目標フラグを有効化
            self._user_goal_active = True
        
        self.current_goal = new_goal
        self.log(f"目標更新 [{source}]: {old_goal} → {new_goal}", "INFO")
    
    def log(self, message: str, level: str = "INFO"):
        """
        ログを記録
        
        Args:
            message: ログメッセージ
            level: ログレベル
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # ファイルに書き込み
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # コンソールにも出力
        print(log_entry.strip())
    
    def build_context(self) -> str:
        """
        現在のコンテキストを構築
        
        Returns:
            GPTに送信するコンテキスト
        """
        context = f"""# 現在の状態

## 日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 現在の目標
{self.current_goal}

## 実行回数
{self.iteration_count}回目

## 最近の日誌
{self.memory.read_diary(lines=20)}

## メモリサマリー
{self.memory.get_summary()}

## 最近のメモリ
"""
        # 最近のメモリを追加
        recent_memories = self.memory.get_recent_memories(count=3)
        for mem in recent_memories:
            content = self.memory.get_memory_content(mem['filename'])
            if content:
                context += f"\n### {mem['filename']}\n{content[:300]}...\n"
        
        context += "\n# 指示\n上記の情報を基に、次に実行すべきアクションをJSON形式で出力してください。"
        
        return context
    
    def parse_gpt_response(self, response: str) -> Optional[Dict]:
        """
        GPTの応答をパース
        
        Args:
            response: GPTの応答テキスト
            
        Returns:
            パースされたJSON（失敗時はNone）
        """
        try:
            # JSON部分を抽出（```json ... ``` で囲まれている場合に対応）
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
            
            # JSONパース
            data = json.loads(json_str)
            
            # スキーマ検証
            required_keys = ["say", "cmd", "memory_write", "diary_append", "next_goal"]
            for key in required_keys:
                if key not in data:
                    self.log(f"JSON検証エラー: {key}が見つかりません", "ERROR")
                    return None
            
            return data
            
        except json.JSONDecodeError as e:
            self.log(f"JSON解析エラー: {e}", "ERROR")
            self.log(f"応答内容: {response}", "ERROR")
            return None
        except Exception as e:
            self.log(f"予期しないエラー: {e}", "ERROR")
            return None
    
    def call_gpt(self, context: str) -> Optional[Dict]:
        """
        GPTを呼び出し
        
        Args:
            context: コンテキスト
            
        Returns:
            パースされた応答（失敗時はNone）
        """
        try:
            self.log("GPT-4を呼び出し中...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            self.log(f"GPT応答を受信: {len(content)}文字")
            
            # 応答をパース
            parsed = self.parse_gpt_response(content)
            
            if parsed:
                self.log(f"GPT指示: {parsed['say']}")
                return parsed
            else:
                self.log("GPT応答のパースに失敗", "ERROR")
                return None
            
        except Exception as e:
            self.log(f"GPT呼び出しエラー: {e}", "ERROR")
            return None
    
    def execute_action(self, action: Dict) -> Dict:
        """
        アクションを実行
        
        Args:
            action: 実行するアクション
            
        Returns:
            実行結果
        """
        result = {
            "say": action.get("say", ""),
            "cmd_results": [],
            "memory_saved": False,
            "diary_saved": False
        }
        
        # コマンド実行
        commands = action.get("cmd", [])
        if commands:
            self.log(f"{len(commands)}個のコマンドを実行")
            for cmd in commands:
                self.log(f"実行: {cmd}")
                cmd_result = self.executor.execute(cmd)
                result["cmd_results"].append({
                    "command": cmd,
                    "success": cmd_result["success"],
                    "output": cmd_result.get("stdout", ""),
                    "error": cmd_result.get("stderr", "") or cmd_result.get("error", "")
                })
        
        # メモリ保存
        memory_writes = action.get("memory_write", [])
        if memory_writes:
            for mem in memory_writes:
                filename = mem.get("filename", "")
                content = mem.get("content", "")
                if filename and content:
                    success = self.memory.write_memory(filename, content)
                    result["memory_saved"] = success
                    self.log(f"メモリ保存: {filename} ({'成功' if success else '失敗'})")
        
        # 日誌追記
        diary_entry = action.get("diary_append", "")
        if diary_entry:
            success = self.memory.append_diary(diary_entry)
            result["diary_saved"] = success
            self.log(f"日誌追記: {'成功' if success else '失敗'}")
        
        # 次の目標を更新（ユーザー目標優先制御）
        next_goal = action.get("next_goal", "")
        if next_goal:
            if self._user_goal_active:
                # ユーザー目標が有効な間はGPTのnext_goalで上書きしない
                self.log(f"GPT提案の目標をスキップ（ユーザー目標優先）: {next_goal}")
                # ただしGPTが明らかに別の主題を提案 → ユーザー目標完了とみなす
                # （簡易判定: say に「完了」「達成」が含まれる場合）
                say_text = action.get("say", "")
                if any(kw in say_text for kw in ["完了", "達成", "終了", "完成", "done", "finished"]):
                    self.log("ユーザー目標完了を検出。GPT提案の目標に切替", "INFO")
                    self._user_goal_active = False
                    self.current_goal = next_goal
                    self.log(f"目標更新: {next_goal}")
            else:
                self.current_goal = next_goal
                self.log(f"目標更新: {next_goal}")
        
        # 自己改善機能
        self_improve = action.get("self_improve", {})
        if self_improve.get("enabled", False):
            self.log("自己改善機能を実行します", "WARNING")
            try:
                from self_modifier import SelfModifier
                
                modifier = SelfModifier(
                    api_key=self.client.api_key,
                    model=self.model
                )
                
                improve_result = modifier.self_improve(
                    target_file=self_improve.get("target_file") or None,
                    specific_request=self_improve.get("request") or None,
                    auto_apply=False  # 安全のため、分析のみ
                )
                
                result["self_improve_result"] = improve_result
                self.log(f"自己改善結果: {improve_result}")
                
            except Exception as e:
                self.log(f"自己改善エラー: {e}", "ERROR")
                result["self_improve_result"] = {"error": str(e)}
        
        return result
    
    def run_iteration(self) -> bool:
        """
        1回のイテレーションを実行
        
        Returns:
            成功したらTrue
        """
        self.iteration_count += 1
        self.log(f"=== イテレーション {self.iteration_count} 開始 ===")
        
        try:
            # コンテキスト構築
            context = self.build_context()
            
            # GPT呼び出し
            action = self.call_gpt(context)
            
            if not action:
                self.log("GPT呼び出しに失敗しました", "ERROR")
                return False
            
            # 実行履歴を保存（通知用）
            self.last_action = action
            self.last_thinking = action.get("say", "")
            self.last_commands = action.get("cmd", [])
            
            # アクション実行
            result = self.execute_action(action)
            
            # 実行結果を保存
            self.last_results = result.get("cmd_results", [])
            
            # 実行結果をログ
            self.log(f"実行結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            self.last_execution_time = datetime.now()
            
            return True
            
        except Exception as e:
            self.log(f"イテレーション実行エラー: {e}", "ERROR")
            return False
    
    def run_loop(self, interval: int = 30):
        """
        自律実行ループ
        
        Args:
            interval: イテレーション間隔（秒）
        """
        self.log("自律実行ループを開始します")
        self.memory.append_diary("エージェント起動")
        
        while True:
            try:
                # イテレーション実行
                success = self.run_iteration()
                
                if not success:
                    self.log("イテレーション失敗。リトライします。", "WARNING")
                
                # 待機
                self.log(f"{interval}秒待機中...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.log("ユーザーによる中断")
                self.memory.append_diary("エージェント停止（ユーザー中断）")
                break
            except Exception as e:
                self.log(f"予期しないエラー: {e}", "ERROR")
                self.memory.append_diary(f"エラー発生: {e}")
                time.sleep(interval)


# メイン実行
if __name__ == "__main__":
    # 環境変数からAPIキーを取得
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("エラー: OPENAI_API_KEYが設定されていません")
        exit(1)
    
    # エージェント起動
    agent = AutonomousAgent(
        api_key=api_key,
        model="gpt-4o-mini",
        memory_dir="/home/pi/autonomous_ai/memory",
        log_dir="/home/pi/autonomous_ai/logs"
    )
    
    # 自律ループ開始
    agent.run_loop(interval=30)
>>>>>>> Stashed changes
