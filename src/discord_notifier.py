#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord通知モジュール
システム状態をDiscordに通知
"""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, List


class DiscordNotifier:
    """Discord通知クラス"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初期化
        
        Args:
            webhook_url: Discord Webhook URL（環境変数から取得も可能）
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        
        if not self.webhook_url:
            raise ValueError("Discord Webhook URLが設定されていません")
    
    def send_message(
        self,
        content: str,
        username: str = "自律AIエージェント",
        embeds: Optional[List[Dict]] = None
    ) -> bool:
        """
        Discordにメッセージを送信
        
        Args:
            content: メッセージ内容
            username: 送信者名
            embeds: 埋め込みメッセージのリスト
            
        Returns:
            成功したらTrue
        """
        try:
            payload = {
                "username": username,
                "content": content
            }
            
            if embeds:
                payload["embeds"] = embeds
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204
            
        except Exception as e:
            print(f"Discord送信エラー: {e}")
            return False
    
    def send_startup_notification(self) -> bool:
        """
        起動通知を送信
        
        Returns:
            成功したらTrue
        """
        embed = {
            "title": "🚀 システム起動",
            "description": "自律AIエージェントが起動しました",
            "color": 0x00FF00,  # 緑
            "fields": [
                {
                    "name": "起動時刻",
                    "value": datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
                    "inline": False
                },
                {
                    "name": "ステータス",
                    "value": "✅ 正常起動",
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])
    
    def send_shutdown_notification(self, reason: str = "通常終了") -> bool:
        """
        停止通知を送信
        
        Args:
            reason: 停止理由
            
        Returns:
            成功したらTrue
        """
        embed = {
            "title": "⏹️ システム停止",
            "description": "自律AIエージェントが停止しました",
            "color": 0xFF0000,  # 赤
            "fields": [
                {
                    "name": "停止時刻",
                    "value": datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
                    "inline": False
                },
                {
                    "name": "停止理由",
                    "value": reason,
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])
    
    def send_execution_log(
        self,
        iteration: int,
        goal: str,
        commands: List[str],
        results: List[Dict],
        thinking: str = ""
    ) -> bool:
        """
        実行ログを送信
        
        Args:
            iteration: イテレーション番号
            goal: 現在の目標
            commands: 実行したコマンドのリスト
            results: 実行結果のリスト
            thinking: AIの思考プロセス
            
        Returns:
            成功したらTrue
        """
        # コマンドと結果を整形
        cmd_text = "\n".join([f"```bash\n{cmd}\n```" for cmd in commands[:3]])  # 最大3個
        if len(commands) > 3:
            cmd_text += f"\n... 他 {len(commands) - 3} 個"
        
        # 成功/失敗のカウント
        success_count = sum(1 for r in results if r.get("success", False))
        fail_count = len(results) - success_count
        
        # AIの思考プロセスを追加
        fields = []
        
        # 思考プロセスがあれば追加
        if thinking:
            thinking_short = thinking[:300] + "..." if len(thinking) > 300 else thinking
            fields.append({
                "name": "🧠 AIの思考",
                "value": thinking_short,
                "inline": False
            })
        
        fields.extend([
            {
                "name": "実行コマンド",
                "value": cmd_text if cmd_text else "なし",
                "inline": False
            },
            {
                "name": "実行結果",
                "value": f"✅ 成功: {success_count} / ❌ 失敗: {fail_count}",
                "inline": False
            }
        ])
        
        embed = {
            "title": f"📊 実行ログ #{iteration}",
            "description": f"**目標**: {goal}",
            "color": 0x0099FF,  # 青
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])
    
    def send_error_notification(self, error_message: str, details: str = "") -> bool:
        """
        エラー通知を送信
        
        Args:
            error_message: エラーメッセージ
            details: 詳細情報
            
        Returns:
            成功したらTrue
        """
        embed = {
            "title": "⚠️ エラー発生",
            "description": error_message,
            "color": 0xFF0000,  # 赤
            "fields": [
                {
                    "name": "発生時刻",
                    "value": datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
                    "inline": False
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if details:
            embed["fields"].append({
                "name": "詳細",
                "value": f"```\n{details[:1000]}\n```",  # 最大1000文字
                "inline": False
            })
        
        return self.send_message("", embeds=[embed])
    
    def send_memory_summary(self, summary: str) -> bool:
        """
        メモリ要約を送信
        
        Args:
            summary: メモリの要約（日本語）
            
        Returns:
            成功したらTrue
        """
        # 要約を適切な長さに切り詰め
        if len(summary) > 1900:
            summary = summary[:1900] + "..."
        
        embed = {
            "title": "📚 メモリサマリー",
            "description": summary,
            "color": 0x9900FF,  # 紫
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])
    
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
            alert_level: アラートレベル（注意/警告/停止）
            
        Returns:
            成功したらTrue
        """
        # アラートレベルに応じた色とアイコン
        colors = {
            "注意": 0xFFFF00,  # 黄
            "警告": 0xFF9900,  # オレンジ
            "停止": 0xFF0000   # 赤
        }
        icons = {
            "注意": "⚠️",
            "警告": "🚨",
            "停止": "🛑"
        }
        
        color = colors.get(alert_level, 0xFFFF00)
        icon = icons.get(alert_level, "⚠️")
        
        embed = {
            "title": f"{icon} コストアラート: {alert_level}",
            "description": f"API使用料が閾値に達しました",
            "color": color,
            "fields": [
                {
                    "name": "現在のコスト",
                    "value": f"¥{current_cost:.2f}",
                    "inline": True
                },
                {
                    "name": "閾値",
                    "value": f"¥{threshold:.2f}",
                    "inline": True
                },
                {
                    "name": "アラートレベル",
                    "value": alert_level,
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])
    
    def send_health_check(self, status: Dict) -> bool:
        """
        ヘルスチェック結果を送信
        
        Args:
            status: ステータス情報
            
        Returns:
            成功したらTrue
        """
        embed = {
            "title": "💚 ヘルスチェック",
            "description": "システムは正常に動作しています",
            "color": 0x00FF00,  # 緑
            "fields": [
                {
                    "name": "稼働時間",
                    "value": status.get("uptime", "不明"),
                    "inline": True
                },
                {
                    "name": "実行回数",
                    "value": str(status.get("iterations", 0)),
                    "inline": True
                },
                {
                    "name": "メモリ使用量",
                    "value": status.get("memory_usage", "不明"),
                    "inline": True
                }
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_message("", embeds=[embed])


# テスト用
if __name__ == "__main__":
    # 環境変数からWebhook URLを取得
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("エラー: DISCORD_WEBHOOK_URLが設定されていません")
        exit(1)
    
    notifier = DiscordNotifier(webhook_url)
    
    # テスト送信
    print("起動通知を送信...")
    notifier.send_startup_notification()
    
    print("実行ログを送信...")
    notifier.send_execution_log(
        iteration=1,
        goal="システムの状態確認",
        commands=["ls -la", "df -h"],
        results=[{"success": True}, {"success": True}]
    )
    
    print("メモリ要約を送信...")
    notifier.send_memory_summary("テストメモリ要約\n総メモリ数: 5\nトピック数: 3")
    
    print("テスト完了")
