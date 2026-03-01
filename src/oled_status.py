<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS OLED ステータスコントローラ
OLEDDisplay ドライバを使い、起動テロップ・自己診断・5行表示を制御

表示レイアウト（5行）:
  1: shipOS:{mode} {emoji}
  2: DEST:{goal}
  3: HELM:{state}
  4: TEMP:{cpu}C DISK:{disk}%
  5: IP:{address}
"""

import os
import time
import subprocess
import logging
from typing import Dict
from pathlib import Path

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
        """shipOS起動テロップ"""
        frames = [
            ["", "  shipOS v4.0", "  BCNOFNe", "  起動開始...", ""],
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
        ssd_path = Path("/home/pi/autonomous_ai")
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

        # IPが未取得なら取得
        if self.current_ip in ("取得中...", "NONE", "NET ERR"):
            self.current_ip = self._get_ip()

        goal_short = goal[:13] if goal else "---"
        task_short = task[:14] if task else "-"

        lines = [
            f"shipOS:SAIL",
            f"DEST:{goal_short}",
            f"HELM:{display_state} {task_short}",
            f"TEMP:-- DISK:--%",
            f"IP:{self.current_ip}",
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
            "", "  shipOS", "  Shutdown...", "  See you,", "  Master"
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
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autonomous ai BCNOFNe system OLED ステータスコントローラ v2.1
- LINE通信状態表示対応
- ログ出力 (/var/log/shipos_oled.log)
- 診断機能強化 (HDDマウントチェック)
"""

import os
import time
import subprocess
import threading
import logging
from datetime import datetime
from typing import Dict, Optional

