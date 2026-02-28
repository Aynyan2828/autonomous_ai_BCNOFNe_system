#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AudioManager（音声統合マネージャー）
録音/再生/独り言/通知を一括管理し、競合防止を行う

優先度: 会話(1) > 緊急通知(2) > 通常通知(3) > 独り言(4)
ステート: IDLE / LISTENING / THINKING / SPEAKING
"""

import os
import sys
import time
import queue
import subprocess
import threading
import tempfile
import logging
import signal
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

# 同パッケージからインポート
from audio.stt_engine import create_stt_engine
from audio.tts_engine import create_tts_engine
from audio.recorder import Recorder
from audio.input_listener import InputListener, Action
from audio.monologue_engine import MonologueEngine
from audio.system_status import get_system_status_text

logger = logging.getLogger(__name__)


class AudioState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class Priority(Enum):
    TALK = 1
    EMERGENCY = 2
    NOTIFICATION = 3
    MONOLOGUE = 4


class SpeakRequest:
    """再生リクエスト"""
    def __init__(self, text: str, priority: Priority, volume: float = 0.7,
                 category: str = "general"):
        self.text = text
        self.priority = priority
        self.volume = volume
        self.category = category


class AudioManager:
    """音声統合マネージャー"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: config.yamlの内容
        """
        self.config = config
        self.state = AudioState.IDLE
        self._state_lock = threading.Lock()
        self._speak_lock = threading.Lock()
        self._speak_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._running = False
        
        # AI状態ファイル（OLED/GUI連携用）
        self.ai_audio_state_file = "/var/run/ai_audio_state.json"
        
        # 音量設定
        vol_cfg = config.get("volume", {})
        self.conversation_volume = vol_cfg.get("conversation", 0.70)
        self.monologue_volume = vol_cfg.get("monologue", 0.25)
        self.monologue_night_volume = vol_cfg.get("monologue_night", 0.15)
        self.notification_volume = vol_cfg.get("notification", 0.50)
        self.emergency_volume = vol_cfg.get("emergency", 1.00)
        self.max_volume = vol_cfg.get("max_volume", 0.85)
        self.volume_step = vol_cfg.get("step", 0.05)
        
        # エンジン初期化
        self.stt = None
        self.tts = None
        self.recorder = None
        self.listener = None
        self.monologue = None
        
        self._init_engines()
        
        # LLM応答コールバック（外部から設定）
        self.llm_callback = None
        
        # 航海日誌コールバック（外部から設定）
        self.logbook_callback = None
    
    def _init_engines(self):
        """各エンジンを初期化"""
        # STT
        try:
            stt_cfg = self.config.get("stt", {})
            self.stt = create_stt_engine(stt_cfg)
            logger.info(f"[AudioManager] STT: {stt_cfg.get('engine', 'whisper_cpp')}")
        except Exception as e:
            logger.error(f"[AudioManager] STT初期化失敗: {e}")
        
        # TTS
        try:
            tts_cfg = self.config.get("tts", {})
            self.tts = create_tts_engine(tts_cfg)
            logger.info(f"[AudioManager] TTS: {tts_cfg.get('engine', 'piper')}")
        except Exception as e:
            logger.error(f"[AudioManager] TTS初期化失敗: {e}")
        
        # Recorder
        rec_cfg = self.config.get("recording", {})
        self.recorder = Recorder(
            sample_rate=rec_cfg.get("sample_rate", 16000),
            channels=rec_cfg.get("channels", 1),
            device=rec_cfg.get("device", "default"),
            max_duration=rec_cfg.get("max_duration", 30),
        )
        
        # Input Listener
        input_cfg = self.config.get("input", {})
        key_cfg = self.config.get("keys", {})
        self.listener = InputListener(
            device_path=input_cfg.get("device_path", "/dev/input/event12"),
            key_config=key_cfg,
            callback=self._on_action,
        )
        
        # Monologue
        mono_cfg = self.config.get("monologue", {})
        self.monologue = MonologueEngine(
            min_interval=mono_cfg.get("min_interval_min", 7),
            max_interval=mono_cfg.get("max_interval_min", 25),
            quiet_start=mono_cfg.get("quiet_hours_start", 22),
            quiet_end=mono_cfg.get("quiet_hours_end", 6),
            enabled=mono_cfg.get("enabled", True),
        )
    
    # ========== ステート管理 ==========
    
    def _set_state(self, state: AudioState):
        with self._state_lock:
            self.state = state
            logger.info(f"[AudioManager] State -> {state.value}")
            self._write_state()
    
    def _write_state(self):
        """状態をファイルに書き出し（OLED/GUI連携用）"""
        try:
            import json
            with open(self.ai_audio_state_file, 'w') as f:
                json.dump({"state": self.state.value}, f)
        except Exception:
            pass
    
    # ========== アクションハンドラ ==========
    
    def _on_action(self, action: str):
        """入力リスナーからのアクションを処理"""
        handlers = {
            Action.TALK_PRESS: self._handle_talk_press,
            Action.TALK_RELEASE: self._handle_talk_release,
            Action.MONOLOGUE_TOGGLE: self._handle_monologue_toggle,
            Action.STATUS_READ: self._handle_status_read,
            Action.LOGBOOK: self._handle_logbook,
            Action.EMERGENCY_STOP: self._handle_emergency_stop,
            Action.VOLUME_UP: self._handle_volume_up,
            Action.VOLUME_DOWN: self._handle_volume_down,
        }
        handler = handlers.get(action)
        if handler:
            handler()
    
    def _handle_talk_press(self):
        """F13押下: 録音開始"""
        if self.state == AudioState.SPEAKING:
            return  # 再生中は録音禁止
        
        self._set_state(AudioState.LISTENING)
        self.recorder.start()
    
    def _handle_talk_release(self):
        """F13リリース: 録音停止 → STT → LLM → TTS"""
        if self.state != AudioState.LISTENING:
            return
        
        wav_path = self.recorder.stop()
        if not wav_path:
            self._set_state(AudioState.IDLE)
            fail_msg = self.config.get("failsafe", {}).get(
                "stt_fail_message", "聞き取れんかった、ごめんマスター"
            )
            self.speak(fail_msg, Priority.TALK, self.conversation_volume)
            return
        
        # バックグラウンドで処理
        threading.Thread(target=self._process_talk, args=(wav_path,), daemon=True).start()
    
    def _process_talk(self, wav_path: str):
        """会話処理パイプライン: STT → LLM → TTS"""
        try:
            # STT
            self._set_state(AudioState.THINKING)
            text = ""
            if self.stt:
                text = self.stt.transcribe(wav_path)
            
            # 一時ファイル削除
            try:
                os.remove(wav_path)
            except Exception:
                pass
            
            if not text:
                fail_msg = self.config.get("failsafe", {}).get(
                    "stt_fail_message", "聞き取れんかった、ごめんマスター"
                )
                self.speak(fail_msg, Priority.TALK, self.conversation_volume)
                return
            
            logger.info(f"[AudioManager] 認識: {text}")
            
            # LLM応答
            response = ""
            if self.llm_callback:
                try:
                    response = self.llm_callback(text)
                except Exception as e:
                    logger.error(f"[AudioManager] LLMエラー: {e}")
                    response = "うーん、ちょっとエラーが出たみたい。ごめんマスター"
            else:
                response = f"「{text}」って言ったね。了解ばい！"
            
            # TTS再生
            self.speak(response, Priority.TALK, self.conversation_volume)
            
        except Exception as e:
            logger.error(f"[AudioManager] 会話処理エラー: {e}")
            self._set_state(AudioState.IDLE)
    
    def _handle_monologue_toggle(self):
        """F14: 独り言ミュートトグル"""
        if self.monologue:
            muted = self.monologue.toggle_mute()
            msg = "独り言ミュートしたよ" if muted else "独り言再開するね"
            self.speak(msg, Priority.NOTIFICATION, self.notification_volume)
    
    def _handle_status_read(self):
        """F15: システム状態読み上げ"""
        text = get_system_status_text()
        self.speak(text, Priority.NOTIFICATION, self.conversation_volume)
    
    def _handle_logbook(self):
        """F16: 航海日誌"""
        if self.logbook_callback:
            try:
                entry = self.logbook_callback()
                self.speak(f"航海日誌に記録。{entry}", Priority.NOTIFICATION, self.conversation_volume)
            except Exception as e:
                self.speak("日誌の記録にエラーが出たよ", Priority.NOTIFICATION, self.conversation_volume)
        else:
            self.speak("航海日誌機能はまだ準備中ばい", Priority.NOTIFICATION, self.conversation_volume)
    
    def _handle_emergency_stop(self):
        """F17: 緊急停止"""
        self.speak("緊急停止するね、マスター", Priority.EMERGENCY, self.emergency_volume)
        # 少し待って発話完了を待つ
        time.sleep(2)
        try:
            subprocess.run(
                ["systemctl", "stop", "autonomous-ai.service"],
                timeout=10
            )
            logger.warning("[AudioManager] 緊急停止実行")
        except Exception as e:
            logger.error(f"[AudioManager] 緊急停止エラー: {e}")
    
    def _handle_volume_up(self):
        """ノブ: 音量UP"""
        self._adjust_volume(self.volume_step)
    
    def _handle_volume_down(self):
        """ノブ: 音量DOWN"""
        self._adjust_volume(-self.volume_step)
    
    def _adjust_volume(self, delta: float):
        """wpctlで音量調整"""
        try:
            if delta > 0:
                subprocess.run(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                     f"{abs(delta):.2f}+"],
                    timeout=3
                )
            else:
                subprocess.run(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                     f"{abs(delta):.2f}-"],
                    timeout=3
                )
        except Exception as e:
            logger.error(f"[AudioManager] 音量調整エラー: {e}")
    
    # ========== 再生 ==========
    
    def speak(self, text: str, priority: Priority = Priority.NOTIFICATION,
              volume: float = 0.5):
        """テキストを音声再生キューに追加"""
        self._speak_queue.put((priority.value, time.time(), SpeakRequest(text, priority, volume)))
    
    def _speak_worker(self):
        """再生ワーカースレッド"""
        while self._running:
            try:
                _, _, req = self._speak_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            with self._speak_lock:
                self._do_speak(req)
    
    def _do_speak(self, req: SpeakRequest):
        """実際のTTS + 再生"""
        if not self.tts:
            logger.warning("[AudioManager] TTSエンジンなし")
            return
        
        prev_state = self.state
        self._set_state(AudioState.SPEAKING)
        
        try:
            # WAV生成
            fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="tts_")
            os.close(fd)
            
            success = self.tts.synthesize(req.text, wav_path)
            if not success:
                logger.warning("[AudioManager] TTS合成失敗")
                self._set_state(AudioState.IDLE)
                return
            
            # 音量設定
            try:
                vol = min(req.volume, self.max_volume)
                subprocess.run(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol:.2f}"],
                    timeout=3
                )
            except Exception:
                pass
            
            # 再生
            subprocess.run(
                ["aplay", wav_path],
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # 一時ファイル削除
            try:
                os.remove(wav_path)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"[AudioManager] 再生エラー: {e}")
        finally:
            self._set_state(AudioState.IDLE)
    
    # ========== 独り言チェック ==========
    
    def _monologue_worker(self):
        """独り言ワーカースレッド"""
        while self._running:
            try:
                if self.monologue and self.state == AudioState.IDLE:
                    text = self.monologue.check_and_generate()
                    if text:
                        vol = self.monologue.get_volume(
                            self.monologue_volume,
                            self.monologue_night_volume
                        )
                        self.speak(text, Priority.MONOLOGUE, vol)
                        logger.info(f"[Monologue] {text}")
            except Exception as e:
                logger.error(f"[Monologue] エラー: {e}")
            
            time.sleep(10)  # 10秒間隔でチェック
    
    # ========== ライフサイクル ==========
    
    def start(self):
        """AudioManager起動"""
        self._running = True
        
        # 入力リスナー開始
        if self.listener:
            self.listener.start()
        
        # 再生ワーカー
        threading.Thread(target=self._speak_worker, daemon=True).start()
        
        # 独り言ワーカー
        threading.Thread(target=self._monologue_worker, daemon=True).start()
        
        logger.info("[AudioManager] 起動完了")
        self.speak("aynyan起動。おはよう、マスター", Priority.NOTIFICATION, self.notification_volume)
    
    def stop(self):
        """AudioManager停止"""
        self._running = False
        if self.listener:
            self.listener.stop()
        logger.info("[AudioManager] 停止")
    
    def run_forever(self):
        """永久ループ（systemd用）"""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


# ========== エントリーポイント ==========

def main():
    """systemd起動用"""
    import yaml
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler("/home/pi/autonomous_ai/logs/audio.log"),
            logging.StreamHandler(),
        ]
    )
    
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    manager = AudioManager(config)
    
    def sig_handler(signum, frame):
        manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    
    manager.run_forever()


if __name__ == "__main__":
    main()
