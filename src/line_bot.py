#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE Botモジュール
スマホからの指示受付と通知
"""

import os
import json
import subprocess
import uuid
import re
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # 代替パスも試す
    load_dotenv("/home/pi/autonomous_ai/.env")
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)


class LINEBot:
    """LINE Bot クラス"""
    
    def __init__(
        self,
        channel_access_token: Optional[str] = None,
        channel_secret: Optional[str] = None,
        target_user_id: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            channel_access_token: LINE Channel Access Token
            channel_secret: LINE Channel Secret
            target_user_id: 通知先のユーザーID
        """
        self.channel_access_token = channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = channel_secret or os.getenv("LINE_CHANNEL_SECRET")
        self.target_user_id = target_user_id or os.getenv("LINE_TARGET_USER_ID")
        
        if not self.channel_access_token or not self.channel_secret:
            raise ValueError("LINE認証情報が設定されていません")
        
        self.line_bot_api = LineBotApi(self.channel_access_token)
        self.handler = WebhookHandler(self.channel_secret)
        
        # 課金確認の待機状態を管理
        self.pending_confirmations = {}
        
        # LINE実行ログ送信フラグ（デフォルトOFF）
        self.exec_log_enabled = os.getenv("LINE_EXEC_LOG_ENABLED", "false").lower() == "true"
        self._exec_log_timeout = None  # 一時有効化のタイムアウト
    
    def send_message(self, message: str, user_id: Optional[str] = None) -> bool:
        """
        LINEメッセージを送信
        
        Args:
            message: 送信するメッセージ
            user_id: 送信先ユーザーID（指定しない場合はデフォルト）
            
        Returns:
            成功したらTrue
        """
        try:
            target = user_id or self.target_user_id
            
            if not target:
                print("エラー: 送信先ユーザーIDが設定されていません")
                return False
            
            self.line_bot_api.push_message(
                target,
                TextSendMessage(text=message)
            )
            
            return True
            
        except Exception as e:
            print(f"LINEメッセージ送信エラー: {e}")
            return False
    
    def send_startup_notification(self) -> bool:
        """
        起動通知を送信
        
        Returns:
            成功したらTrue
        """
        message = f"""🚀 システム起動

自律AIエージェントが起動しました

起動時刻: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
ステータス: ✅ 正常起動
"""
        return self.send_message(message)
    
    def send_shutdown_notification(self, reason: str = "通常終了") -> bool:
        """
        停止通知を送信
        
        Args:
            reason: 停止理由
            
        Returns:
            成功したらTrue
        """
        message = f"""⏹️ システム停止

自律AIエージェントが停止しました

停止時刻: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
停止理由: {reason}
"""
        return self.send_message(message)
    
    def send_execution_log(
        self,
        iteration: int,
        goal: str,
        commands: list,
        results: list
    ) -> bool:
        """
        実行ログを送信
        
        Args:
            iteration: イテレーション番号
            goal: 現在の目標
            commands: 実行したコマンド
            results: 実行結果
            
        Returns:
            成功したらTrue
        """
        success_count = sum(1 for r in results if r.get("success", False))
        fail_count = len(results) - success_count
        
        message = f"""📊 実行ログ #{iteration}

目標: {goal}

実行コマンド数: {len(commands)}
✅ 成功: {success_count}
❌ 失敗: {fail_count}

時刻: {datetime.now().strftime("%H:%M:%S")}
"""
        return self.send_message(message)
    
    def send_status(self, status_message: str) -> bool:
        """
        短い状態通知をLINEに送信
        
        Args:
            status_message: 状態メッセージ（例: "⏳ 実行中: ファイル整理"）
            
        Returns:
            成功したらTrue
        """
        return self.send_message(status_message)
    
    def is_exec_log_enabled(self) -> bool:
        """
        LINE実行ログ送信が有効かチェック（一時有効化対応）
        
        Returns:
            有効ならTrue
        """
        import time
        if self._exec_log_timeout and time.time() < self._exec_log_timeout:
            return True
        if self._exec_log_timeout and time.time() >= self._exec_log_timeout:
            self._exec_log_timeout = None  # タイムアウト
        return self.exec_log_enabled
    
    def send_error_notification(self, error_message: str) -> bool:
        """
        エラー通知を送信
        
        Args:
            error_message: エラーメッセージ
            
        Returns:
            成功したらTrue
        """
        message = f"""⚠️ エラー発生

{error_message}

発生時刻: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
"""
        return self.send_message(message)
    
    def send_memory_summary(self, summary: str) -> bool:
        """
        メモリ要約を送信
        
        Args:
            summary: メモリの要約
            
        Returns:
            成功したらTrue
        """
        # LINEの文字数制限に対応（最大5000文字）
        if len(summary) > 4900:
            summary = summary[:4900] + "..."
        
        message = f"📚 メモリサマリー\n\n{summary}"
        return self.send_message(message)
    
    def send_cost_alert(
        self,
        current_cost: float,
        threshold: float,
        alert_level: str = "注意"
    ) -> bool:
        """
        コストアラートを送信
        
        Args:
            current_cost: 現在のコスト（円）
            threshold: 閾値（円）
            alert_level: アラートレベル
            
        Returns:
            成功したらTrue
        """
        icons = {
            "注意": "⚠️",
            "警告": "🚨",
            "停止": "🛑"
        }
        icon = icons.get(alert_level, "⚠️")
        
        message = f"""{icon} コストアラート: {alert_level}

API使用料が閾値に達しました

現在のコスト: ¥{current_cost:.2f}
閾値: ¥{threshold:.2f}

{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
"""
        return self.send_message(message)
    
    def request_billing_confirmation(
        self,
        action_description: str,
        estimated_cost: float,
        confirmation_id: str
    ) -> bool:
        """
        課金確認リクエストを送信
        
        Args:
            action_description: アクションの説明
            estimated_cost: 見積もりコスト（円）
            confirmation_id: 確認ID
            
        Returns:
            成功したらTrue
        """
        try:
            message = f"""💰 課金確認

以下のアクションを実行しますか?

アクション: {action_description}
見積もりコスト: ¥{estimated_cost:.2f}

10分以内に応答がない場合は自動キャンセルされます。
"""
            
            # クイックリプライボタンを追加
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="✅ 許可", text=f"許可:{confirmation_id}")),
                QuickReplyButton(action=MessageAction(label="❌ 拒否", text=f"拒否:{confirmation_id}"))
            ])
            
            self.line_bot_api.push_message(
                self.target_user_id,
                TextSendMessage(text=message, quick_reply=quick_reply)
            )
            
            # 待機状態を記録
            self.pending_confirmations[confirmation_id] = {
                "action": action_description,
                "cost": estimated_cost,
                "timestamp": datetime.now().isoformat()
            }
            
            return True
            
        except Exception as e:
            print(f"課金確認送信エラー: {e}")
            return False
    
    def create_webhook_app(self) -> Flask:
        """
        Webhook用のFlaskアプリを作成
        
        Returns:
            Flaskアプリ
        """
        app = Flask(__name__)
        
        @app.route("/webhook", methods=['POST'])
        def webhook():
            # 署名検証
            signature = request.headers['X-Line-Signature']
            body = request.get_data(as_text=True)
            
            try:
                self.handler.handle(body, signature)
            except InvalidSignatureError:
                abort(400)
            
            return 'OK'
        
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_message(event):
            text = event.message.text
            
            # 課金確認の応答をチェック
            if text.startswith("許可:") or text.startswith("拒否:"):
                confirmation_id = text.split(":", 1)[1]
                response = "許可" if text.startswith("許可:") else "拒否"
                
                if confirmation_id in self.pending_confirmations:
                    # 確認結果を保存（別のモジュールから参照できるように）
                    self._save_confirmation_result(confirmation_id, response)
                    
                    reply_text = f"✅ {response}しました" if response == "許可" else f"❌ {response}しました"
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
                else:
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="⚠️ 確認IDが見つかりません")
                    )
            else:
                # 特別なコマンドをチェック
                if text in ["停止", "ストップ", "stop", "STOP"]:
                    # AIエージェントを停止
                    result = self._stop_ai_service()
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=result)
                    )
                elif text in ["再開", "起動", "start", "START", "スタート"]:
                    # AIエージェントを起動
                    result = self._start_ai_service()
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=result)
                    )
                elif text in ["状態", "ステータス", "status", "STATUS"]:
                    # AIエージェントの状態を確認
                    result = self._check_ai_service_status()
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=result)
                    )
                elif text.lower() in ["log on", "ログon", "ログオン"]:
                    # LINE実行ログを一時有効化（30分間）
                    import time as _time
                    self._exec_log_timeout = _time.time() + 1800
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="📊 LINE実行ログを30分間有効にしました。\n無効にするには「log off」と送信してください。")
                    )
                elif text.lower() in ["log off", "ログoff", "ログオフ"]:
                    # LINE実行ログを無効化
                    self._exec_log_timeout = None
                    self.exec_log_enabled = False
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="📊 LINE実行ログを無効にしました。")
                    )
                else:
                    # 入力種別を判定
                    event_type = self._classify_input(text)
                    self._save_event(event_type, text, event.source.user_id)
                    
                    if event_type == "query":
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="🔍 質問を受け付けました。回答を準備中...")
                        )
                    else:
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="📝 指示を受け付けました\n\n✅ 目標を設定しました:\n" + text)
                        )
        
        return app
    
    def _save_confirmation_result(self, confirmation_id: str, response: str):
        """
        確認結果を保存
        
        Args:
            confirmation_id: 確認ID
            response: 応答（許可/拒否）
        """
        result_file = f"/home/pi/autonomous_ai/billing/confirmations/{confirmation_id}.json"
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "confirmation_id": confirmation_id,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def _classify_input(self, text: str) -> str:
        """
        入力テキストを種別判定する
        
        Args:
            text: ユーザーの入力テキスト
            
        Returns:
            "query" or "goal"
        """
        # 質問パターン（正規表現）
        query_patterns = [
            r'[?？]',                    # 疑問符
            r'(教えて|おしえて)',         # 教えて系
            r'(天気|気温|温度)',          # 天気系
            r'^(何|なに|なん)',           # 何〜
            r'^(いつ|どこ|誰|だれ)',     # 疑問詞
            r'(調べて|しらべて)',         # 調べて系
            r'(どう|どんな|どれ)',       # どう系
            r'(ある|ない|できる)\s*[?？]',  # 可否質問
            r'(とは|って何|ってなに)',   # 定義質問
            r'(意味|違い)',              # 意味・違い
            r'(わかる|知って|しって)',   # 知識確認
        ]
        
        text_stripped = text.strip()
        
        for pattern in query_patterns:
            if re.search(pattern, text_stripped):
                return "query"
        
        # 短いテキスト（10文字以下）で命令形でなければ質問扱い
        if len(text_stripped) <= 10 and not re.search(r'(して|しろ|せよ|する)$', text_stripped):
            return "query"
        
        return "goal"
    
    def _save_event(self, event_type: str, text: str, user_id: str):
        """
        イベントをインボックスと履歴に保存
        
        Args:
            event_type: "query" or "goal"
            text: テキスト
            user_id: ユーザーID
        """
        event_data = {
            "type": event_type,
            "text": text,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # 1) インボックスに追記（未処理キュー）
        inbox_file = "/home/pi/autonomous_ai/commands/inbox.jsonl"
        os.makedirs(os.path.dirname(inbox_file), exist_ok=True)
        
        with open(inbox_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + "\n")
        
        # 2) 永続履歴に保存
        today = datetime.now().strftime("%Y%m%d")
        history_dir = f"/home/pi/autonomous_ai/commands/history/{today}"
        os.makedirs(history_dir, exist_ok=True)
        
        event_id = str(uuid.uuid4())
        history_file = os.path.join(history_dir, f"{event_id}.json")
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump({
                **event_data,
                "event_id": event_id
            }, f, ensure_ascii=False, indent=2)
    
    def _save_user_command(self, command: str, user_id: str):
        """
        ユーザーコマンドを保存（後方互換用）
        
        Args:
            command: コマンド
            user_id: ユーザーID
        """
        # 新しいイベント方式で保存
        self._save_event("goal", command, user_id)
    
    def _stop_ai_service(self) -> str:
        """
        AIエージェントサービスを停止
        
        Returns:
            結果メッセージ
        """
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "stop", "autonomous-ai.service"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return "⏹️ AIエージェントを停止しました\n\n再開するには「再開」と送信してください。"
            else:
                return f"⚠️ 停止に失敗しました\n\nエラー: {result.stderr}"
        except Exception as e:
            return f"❌ エラーが発生しました: {str(e)}"
    
    def _start_ai_service(self) -> str:
        """
        AIエージェントサービスを起動
        
        Returns:
            結果メッセージ
        """
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "start", "autonomous-ai.service"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return "🚀 AIエージェントを起動しました\n\n数秒後に動作を開始します。"
            else:
                return f"⚠️ 起動に失敗しました\n\nエラー: {result.stderr}"
        except Exception as e:
            return f"❌ エラーが発生しました: {str(e)}"
    
    def _check_ai_service_status(self) -> str:
        """
        AIエージェントサービスの状態を確認
        
        Returns:
            状態メッセージ
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "autonomous-ai.service"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            status = result.stdout.strip()
            
            if status == "active":
                return "✅ AIエージェント: 稼働中\n\n停止するには「停止」と送信してください。"
            elif status == "inactive":
                return "⏹️ AIエージェント: 停止中\n\n起動するには「再開」と送信してください。"
            else:
                return f"⚠️ AIエージェント: {status}\n\n詳細はログを確認してください。"
        except Exception as e:
            return f"❌ 状態確認エラー: {str(e)}"
    
    def run_webhook_server(self, host: str = "0.0.0.0", port: int = 5000):
        """
        Webhookサーバーを起動
        
        Args:
            host: ホスト
            port: ポート
        """
        app = self.create_webhook_app()
        app.run(host=host, port=port)


# Webhookサーバー起動
if __name__ == "__main__":
    print("LINE Bot Webhookサーバーを起動します...")
    print("ポート: 5000")
    print("Ctrl+Cで停止")
    
    # 環境変数から認証情報を取得
    bot = LINEBot()
    
    # Webhookサーバー起動
    bot.run_webhook_server(host="0.0.0.0", port=5000)