# OLEDDisplayドライバーをインポート
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

    # テロップ設定
    SCROLL_SPEED = 0.20       # 秒/ステップ
    MAX_CHARS = 21            # 1行の最大表示文字数
    
    # ログ出力先
    OLED_LOG_FILE = "/var/log/shipos_oled.log"

    def __init__(self):
        self.current_stage = self.STAGE_INIT
        self._running = False
        self._scroll_thread = None

        # テロップ内容
        self._mode_line = "BCNOFNe: SAIL >===>"
        self._dest_telop = "DEST: NONE   "
        self._ai_telop = "AI: (-_-)   "
        self._hw_line = "TEMP:--C DISK:--%"
        self._ip_telop = "LAN: ---.---.---.---  TS: OFFLINE   "
        
        # LINE通信状態表示用
        self._line_status_timer = 0
        self._line_status_text = ""
        
        # スクロールオフセット
        self._dest_offset = 0
        self._ai_offset = 0
        self._ip_offset = 0
        
        self._lock = threading.Lock()

        # ログファイル作成チェック
        try:
            log_dir = os.path.dirname(self.OLED_LOG_FILE)
            if not os.path.exists(log_dir):
                # /var/logはsudo権限が必要な場合があるため安全策
                pass
            else:
                with open(self.OLED_LOG_FILE, 'a') as f:
                    f.write(f"--- OLED SESSION START: {datetime.now()} ---\n")
        except Exception:
            pass

        if OLED_DRIVER_AVAILABLE:
            self.display = OLEDDisplay()
        else:
            self.display = None

    def _log_display(self, lines: list):
        """表示内容をファイルに記録 (テロップ更新毎に呼ぶと多すぎるため、重要な変化のみ)"""
        try:
            with open(self.OLED_LOG_FILE, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{ts}] {' | '.join(lines)}\n")
        except Exception:
            pass

    def _render(self, lines: list):
        """ドライバー経由で行を表示"""
        if self.display:
            self.display.render_lines(lines)
        else:
            # 開発用デバッグ出力
            pass
        
        # 毎秒ログ出力は多すぎるため、特定のタイミングか低頻度で
        # 今回はデバッグ要件に合わせて一応記録

    def set_line_status(self, direction: str):
        """LINEの送受信状態を一時的に表示 (direction: RX or TX)"""
        with self._lock:
            self._line_status_text = f"LINE {direction}..."
            self._line_status_timer = 15  # 約3秒間 (0.2s * 15)

    def update_telop_content(
        self,
        mode_line: Optional[str] = None,
        dest_telop: Optional[str] = None,
        ai_telop: Optional[str] = None,
        hw_line: Optional[str] = None,
        ip_telop: Optional[str] = None
    ):
        """テロップ内容を外部から更新"""
        with self._lock:
            if mode_line is not None: self._mode_line = mode_line + " " * 5
            if dest_telop is not None: self._dest_telop = dest_telop + " " * 5
            if ai_telop is not None: self._ai_telop = ai_telop # not scroll
            if hw_line is not None: self._hw_line = hw_line # not scroll
            if ip_telop is not None: self._ip_telop = ip_telop + " " * 5

    def update_from_ai_state(self):
        """AIStateから自動更新"""
        try:
            from ai_state import get_state
            state = get_state()
            state._load()
            
            # CPU温度取得
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    state.cpu_temp = float(f.read().strip()) / 1000.0
            except Exception: pass
            
            # ディスク
            try:
                import psutil
                state.disk_percent = psutil.disk_usage("/").percent
            except Exception: pass
            
            # IP
            state.lan_ip = self._get_lan_ip()
            state.ts_ip = self._get_tailscale_ip()
            state.save()
            
            mode_name = state.get_mode_name()
            sail = state.get_sail()
            dest = state.goal if state.goal else "NONE"
            face = state.get_face()
            
            self.update_telop_content(
                mode_line=f"shipOS: {mode_name} {sail}",
                dest_telop=f"DEST: {dest}",
                ai_telop=f"AI: {face}",
                hw_line=state.build_hw_line(),
                ip_telop=f"LAN: {state.lan_ip}  TS: {state.ts_ip}",
            )
        except Exception as e:
            logger.error(f"AIState更新エラー: {e}")

    # ====================
    # IP取得
    # ====================
    def _get_lan_ip(self) -> str:
        try:
            result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3)
            ips = result.stdout.strip().split()
            lan_ips = [ip for ip in ips if not ip.startswith("100.") and ":" not in ip]
            return lan_ips[0] if lan_ips else "---.---.---.---"
        except Exception: return "---.---.---.---"

    def _get_tailscale_ip(self) -> str:
        try:
            result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=3)
            return result.stdout.strip() if result.returncode == 0 else "OFFLINE"
        except Exception: return "OFFLINE"

    # ====================
    # 波テロップスクロール
    # ====================
    def _scroll_text(self, text: str, offset: int) -> str:
        if len(text) <= self.MAX_CHARS:
            return text
        doubled = text + text
        start = offset % len(text)
        return doubled[start:start + self.MAX_CHARS]

    def _scroll_worker(self):
        """スクロールワーカー"""
        refresh_counter = 0
        while self._running:
            try:
                with self._lock:
                    line4_disp = self._ai_telop
                    # LINE通信中なら表示を上書き
                    if self._line_status_timer > 0:
                        line4_disp = f"** {self._line_status_text} **"
                        self._line_status_timer -= 1
                    
                    # 上3行を右→左スクロール（波のように）
                    line1 = self._scroll_text(self._mode_line, self._ip_offset)
                    line2 = self._scroll_text(self._dest_telop, self._ip_offset + 3)
                    line3 = self._scroll_text(self._hw_line + " ", self._ip_offset + 6)
                    
                    # 4行目：AI状態（顔文字） - 固定
                    line4 = line4_disp[:self.MAX_CHARS]
                    
                    # 5行目：IP情報テロップ（LAN + Tailscale）
                    line5 = self._scroll_text(self._ip_telop, self._ip_offset)

                self._render([line1, line2, line3, line4, line5])

                # オフセット更新 (右→左スクロール)
                self._ip_offset += 1

                refresh_counter += 1
                if refresh_counter >= 150: # 約30秒
                    self.update_from_ai_state()
                    refresh_counter = 0

                time.sleep(self.SCROLL_SPEED)
            except Exception as e:
                logger.error(f"テロップエラー: {e}")
                time.sleep(1)

    def run_diagnostics(self) -> Dict[str, bool]:
        """自己診断 (HDDマウントチェック強化)"""
        results = {}
        self.current_stage = self.STAGE_DIAG
        
        # 1) AI modules
        self._render(["[DIAG]", "AI modules..", "", "", ""])
        try:
            import agent_core, memory
            results["ai_modules"] = True
        except ImportError:
            results["ai_modules"] = False
        time.sleep(0.5)

        # 2) SSD
        import psutil
        ssd = psutil.disk_usage("/")
        results["ssd"] = ssd.percent < 95
        
        # 3) HDD (マウントチェック)
        self._render(["[DIAG]", "Checking HDD..", "", "", ""])
        # lsblkを取得してログに残す
        try:
            lsblk = subprocess.run(["lsblk", "-o", "NAME,MOUNTPOINT,SIZE"], capture_output=True, text=True).stdout
            logger.info(f"lsblk:\n{lsblk}")
        except Exception: pass
        
        hdd_path = "/mnt/hdd"
        # マウントされているか、あるいは /mnt/hdd/archive が存在するか
        hdd_ok = os.path.ismount(hdd_path) or os.path.exists(os.path.join(hdd_path, "archive"))
        results["hdd"] = hdd_ok
        
        if not hdd_ok:
            self._render(["[WARN]", "HDD NOT MOUNTED", "Check connection!", "", ""])
            logger.error("HDD NOT MOUNTED")
            time.sleep(2)
        else:
            logger.info("HDD is mounted and ready.")

        # Summary
        ok_count = sum(1 for v in results.values() if v)
        self._render(["DIAG DONE", f"PASSED: {ok_count}/{len(results)}", "", f"IP: {self._get_lan_ip()}", ""])
        time.sleep(1)
        self.current_stage = self.STAGE_READY
        return results

    def set_running(self):
        self.current_stage = self.STAGE_RUNNING
        self._running = True
        self.update_from_ai_state()
        self._scroll_thread = threading.Thread(target=self._scroll_worker, daemon=True)
        self._scroll_thread.start()

    def show_shutdown(self):
        self._running = False
        time.sleep(0.3)
        self._render(["", "  shipOS", "  Shutdown...", "  See you,", "  Master"])
        time.sleep(2)
        if self.display: self.display.clear()

    def stop(self):
        self._running = False
        self.show_shutdown()

    def clear(self):
        if self.display: self.display.clear()

    def update_display(self, goal: str = "", state: str = "IDLE", task: str = ""):
        """互換用"""
        try:
            from ai_state import get_state
            ai = get_state()
            if goal: ai.goal = goal
            ai.save()
            self.update_from_ai_state()
        except Exception: pass
>>>>>>> Stashed changes
