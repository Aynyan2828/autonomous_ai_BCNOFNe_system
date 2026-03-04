#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS OLED ステータスコントローラ
OLEDDisplay ドライバを使い、起動テロップ・自己診断・5行表示を制御

表示レイアウト（5行）:
  1: BCNOFNe:SAIL (Scrolling)
  2: DEST:{goal}
  3: HELM:{state}
  4: TEMP:{cpu}C DISK:{disk}%
  5: IP:{LAN} TS:{Tailscale}
"""

import os
import time
import subprocess
import logging
from typing import Dict
from pathlib import Path
import psutil
from PIL import Image, ImageDraw, ImageFont
from version import get_version

# OLEDDisplayドライバをインポート
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hardware'))
    from oled_display import OLEDDisplay
    OLED_DRIVER_AVAILABLE = True
except ImportError:
    OLED_DRIVER_AVAILABLE = False

logger = logging.getLogger(__name__)


class OLEDStatus:
    """shipOS OLED ステータスコントローラ"""

    # 起動段階
    STAGE_INIT = "INIT"
    STAGE_LOAD = "LOAD"
    STAGE_DIAG = "DIAG"
    STAGE_READY = "READY"
    STAGE_RUNNING = "RUNNING"

    def __init__(self):
        self.current_stage = self.STAGE_INIT
        self.current_ip = "取得中..."
        self.ts_ip = "OFFLINE"
        
        # スクロール用
        version = get_version()
        self.banner_text = f"BCNOFNe v{version} : SAIL"
        self.scroll_pos = 127
        self.scroll_speed = 4  # 高速化 (以前より速く)

        # OLEDDisplayドライバを利用
        if OLED_DRIVER_AVAILABLE:
            self.display = OLEDDisplay()
        else:
            self.display = None
            logger.warning("OLEDDisplayドライバなし（開発環境モード）")

    def _render(self, lines: list):
        """ドライバ経由で行を表示"""
        if self.display:
            self.display.render_lines(lines)
        else:
            print("\n" + "=" * 30)
            for line in lines:
                print(f"  {line}")
            print("=" * 30)

    def _get_ip(self) -> str:
        """IPアドレスを取得 (LAN & Tailscale)"""
        lan_ip = "NONE"
        ts_ip = "OFFLINE"
        try:
            # LAN IP
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True, timeout=2
            )
            ips = result.stdout.strip().split()
            if ips:
                lan_ip = ips[0]
            
            # Tailscale IP
            ts_result = subprocess.run(
                ["tailscale", "ip", "-4"],
                capture_output=True, text=True, timeout=2
            )
            if ts_result.returncode == 0:
                ts_ip = ts_result.stdout.strip()
            
            self.ts_ip = ts_ip
            return lan_ip
        except Exception:
            return "ERR"

    # ====================
    # 起動テロップ
    # ====================
    def show_startup_telop(self):
        """BCNOFNe起動テロップ"""
        frames = [
            ["", "   BCNOFNe", "    ShipOS", "  起動開始...", ""],
            ["=== BOOT ===", "  Engine:  CHECK", "  Helm:    CHECK", "  Comms:   CHECK", "  Storage: CHECK"],
        ]
        for frame in frames:
            self._render(frame)
            time.sleep(1.5)

    # ====================
    # 自己診断
    # ====================
    def run_diagnostics(self) -> Dict[str, bool]:
        """起動時自己診断"""
        results = {}
        self.current_stage = self.STAGE_DIAG

        # 1) AIモジュール
        self._render(["[DIAG]", "AI modules..", "", "", ""])
        try:
            import agent_core  # noqa: F401
            import memory      # noqa: F401
            results["ai_modules"] = True
            self._render(["[DIAG]", "AI modules: OK", "", "", ""])
        except ImportError:
            results["ai_modules"] = False
            self._render(["[DIAG]", "AI modules: NG", "", "", ""])
        time.sleep(0.5)

        # 2) SSD
        ssd_path = Path("/home/pi/autonomous_ai_BCNOFNe_system")
        ssd_ok = ssd_path.exists() and os.access(str(ssd_path), os.W_OK)
        results["ssd"] = ssd_ok
        self._render(["[DIAG]", f"SSD: {'OK' if ssd_ok else 'NG'}", "", "", ""])
        time.sleep(0.3)

        # 3) HDD
        hdd_path = Path("/mnt/hdd/archive")
        hdd_ok = hdd_path.exists() and os.access(str(hdd_path), os.W_OK)
        results["hdd"] = hdd_ok
        self._render(["[DIAG]", f"HDD: {'OK' if hdd_ok else 'NOT MOUNT'}", "", "", ""])
        time.sleep(0.3)

        # 4) ネットワーク
        self.current_ip = self._get_ip()
        net_ok = self.current_ip not in ("NONE", "NET ERR")
        results["network"] = net_ok
        self._render(["[DIAG]", f"NET: {'OK' if net_ok else 'NG'}", f"IP: {self.current_ip}", "", ""])
        time.sleep(0.3)

        # 結果サマリー
        ok_count = sum(1 for v in results.values() if v)
        total = len(results)
        self._render([
            "=== DIAG DONE ===",
            f"  {ok_count}/{total} passed",
            "",
            f"  IP: {self.current_ip}",
            ""
        ])
        time.sleep(1)

        self.current_stage = self.STAGE_READY
        return results

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
            state: AI状態
            task: 現在のタスク
        """
        state_map = {
            "Idle": "WATCH",
            "Planning": "HELM",
            "Acting": "ENGINE",
            "Moving Files": "CARGO",
            "Error": "DAMAGE",
            "Wait Approval": "STANDBY",
        }
        display_state = state_map.get(state, state[:6].upper())

        # スクロール更新
        self.scroll_pos -= self.scroll_speed
        if self.scroll_pos < -120:
            self.scroll_pos = 127
            
        banner = " " * (self.scroll_pos // 6) + self.banner_text if self.scroll_pos > 0 else self.banner_text[abs(self.scroll_pos)//6:]
        # Note: 簡易スクロール（文字単位）
        
        goal_short = goal[:13] if goal else "---"
        task_short = task[:14] if task else "-"

        # ボイスモードの読み込み
        voice_mode = "HYB"
        try:
            import json
            if os.path.exists("/var/run/ai_audio_state.json"):
                with open("/var/run/ai_audio_state.json", "r") as f:
                    voice_mode = json.load(f).get("voice_mode", "HYB")
        except:
            pass

        lines = [
            banner,
            f"DEST:{goal_short}",
            f"HELM:{display_state} [{voice_mode}]",
            f"TEMP:-- DISK:--%",
            f"IP:{self.current_ip} TS:{self.ts_ip[:10]}",
        ]

        # CPU温度/ディスクをできれば取得
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_t = float(f.read().strip()) / 1000.0
            import psutil
            disk = psutil.disk_usage("/")
            lines[3] = f"TEMP:{cpu_t:.0f}C DISK:{disk.percent:.0f}%"
        except Exception:
            pass

        self._render(lines)

    # ====================
    # ライフサイクル
    # ====================
    def set_running(self):
        """Running段階に移行"""
        self.current_stage = self.STAGE_RUNNING
        logger.info("OLED: RUNNING段階へ移行")

    def show_shutdown(self):
        """シャットダウン表示"""
        self._render([
            "", "  BCNOFNe", "  Shutdown...", "  See you,", "  Master"
        ])
        time.sleep(2)
        self.clear()

    def stop(self):
        """停止"""
        self.show_shutdown()

    def clear(self):
        """画面クリア"""
        if self.display:
            self.display.clear()


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
        task="iter#42"
    )
