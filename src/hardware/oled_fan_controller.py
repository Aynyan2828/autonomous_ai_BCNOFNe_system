#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS OLED・ファン制御統合モジュール
- 航海用語ベースの5行表示
- shipOSモードシステム連携
- Mood算出（aynyan人格）
- ファン温度連動制御
- 日記素材として mood_log.jsonl 保存
"""

import os
import json
import time
import logging
import socket
import subprocess
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fan_controller import FanController
from oled_display import OLEDDisplay


JST = timezone(timedelta(hours=9))


# shipOS モード表示マッピング（航海用語）
SHIP_MODE_DISPLAY = {
    "autonomous":  "SAIL",    # 自律航海
    "user_first":  "PORT",    # 入港待機
    "maintenance": "DOCK",    # ドック入り
    "power_save":  "ANCHOR",  # 停泊
    "safe":        "SOS",     # 救難信号
    "BOOT":        "BOOT",
    "STORM":       "STORM",
    "EMERGENCY":   "EMERGNCY",
    "SHUTDOWN":    "HALT",
}

SHIP_MODE_ASCII = {
    "autonomous":  ">===>",
    "user_first":  "[=]",
    "maintenance": "{=}",
    "power_save":  "---",
    "safe":        "!!!",
    "BOOT":        ".oOo.",
    "STORM":       "~~~~~",
    "EMERGENCY":   "!!!",
    "SHUTDOWN":    "...",
}

# AI状態 → 顔文字
AI_STATE_FACE = {
    "idle":         "(-_-)",
    "thinking":     "( ..)phi",
    "active":       "(`-w-')",
    "error":        "(x_x)",
}

def get_ai_face(state: str) -> str:
    st = (state or "").lower()
    if "error" in st: return AI_STATE_FACE["error"]
    if "acting" in st or "planning" in st: return AI_STATE_FACE["active"]
    if "listen" in st: return "(o_o)"
    if "wait" in st: return "(-_-)zZ"
    return AI_STATE_FACE["idle"]


@dataclass
class Mood:
    score: int           # 0-100
    emoji: str           # 😊😗😨😤🥶🥵😎 etc
    line: str            # 一言（aynyan人格）
    reasons: Dict[str, Any]


class OLEDFanController:
    """shipOS OLED・ファン制御統合クラス"""

    # AI状態ファイル
    AI_STATE_FILE = "/var/run/ai_state.json"

    # shipOSモード状態ファイル
    SHIP_MODE_FILE = "/home/pi/autonomous_ai/state/ship_mode.json"

    # 状態ログ
    STATE_DIR = "/home/pi/autonomous_ai/state"
    MOOD_LOG_PATH = os.path.join(STATE_DIR, "mood_log.jsonl")
    LAST_TOUCH_PATH = os.path.join(STATE_DIR, "last_user_touch.txt")
    LINE_STATUS_FILE = "/tmp/shipos_line_status.json"

    # 更新間隔
    OLED_UPDATE_INTERVAL = 0.12  # 少し高速化
    SYS_UPDATE_INTERVAL = 2.0
    FAN_UPDATE_INTERVAL = 5.0
    AI_STATE_CHECK_INTERVAL = 1.0

    def __init__(
        self,
        log_dir: str = "/home/pi/autonomous_ai/logs",
        enable_fan_warnings: bool = True
    ):
        """初期化"""
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(self.STATE_DIR, exist_ok=True)

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
        self.last_oled_update = 0.0
        self.last_sys_update = 0.0
        self.last_fan_update = 0.0
        self.last_ai_state_check = 0.0

        # AI状態キャッシュ
        self.current_ai_state = "Idle"
        self.current_ai_task = ""

        # shipOSモードキャッシュ
        self.current_ship_mode = "autonomous"

        # IP アドレスキャッシュ
        self._ip_cache = "..."
        self._ts_cache = "OFFLINE"
        self._ip_cache_time = 0.0
        self._ip_offset = 0

        # System info cache
        self._system_info_cache = {}

        # Mood
        self.current_mood: Optional[Mood] = None

        # 警告通知コールバック
        self.warning_callback = None

        self.logger.info("shipOS OLED・ファン制御システムを初期化しました")

    # ========== ユーザータッチ ==========

    def touch(self):
        """ユーザーが構った時刻を保存"""
        try:
            with open(self.LAST_TOUCH_PATH, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except Exception as e:
            self.logger.debug(f"touch更新失敗: {e}")

    def _read_last_touch_ts(self) -> Optional[float]:
        try:
            if not os.path.exists(self.LAST_TOUCH_PATH):
                return None
            with open(self.LAST_TOUCH_PATH, "r", encoding="utf-8") as f:
                return float(f.read().strip())
        except Exception:
            return None

    # ========== 警告コールバック ==========

    def set_warning_callback(self, callback):
        """警告通知コールバックを設定"""
        self.warning_callback = callback

    # ========== AI状態 / shipOSモード読み込み ==========

    def read_ai_state(self) -> dict:
        """AI状態ファイルを読み込み"""
        try:
            if os.path.exists(self.AI_STATE_FILE):
                with open(self.AI_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"state": "Idle", "task": "", "timestamp": ""}
        except Exception as e:
            self.logger.error(f"AI状態読み込みエラー: {e}")
            return {"state": "Error", "task": "", "timestamp": ""}

    def read_ship_mode(self) -> str:
        """shipOSモードを読み込み"""
        try:
            if os.path.exists(self.SHIP_MODE_FILE):
                with open(self.SHIP_MODE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("mode", "autonomous")
        except Exception:
            pass
        return "autonomous"

    def update_ai_state(self):
        """AI状態とshipOSモードを更新"""
        current_time = time.time()

        if current_time - self.last_ai_state_check < self.AI_STATE_CHECK_INTERVAL:
            return

        self.last_ai_state_check = current_time

        ai_data = self.read_ai_state()
        self.current_ai_state = ai_data.get("state", "Idle") or "Idle"
        self.current_ai_task = ai_data.get("task", "") or ""
        self.current_ship_mode = self.read_ship_mode()

    def _force_mode(self, mode: str, reason: str):
        """設定ファイルに直接モードを書き込む（緊急用）"""
        try:
            self.current_ship_mode = mode
            os.makedirs(os.path.dirname(self.SHIP_MODE_FILE), exist_ok=True)
            with open(self.SHIP_MODE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["mode"] = mode
            state["since"] = datetime.now().isoformat()
            state["override"] = True
            with open(self.SHIP_MODE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            self.logger.warning(f"強制モード移行: {mode} ({reason})")
        except Exception as e:
            self.logger.error(f"モード強制移行失敗: {e}")

    def _check_line_status(self) -> str:
        """LINEの送受信状態をチェックして文字列を返す"""
        try:
            if not os.path.exists(self.LINE_STATUS_FILE):
                return ""
            
            with open(self.LINE_STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 5秒以内のステータスのみ有効
            ts = data.get("timestamp", 0.0)
            if time.time() - ts <= 5.0:
                direction = data.get("direction", "")
                if direction == "RX":
                    return " [LINE: RX] "
                elif direction == "TX":
                    return " [LINE: TX] "
        except Exception:
            pass
        return ""

    # ========== システム状態 / IP取得 ==========

    def get_system_info(self) -> dict:
        info = {"cpu_temp": 0.0, "disk_percent": 0.0, "cpu_percent": 0.0, "mem_percent": 0.0}
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                info["cpu_temp"] = float(f.read().strip()) / 1000.0
        except Exception: pass
        try:
            import psutil
            info["disk_percent"] = psutil.disk_usage("/").percent
            info["cpu_percent"] = psutil.cpu_percent()
            info["mem_percent"] = psutil.virtual_memory().percent
        except Exception: pass
        return info

    def _update_ips(self):
        """IPアドレスを一括取得（60秒キャッシュ）"""
        if time.time() - self._ip_cache_time < 60:
            return
        
        # LAN
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True, timeout=3
            )
            ips = result.stdout.strip().split()
            # dockerやtailscale等を除外
            lan_ips = [ip for ip in ips if not ip.startswith("100.") and ":" not in ip]
            self._ip_cache = lan_ips[0] if lan_ips else "---.---.---.---"
        except Exception:
            self._ip_cache = "ERR"
            
        # Tailscale
        try:
            result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3)
            self._ts_cache = result.stdout.strip() if result.returncode == 0 else "OFFLINE"
        except Exception:
            self._ts_cache = "OFFLINE"
            
        self._ip_cache_time = time.time()

    # ========== ネット疎通 ==========

    def _check_network(self, host: str = "1.1.1.1", port: int = 53, timeout: float = 0.7) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    # ========== Mood算出（aynyan人格） ==========

    def compute_mood(self, system_info: dict, ai_state: str) -> Mood:
        cpu_t = float(system_info.get("cpu_temp", 0.0))
        disk = float(system_info.get("disk_percent", 0.0))
        net_ok = bool(system_info.get("net_ok", True))

        last_touch = self._read_last_touch_ts()
        idle_min = None
        if last_touch is not None:
            idle_min = max(0.0, (time.time() - last_touch) / 60.0)

        score = 80
        reasons: Dict[str, Any] = {}

        # CPU温度
        if cpu_t >= 75:
            score -= 35; reasons["cpu_hot"] = cpu_t
        elif cpu_t >= 65:
            score -= 20; reasons["cpu_warm"] = cpu_t
        elif 0 < cpu_t <= 45:
            score += 5; reasons["cpu_cool"] = cpu_t

        # ディスク
        if disk >= 92:
            score -= 30; reasons["disk_critical"] = disk
        elif disk >= 85:
            score -= 15; reasons["disk_high"] = disk
        else:
            score += 3; reasons["disk_ok"] = disk

        # ネット断
        if not net_ok:
            score -= 18; reasons["net_down"] = True

        # 放置
        if idle_min is not None:
            reasons["idle_min"] = round(idle_min, 1)
            if idle_min >= 180:
                score -= 22
            elif idle_min >= 60:
                score -= 12
            elif idle_min <= 10:
                score += 6
        else:
            reasons["idle_unknown"] = True

        # AI状態補正
        st = (ai_state or "").lower()
        if "error" in st or "fail" in st:
            score -= 25; reasons["ai_error"] = ai_state
        elif "wait" in st or "approval" in st:
            score -= 8; reasons["ai_waiting"] = ai_state
        elif "acting" in st or "planning" in st:
            score += 2; reasons["ai_working"] = ai_state

        score = max(0, min(100, int(round(score))))

        # aynyan人格に合わせた表情＆一言
        if not net_ok:
            emoji, line = "🥶", "通信きつか…マスター、孤独ばい"
        elif score >= 85:
            emoji, line = "😎", "調子よか！任せんしゃい♪"
        elif score >= 70:
            emoji, line = "😊", "穏やかな航海ばい〜"
        elif score >= 55:
            emoji, line = "😗", "ちょい構ってほしか〜"
        elif score >= 35:
            emoji, line = "😨", "なんか不安たい…マスター"
        else:
            if cpu_t >= 70:
                emoji, line = "🥵", "アッツアツ！冷やして〜"
            else:
                emoji, line = "😤", "だいぶキツか…助けて"

        return Mood(score=score, emoji=emoji, line=line, reasons=reasons)

    def _append_mood_log(self, system_info: dict, ai_state: str, ai_task: str, mood: Mood):
        """JSONLで保存（航海日誌素材）"""
        try:
            rec = {
                "ts": datetime.now(JST).isoformat(timespec="seconds"),
                "ship_mode": self.current_ship_mode,
                "system": {
                    "cpu_temp": round(float(system_info.get("cpu_temp", 0.0)), 1),
                    "cpu_percent": round(float(system_info.get("cpu_percent", 0.0)), 1),
                    "mem_percent": round(float(system_info.get("mem_percent", 0.0)), 1),
                    "disk_percent": round(float(system_info.get("disk_percent", 0.0)), 1),
                    "net_ok": bool(system_info.get("net_ok", True)),
                },
                "ai": {"state": ai_state, "task": ai_task},
                "mood": {"score": mood.score, "emoji": mood.emoji, "line": mood.line, "reasons": mood.reasons},
            }
            with open(self.MOOD_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.debug(f"moodログ書き込み失敗: {e}")

    # ========== ファン制御 ==========

    def update_fan(self) -> dict:
        """ファン制御を更新"""
        current_time = time.time()

        if current_time - self.last_fan_update < self.FAN_UPDATE_INTERVAL:
            return {}

        self.last_fan_update = current_time

        fan_status = self.fan_controller.update()

        if fan_status.get("warning_sent", False):
            if self.warning_callback:
                try:
                    self.warning_callback(fan_status["temperature"])
                except Exception as e:
                    self.logger.error(f"警告コールバックエラー: {e}")

        return fan_status

    # ========== システム状態定期計算 ==========

    def update_sys_state(self):
        """システム状態とMoodを定期計算（OLED描画とは非同期）"""
        current_time = time.time()
        if current_time - self.last_sys_update < self.SYS_UPDATE_INTERVAL:
            return

        self.last_sys_update = current_time

        # システム情報取得
        system_info = self.get_system_info()
        system_info["net_ok"] = self._check_network()
        self._system_info_cache = system_info
        
        # IP更新
        self._update_ips()

        # EMERGENCY / STORM 自動切替
        cpu_t = system_info.get("cpu_temp", 0.0)
        disk_pct = system_info.get("disk_percent", 0.0)
        cpu_pct = system_info.get("cpu_percent", 0.0)
        
        if cpu_t >= 80 or disk_pct >= 90:
            if self.current_ship_mode != "EMERGENCY":
                self._force_mode("EMERGENCY", f"熱/容量限界 (CPU:{cpu_t}C, Disk:{disk_pct}%)")
        elif cpu_pct >= 85:
            if self.current_ship_mode not in ["EMERGENCY", "STORM"]:
                self._force_mode("STORM", f"高負荷検知 (CPU:{cpu_pct}%)")

        # Mood算出
        mood = self.compute_mood(system_info, self.current_ai_state)
        self.current_mood = mood
        self._append_mood_log(system_info, self.current_ai_state, self.current_ai_task, mood)

    # ========== OLED更新（航海用語5行スクロール表示） ==========

    def _scroll_text(self, text: str, offset: int) -> str:
        MAX_CHARS = 21
        if len(text) <= MAX_CHARS:
            return text
        doubled = text + text
        start = offset % len(text)
        return doubled[start:start + MAX_CHARS]

    def render_oled(self, fan_status: dict):
        """OLED表示を0.2秒間隔でスクロール更新"""
        current_time = time.time()

        if current_time - self.last_oled_update < self.OLED_UPDATE_INTERVAL:
            return

        self.last_oled_update = current_time

        # キャッシュから情報取得
        mode_disp = SHIP_MODE_DISPLAY.get(self.current_ship_mode, "SAIL")
        mode_ascii = SHIP_MODE_ASCII.get(self.current_ship_mode, ">===>")
        ai_face = get_ai_face(self.current_ai_state)
        goal_short = self.current_ai_task[:20] if self.current_ai_task else "NONE"
        ip_lan = self._ip_cache
        ip_ts = getattr(self, "_ts_cache", "OFFLINE")

        sys_info = getattr(self, "_system_info_cache", {})
        cpu_t = sys_info.get("cpu_temp", 0)
        disk_pct = sys_info.get("disk_percent", 0)

        # 5行構成用の元テキストにパディングを追加してスクロール感を出す
        line_stat = self._check_line_status()
        
        mode_line = f"shipOS: {mode_disp} {mode_ascii}" + " " * 5
        dest_log = f"DEST: {goal_short}" + " " * 5
        sys_log = f"TEMP:{cpu_t:.0f}C DISK:{disk_pct:.0f}%" + " " * 5
        
        if line_stat:
            ip_line = f"LAN: {ip_lan} {line_stat} TS: {ip_ts}" + " " * 5
        else:
            ip_line = f"LAN: {ip_lan}  TS: {ip_ts}" + " " * 5

        # 上3行: 右→左スクロール（波のように位相をずらす）
        line1 = self._scroll_text(mode_line, self._ip_offset)
        line2 = self._scroll_text(dest_log, self._ip_offset + 3)
        line3 = self._scroll_text(sys_log, self._ip_offset + 6)
        
        # 4行目: AI状態（顔文字）等 - 固定
        line4 = f"AI: {ai_face}"[:21]
        
        # 5行目: IPテロップ
        line5 = self._scroll_text(ip_line, self._ip_offset)

        self.oled_display.render_lines([line1, line2, line3, line4, line5])
        self._ip_offset += 1

    # ========== メインループ ==========

    def boot_sequence(self):
        """起動演出"""
        from time import sleep
        self.oled_display.show_message("===Boot===\nengine check", 0.5)
        sleep(0.5)
        self.oled_display.show_message("===Boot===\ncomms check", 0.5)
        sleep(0.5)
        self.oled_display.show_message("===Boot===\nstorage check", 0.5)
        sleep(0.5)
        self.oled_display.show_message("===Boot===\naudio check", 0.5)
        sleep(0.5)
        self.oled_display.show_message("=DIAG=\nAI modules...ok\nSSD...ok\nHDD...ok", 1.5)
        sleep(1.0)

    def run(self):
        """メインループ"""
        self.logger.info("shipOS OLED・ファン制御システムを開始します")

        # systemd SIGTERM を受信して綺麗に終了するためのハンドラー
        def sig_handler(signum, frame):
            self.logger.info("SIGTERM受信、シャットダウン開始")
            self.cleanup()
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, sig_handler)

        self.boot_sequence()

        # 出港テロップ
        self.oled_display.show_message("shipOS BCNOFNe\nSetting Sail...", 1.5)

        try:
            fan_status = {}

            while True:
                # AI状態 + モード更新
                self.update_ai_state()

                # ファン制御
                new_fan_status = self.update_fan()
                if new_fan_status:
                    fan_status = new_fan_status

                # システム状態更新
                self.update_sys_state()

                # OLED表示更新（スクロール）
                self.render_oled(fan_status)

                time.sleep(0.05)

        except KeyboardInterrupt:
            self.logger.info("終了シグナルを受信しました")

        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}", exc_info=True)

        finally:
            self.cleanup()

    def cleanup(self):
        """クリーンアップ"""
        self.logger.info("投錨。全機関停止...")
        self.oled_display.show_message(" \nANCHOR DROPPED...\nALL STOP.", 1.5)
        time.sleep(1.5)
        self.oled_display.show_message(" \nSEE YOU,\n MASTER.", 1.5)
        time.sleep(1.5)
        self.oled_display.clear()
        self.fan_controller.cleanup()
        self.logger.info("クリーンアップ完了")


def warning_notification(temperature: float):
    """高温警告通知"""
    print(f"🥵 機関温度警報: {temperature:.1f}°C！冷却が必要です")


def main():
    """メイン関数"""
    controller = OLEDFanController()
    controller.set_warning_callback(warning_notification)
    controller.run()


if __name__ == "__main__":
    main()
