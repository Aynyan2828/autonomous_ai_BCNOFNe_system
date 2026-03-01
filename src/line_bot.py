<<<<<<< Updated upstream
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
                
                # === shipOS コマンド ===
                elif text.lower().startswith("mode ") or text.startswith("モード "):
                    mode_name = text.split(" ", 1)[1].strip().lower()
                    mode_map = {
                        "自律": "autonomous", "航海": "autonomous", "sail": "autonomous",
                        "ユーザー": "user_first", "入港": "user_first", "port": "user_first",
                        "メンテ": "maintenance", "ドック": "maintenance", "dock": "maintenance",
                        "省電力": "power_save", "停泊": "power_save", "anchor": "power_save",
                        "セーフ": "safe", "救難": "safe", "sos": "safe",
                    }
                    resolved = mode_map.get(mode_name, mode_name)
                    valid_modes = ["autonomous", "user_first", "maintenance", "power_save", "safe"]
                    if resolved in valid_modes:
                        result = self._switch_ship_mode(resolved, "LINE手動切替")
                        self.line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=result))
                    else:
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"⚠️ 不明なモード: {mode_name}\n有効: autonomous/user_first/maintenance/power_save/safe"))
                
                elif text in ["ヘルス", "health", "健康"]:
                    result = self._get_health_summary()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["航海日誌", "日誌", "logbook"]:
                    result = self._get_daily_log()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["今日なにした", "今日何した", "today"]:
                    result = self._what_did_i_do()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["モード", "mode"]:
                    mode_data = self._read_current_mode()
                    mode_names = {
                        "autonomous": "⛵ 自律航海", "user_first": "🏠 入港待機",
                        "maintenance": "🔧 ドック入り", "power_save": "🌙 停泊", "safe": "🆘 救難信号"}
                    name = mode_names.get(mode_data.get("mode", ""), mode_data.get("mode", ""))
                    since = mode_data.get("since", "")[:19]
                    override = "（手動オーバーライド中）" if mode_data.get("override") else ""
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"現在のモード: {name}\n開始: {since}\n{override}"))
                
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
    
    # === shipOS 連携メソッド ===
    
    SHIP_MODE_FILE = "/home/pi/autonomous_ai/state/ship_mode.json"
    MODE_HISTORY_FILE = "/home/pi/autonomous_ai/state/mode_history.jsonl"
    HEALTH_HISTORY_FILE = "/home/pi/autonomous_ai/state/health_history.jsonl"
    SHIPS_LOG_DIR = "/home/pi/autonomous_ai/state/ships_log"
    
    def _read_current_mode(self) -> dict:
        """現在のモード状態を読み取り"""
        try:
            if os.path.exists(self.SHIP_MODE_FILE):
                with open(self.SHIP_MODE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"mode": "autonomous", "since": "", "override": False}
    
    def _switch_ship_mode(self, mode: str, reason: str = "") -> str:
        """モードを切り替えて結果メッセージを返す"""
        import os
        mode_names = {
            "autonomous": "⛵ 自律航海", "user_first": "🏠 入港待機",
            "maintenance": "🔧 ドック入り", "power_save": "🌙 停泊", "safe": "🆘 救難信号"
        }
        try:
            old_data = self._read_current_mode()
            old_mode = old_data.get("mode", "autonomous")
            
            new_state = {
                "mode": mode,
                "since": datetime.now().isoformat(),
                "override": True,
                "override_until": None,
                "updated": datetime.now().isoformat()
            }
            os.makedirs(os.path.dirname(self.SHIP_MODE_FILE), exist_ok=True)
            with open(self.SHIP_MODE_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_state, f, ensure_ascii=False, indent=2)
            
            # 履歴記録
            try:
                with open(self.MODE_HISTORY_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "from": old_mode, "to": mode, "reason": reason,
                        "source": "line", "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            
            old_name = mode_names.get(old_mode, old_mode)
            new_name = mode_names.get(mode, mode)
            return f"🔄 モード切替完了\n{old_name} → {new_name}\n理由: {reason}"
        except Exception as e:
            return f"❌ モード切替失敗: {e}"
    
    def _get_health_summary(self) -> str:
        """最新ヘルスチェック結果をテキストで返す"""
        try:
            if os.path.exists(self.HEALTH_HISTORY_FILE):
                with open(self.HEALTH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    h = json.loads(lines[-1].strip())
                    ts = h.get("timestamp", "")[:19]
                    result = [f"🏥 ヘルス状態 ({ts})"]
                    for c in h.get("checks", []):
                        icon = {"OK": "🟢", "WARN": "🟡", "CRITICAL": "🔴"}.get(c.get("status", ""), "⚪")
                        result.append(f"{icon} {c.get('name', '')}: {c.get('message', '')}")
                    return "\n".join(result)
        except Exception as e:
            return f"❌ ヘルス取得エラー: {e}"
        return "ヘルスデータなし"
    
    def _get_daily_log(self) -> str:
        """今日の航海日誌サマリーを返す"""
        try:
            today_file = os.path.join(
                self.SHIPS_LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            if os.path.exists(today_file):
                with open(today_file, 'r', encoding='utf-8') as f:
                    entries = [json.loads(l.strip()) for l in f if l.strip()]
                if entries:
                    total = len(entries)
                    success = sum(1 for e in entries if e.get("success", True))
                    rate = round(success / total * 100, 1) if total else 0
                    return (
                        f"📔 航海日誌 {datetime.now().strftime('%Y/%m/%d')}\n"
                        f"行動回数: {total}回\n"
                        f"成功率: {rate}%\n"
                        f"最新: {entries[-1].get('type', '')}: {entries[-1].get('detail', '')[:40]}"
                    )
        except Exception as e:
            return f"❌ 航海日誌エラー: {e}"
        return "本日のエントリなし"
    
    def _what_did_i_do(self) -> str:
        """「今日なにした？」への回答"""
        try:
            today_file = os.path.join(
                self.SHIPS_LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            if os.path.exists(today_file):
                with open(today_file, 'r', encoding='utf-8') as f:
                    entries = [json.loads(l.strip()) for l in f if l.strip()]
                if entries:
                    total = len(entries)
                    success = sum(1 for e in entries if e.get("success", True))
                    rate = round(success / total * 100, 1) if total else 0
                    recent = entries[-3:]
                    recent_str = "、".join(e.get("detail", "")[:20] for e in recent)
                    return (
                        f"今日は{total}回動いたよ！成功率は{rate}%。\n"
                        f"最近: {recent_str}"
                    )
        except Exception:
            pass
        return "今日はまだ何もしてないよ。のんびり航海中〜"


# Webhookサーバー起動
if __name__ == "__main__":
    print("LINE Bot Webhookサーバーを起動します...")
    print("ポート: 5000")
    print("Ctrl+Cで停止")
    
    # 環境変数から認証情報を取得
    bot = LINEBot()
    
    # Webhookサーバー起動
    bot.run_webhook_server(host="0.0.0.0", port=5000)
=======
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
        target_user_id: Optional[str] = None,
        oled = None
    ):
        """
        初期化
        
        Args:
            channel_access_token: LINE Channel Access Token
            channel_secret: LINE Channel Secret
            target_user_id: 通知先のユーザーID
            oled: OLEDStatusインスタンス
        """
        self.channel_access_token = channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = channel_secret or os.getenv("LINE_CHANNEL_SECRET")
        self.target_user_id = target_user_id or os.getenv("LINE_TARGET_USER_ID")
        self.oled = oled
        
        if not self.channel_access_token or not self.channel_secret:
            raise ValueError("LINE認証情報が設定されていません")
        
        self.line_bot_api = LineBotApi(self.channel_access_token)
        self.handler = WebhookHandler(self.channel_secret)
        
        # 課金確認の待機状態を管理
        self.pending_confirmations = {}
        
        # LINE実行ログ送信フラグ（デフォルトOFF）
        self.exec_log_enabled = os.getenv("LINE_EXEC_LOG_ENABLED", "false").lower() == "true"
        self._exec_log_timeout = None  # 一時有効化のタイムアウト

    def _write_line_status(self, direction: str):
        """OLEDコントローラー向けにIPC経由で送受信状態を通知"""
        try:
            import json, time
            with open("/tmp/shipos_line_status.json", "w", encoding="utf-8") as f:
                json.dump({"direction": direction, "timestamp": time.time()}, f)
        except Exception as e:
            print(f"LINEステータスIPC送信エラー: {e}")
    
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
            
            # OLED通知
            self._write_line_status("TX")

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
        message = f""">===> システム起動

あゆにゃん、出港したばい！

起動時刻: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
ステータス: [OK] 正常起動
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
        message = f"""[=] システム停止

あゆにゃん、投錨したよ。

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
            
            # OLED通知 (受信)
            self._write_line_status("RX")

            # 課金確認の応答をチェック
            if text.startswith("許可:") or text.startswith("拒否:"):
                confirmation_id = text.split(":", 1)[1]
                response = "許可" if text.startswith("許可:") else "拒否"
                
                if confirmation_id in self.pending_confirmations:
                    # 確認結果を保存（別のモジュールから参照できるように）
                    self._save_confirmation_result(confirmation_id, response)
                    
                    reply_text = f"[OK] {response}したよ" if response == "許可" else f"[NG] {response}したよ"
                    
                    # OLED通知 (返信)
                    self._write_line_status("TX")

                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
                else:
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="[!] 確認IDが見つからんばい")
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
                
                # === shipOS コマンド ===
                elif text.lower().startswith("mode ") or text.startswith("モード "):
                    mode_name = text.split(" ", 1)[1].strip().lower()
                    mode_map = {
                        "自律": "autonomous", "航海": "autonomous", "sail": "autonomous",
                        "ユーザー": "user_first", "入港": "user_first", "port": "user_first",
                        "メンテ": "maintenance", "ドック": "maintenance", "dock": "maintenance",
                        "省電力": "power_save", "停泊": "power_save", "anchor": "power_save",
                        "セーフ": "safe", "救難": "safe", "sos": "safe",
                    }
                    resolved = mode_map.get(mode_name, mode_name)
                    valid_modes = ["autonomous", "user_first", "maintenance", "power_save", "safe"]
                    if resolved in valid_modes:
                        result = self._switch_ship_mode(resolved, "LINE手動切替")
                        self.line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=result))
                    else:
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"⚠️ 不明なモード: {mode_name}\n有効: autonomous/user_first/maintenance/power_save/safe"))
                
                elif text in ["ヘルス", "health", "健康"]:
                    result = self._get_health_summary()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["航海日誌", "日誌", "logbook"]:
                    result = self._get_daily_log()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["今日なにした", "今日何した", "today"]:
                    result = self._what_did_i_do()
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                # === 音声コマンド ===
                elif text.startswith("話して ") or text.startswith("say "):
                    speak_text = text.split(" ", 1)[1].strip()
                    result = self._audio_command("speak", {"text": speak_text})
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["ミュート", "mute"]:
                    result = self._audio_command("monologue_mute", {})
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["ミュート解除", "unmute"]:
                    result = self._audio_command("monologue_unmute", {})
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text in ["読み上げ", "状態読み上げ", "read status"]:
                    result = self._audio_command("status_read", {})
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=result))
                
                elif text.startswith("声 ") or text.startswith("voice "):
                    voice_name = text.split(" ", 1)[1].strip().lower()
                    valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                    if voice_name in valid_voices:
                        result = self._audio_command("change_voice", {"voice": voice_name})
                        self.line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text=result))
                    else:
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f"⚠️ 不明な声: {voice_name}\n有効: {', '.join(valid_voices)}"))
                
                elif text in ["音声ヘルプ", "voice help"]:
                    help_text = (
                        "🔊 音声コマンド一覧\n\n"
                        "「話して ○○」→ 指定テキストを読み上げ\n"
                        "「ミュート」→ 独り言を停止\n"
                        "「ミュート解除」→ 独り言を再開\n"
                        "「読み上げ」→ システム状態を読み上げ\n"
                        "「声 nova」→ 声を変更\n"
                        "  (alloy/echo/fable/onyx/nova/shimmer)"
                    )
                    self.line_bot_api.reply_message(
                        event.reply_token, TextSendMessage(text=help_text))
                
                elif text in ["モード", "mode"]:
                    mode_data = self._read_current_mode()
                    mode_names = {
                        "autonomous": ">===> 自律航海", "user_first": "[PORT] 入港待機",
                        "maintenance": "{DOCK} ドック入り", "power_save": "--- 停泊", "safe": "!!! 救難信号"}
                    name = mode_names.get(mode_data.get("mode", ""), mode_data.get("mode", ""))
                    since = mode_data.get("since", "")[:19]
                    override = "（手動オーバーライド中）" if mode_data.get("override") else ""
                    self.line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"現在のモード: {name}\n開始: {since}\n{override}"))
                
                else:
                    # 入力種別を判定
                    event_type = self._classify_input(text)
                    self._save_event(event_type, text, event.source.user_id)
                    
                    if event_type == "query":
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=">> 了解、マスター。あたいが調べるけん、ちょっと待っとって。")
                        )
                    else:
                        self.line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=f">> よかよ、マスター！新しい航路を設定したばい。\n\n[NAV] 目的地: {text}")
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
    
    # === shipOS 連携メソッド ===
    
    SHIP_MODE_FILE = "/home/pi/autonomous_ai/state/ship_mode.json"
    MODE_HISTORY_FILE = "/home/pi/autonomous_ai/state/mode_history.jsonl"
    HEALTH_HISTORY_FILE = "/home/pi/autonomous_ai/state/health_history.jsonl"
    SHIPS_LOG_DIR = "/home/pi/autonomous_ai/state/ships_log"
    
    def _read_current_mode(self) -> dict:
        """現在のモード状態を読み取り"""
        try:
            if os.path.exists(self.SHIP_MODE_FILE):
                with open(self.SHIP_MODE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"mode": "autonomous", "since": "", "override": False}
    
    AUDIO_CMD_FILE = "/tmp/shipos_audio_cmd.json"
    
    def _audio_command(self, action: str, params: dict) -> str:
        """音声サブシステムにコマンドを送信（ファイルベースIPC）"""
        try:
            cmd = {
                "action": action,
                "params": params,
                "timestamp": datetime.now().isoformat(),
                "source": "line"
            }
            with open(self.AUDIO_CMD_FILE, 'w', encoding='utf-8') as f:
                json.dump(cmd, f, ensure_ascii=False)
            
            action_names = {
                "speak": "🔊 読み上げコマンドを送信しました",
                "monologue_mute": "🔇 独り言をミュートしました",
                "monologue_unmute": "🔊 独り言を再開しました",
                "status_read": "📊 状態読み上げを開始します",
                "change_voice": f"🎙️ 声を {params.get('voice', '')} に変更しました",
            }
            return action_names.get(action, f"✅ コマンド送信: {action}")
        except Exception as e:
            return f"❌ 音声コマンドエラー: {e}"
    
    def _switch_ship_mode(self, mode: str, reason: str = "") -> str:
        """モードを切り替えて結果メッセージを返す"""
        import os
        mode_names = {
            "autonomous": "⛵ 自律航海", "user_first": "🏠 入港待機",
            "maintenance": "🔧 ドック入り", "power_save": "🌙 停泊", "safe": "🆘 救難信号"
        }
        try:
            old_data = self._read_current_mode()
            old_mode = old_data.get("mode", "autonomous")
            
            new_state = {
                "mode": mode,
                "since": datetime.now().isoformat(),
                "override": True,
                "override_until": None,
                "updated": datetime.now().isoformat()
            }
            os.makedirs(os.path.dirname(self.SHIP_MODE_FILE), exist_ok=True)
            with open(self.SHIP_MODE_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_state, f, ensure_ascii=False, indent=2)
            
            # 履歴記録
            try:
                with open(self.MODE_HISTORY_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "from": old_mode, "to": mode, "reason": reason,
                        "source": "line", "timestamp": datetime.now().isoformat()
                    }, ensure_ascii=False) + "\n")
            except Exception:
                pass
            
            old_name = mode_names.get(old_mode, old_mode)
            new_name = mode_names.get(mode, mode)
            return f"🔄 モード切替完了\n{old_name} → {new_name}\n理由: {reason}"
        except Exception as e:
            return f"❌ モード切替失敗: {e}"
    
    def _get_health_summary(self) -> str:
        """最新ヘルスチェック結果をテキストで返す"""
        try:
            if os.path.exists(self.HEALTH_HISTORY_FILE):
                with open(self.HEALTH_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    h = json.loads(lines[-1].strip())
                    ts = h.get("timestamp", "")[:19]
                    result = [f"🏥 ヘルス状態 ({ts})"]
                    for c in h.get("checks", []):
                        icon = {"OK": "🟢", "WARN": "🟡", "CRITICAL": "🔴"}.get(c.get("status", ""), "⚪")
                        result.append(f"{icon} {c.get('name', '')}: {c.get('message', '')}")
                    return "\n".join(result)
        except Exception as e:
            return f"❌ ヘルス取得エラー: {e}"
        return "ヘルスデータなし"
    
    def _get_daily_log(self) -> str:
        """今日の航海日誌サマリーを返す"""
        try:
            today_file = os.path.join(
                self.SHIPS_LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            if os.path.exists(today_file):
                with open(today_file, 'r', encoding='utf-8') as f:
                    entries = [json.loads(l.strip()) for l in f if l.strip()]
                if entries:
                    total = len(entries)
                    success = sum(1 for e in entries if e.get("success", True))
                    rate = round(success / total * 100, 1) if total else 0
                    return (
                        f"📔 航海日誌 {datetime.now().strftime('%Y/%m/%d')}\n"
                        f"行動回数: {total}回\n"
                        f"成功率: {rate}%\n"
                        f"最新: {entries[-1].get('type', '')}: {entries[-1].get('detail', '')[:40]}"
                    )
        except Exception as e:
            return f"❌ 航海日誌エラー: {e}"
        return "本日のエントリなし"
    
    def _what_did_i_do(self) -> str:
        """「今日なにした？」への回答"""
        try:
            today_file = os.path.join(
                self.SHIPS_LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.jsonl"
            )
            if os.path.exists(today_file):
                with open(today_file, 'r', encoding='utf-8') as f:
                    entries = [json.loads(l.strip()) for l in f if l.strip()]
                if entries:
                    total = len(entries)
                    success = sum(1 for e in entries if e.get("success", True))
                    rate = round(success / total * 100, 1) if total else 0
                    recent = entries[-3:]
                    recent_str = "、".join(e.get("detail", "")[:20] for e in recent)
                    return (
                        f"今日は{total}回動いたよ！成功率は{rate}%。\n"
                        f"最近: {recent_str}"
                    )
        except Exception:
            pass
        return "今日はまだ何もしてないよ。のんびり航海中〜"


# Webhookサーバー起動
if __name__ == "__main__":
    print("LINE Bot Webhookサーバーを起動します...")
    print("ポート: 5000")
    print("Ctrl+Cで停止")
    
    # 環境変数から認証情報を取得
    bot = LINEBot()
    
    # Webhookサーバー起動
    bot.run_webhook_server(host="0.0.0.0", port=5000)
>>>>>>> Stashed changes
