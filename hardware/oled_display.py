#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED表示ドライバ
SSD1306 I2C OLEDの低レベル制御のみを担当

責務:
  - I2C / SSD1306 ハードウェア初期化
  - テキスト描画（座標指定 / 行指定）
  - 画面クリア / 画面転送
  - フォント管理

shipOS固有のレイアウト・演出ロジックはここに含めない。
それらは oled_fan_controller.py (上位コントローラ) が担当する。
"""

import time
import logging
from typing import Optional, List

try:
    from board import SCL, SDA
    import busio
    from PIL import Image, ImageDraw, ImageFont
    import adafruit_ssd1306
    OLED_AVAILABLE = True
except ImportError:
    OLED_AVAILABLE = False

logger = logging.getLogger(__name__)


class OLEDDisplay:
    """SSD1306 OLEDディスプレイ 表示ドライバ"""

    # ハードウェア定数
    WIDTH = 128
    HEIGHT = 64
    I2C_ADDRESS = 0x3C

    # デフォルト描画設定
    DEFAULT_FONT_SIZE = 10
    DEFAULT_LINE_HEIGHT = 12   # 5行 × 12px = 60px（64px内に収まる）
    MAX_CHARS_PER_LINE = 21    # 10ptモノスペースで約21文字

    def __init__(self, i2c_address: int = 0x3C):
        """
        ドライバ初期化

        Args:
            i2c_address: I2Cアドレス（デフォルト 0x3C）
        """
        self.I2C_ADDRESS = i2c_address
        self.oled = None
        self.image = None
        self.draw = None
        self.font = None
        self.available = False

        if OLED_AVAILABLE:
            self._init_hardware()
        else:
            logger.warning("OLEDライブラリ未インストール（開発環境モード）")

    def _init_hardware(self):
        """I2C + SSD1306 ハードウェア初期化"""
        try:
            i2c = busio.I2C(SCL, SDA)
            self.oled = adafruit_ssd1306.SSD1306_I2C(
                self.WIDTH, self.HEIGHT, i2c, addr=self.I2C_ADDRESS
            )
            self.oled.fill(0)
            self.oled.show()

            # 描画バッファ
            self.image = Image.new("1", (self.WIDTH, self.HEIGHT))
            self.draw = ImageDraw.Draw(self.image)

            # フォント
            self.font = self._load_font()
            self.available = True
            logger.info("OLEDドライバ初期化完了")

        except Exception as e:
            logger.error(f"OLEDドライバ初期化エラー: {e}")
            self.oled = None
            self.available = False

    def _load_font(self, size: int = 10):
        """フォントをロード"""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # ========== 基本描画API ==========

    def is_available(self) -> bool:
        """OLEDが利用可能か"""
        return self.available and self.oled is not None

    def clear(self):
        """画面クリア（バッファ + 転送）"""
        if self.oled:
            try:
                self.oled.fill(0)
                self.oled.show()
            except Exception as e:
                logger.error(f"画面クリアエラー: {e}")

    def clear_buffer(self):
        """描画バッファのみクリア（転送しない）"""
        if self.draw:
            self.draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), outline=0, fill=0)

    def flush(self):
        """描画バッファをOLEDに転送"""
        if self.oled and self.image:
            try:
                self.oled.image(self.image)
                self.oled.show()
            except Exception as e:
                logger.error(f"OLED転送エラー: {e}")

    def draw_text(self, x: int, y: int, text: str, fill: int = 255):
        """
        指定座標にテキストを描画（バッファのみ、転送しない）

        Args:
            x: X座標
            y: Y座標
            text: テキスト
            fill: 色（255=白, 0=黒）
        """
        if self.draw:
            self.draw.text((x, y), text, font=self.font, fill=fill)

    def draw_text_line(self, line_num: int, text: str, fill: int = 255):
        """
        行番号指定でテキストを描画（0始まり、バッファのみ）

        Args:
            line_num: 行番号（0-4）
            text: テキスト
            fill: 色
        """
        if self.draw:
            y = line_num * self.DEFAULT_LINE_HEIGHT
            truncated = self.truncate(text)
            self.draw.text((0, y), truncated, font=self.font, fill=fill)

    def draw_rect(self, x0: int, y0: int, x1: int, y1: int,
                  outline: int = 255, fill: int = 0):
        """矩形描画（バッファのみ）"""
        if self.draw:
            self.draw.rectangle((x0, y0, x1, y1), outline=outline, fill=fill)

    # ========== 高レベル描画ヘルパー ==========

    def render_lines(self, lines: List[str]):
        """
        最大5行のテキストを描画して転送

        Args:
            lines: 表示する行のリスト（最大5行）
        """
        if not self.is_available():
            # コンソールフォールバック
            self._console_fallback(lines)
            return

        try:
            self.clear_buffer()
            for i, line in enumerate(lines[:5]):
                self.draw_text_line(i, line)
            self.flush()
        except Exception as e:
            logger.error(f"render_lines エラー: {e}")

    def show_message(self, message: str, duration: float = 2.0):
        """
        メッセージを表示して一定時間待つ

        Args:
            message: 表示テキスト（\\n区切り可）
            duration: 表示時間（秒）
        """
        lines = message.split('\n')
        # 5行に満たない場合は上下中央寄せ
        while len(lines) < 5:
            lines.append("")
        self.render_lines(lines[:5])
        time.sleep(duration)

    # ========== ユーティリティ ==========

    def truncate(self, text: str, max_len: int = 0) -> str:
        """文字列を最大長に切り詰め"""
        if max_len <= 0:
            max_len = self.MAX_CHARS_PER_LINE
        if len(text) > max_len:
            return text[:max_len - 2] + ".."
        return text

    def _console_fallback(self, lines: List[str]):
        """コンソール出力（OLEDが利用できない場合）"""
        print("\n" + "=" * 30)
        for line in lines:
            print(f"  {line}")
        print("=" * 30)


# ========== テスト ==========
def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    d = OLEDDisplay()

    print(f"OLED available: {d.is_available()}")

    d.show_message("OLED Driver\nTest Mode", 2.0)
    d.render_lines(["Line 0", "Line 1", "Line 2", "Line 3", "Line 4"])
    time.sleep(3)
    d.clear()
    print("テスト完了")


if __name__ == "__main__":
    main()
