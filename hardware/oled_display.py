#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED表示モジュール
システム状態とAI状態をリアルタイム表示
"""

import time
import psutil
import shutil
import logging
from typing import Optional

try:
    from board import SCL, SDA
    import busio
    from PIL import Image, ImageDraw, ImageFont
    import adafruit_ssd1306
    OLED_AVAILABLE = True
except ImportError:
    OLED_AVAILABLE = False


class OLEDDisplay:
    """OLEDディスプレイ制御クラス"""
    
    # ディスプレイ設定
    WIDTH = 128
    HEIGHT = 64
    I2C_ADDRESS = 0x3C
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.oled = None
        self.image = None
        self.draw = None
        self.font = None
        
        if OLED_AVAILABLE:
            self._setup_oled()
        else:
            self.logger.warning("OLEDライブラリが利用できません（開発環境モード）")
    
    def _setup_oled(self):
        """OLED初期化"""
        try:
            # I2C初期化
            i2c = busio.I2C(SCL, SDA)
            
            # OLED初期化
            self.oled = adafruit_ssd1306.SSD1306_I2C(
                self.WIDTH,
                self.HEIGHT,
                i2c,
                addr=self.I2C_ADDRESS
            )
            
            # クリア
            self.oled.fill(0)
            self.oled.show()
            
            # 描画用イメージ作成
            self.image = Image.new("1", (self.WIDTH, self.HEIGHT))
            self.draw = ImageDraw.Draw(self.image)
            
            # フォント読み込み（デフォルトフォント）
            try:
                # システムフォントを試す
                self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
            except:
                # デフォルトフォント
                self.font = ImageFont.load_default()
            
            self.logger.info("OLEDディスプレイを初期化しました")
            
        except Exception as e:
            self.logger.error(f"OLED初期化エラー: {e}")
            self.oled = None
    
    def get_system_info(self) -> dict:
        """
        システム情報を取得
        
        Returns:
            システム情報辞書
        """
        try:
            # CPU温度
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
            except:
                cpu_temp = 0.0
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            mem_percent = memory.percent
            
            # ディスク使用率（SSD: /）
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            return {
                "cpu_temp": cpu_temp,
                "cpu_percent": cpu_percent,
                "mem_percent": mem_percent,
                "disk_percent": disk_percent
            }
        
        except Exception as e:
            self.logger.error(f"システム情報取得エラー: {e}")
            return {
                "cpu_temp": 0.0,
                "cpu_percent": 0.0,
                "mem_percent": 0.0,
                "disk_percent": 0.0
            }
    
    def format_line(self, text: str, max_width: int = 21) -> str:
        """
        テキストを指定幅に整形
        
        Args:
            text: 元のテキスト
            max_width: 最大文字数
            
        Returns:
            整形されたテキスト
        """
        if len(text) > max_width:
            return text[:max_width-2] + ".."
        return text
    
    def display(
        self,
        system_info: dict,
        fan_status: str,
        fan_rpm: Optional[int],
        ai_state: str
    ):
        """
        情報を表示
        
        Args:
            system_info: システム情報
            fan_status: ファン状態
            fan_rpm: ファンRPM
            ai_state: AI状態
        """
        if not self.oled or not self.draw:
            # OLEDが利用できない場合はコンソールに出力
            self._console_display(system_info, fan_status, fan_rpm, ai_state)
            return
        
        try:
            # 画面クリア
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
            
            # 1行目: CPU温度 + CPU使用率
            line1 = f"CPU:{system_info['cpu_temp']:.0f}C Load:{system_info['cpu_percent']:.0f}%"
            self.draw.text((0, 0), line1, font=self.font, fill=255)
            
            # 2行目: メモリ使用率 + ディスク使用率
            line2 = f"Mem:{system_info['mem_percent']:.0f}% SSD:{system_info['disk_percent']:.0f}%"
            self.draw.text((0, 16), line2, font=self.font, fill=255)
            
            # 3行目: ファン状態
            if fan_rpm is not None and fan_rpm > 0:
                line3 = f"Fan:{fan_rpm}RPM"
            else:
                line3 = f"Fan:{fan_status}"
            self.draw.text((0, 32), line3, font=self.font, fill=255)
            
            # 4行目: AI状態
            line4 = f"AI:{ai_state}"
            line4 = self.format_line(line4, 21)
            self.draw.text((0, 48), line4, font=self.font, fill=255)
            
            # ディスプレイに表示
            self.oled.image(self.image)
            self.oled.show()
            
        except Exception as e:
            self.logger.error(f"OLED表示エラー: {e}")
    
    def _console_display(
        self,
        system_info: dict,
        fan_status: str,
        fan_rpm: Optional[int],
        ai_state: str
    ):
        """
        コンソールに表示（開発環境用）
        
        Args:
            system_info: システム情報
            fan_status: ファン状態
            fan_rpm: ファンRPM
            ai_state: AI状態
        """
        print("\n" + "="*40)
        print(f"CPU: {system_info['cpu_temp']:.1f}°C  Load: {system_info['cpu_percent']:.1f}%")
        print(f"Mem: {system_info['mem_percent']:.1f}%  SSD: {system_info['disk_percent']:.1f}%")
        
        if fan_rpm is not None and fan_rpm > 0:
            print(f"Fan: {fan_rpm} RPM")
        else:
            print(f"Fan: {fan_status}")
        
        print(f"AI: {ai_state}")
        print("="*40)
    
    def show_message(self, message: str, duration: float = 2.0):
        """
        メッセージを表示
        
        Args:
            message: 表示するメッセージ
            duration: 表示時間（秒）
        """
        if not self.oled or not self.draw:
            print(f"[MESSAGE] {message}")
            return
        
        try:
            # 画面クリア
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)
            
            # メッセージを中央に表示
            lines = message.split('\n')
            y = (self.HEIGHT - len(lines) * 16) // 2
            
            for line in lines:
                line = self.format_line(line, 21)
                self.draw.text((0, y), line, font=self.font, fill=255)
                y += 16
            
            # ディスプレイに表示
            self.oled.image(self.image)
            self.oled.show()
            
            time.sleep(duration)
            
        except Exception as e:
            self.logger.error(f"メッセージ表示エラー: {e}")
    
    def clear(self):
        """画面をクリア"""
        if self.oled:
            try:
                self.oled.fill(0)
                self.oled.show()
            except Exception as e:
                self.logger.error(f"画面クリアエラー: {e}")


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    display = OLEDDisplay()
    
    try:
        print("OLED表示テスト開始（Ctrl+Cで終了）")
        
        # 起動メッセージ
        display.show_message("System\nStarting...", 2.0)
        
        # メインループ
        ai_states = ["Idle", "Planning", "Acting", "Moving Files", "Error", "Wait Approval"]
        state_index = 0
        
        while True:
            system_info = display.get_system_info()
            ai_state = ai_states[state_index % len(ai_states)]
            
            display.display(
                system_info=system_info,
                fan_status="中速",
                fan_rpm=2500,
                ai_state=ai_state
            )
            
            state_index += 1
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n終了します")
        display.clear()


if __name__ == "__main__":
    main()
