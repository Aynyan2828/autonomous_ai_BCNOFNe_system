#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED・ファン制御統合モジュール
システム状態、AI状態をOLEDに表示し、ファンを温度連動で制御
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fan_controller import FanController
from oled_display import OLEDDisplay


class OLEDFanController:
    """OLED・ファン制御統合クラス"""
    
    # AI状態ファイル
    AI_STATE_FILE = "/var/run/ai_state.json"
    
    # 更新間隔
    OLED_UPDATE_INTERVAL = 2.0  # 2秒
    FAN_UPDATE_INTERVAL = 5.0   # 5秒
    AI_STATE_CHECK_INTERVAL = 1.0  # 1秒
    
    def __init__(
        self,
        log_dir: str = "/home/pi/autonomous_ai/logs",
        enable_fan_warnings: bool = True
    ):
        """
        初期化
        
        Args:
            log_dir: ログディレクトリ
            enable_fan_warnings: ファン高温警告を有効にするか
        """
        # ログ設定
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "oled_fan.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
        # コンポーネント初期化
        self.fan_controller = FanController(enable_warnings=enable_fan_warnings)
        self.oled_display = OLEDDisplay()
        
        # タイマー
        self.last_oled_update = 0
        self.last_fan_update = 0
        self.last_ai_state_check = 0
        
        # AI状態キャッシュ
        self.current_ai_state = "Idle"
        self.current_ai_task = ""
        
        # 警告通知用（Discord/LINE連携）
        self.warning_callback = None
        
        self.logger.info("OLED・ファン制御システムを初期化しました")
    
    def set_warning_callback(self, callback):
        """
        警告通知コールバックを設定
        
        Args:
            callback: 警告通知関数 (temperature: float) -> None
        """
        self.warning_callback = callback
    
    def read_ai_state(self) -> dict:
        """
        AI状態ファイルを読み込み
        
        Returns:
            AI状態辞書
        """
        try:
            if os.path.exists(self.AI_STATE_FILE):
                with open(self.AI_STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            else:
                return {"state": "Idle", "task": "", "timestamp": ""}
        
        except Exception as e:
            self.logger.error(f"AI状態ファイル読み込みエラー: {e}")
            return {"state": "Error", "task": "", "timestamp": ""}
    
    def update_ai_state(self):
        """AI状態を更新"""
        current_time = time.time()
        
        if current_time - self.last_ai_state_check < self.AI_STATE_CHECK_INTERVAL:
            return
        
        self.last_ai_state_check = current_time
        
        ai_data = self.read_ai_state()
        self.current_ai_state = ai_data.get("state", "Idle")
        self.current_ai_task = ai_data.get("task", "")
    
    def update_fan(self) -> dict:
        """
        ファン制御を更新
        
        Returns:
            ファン状態
        """
        current_time = time.time()
        
        if current_time - self.last_fan_update < self.FAN_UPDATE_INTERVAL:
            return {}
        
        self.last_fan_update = current_time
        
        # ファン制御更新
        fan_status = self.fan_controller.update()
        
        # 高温警告が発生した場合
        if fan_status.get("warning_sent", False):
            if self.warning_callback:
                try:
                    self.warning_callback(fan_status["temperature"])
                except Exception as e:
                    self.logger.error(f"警告コールバックエラー: {e}")
        
        return fan_status
    
    def update_oled(self, fan_status: dict):
        """
        OLED表示を更新
        
        Args:
            fan_status: ファン状態
        """
        current_time = time.time()
        
        if current_time - self.last_oled_update < self.OLED_UPDATE_INTERVAL:
            return
        
        self.last_oled_update = current_time
        
        # システム情報取得
        system_info = self.oled_display.get_system_info()
        
        # ファン情報
        fan_rpm = self.fan_controller.get_fan_rpm()
        fan_status_text = fan_status.get("fan_status", "不明")
        
        # OLED表示
        self.oled_display.display(
            system_info=system_info,
            fan_status=fan_status_text,
            fan_rpm=fan_rpm,
            ai_state=self.current_ai_state
        )
    
    def run(self):
        """メインループ"""
        self.logger.info("OLED・ファン制御システムを開始します")
        
        # 起動メッセージ
        self.oled_display.show_message("Autonomous AI\nSystem\nStarting...", 2.0)
        
        try:
            fan_status = {}
            
            while True:
                # AI状態更新
                self.update_ai_state()
                
                # ファン制御更新
                new_fan_status = self.update_fan()
                if new_fan_status:
                    fan_status = new_fan_status
                
                # OLED表示更新
                self.update_oled(fan_status)
                
                # 短いスリープ（CPU負荷軽減）
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            self.logger.info("終了シグナルを受信しました")
        
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}", exc_info=True)
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """クリーンアップ"""
        self.logger.info("クリーンアップ中...")
        self.oled_display.show_message("System\nShutting Down...", 1.0)
        self.oled_display.clear()
        self.fan_controller.cleanup()
        self.logger.info("クリーンアップ完了")


def warning_notification(temperature: float):
    """
    高温警告通知（Discord/LINE連携用）
    
    Args:
        temperature: CPU温度
    """
    # ここでDiscord/LINE通知を送信
    # 実装例:
    # from discord_notifier import DiscordNotifier
    # notifier = DiscordNotifier(webhook_url="...")
    # notifier.send(f"🔥 CPU温度が危険レベルです: {temperature:.1f}°C")
    
    print(f"🔥 警告: CPU温度が {temperature:.1f}°C に達しました")


def main():
    """メイン関数"""
    controller = OLEDFanController()
    
    # 警告通知コールバック設定
    controller.set_warning_callback(warning_notification)
    
    # 実行
    controller.run()


if __name__ == "__main__":
    main()
