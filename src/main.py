#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autonomous ai BCNOFNe system メインプログラム
自律AIシステム統合制御

v4.0: BCNOFNe進化 - モードシステム、カレンダー連携、ヘルスモニタ、
      航海日誌、自己修復、音声IF、航海用語演出
"""

import os
import sys
import time
import signal
import json
import threading
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
from quick_responder import QuickResponder
from ship_mode import ShipMode
from ship_narrator import ShipNarrator
from ships_log import ShipsLog
from health_monitor import HealthMonitor
from failsafe import FailSafe
from ai_state import get_state as get_ai_state

# オプショナルモジュール
try:
    from calendar_sync import CalendarSync
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

try:
    from task_scheduler import TaskScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

try:
    from oled_status import OLEDStatus
    OLED_ENABLED = True
except ImportError:
    OLED_ENABLED = False


class IntegratedSystem:
    """統合システムクラス"""
    
    def __init__(self):
        """初期化"""
        print("システムを初期化中...")
        
        # 各モジュールの初期化
        self.agent = AutonomousAgent(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
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
        
        # Quick Responder（質問即時回答用）
        self.quick_responder = QuickResponder(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.browser = None  # 必要時に起動
        
        # === shipOS モジュール ===
        self.ship_mode = ShipMode()
        self.narrator = ShipNarrator
        self.ships_log = ShipsLog()
        self.health = HealthMonitor()
        self.failsafe = FailSafe()
        
        # カレンダー連携（オプショナル）
        self.calendar = None
        self.scheduler = None
        if CALENDAR_AVAILABLE and os.getenv("CALENDAR_ICS_URL"):
            try:
                self.calendar = CalendarSync()
                if SCHEDULER_AVAILABLE:
                    self.scheduler = TaskScheduler(self.calendar, self.ship_mode)
                    self._register_periodic_tasks()
                print("カレンダー連携を初期化しました")
            except Exception as e:
                print(f"カレンダー初期化スキップ: {e}")
        
        # OLEDステータス表示（オプショナル）
        self.oled = None
        if OLED_ENABLED:
            try:
                self.oled = OLEDStatus()
                print("OLEDステータス表示を初期化しました")
            except Exception as e:
                print(f"OLED初期化スキップ: {e}")
        
        # LINE Botの初期化 (OLEDを渡す)
        self.line = LINEBot(
            channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"),
            channel_secret=os.getenv("LINE_CHANNEL_SECRET"),
            target_user_id=os.getenv("LINE_TARGET_USER_ID"),
            oled=self.oled
        )

        # シグナルハンドラ設定
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        # self.inbox_thread = threading.Thread(target=self._inbox_worker, daemon=True)
        # self.inbox_thread.start()
        # -> main.pyのインボックス処理はループ内で呼ぶため、スレッドは不要(あるいは別管理)
        # 既存のロジックを維持しつつOLEDのみ無効化

        self.running = True
        self.start_time = datetime.now()
    
    def handle_shutdown(self, signum, frame):
        """シャットダウンハンドラ"""
        print("\n" + self.narrator.narrate("shutdown"))
        self.running = False
    
    def _register_periodic_tasks(self):
        """定期タスクをスケジューラに登録"""
        if not self.scheduler:
            return
        
        # HDD整理: 毎日1回（自律モード時のみ）
        self.scheduler.register(
            "HDD整理", 
            lambda: self.storage.archive_old_files(dry_run=False),
            interval_sec=86400,
            run_in_modes=["autonomous", "maintenance"]
        )
        
        # SSD80%チェック: 1時間ごと
        def check_ssd():
            import psutil
            usage = psutil.disk_usage("/")
            if usage.percent >= 80:
                result = self.storage.archive_old_files(dry_run=False)
                return f"SSD{usage.percent:.0f}% → {result['moved_files']}件移動"
            return f"SSD{usage.percent:.0f}% 正常"
        
        self.scheduler.register("SSD監視", check_ssd, interval_sec=3600)
        
        # ヘルスチェック: 5分ごと
        self.scheduler.register(
            "ヘルスチェック",
            lambda: self.health.run_all_checks(),
            interval_sec=300
        )
        
        # 自己修復: 10分ごと
        self.scheduler.register(
            "自己修復チェック",
            lambda: self.failsafe.check_and_recover(),
            interval_sec=600,
            run_in_modes=["autonomous", "maintenance", "safe"]
        )

        # 航海日誌生成: 毎日22:00（便宜上1日1回）
        def create_diary():
            try:
                diary_text = self.ships_log.generate_daily_report()
                save_path = f"/mnt/hdd/diary/{datetime.now().strftime('%Y%m%d')}.txt"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(diary_text)
                self.line.send_message(f"[LOG] 本日の航海日誌ばい！\n\n{diary_text}")
                # 音声でも語る (要約)
                summary = f"今日も一日お疲れ様、マスター。本日の航海日誌をまとめたよ。{diary_text[:200]}... 詳細はLINEを見てね。"
                self._send_audio_cmd("speak", {"text": summary})
                return "航海日誌生成完了"
            except Exception as e:
                self.agent.log(f"日誌生成エラー: {e}", "ERROR")
                return f"日誌エラー: {e}"

        self.scheduler.register("航海日誌", create_diary, interval_sec=86400)
    
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
        
        # LINE通知（起動通知は重要なので送信）
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
        
        # LINE通知（停止通知は重要なので送信）
        self.line.send_shutdown_notification(reason)
    
    def process_inbox(self):
        """
        イベントインボックスを処理
        - query → QuickResponder で即時回答
        - goal → agent.update_goal() で目標更新
        - 後方互換: user_commands.jsonl もサポート
        """
        # === 新形式: inbox.jsonl ===
        inbox_file = "/home/pi/autonomous_ai/commands/inbox.jsonl"
        
        if os.path.exists(inbox_file):
            try:
                with open(inbox_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if lines:
                    for line in lines:
                        try:
                            event = json.loads(line.strip())
                            self._handle_event(event)
                        except json.JSONDecodeError:
                            continue
                    
                    # 処理済みのインボックスを削除（履歴は残る）
                    os.remove(inbox_file)
                    
            except Exception as e:
                self.agent.log(f"インボックス処理エラー: {e}", "ERROR")
        
        # === 後方互換: user_commands.jsonl ===
        legacy_file = "/home/pi/autonomous_ai/commands/user_commands.jsonl"
        
        if os.path.exists(legacy_file):
            try:
                with open(legacy_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if lines:
                    last_command = json.loads(lines[-1])
                    command_text = last_command.get("command", "")
                    
                    if command_text:
                        # 旧形式は全てgoal扱い
                        self.agent.update_goal(command_text, source="user")
                        self.agent.log(f"レガシーコマンドを受信: {command_text}", "INFO")
                        self.line.send_status(f"✅ 目標を設定しました:\n{command_text}")
                        self.discord.send_message(f"📨 LINEから新しい目標を受信:\n{command_text}")
                    
                    os.remove(legacy_file)
                    
            except Exception as e:
                self.agent.log(f"レガシーコマンド読み取りエラー: {e}", "ERROR")
    
    AUDIO_CMD_FILE = "/tmp/shipos_audio_cmd.json"
    
    def _send_audio_cmd(self, action: str, params: dict):
        """AudioManagerに音声コマンドを送信（ファイルベースIPC）"""
        try:
            import json as _json
            cmd = {
                "action": action,
                "params": params,
                "timestamp": datetime.now().isoformat(),
                "source": "main"
            }
            with open(self.AUDIO_CMD_FILE, 'w', encoding='utf-8') as f:
                _json.dump(cmd, f, ensure_ascii=False)
            self.agent.log(f"音声コマンド送信完了: {action}", "DEBUG")
        except Exception as e:
            self.agent.log(f"音声コマンド送信エラー: {e}", "ERROR")

    def _inbox_worker(self):
        """低遅延でインボックスを監視するワーカー"""
        while self.running:
            try:
                self.process_inbox()
                time.sleep(2) # 2秒おきにチェック
            except Exception as e:
                time.sleep(5)

    def _handle_event(self, event: dict):
        """Individual event processing with system status and cleanup support"""
        event_type = event.get("type", "goal")
        text = event.get("text", "")
        uid = event.get("user_id", "")
        is_voice = (uid == "voice_ctrl")
        
        if not text:
            return
        
        # === 特殊コマンド判定 ===
        if "システムの状態" in text or "システム、報告" in text or "ステータス教えて" in text:
            from audio.system_status import get_system_status_text
            status_text = get_system_status_text()
            if not is_voice:
                self.line.send_message(f"[STAT] システムステータスばい：\n{status_text}")
            self._send_audio_cmd("speak", {"text": status_text})
            return

        if text.startswith("/cleanup") or "整理して" in text:
            dry_run = "dry" in text
            if not is_voice:
                self.line.send_message(f"[CLEAN] 整理を開始するばい... (dry_run={dry_run})")
            result = self.storage.archive_old_files(dry_run=dry_run)
            msg = f"[OK] 整理完了！\n移動: {result['moved_files']}件\n解放サイズ: {result['total_size']//1024//1024}MB"
            if not is_voice:
                self.line.send_message(msg)
            self._send_audio_cmd("speak", {"text": "ストレージの整理が終わったよ、マスター。"})
            return

        if event_type == "query":
            # === 質問 → QuickResponder で即時回答 ===
            self.agent.log(f"USER_QUERY受信: {text}", "INFO")
            if not is_voice:
                self.line.send_status("( ..)phi 思考中...")
            
            try:
                answer = self.quick_responder.respond(text)
                if not is_voice:
                    self.line.send_message(f"<< {answer}")
                self.agent.log(f"質問回答完了: {text[:30]}...", "INFO")
                # 回答を音声で読み上げ（最優先）
                self._send_audio_cmd("speak", {"text": answer[:200]})
                try:
                    self.discord.send_message(f">> 質問応答:\nQ: {text}\nA: {answer[:200]}")
                except Exception:
                    pass
            except Exception as e:
                self.agent.log(f"質問回答エラー: {e}", "ERROR")
                if not is_voice:
                    self.line.send_message("[!] 回答の生成中にエラーが発生したばい。")
                else:
                    self._send_audio_cmd("speak", {"text": "ごめん、ちょっとエラーが起きたばい"})
        
        elif event_type == "goal":
            # === 目標 → エージェントの目標を更新 ===
            self.agent.log(f"USER_GOAL受信: {text}", "INFO")
            self.agent.update_goal(text, source="user")
            
            if not is_voice:
                self.line.send_status(f"[OK] 目標を設定したばい:\n{text}")
            # 音声で通知
            self._send_audio_cmd("speak", {"text": f"マスター、了解ばい。{text[:50]}、やっておくね。"})
            try:
                self.discord.send_message(f">> LINEから新しい目標を受信:\n{text}")
            except Exception:
                pass
    
    def run_iteration_with_monitoring(self) -> bool:
        """
        監視付きイテレーション実行
        
        Returns:
            成功したらTrue
        """
        try:
            # イベントインボックス処理
            self.process_inbox()
            
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
                    # 重大エラー → LINEにも送信
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
                    # 重大 → LINEにも送信
                    self.line.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "警告"
                    )
                
                elif alert["level"] == "warning":
                    # 注意通知（Discordのみ）
                    self.discord.send_cost_alert(
                        alert["today_cost"],
                        alert["threshold"],
                        "注意"
                    )
            
            # エージェント実行
            success = self.agent.run_iteration()
            
            if success:
                # 使用量を記録
                self.billing.record_usage(
                    model="gpt-4o-mini",
                    input_tokens=1500,
                    output_tokens=500
                )
                
                # Discord通知（従来通り10回に1回）
                if self.agent.iteration_count % 10 == 0:
                    commands = self.agent.last_commands if hasattr(self.agent, 'last_commands') else []
                    results = self.agent.last_results if hasattr(self.agent, 'last_results') else []
                    thinking = self.agent.last_thinking if hasattr(self.agent, 'last_thinking') else ""
                    
                    # Discordは常に詳細ログを送信
                    self.discord.send_execution_log(
                        iteration=self.agent.iteration_count,
                        goal=self.agent.current_goal,
                        commands=commands,
                        results=results,
                        thinking=thinking
                    )
                    
                    # LINEは is_exec_log_enabled() がTrueの場合のみ
                    if self.line.is_exec_log_enabled():
                        self.line.send_execution_log(
                            iteration=self.agent.iteration_count,
                            goal=self.agent.current_goal,
                            commands=commands,
                            results=results
                        )
            
            return success
            
        except Exception as e:
            self.agent.log(f"イテレーション実行エラー: {e}", "ERROR")
            
            # エラー通知（Discordは常に）
            self.discord.send_error_notification(str(e))
            
            # 重大エラーのみLINEに通知
            self.line.send_error_notification(str(e))
            
            return False
    
    def run_maintenance(self):
        """定期メンテナンス"""
        print("定期メンテナンスを実行中...")
        self.line.send_status("🔧 定期メンテナンス実行中...")
        
        # ストレージチェック
        alert = self.storage.monitor_storage(threshold_percent=80.0)
        if alert:
            self.agent.log(alert["message"], "WARNING")
            self.discord.send_message(f"⚠️ {alert['message']}")
            # ストレージ逼迫は重大 → LINEにも通知
            self.line.send_status(f"⚠️ {alert['message']}")
            
            # 自動アーカイブ
            result = self.storage.archive_old_files(dry_run=False)
            if result["moved_files"] > 0:
                msg = f"古いファイルを{result['moved_files']}個アーカイブしました"
                self.agent.log(msg, "INFO")
                # Discordには詳細
                self.discord.send_message(
                    f"📦 {msg}\n"
                    f"対象ファイル: {result['total_files']}個\n"
                    f"移動成功: {result['moved_files']}個\n"
                    f"失敗: {result['failed_files']}個\n"
                    f"合計サイズ: {result['total_size'] / (1024**2):.2f} MB"
                )
                # LINEには短いサマリー
                self.line.send_status(f"📦 {msg}")
        
        # 一時ファイル削除
        deleted = self.storage.cleanup_temp_files()
        if deleted > 0:
            self.agent.log(f"一時ファイルを{deleted}個削除しました", "INFO")
        
        # メモリサマリー送信（Discordのみ）
        if self.agent.iteration_count % 50 == 0:
            summary = self.agent.memory.get_summary()
            self.discord.send_memory_summary(summary)
        
        self.line.send_status("✅ メンテナンス完了")
    
    def run(self):
        """メインループ"""
        print("=" * 60)
        print(self.narrator.startup_message())
        print("=" * 60)
        
        # OLED起動テロップ + 自己診断 (ハードウェアサービス側に移行)
        if self.oled:
            self.oled.set_running()
        
        # 起動通知
        self.send_startup_notifications()
        
        # メインループ
        iteration_interval = 30  # 秒
        maintenance_interval = 3600  # 1時間
        last_maintenance = time.time()
        
        while self.running:
            try:
                # イテレーション実行（インボックス処理も含む）
                self.run_iteration_with_monitoring()
                
                # AIState更新
                ai = get_ai_state()
                ai.mode = self.ship_mode.current_mode
                ai.goal = self.agent.current_goal or ""
                ai.ai_status = "active" if self.agent.iteration_count > 0 else "idle"
                ai.save()
                
                # スケジューラ（カレンダーモード切替 + 定期タスク）
                if self.scheduler:
                    mode_result = self.scheduler.check_calendar_mode()
                    if mode_result and mode_result.get("success"):
                        msg = self.narrator.mode_switch_message(
                            mode_result["old_mode"], mode_result["new_mode"],
                            mode_result.get("reason", "")
                        )
                        self.discord.send_message(msg)
                        self.line.send_status(msg[:100])
                        self.ships_log.record_action("mode_switch", msg)
                    
                    task_results = self.scheduler.run_due_tasks(self.ship_mode.current_mode)
                    for tr in task_results:
                        self.ships_log.record_action(
                            "scheduled_task", tr["name"], tr["success"]
                        )
                
                # ヘルスモニタ（ハートビート更新）
                self.health.update_heartbeat()
                
                # 航海日誌記録
                self.ships_log.record_action(
                    "iteration", f"iter#{self.agent.iteration_count}",
                    success=True
                )
                
                # 定期メンテナンス
                if time.time() - last_maintenance > maintenance_interval:
                    self.run_maintenance()
                    last_maintenance = time.time()
                
                # モード連動イテレーション間隔
                mode_config = self.ship_mode.get_config()
                wait_sec = mode_config.get("iteration_interval", iteration_interval)
                
                # 待機
                if self.running:
                    time.sleep(wait_sec)
                
            except KeyboardInterrupt:
                print("\nユーザーによる中断")
                break
            except Exception as e:
                self.agent.log(f"予期しないエラー: {e}", "ERROR")
                self.discord.send_error_notification(str(e), str(e))
                # 重大エラー → LINEにも通知
                self.line.send_error_notification(str(e))
                time.sleep(iteration_interval)
        
        # 停止処理
        self.shutdown()
    
    def shutdown(self):
        """シャットダウン処理"""
        print(self.narrator.shutdown_message())
        
        # 停止通知
        self.send_shutdown_notifications()
        
        # ブラウザ停止
        if self.browser:
            self.browser.stop()
        
        # OLEDシャットダウン
        if self.oled:
            self.oled.show_shutdown()
        
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
