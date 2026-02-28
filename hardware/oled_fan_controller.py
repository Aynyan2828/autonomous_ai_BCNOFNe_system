#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OLED・ファン制御統合モジュール（改良版）
- システム状態、AI状態をOLEDに表示し、ファンを温度連動で制御
- 追加: 感情(Mood) を算出してOLEDに表示
- 追加: 日記素材として mood_log.jsonl に状態ログを保存
"""

import os
import json
import time
import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fan_controller import FanController
from oled_display import OLEDDisplay


JST = timezone(timedelta(hours=9))

@dataclass
class Mood:
    score: int           # 0-100
    emoji: str           # 😊😗😨😤🥶🥵😎 etc
    line: str            # 一言
    reasons: Dict[str, Any]


class OLEDFanController:
    """OLED・ファン制御統合クラス"""

    # AI状態ファイル
    AI_STATE_FILE = "/var/run/ai_state.json"

    # 追加：状態ログ（AI日記素材）
    STATE_DIR = "/home/pi/autonomous_ai/state"
    MOOD_LOG_PATH = os.path.join(STATE_DIR, "mood_log.jsonl")
    LAST_TOUCH_PATH = os.path.join(STATE_DIR, "last_user_touch.txt")

    # 更新間隔
    OLED_UPDATE_INTERVAL = 2.0   # 2秒
    FAN_UPDATE_INTERVAL = 5.0    # 5秒
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

        # 直近のmood（デバッグ/ログ用）
        self.current_mood: Optional[Mood] = None

        # 警告通知用（Discord/LINE連携）
        self.warning_callback = None

        self.logger.info("OLED・ファン制御システム（改良版）を初期化しました")

    # -----------------------------
    # 外部（LINE等）から「構った」を更新したい場合用
    # -----------------------------
    def touch(self):
        """ユーザーが構った時刻を保存（放置判定に使う）"""
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

    # -----------------------------
    # 警告通知
    # -----------------------------
    def set_warning_callback(self, callback):
        """
        警告通知コールバックを設定

        Args:
            callback: 警告通知関数 (temperature: float) -> None
        """
        self.warning_callback = callback

    # -----------------------------
    # AI状態読み込み
    # -----------------------------
    def read_ai_state(self) -> dict:
        """
        AI状態ファイルを読み込み

        Returns:
            AI状態辞書
        """
        try:
            if os.path.exists(self.AI_STATE_FILE):
                with open(self.AI_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
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
        self.current_ai_state = ai_data.get("state", "Idle") or "Idle"
        self.current_ai_task = ai_data.get("task", "") or ""

    # -----------------------------
    # ネット疎通
    # -----------------------------
    def _check_network(self, host: str = "1.1.1.1", port: int = 53, timeout: float = 0.7) -> bool:
        """軽い疎通チェック（DNSへTCP接続）"""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    # -----------------------------
    # Mood算出
    # -----------------------------
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

        # 表情＆一言（九州ノリ）
        if not net_ok:
            emoji, line = "🥶", "通信きつか…孤独ばい"
        elif score >= 85:
            emoji, line = "😎", "調子よか！任せんしゃい"
        elif score >= 70:
            emoji, line = "😊", "今日は穏やかばい"
        elif score >= 55:
            emoji, line = "😗", "ちょい構ってほしか〜"
        elif score >= 35:
            emoji, line = "😨", "なんか不安たい…"
        else:
            if cpu_t >= 70:
                emoji, line = "🥵", "暑すぎ！冷やして〜"
            else:
                emoji, line = "😤", "だいぶキツか…助けて"

        return Mood(score=score, emoji=emoji, line=line, reasons=reasons)

    def _append_mood_log(self, system_info: dict, ai_state: str, ai_task: str, mood: Mood):
        """JSONLで保存（AI日記素材）"""
        try:
            rec = {
                "ts": datetime.now(JST).isoformat(timespec="seconds"),
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

    # -----------------------------
    # ファン制御
    # -----------------------------
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

        fan_status = self.fan_controller.update()

        if fan_status.get("warning_sent", False):
            if self.warning_callback:
                try:
                    self.warning_callback(fan_status["temperature"])
                except Exception as e:
                    self.logger.error(f"警告コールバックエラー: {e}")

        return fan_status

    # -----------------------------
    # OLED更新
    # -----------------------------
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

        # システム情報取得（既存OLEDDisplayを活用）
        system_info = self.oled_display.get_system_info()

        # 追加：net_ok をここで付与（oled_display側が未対応でもOK）
        system_info["net_ok"] = self._check_network()

        # ファン情報
        fan_rpm = self.fan_controller.get_fan_rpm()
        fan_status_text = fan_status.get("fan_status", "不明")

        # 追加：mood算出 + ログ保存
        mood = self.compute_mood(system_info, self.current_ai_state)
        self.current_mood = mood
        self._append_mood_log(system_info, self.current_ai_state, self.current_ai_task, mood)

        # OLED表示（既存の display を"そのまま"使う）
        # ただし既存displayは4行目が "AI:{ai_state}" の想定なので、
        # ここで ai_state を「AI状態 + mood」を合成して渡す（oled_display.pyを触らずに実現）
        ai_line = f"{self.current_ai_state} {mood.emoji}{mood.score:02d}"

        self.oled_display.display(
            system_info=system_info,
            fan_status=fan_status_text,
            fan_rpm=fan_rpm,
            ai_state=ai_line
        )

    # -----------------------------
    # メインループ
    # -----------------------------
    def run(self):
        """メインループ"""
        self.logger.info("OLED・ファン制御システム（改良版）を開始します")

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
    """高温警告通知（Discord/LINE連携用）

    Args:
        temperature: CPU温度
    """
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
