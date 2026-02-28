#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED ステータス表示モジュール
5行表示 + IP固定 + 起動テロップ + 自己診断

表示レイアウト（5行）:
  1: autonomous AI: ONLINE
  2: GOAL: (短縮表示)
  3: STATE: THINK/RUN/IDLE/ERR
  4: TASK: LINE送信/ログ出力等
  5: IP: xxx.xxx.xxx.xxx
"""

import os
import json
import time
import subprocess
import logging
from typing import Optional, Dict
from pathlib import Path

try:
    from board import SCL, SDA
    import busio
    from PIL import Image, ImageDraw, ImageFont
    import adafruit_ssd1306
    OLED_AVAILABLE = True
except ImportError:
    OLED_AVAILABLE = False


class OLEDStatus:
    """OLED 5行ステータス表示クラス"""
    
    # ディスプレイ設定
    WIDTH = 128
    HEIGHT = 64
    I2C_ADDRESS = 0x3C
    LINE_HEIGHT = 12
    MAX_CHARS = 21
    
    # AI状態ファイル
    AI_STATE_FILE = "/var/run/ai_state.json"
    
    # 起動段階
    STAGE_INIT = "Initializing"
    STAGE_LOAD = "Loading"
    STAGE_READY = "Ready"
    STAGE_RUNNING = "Running"
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.oled = None
        self.image = None
        self.draw = None
        self.font = None
        self.current_stage = self.STAGE_INIT
        self.current_ip = "取得中..."
        
        if OLED_AVAILABLE:
            self._setup_oled()
        else:
            self.logger.warning("OLEDライブラリなし（開発環境モード）")
    
    def _setup_oled(self):
        """OLED初期化"""
        try:
            i2c = busio.I2C(SCL, SDA)
            self.oled = adafruit_ssd1306.SSD1306_I2C(
                self.WIDTH, self.HEIGHT, i2c, addr=self.I2C_ADDRESS
            )
            self.oled.fill(0)
            self.oled.show()
            
            self.image = Image.new("1", (self.WIDTH, self.HEIGHT))
            self.draw = ImageDraw.Draw(self.image)
            
            try:
                self.font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 9
                )
            except Exception:
                self.font = ImageFont.load_default()
            
            self.logger.info("OLED初期化完了")
        except Exception as e:
            self.logger.error(f"OLED初期化エラー: {e}")
            self.oled = None
    
    def _truncate(self, text: str, max_len: int = None) -> str:
        """テキストを指定幅に切り詰め"""
        max_len = max_len or self.MAX_CHARS
        if len(text) > max_len:
            return text[:max_len - 2] + ".."
        return text
    
    def get_ip_address(self) -> str:
        """IPアドレスを取得"""
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True, timeout=3
            )
            ips = result.stdout.strip().split()
            return ips[0] if ips else "NONE"
        except Exception:
            return "NET ERR"
    
    # ====================
    # 起動テロップ
    # ====================
    def show_startup_telop(self):
        """起動テロップをスクロール表示"""
        telop = "autonomous AI system BCNOFNe 起動開始"
        self._show_message(telop, duration=2.0)
    
    # ====================
    # 自己診断
    # ====================
    def run_diagnostics(self) -> Dict[str, bool]:
        """
        起動時自己診断を実行
        
        Returns:
            診断結果 {項目名: 成功/失敗}
        """
        results = {}
        
        # 1) AIモジュールロード確認
        self._update_stage(self.STAGE_LOAD)
        self._show_diagnostic("AI modules", "Loading...")
        try:
            import agent_core  # noqa: F401
            import memory      # noqa: F401
            results["ai_modules"] = True
            self._show_diagnostic("AI modules", "OK")
        except ImportError as e:
            results["ai_modules"] = False
            self._show_diagnostic("AI modules", f"ERR: {e}")
        time.sleep(0.5)
        
        # 2) SSD確認
        ssd_path = Path("/home/pi/autonomous_ai")
        self._show_diagnostic("SSD", "Checking...")
        if ssd_path.exists() and os.access(str(ssd_path), os.W_OK):
            results["ssd"] = True
            self._show_diagnostic("SSD", "OK")
        else:
            results["ssd"] = False
            self._show_diagnostic("SSD", "NOT FOUND")
        time.sleep(0.3)
        
        # 3) HDD確認
        hdd_path = Path("/mnt/hdd/archive")
        self._show_diagnostic("HDD", "Checking...")
        if hdd_path.exists() and os.access(str(hdd_path), os.W_OK):
            results["hdd"] = True
            self._show_diagnostic("HDD", "OK")
        else:
            results["hdd"] = False
            self._show_diagnostic("HDD", "NOT MOUNTED")
        time.sleep(0.3)
        
        # 4) IP取得
        self._show_diagnostic("Network", "Checking...")
        self.current_ip = self.get_ip_address()
        if self.current_ip != "NONE" and self.current_ip != "NET ERR":
            results["network"] = True
            self._show_diagnostic("Network", f"OK: {self.current_ip}")
        else:
            results["network"] = False
            self._show_diagnostic("Network", "FAILED")
        time.sleep(0.3)
        
        # Ready段階
        self._update_stage(self.STAGE_READY)
        time.sleep(0.5)
        
        return results
    
    def _show_diagnostic(self, item: str, status: str):
        """診断項目を表示"""
        msg = f"DIAG: {item}\n{status}"
        if self.oled and self.draw:
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
            self.draw.text((0, 0), f"[{self.current_stage}]", font=self.font, fill=255)
            self.draw.text((0, 16), f"CHECK: {item}", font=self.font, fill=255)
            self.draw.text((0, 32), f"  -> {status}", font=self.font, fill=255)
            self.oled.image(self.image)
            self.oled.show()
        else:
            print(f"[DIAG] {item}: {status}")
    
    def _update_stage(self, stage: str):
        """起動段階を更新"""
        self.current_stage = stage
        self.logger.info(f"起動段階: {stage}")
    
    # ====================
    # 5行表示（メイン）
    # ====================
    def update_display(
        self,
        goal: str = "",
        state: str = "IDLE",
        task: str = ""
    ):
        """
        5行ステータス表示を更新
        
        Args:
            goal: 現在の目標
            state: AI状態 (THINK/RUN/IDLE/ERR)
            task: 現在のタスク
        """
        # 状態マッピング
        state_map = {
            "Idle": "IDLE",
            "Planning": "THINK",
            "Acting": "RUN",
            "Moving Files": "FILE",
            "Error": "ERR",
            "Wait Approval": "WAIT",
        }
        display_state = state_map.get(state, state[:5].upper())
        
        # 5行構成
        lines = [
            self._truncate(f"AI: ONLINE"),
            self._truncate(f"GOAL:{goal[:15] if goal else 'なし'}"),
            self._truncate(f"STATE:{display_state}"),
            self._truncate(f"TASK:{task[:14] if task else '-'}"),
            self._truncate(f"IP:{self.current_ip}"),
        ]
        
        if self.oled and self.draw:
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
            for i, line in enumerate(lines):
                self.draw.text((0, i * self.LINE_HEIGHT), line, font=self.font, fill=255)
            self.oled.image(self.image)
            self.oled.show()
        else:
            # コンソール出力（開発環境用）
            print("\n" + "=" * 30)
            for line in lines:
                print(f"  {line}")
            print("=" * 30)
    
    # ====================
    # ユーティリティ
    # ====================
    def _show_message(self, message: str, duration: float = 2.0):
        """メッセージを表示"""
        if self.oled and self.draw:
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
            words = message.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + " " + word) <= self.MAX_CHARS:
                    current_line = (current_line + " " + word).strip()
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            y = max(0, (self.HEIGHT - len(lines) * self.LINE_HEIGHT) // 2)
            for line in lines:
                self.draw.text((0, y), line, font=self.font, fill=255)
                y += self.LINE_HEIGHT
            
            self.oled.image(self.image)
            self.oled.show()
            time.sleep(duration)
        else:
            print(f"[TELOP] {message}")
    
    def set_running(self):
        """Running段階に移行"""
        self._update_stage(self.STAGE_RUNNING)
    
    def clear(self):
        """画面クリア"""
        if self.oled:
            try:
                self.oled.fill(0)
                self.oled.show()
            except Exception as e:
                self.logger.error(f"画面クリアエラー: {e}")
    
    def show_shutdown(self):
        """シャットダウンメッセージ表示"""
        self._show_message("System Shutdown...", 1.0)
        self.clear()


# テスト用
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    oled = OLEDStatus()
    
    print("=== 起動テロップ ===")
    oled.show_startup_telop()
    
    print("\n=== 自己診断 ===")
    results = oled.run_diagnostics()
    for k, v in results.items():
        print(f"  {k}: {'OK' if v else 'FAIL'}")
    
    print("\n=== 5行表示 ===")
    oled.set_running()
    oled.update_display(
        goal="ファイルを整理する",
        state="Acting",
        task="LINE送信中"
    )
