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
}

SHIP_MODE_EMOJI = {
    "autonomous":  "⛵",
    "user_first":  "🏠",
    "maintenance": "🔧",
    "power_save":  "🌙",
    "safe":        "🆘",
}

# AI状態 → 航海用語
AI_STATE_DISPLAY = {
    "Idle":          "WATCH",    # 見張り
    "Planning":      "HELM",     # 操舵中
    "Acting":        "ENGINE",   # 機関稼働
    "Moving Files":  "CARGO",    # 積荷移動
    "Error":         "ALARM",    # 警報
    "Wait Approval": "SIGNAL",   # 信号待ち
}


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

    # 更新間隔
    OLED_UPDATE_INTERVAL = 2.0
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
        self.last_fan_update = 0.0
        self.last_ai_state_check = 0.0

        # AI状態キャッシュ
        self.current_ai_state = "Idle"
        self.current_ai_task = ""

        # shipOSモードキャッシュ
        self.current_ship_mode = "autonomous"

        # IP アドレスキャッシュ
        self._ip_cache = "..."
        self._ip_cache_time = 0.0

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

    # ========== IP取得 ==========

    def _get_ip(self) -> str:
        """IPアドレスを取得（60秒キャッシュ）"""
        if time.time() - self._ip_cache_time < 60:
            return self._ip_cache
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True, timeout=3
            )
            ips = result.stdout.strip().split()
            self._ip_cache = ips[0] if ips else "NONE"
        except Exception:
            self._ip_cache = "ERR"
        self._ip_cache_time = time.time()
        return self._ip_cache

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

    # ========== OLED更新（航海用語5行表示） ==========

    def update_oled(self, fan_status: dict):
        """OLED表示を航海用語ベースで更新"""
        current_time = time.time()

        if current_time - self.last_oled_update < self.OLED_UPDATE_INTERVAL:
            return

        self.last_oled_update = current_time

        # システム情報取得
        system_info = self.oled_display.get_system_info()
        system_info["net_ok"] = self._check_network()

        # Mood算出
        mood = self.compute_mood(system_info, self.current_ai_state)
        self.current_mood = mood
        self._append_mood_log(system_info, self.current_ai_state, self.current_ai_task, mood)

        # ===== 航海用語5行表示 =====
        mode_disp = SHIP_MODE_DISPLAY.get(self.current_ship_mode, "SAIL")
        mode_emoji = SHIP_MODE_EMOJI.get(self.current_ship_mode, "⛵")
        ai_disp = AI_STATE_DISPLAY.get(self.current_ai_state, self.current_ai_state[:6])
        ip = self._get_ip()

        # 目標の短縮表示
        goal_short = self.current_ai_task[:13] if self.current_ai_task else "---"

        # 5行構成:
        #  1: shipOS: SAIL ⛵  (or PORT/DOCK/ANCHOR/SOS)
        #  2: DEST: {目標短縮}
        #  3: HELM: {AI状態} 😊85
        #  4: TEMP: {温度}C FAN:{RPM}
        #  5: IP: {address}

        cpu_t = system_info.get("cpu_temp", 0)
        disk_pct = system_info.get("disk_percent", 0)

        # 5行を構築してドライバに渡す
        lines = [
            f"shipOS:{mode_disp} {mode_emoji}",
            f"DEST:{goal_short}",
            f"HELM:{ai_disp} {mood.emoji}{mood.score:02d}",
            f"TEMP:{cpu_t:.0f}C DISK:{disk_pct:.0f}%",
            f"IP:{ip}",
        ]
        self.oled_display.render_lines(lines)

    # ========== メインループ ==========

    def run(self):
        """メインループ"""
        self.logger.info("shipOS OLED・ファン制御システムを開始します")

        # 出港テロップ
        self.oled_display.show_message("shipOS BCNOFNe\nSetting Sail...", 2.0)

        try:
            fan_status = {}

            while True:
                # AI状態 + モード更新
                self.update_ai_state()

                # ファン制御
                new_fan_status = self.update_fan()
                if new_fan_status:
                    fan_status = new_fan_status

                # OLED表示更新（航海用語5行）
                self.update_oled(fan_status)

                time.sleep(0.5)

        except KeyboardInterrupt:
            self.logger.info("終了シグナルを受信しました")

        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}", exc_info=True)

        finally:
            self.cleanup()

    def cleanup(self):
        """クリーンアップ"""
        self.logger.info("投錨。全機関停止...")
        self.oled_display.show_message("Anchored.\nAll Stop.", 1.0)
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
