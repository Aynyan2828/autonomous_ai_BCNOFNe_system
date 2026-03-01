<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力リスナー（USBマクロパッド）
evdevでキーイベントを検知し、audio_managerへ通知
"""

import os
import time
import logging
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    logger.warning("evdevが未インストール（pip install evdev）")


# アクション定義
class Action:
    TALK_PRESS = "talk_press"
    TALK_RELEASE = "talk_release"
    MONOLOGUE_TOGGLE = "monologue_toggle"
    STATUS_READ = "status_read"
    LOGBOOK = "logbook"
    EMERGENCY_STOP = "emergency_stop"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"


class InputListener:
    """USBマクロパッド入力リスナー"""
    
    DEFAULT_KEY_MAP = {
        183: ("talk", Action.TALK_PRESS, Action.TALK_RELEASE),  # F13
        184: ("monologue_mute", Action.MONOLOGUE_TOGGLE, None),  # F14
        185: ("status_read", Action.STATUS_READ, None),           # F15
        186: ("logbook", Action.LOGBOOK, None),                   # F16
        187: ("emergency_stop", Action.EMERGENCY_STOP, None),     # F17
        115: ("volume_up", Action.VOLUME_UP, None),               # KEY_VOLUMEUP
        114: ("volume_down", Action.VOLUME_DOWN, None),           # KEY_VOLUMEDOWN
    }
    
    def __init__(self, device_path: str = "/dev/input/event12",
                 key_config: Optional[Dict] = None,
                 callback: Optional[Callable] = None):
        """
        Args:
            device_path: evdevデバイスパス
            key_config: キー設定（configのkeys部分）
            callback: アクション発火時のコールバック (action: str) -> None
        """
        self.device_path = device_path
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._device: Optional[object] = None
        
        # キーマップ構築
        self.key_map = dict(self.DEFAULT_KEY_MAP)
        if key_config:
            self._apply_key_config(key_config)
    
    def _apply_key_config(self, key_config: Dict):
        """config.yamlのキー設定を反映"""
        config_to_action = {
            "talk": (Action.TALK_PRESS, Action.TALK_RELEASE),
            "monologue_mute": (Action.MONOLOGUE_TOGGLE, None),
            "status_read": (Action.STATUS_READ, None),
            "logbook": (Action.LOGBOOK, None),
            "emergency_stop": (Action.EMERGENCY_STOP, None),
            "volume_up": (Action.VOLUME_UP, None),
            "volume_down": (Action.VOLUME_DOWN, None),
        }
        
        new_map = {}
        for name, code in key_config.items():
            if name in config_to_action:
                press, release = config_to_action[name]
                new_map[code] = (name, press, release)
        
        if new_map:
            self.key_map = new_map
    
    def start(self):
        """リスニング開始（バックグラウンドスレッド）"""
        if not EVDEV_AVAILABLE:
            logger.error("evdev未インストール、入力リスナーを起動できません")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(f"[InputListener] 起動: {self.device_path}")
    
    def stop(self):
        """リスニング停止"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("[InputListener] 停止")
    
    def _listen_loop(self):
        """メインリスニングループ（自動再接続付き）"""
        while self._running:
            try:
                self._device = InputDevice(self.device_path)
                logger.info(f"[InputListener] デバイス接続: {self._device.name}")
                
                for event in self._device.read_loop():
                    if not self._running:
                        break
                    
                    if event.type != ecodes.EV_KEY:
                        continue
                    
                    if event.code in self.key_map:
                        name, press_action, release_action = self.key_map[event.code]
                        
                        if event.value == 1 and press_action:  # 押下
                            logger.debug(f"[InputListener] PRESS: {name} -> {press_action}")
                            self._fire(press_action)
                        elif event.value == 0 and release_action:  # リリース
                            logger.debug(f"[InputListener] RELEASE: {name} -> {release_action}")
                            self._fire(release_action)
                
            except FileNotFoundError:
                logger.warning(f"[InputListener] デバイス未検出: {self.device_path}")
                time.sleep(5)
            except PermissionError:
                logger.error(f"[InputListener] 権限不足: {self.device_path}")
                logger.error("  sudo usermod -aG input pi && sudo reboot")
                time.sleep(10)
            except OSError as e:
                logger.warning(f"[InputListener] デバイスエラー（再接続中）: {e}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"[InputListener] 予期しないエラー: {e}")
                time.sleep(5)
    
    def _fire(self, action: str):
        """コールバック発火"""
        if self.callback:
            try:
                self.callback(action)
            except Exception as e:
                logger.error(f"[InputListener] コールバックエラー: {e}")
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入力リスナー（USBマクロパッド）
evdevでキーイベントを検知し、audio_managerへ通知
"""

import os
import time
import logging
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    logger.warning("evdevが未インストール（pip install evdev）")


# アクション定義
class Action:
    TALK_PRESS = "talk_press"
    TALK_RELEASE = "talk_release"
    MONOLOGUE_TOGGLE = "monologue_toggle"
    STATUS_READ = "status_read"
    LOGBOOK = "logbook"
    EMERGENCY_STOP = "emergency_stop"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"


class InputListener:
    """USBマクロパッド入力リスナー"""
    
    DEFAULT_KEY_MAP = {
        183: ("talk", Action.TALK_PRESS, Action.TALK_RELEASE),  # F13
        184: ("monologue_mute", Action.MONOLOGUE_TOGGLE, None),  # F14
        185: ("status_read", Action.STATUS_READ, None),           # F15
        186: ("logbook", Action.LOGBOOK, None),                   # F16
        187: ("emergency_stop", Action.EMERGENCY_STOP, None),     # F17
        115: ("volume_up", Action.VOLUME_UP, None),               # KEY_VOLUMEUP
        114: ("volume_down", Action.VOLUME_DOWN, None),           # KEY_VOLUMEDOWN
    }
    
    def __init__(self, device_path: str = "/dev/input/event12",
                 device_name: Optional[str] = None,
                 key_config: Optional[Dict] = None,
                 callback: Optional[Callable] = None):
        """
        Args:
            device_path: evdevデバイスパス
            device_name: デバイス名（パスが見つからない場合の検索用）
            key_config: キー設定（configのkeys部分）
            callback: アクション発火時のコールバック (action: str) -> None
        """
        self.device_path = device_path
        self.device_name = device_name
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._device: Optional[object] = None
        
        # キーマップ構築
        self.key_map = dict(self.DEFAULT_KEY_MAP)
        if key_config:
            self._apply_key_config(key_config)

    def _find_device_by_name(self) -> Optional[str]:
        """デバイス名からパスを検索"""
        if not EVDEV_AVAILABLE or not self.device_name:
            return None
        try:
            from evdev import list_devices
            for path in list_devices():
                dev = InputDevice(path)
                if self.device_name.lower() in dev.name.lower():
                    logger.info(f"[InputListener] デバイス名を検出: {dev.name} at {path}")
                    return path
        except Exception as e:
            logger.error(f"[InputListener] デバイス検索エラー: {e}")
        return None
    
    def _apply_key_config(self, key_config: Dict):
        """config.yamlのキー設定を反映"""
        config_to_action = {
            "talk": (Action.TALK_PRESS, Action.TALK_RELEASE),
            "monologue_mute": (Action.MONOLOGUE_TOGGLE, None),
            "status_read": (Action.STATUS_READ, None),
            "logbook": (Action.LOGBOOK, None),
            "emergency_stop": (Action.EMERGENCY_STOP, None),
            "volume_up": (Action.VOLUME_UP, None),
            "volume_down": (Action.VOLUME_DOWN, None),
        }
        
        new_map = {}
        for name, code in key_config.items():
            if name in config_to_action:
                press, release = config_to_action[name]
                new_map[code] = (name, press, release)
        
        if new_map:
            self.key_map = new_map
    
    def start(self):
        """リスニング開始（バックグラウンドスレッド）"""
        if not EVDEV_AVAILABLE:
            logger.error("evdev未インストール、入力リスナーを起動できません")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info(f"[InputListener] 起動完了 (target: {self.device_path or self.device_name})")
    
    def stop(self):
        """リスニング停止"""
        self._running = False
        if self._thread:
            # スレッド内で read_loop しているため、joinはタイムアウト付きで
            pass
        logger.info("[InputListener] 停止")
    
    def _listen_loop(self):
        """メインリスニングループ（自動再接続付き）"""
        while self._running:
            try:
                target_path = None
                
                # 名前の指定があれば常に名前を優先検索（ホットプラグ対策）
                if self.device_name:
                    target_path = self._find_device_by_name()
                
                # 名前検索で失敗したか、名前指定がない場合はデフォルトパスを使用
                if not target_path:
                    if self.device_path and os.path.exists(self.device_path):
                        # 名前検証（もし名前指定があるなら警告を出すだけでパス自体は試す）
                        target_path = self.device_path
                    else:
                        logger.warning(f"[InputListener] デバイス未検出。再試行中... (path={self.device_path}, name={self.device_name})")
                        time.sleep(5)
                        continue

                self._device = InputDevice(target_path)
                logger.info(f"[InputListener] デバイス接続成功: {self._device.name} ({target_path})")
                
                # イベントループ
                for event in self._device.read_loop():
                    if not self._running:
                        break
                    
                    if event.type != ecodes.EV_KEY:
                        continue
                    
                    if event.code in self.key_map:
                        name, press_action, release_action = self.key_map[event.code]
                        
                        if event.value == 1 and press_action:  # 押下
                            logger.debug(f"[InputListener] PRESS: {name} -> {press_action}")
                            self._fire(press_action)
                        elif event.value == 0 and release_action:  # リリース
                            logger.debug(f"[InputListener] RELEASE: {name} -> {release_action}")
                            self._fire(release_action)
                    else:
                        if event.value == 1:
                            logger.info(f"[InputListener] 未マッピングキー: code={event.code}")
                
            except (FileNotFoundError, OSError) as e:
                logger.warning(f"[InputListener] 接断またはエラー: {e}")
                time.sleep(5)
            except PermissionError:
                logger.error(f"[InputListener] 権限不足: {target_path if 'target_path' in locals() else self.device_path}")
                logger.error("  sudo usermod -aG input pi && sudo reboot")
                time.sleep(10)
            except Exception as e:
                logger.error(f"[InputListener] 予期しないエラー: {e}")
                time.sleep(5)
    
    def _fire(self, action: str):
        """コールバック発火"""
        if self.callback:
            try:
                self.callback(action)
            except Exception as e:
                logger.error(f"[InputListener] コールバックエラー: {e}")
>>>>>>> Stashed changes
