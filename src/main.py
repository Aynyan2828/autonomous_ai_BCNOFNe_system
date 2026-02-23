#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全自律型AIシステム メインプログラム
全モジュールを統合して実行
"""

import os
import sys
import time
import signal
import json
from datetime import datetime
from typing import Optional

# 環境変数チェック
required_env_vars = [
    "OPENAI_API_KEY",
    "DISCORD_WEBHOOK_URL",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_CHANNEL_SECRET",
    "LINE_TARGET_USER_ID"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"エラー: 以下の環境変数が設定されていません: {', '.join(missing_vars)}")
    print("設定方法: /home/pi/autonomous_ai/.env ファイルを作成してください")
    sys.exit(1)

# モジュールインポート
from agent_core import AutonomousAgent
from memory import MemoryManager
from executor import CommandExecutor
from discord_notifier import DiscordNotifier
from line_bot import LINEBot
from browser_controller import BrowserController
from storage_manager import StorageManager
from billing_guard import BillingGuard
from startup_flag import StartupFlag


class IntegratedSystem:
    """統合システムクラス"""
    
    def __init__(self):
        """初期化"""
        print("システムを初期化中...")
        
        # 各モジュールの初期化
        self.agent = AutonomousAgent(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4.1-mini",
            memory_dir="/home/pi/autonomous_ai/memory",
            log_dir="/home/pi/autonomous_ai/logs"
        )
        
        self.discord = DiscordNotifier(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL")
        )
        
        self.line = LINEBot(
            channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"),
            channel_secret=os.getenv("LINE_CHANNEL_SECRET"),
            target_user_id=os.getenv("LINE_TARGET_USER_ID")
        )
        
        self.storage = StorageManager(
            ssd_path="/home/pi/autonomous_ai",
            hdd_path="/mnt/hdd/archive"
        )
        
        self.billing = BillingGuard(
            data_dir="/home/pi/autonomous_ai/billing"
        )
        
        self.browser = None  # 必要時に起動
        
        # シグナルハンドラ設定
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        self.running = True
        self.start_time = datetime.now()
    
    def handle_shutdown(self, signum, frame):
        """シャットダウンハンドラ"""
        print("\nシャットダウンシグナルを受信しました")
        self.running = False
    
    def send_startup_notifications(self):
        """起動通知を送信（重複防止付き）"""
        # 起動フラグチェック
        startup_flag = StartupFlag("/home/pi/autonomous_ai/.startup_flag")
        
        if not startup_flag.should_send_startup_notification(cooldown_minutes=5):
            print("起動通知は最近5分以内に送信済みです。スキップします。")
            return
        
        print("起動通知を送信中...")
        
        # Discord通知
        self.discord.send_startup_notification()
        
        # LINE通知
        self.line.send_startup_notification()
        
        # 課金サマリーも送信
        summary = self.billing.get_summary()
        self.discord.send_message(f"```\n{summary}\n```")
        self.line.send_message(summary)
    
    def send_shutdown_notifications(self, reason: str = "通常終了"):
        """停止通知を送信"""
        print("停止通知を送信中...")
        
        # Discord通知
        self.discord.send_shutdown_notification(reason)
        
        # LINE通知
        self.line.send_shutdown_notification(reason)
    
    def check_line_commands(self):
        """
        LINEからのコマンドをチェック
        """
        command_file = "/home/pi/autonomous_ai/commands/user_commands.jsonl"
        
        if not os.path.exists(command_file):
            return
        
        try:
            # 未読コマンドを読み込み
            with open(command_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                return
            
            # 最後のコマンドを取得
            last_command = json.loads(lines[-1])
            command_text = last_command.get("command", "")
            
            if command_text:
                # 目標を更新
                self.agent.current_goal = command_text
                self.agent.log(f"LINEコマンドを受信: {command_text}", "INFO")
                
                # コマンドファイルをクリア
                os.remove(command_file)
                
                # 確認通知
                self.line.send_message(f"✅ 目標を設定しました:\n{command_text}")
                self.discord.send_message(f"📨 LINEから新しい目標を受信:\n{command_text}")
        
        except Exception as e:
            self.agent.log(f"LINEコマンド読み取りエラー: {e}", "ERROR")
    
    def run_iteration_with_monitoring(self) -> bool:
        """
        監視付きイテレーション実行
        
        Returns:
            成功したらTrue
        """
        try:
            # LINEコマンドチェック
            self.check_line_commands()
            # 課金チェック
            alert = self.billing.check_threshold()
            
            if alert:
                if alert["level"] == "stop":
                    # 自動停止
                    self.discord.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "停止"
                    )
                    self.line.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "停止"
                    )
                    
                    self.agent.log("コスト上限に達したため停止します", "ERROR")
                    self.running = False
                    return False
                
                elif alert["level"] == "alert":
                    # 警告通知
                    self.discord.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "警告"
                    )
                    self.line.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "警告"
                    )
                
                elif alert["level"] == "warning":
                    # 注意通知
                    self.discord.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "注意"
                    )
                    self.line.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "注意"
                    )
            
            # エージェント実行
            success = self.agent.run_iteration()
            
            if success:
                # 使用量を記録（簡易版、実際のトークン数は別途取得が必要）
                self.billing.record_usage(
                    model="gpt-4.1-mini",
                    input_tokens=1500,  # 推定値
                    output_tokens=500   # 推定値
                )
                
                # Discord/LINE通知
                if self.agent.iteration_count % 10 == 0:  # 10回に1回通知
                    # エージェントの実行履歴から詳細情報を取得
                    commands = self.agent.last_commands if hasattr(self.agent, 'last_commands') else []
                    results = self.agent.last_results if hasattr(self.agent, 'last_results') else []
                    thinking = self.agent.last_thinking if hasattr(self.agent, 'last_thinking') else ""
                    
                    self.discord.send_execution_log(
                        iteration=self.agent.iteration_count,
                        goal=self.agent.current_goal,
                        commands=commands,
                        results=results,
                        thinking=thinking
                    )
                    self.line.send_execution_log(
                        iteration=self.agent.iteration_count,
                        goal=self.agent.current_goal,
                        commands=commands,
                        results=results
                    )
            
            return success
            
        except Exception as e:
            self.agent.log(f"イテレーション実行エラー: {e}", "ERROR")
            
            # エラー通知
            self.discord.send_error_notification(str(e))
            self.line.send_error_notification(str(e))
            
            return False
    
    def run_maintenance(self):
        """定期メンテナンス"""
        print("定期メンテナンスを実行中...")
        
        # ストレージチェック
        alert = self.storage.monitor_storage(threshold_percent=80.0)
        if alert:
            self.agent.log(alert["message"], "WARNING")
            self.discord.send_message(f"⚠️ {alert['message']}")
            self.line.send_message(f"⚠️ {alert['message']}")
            
            # 自動アーカイブ
            result = self.storage.archive_old_files(dry_run=False)
            if result["moved_files"] > 0:
                msg = f"古いファイルを{result['moved_files']}個アーカイブしました"
                self.agent.log(msg, "INFO")
                self.discord.send_message(f"📦 {msg}")
        
        # 一時ファイル削除
        deleted = self.storage.cleanup_temp_files()
        if deleted > 0:
            self.agent.log(f"一時ファイルを{deleted}個削除しました", "INFO")
        
        # メモリサマリー送信
        if self.agent.iteration_count % 50 == 0:  # 50回に1回
            summary = self.agent.memory.get_summary()
            self.discord.send_memory_summary(summary)
            self.line.send_memory_summary(summary)
    
    def run(self):
        """メインループ"""
        print("=" * 60)
        print("完全自律型AIシステム 起動")
        print("=" * 60)
        
        # 起動通知
        self.send_startup_notifications()
        
        # メインループ
        iteration_interval = 30  # 秒
        maintenance_interval = 3600  # 1時間
        last_maintenance = time.time()
        
        while self.running:
            try:
                # イテレーション実行（LINEコマンドチェックも含む）
                self.run_iteration_with_monitoring()
                
                # 定期メンテナンス
                if time.time() - last_maintenance > maintenance_interval:
                    self.run_maintenance()
                    last_maintenance = time.time()
                
                # 待機
                if self.running:
                    time.sleep(iteration_interval)
                
            except KeyboardInterrupt:
                print("\nユーザーによる中断")
                break
            except Exception as e:
                self.agent.log(f"予期しないエラー: {e}", "ERROR")
                self.discord.send_error_notification(str(e), str(e))
                self.line.send_error_notification(str(e))
                time.sleep(iteration_interval)
        
        # 停止処理
        self.shutdown()
    
    def shutdown(self):
        """シャットダウン処理"""
        print("システムをシャットダウン中...")
        
        # 停止通知
        self.send_shutdown_notifications()
        
        # ブラウザ停止
        if self.browser:
            self.browser.stop()
        
        # 最終メモリ保存
        self.agent.memory.append_diary("システム停止")
        
        print("シャットダウン完了")


def main():
    """メイン関数"""
    try:
        system = IntegratedSystem()
        system.run()
    except Exception as e:
        print(f"致命的エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
