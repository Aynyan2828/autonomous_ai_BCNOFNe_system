#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AudioManager・磯浹螢ｰ邨ｱ蜷医・繝阪・繧ｸ繝｣繝ｼ・・
骭ｲ髻ｳ/蜀咲函/迢ｬ繧願ｨ/騾夂衍繧剃ｸ諡ｬ邂｡逅・＠縲∫ｫｶ蜷磯亟豁｢繧定｡後≧

蜆ｪ蜈亥ｺｦ: 莨夊ｩｱ(1) > 邱頑･騾夂衍(2) > 騾壼ｸｸ騾夂衍(3) > 迢ｬ繧願ｨ(4)
繧ｹ繝・・繝・ IDLE / LISTENING / THINKING / SPEAKING
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

# 蜷後ヱ繝・こ繝ｼ繧ｸ縺九ｉ繧､繝ｳ繝昴・繝・
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
    """蜀咲函繝ｪ繧ｯ繧ｨ繧ｹ繝・""
    def __init__(self, text: str, priority: Priority, volume: float = 0.7,
                 category: str = "general"):
        self.text = text
        self.priority = priority
        self.volume = volume
        self.category = category


class AudioManager:
    """髻ｳ螢ｰ邨ｱ蜷医・繝阪・繧ｸ繝｣繝ｼ"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: config.yaml縺ｮ蜀・ｮｹ
        """
        self.config = config
        self.state = AudioState.IDLE
        self._state_lock = threading.Lock()
        self._speak_lock = threading.Lock()
        self._speak_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._running = False
        
        # AI迥ｶ諷九ヵ繧｡繧､繝ｫ・・LED/GUI騾｣謳ｺ逕ｨ・・
        self.ai_audio_state_file = "/var/run/ai_audio_state.json"
        
        # 髻ｳ驥剰ｨｭ螳・
        vol_cfg = config.get("volume", {})
        self.conversation_volume = vol_cfg.get("conversation", 0.70)
        self.monologue_volume = vol_cfg.get("monologue", 0.25)
        self.monologue_night_volume = vol_cfg.get("monologue_night", 0.15)
        self.notification_volume = vol_cfg.get("notification", 0.50)
        self.emergency_volume = vol_cfg.get("emergency", 1.00)
        self.max_volume = vol_cfg.get("max_volume", 0.85)
        self.volume_step = vol_cfg.get("step", 0.05)
        
        # 繧ｨ繝ｳ繧ｸ繝ｳ蛻晄悄蛹・
        self.stt = None
        self.tts = None
        self.recorder = None
        self.listener = None
        self.monologue = None
        
        self._init_engines()
        
        # LLM蠢懃ｭ斐さ繝ｼ繝ｫ繝舌ャ繧ｯ・亥､夜Κ縺九ｉ險ｭ螳夲ｼ・
        self.llm_callback = None
        
        # 闊ｪ豬ｷ譌･隱後さ繝ｼ繝ｫ繝舌ャ繧ｯ・亥､夜Κ縺九ｉ險ｭ螳夲ｼ・
        self.logbook_callback = None
    
    def _init_engines(self):
        """蜷・お繝ｳ繧ｸ繝ｳ繧貞・譛溷喧"""
        # STT
        try:
            stt_cfg = self.config.get("stt", {})
            self.stt = create_stt_engine(stt_cfg)
            logger.info(f"[AudioManager] STT: {stt_cfg.get('engine', 'whisper_cpp')}")
        except Exception as e:
            logger.error(f"[AudioManager] STT蛻晄悄蛹門､ｱ謨・ {e}")
        
        # TTS
        try:
            tts_cfg = self.config.get("tts", {})
            self.tts = create_tts_engine(tts_cfg)
            logger.info(f"[AudioManager] TTS: {tts_cfg.get('engine', 'piper')}")
        except Exception as e:
            logger.error(f"[AudioManager] TTS蛻晄悄蛹門､ｱ謨・ {e}")
        
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
    
    # ========== 繧ｹ繝・・繝育ｮ｡逅・==========
    
    def _set_state(self, state: AudioState):
        with self._state_lock:
            self.state = state
            logger.info(f"[AudioManager] State -> {state.value}")
            self._write_state()
    
    def _write_state(self):
        """迥ｶ諷九ｒ繝輔ぃ繧､繝ｫ縺ｫ譖ｸ縺榊・縺暦ｼ・LED/GUI騾｣謳ｺ逕ｨ・・""
        try:
            import json
            with open(self.ai_audio_state_file, 'w') as f:
                json.dump({"state": self.state.value}, f)
        except Exception:
            pass
    
    # ========== 繧｢繧ｯ繧ｷ繝ｧ繝ｳ繝上Φ繝峨Λ ==========
    
    def _on_action(self, action: str):
        """蜈･蜉帙Μ繧ｹ繝翫・縺九ｉ縺ｮ繧｢繧ｯ繧ｷ繝ｧ繝ｳ繧貞・逅・""
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
        """F13謚ｼ荳・ 骭ｲ髻ｳ髢句ｧ・""
        if self.state == AudioState.SPEAKING:
            return  # 蜀咲函荳ｭ縺ｯ骭ｲ髻ｳ遖∵ｭ｢
        
        self._set_state(AudioState.LISTENING)
        self.recorder.start()
    
    def _handle_talk_release(self):
        """F13繝ｪ繝ｪ繝ｼ繧ｹ: 骭ｲ髻ｳ蛛懈ｭ｢ 竊・STT 竊・LLM 竊・TTS"""
        if self.state != AudioState.LISTENING:
            return
        
        wav_path = self.recorder.stop()
        if not wav_path:
            self._set_state(AudioState.IDLE)
            fail_msg = self.config.get("failsafe", {}).get(
                "stt_fail_message", "閨槭″蜿悶ｌ繧薙°縺｣縺溘√＃繧√ｓ繝槭せ繧ｿ繝ｼ"
            )
            self.speak(fail_msg, Priority.TALK, self.conversation_volume)
            return
        
        # 繝舌ャ繧ｯ繧ｰ繝ｩ繧ｦ繝ｳ繝峨〒蜃ｦ逅・
        threading.Thread(target=self._process_talk, args=(wav_path,), daemon=True).start()
    
    def _process_talk(self, wav_path: str):
        """莨夊ｩｱ蜃ｦ逅・ヱ繧､繝励Λ繧､繝ｳ: STT 竊・LLM 竊・TTS"""
        try:
            # STT
            self._set_state(AudioState.THINKING)
            text = ""
            if self.stt:
                text = self.stt.transcribe(wav_path)
            
            # 荳譎ゅヵ繧｡繧､繝ｫ蜑企勁
            try:
                os.remove(wav_path)
            except Exception:
                pass
            
            if not text:
                fail_msg = self.config.get("failsafe", {}).get(
                    "stt_fail_message", "閨槭″蜿悶ｌ繧薙°縺｣縺溘√＃繧√ｓ繝槭せ繧ｿ繝ｼ"
                )
                self.speak(fail_msg, Priority.TALK, self.conversation_volume)
                return
            
            logger.info(f"[AudioManager] 隱崎ｭ・ {text}")
            
            # LLM蠢懃ｭ・
            response = ""
            if self.llm_callback:
                try:
                    response = self.llm_callback(text)
                except Exception as e:
                    logger.error(f"[AudioManager] LLM繧ｨ繝ｩ繝ｼ: {e}")
                    response = "縺・・繧薙√■繧・▲縺ｨ繧ｨ繝ｩ繝ｼ縺悟・縺溘∩縺溘＞縲ゅ＃繧√ｓ繝槭せ繧ｿ繝ｼ"
            else:
                response = f"縲鶏text}縲阪▲縺ｦ險縺｣縺溘・縲ゆｺ・ｧ｣縺ｰ縺・ｼ・
            
            # TTS蜀咲函
            self.speak(response, Priority.TALK, self.conversation_volume)
            
        except Exception as e:
            logger.error(f"[AudioManager] 莨夊ｩｱ蜃ｦ逅・お繝ｩ繝ｼ: {e}")
            self._set_state(AudioState.IDLE)
    
    def _handle_monologue_toggle(self):
        """F14: 迢ｬ繧願ｨ繝溘Η繝ｼ繝医ヨ繧ｰ繝ｫ"""
        if self.monologue:
            muted = self.monologue.toggle_mute()
            msg = "迢ｬ繧願ｨ繝溘Η繝ｼ繝医＠縺溘ｈ" if muted else "迢ｬ繧願ｨ蜀埼幕縺吶ｋ縺ｭ"
            self.speak(msg, Priority.NOTIFICATION, self.notification_volume)
    
    def _handle_status_read(self):
        """F15: 繧ｷ繧ｹ繝・Β迥ｶ諷玖ｪｭ縺ｿ荳翫￡"""
        text = get_system_status_text()
        self.speak(text, Priority.NOTIFICATION, self.conversation_volume)
    
    def _handle_logbook(self):
        """F16: 闊ｪ豬ｷ譌･隱・""
        if self.logbook_callback:
            try:
                entry = self.logbook_callback()
                self.speak(f"闊ｪ豬ｷ譌･隱後↓險倬鹸縲・entry}", Priority.NOTIFICATION, self.conversation_volume)
            except Exception as e:
                self.speak("譌･隱後・險倬鹸縺ｫ繧ｨ繝ｩ繝ｼ縺悟・縺溘ｈ", Priority.NOTIFICATION, self.conversation_volume)
        else:
            self.speak("闊ｪ豬ｷ譌･隱梧ｩ溯・縺ｯ縺ｾ縺貅門ｙ荳ｭ縺ｰ縺・, Priority.NOTIFICATION, self.conversation_volume)
    
    def _handle_emergency_stop(self):
        """F17: 邱頑･蛛懈ｭ｢"""
        self.speak("邱頑･蛛懈ｭ｢縺吶ｋ縺ｭ縲√・繧ｹ繧ｿ繝ｼ", Priority.EMERGENCY, self.emergency_volume)
        # 蟆代＠蠕・▲縺ｦ逋ｺ隧ｱ螳御ｺ・ｒ蠕・▽
        time.sleep(2)
        try:
            subprocess.run(
                ["sudo", "systemctl", "stop", "autonomous-ai.service"],
                timeout=10
            )
            logger.warning("[AudioManager] 邱頑･蛛懈ｭ｢螳溯｡・)
        except Exception as e:
            logger.error(f"[AudioManager] 邱頑･蛛懈ｭ｢繧ｨ繝ｩ繝ｼ: {e}")
    
    def _handle_volume_up(self):
        """繝弱ヶ: 髻ｳ驥酋P"""
        self._adjust_volume(self.volume_step)
    
    def _handle_volume_down(self):
        """繝弱ヶ: 髻ｳ驥愁OWN"""
        self._adjust_volume(-self.volume_step)
    
    def _adjust_volume(self, delta: float):
        """wpctl縺ｧ髻ｳ驥剰ｪｿ謨ｴ"""
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
            logger.error(f"[AudioManager] 髻ｳ驥剰ｪｿ謨ｴ繧ｨ繝ｩ繝ｼ: {e}")
    
    # ========== 蜀咲函 ==========
    
    def speak(self, text: str, priority: Priority = Priority.NOTIFICATION,
              volume: float = 0.5):
        """繝・く繧ｹ繝医ｒ髻ｳ螢ｰ蜀咲函繧ｭ繝･繝ｼ縺ｫ霑ｽ蜉"""
        self._speak_queue.put((priority.value, time.time(), SpeakRequest(text, priority, volume)))
    
    def _speak_worker(self):
        """蜀咲函繝ｯ繝ｼ繧ｫ繝ｼ繧ｹ繝ｬ繝・ラ"""
        while self._running:
            try:
                _, _, req = self._speak_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            with self._speak_lock:
                self._do_speak(req)
    
    def _do_speak(self, req: SpeakRequest):
        """螳滄圀縺ｮTTS + 蜀咲函"""
        if not self.tts:
            logger.warning("[AudioManager] TTS繧ｨ繝ｳ繧ｸ繝ｳ縺ｪ縺・)
            return
        
        prev_state = self.state
        self._set_state(AudioState.SPEAKING)
        
        try:
            # WAV逕滓・
            fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="tts_")
            os.close(fd)
            
            success = self.tts.synthesize(req.text, wav_path)
            if not success:
                logger.warning("[AudioManager] TTS蜷域・螟ｱ謨・)
                self._set_state(AudioState.IDLE)
                return
            
            # 髻ｳ驥剰ｨｭ螳・
            try:
                vol = min(req.volume, self.max_volume)
                subprocess.run(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{vol:.2f}"],
                    timeout=3
                )
            except Exception:
                pass
            
            # 繧ｹ繝・Ξ繧ｪ螟画鋤 + 蜀咲函
            play_path = wav_path
            playback_cfg = self.config.get("playback", {})
            device = playback_cfg.get("device", "default")
            stereo = playback_cfg.get("stereo", False)
            
            if stereo:
                stereo_path = wav_path.replace(".wav", "_stereo.wav")
                try:
                    subprocess.run(
                        ["sox", wav_path, stereo_path, "channels", "2"],
                        timeout=10,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if os.path.exists(stereo_path):
                        play_path = stereo_path
                except Exception:
                    pass  # 螟画鋤螟ｱ謨玲凾縺ｯ繝｢繝弱Λ繝ｫ縺ｮ縺ｾ縺ｾ蜀咲函
            
            # 蜀咲函
            aplay_cmd = ["aplay"]
            if device != "default":
                aplay_cmd.extend(["-D", device])
            aplay_cmd.append(play_path)
            
            subprocess.run(
                aplay_cmd,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # 荳譎ゅヵ繧｡繧､繝ｫ蜑企勁
            for p in [wav_path, wav_path.replace(".wav", "_stereo.wav")]:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            
        except Exception as e:
            logger.error(f"[AudioManager] 蜀咲函繧ｨ繝ｩ繝ｼ: {e}")
        finally:
            self._set_state(AudioState.IDLE)
    
    # ========== 迢ｬ繧願ｨ繝√ぉ繝・け ==========
    
    def _monologue_worker(self):
        """迢ｬ繧願ｨ繝ｯ繝ｼ繧ｫ繝ｼ繧ｹ繝ｬ繝・ラ"""
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
                logger.error(f"[Monologue] 繧ｨ繝ｩ繝ｼ: {e}")
            
            time.sleep(10)  # 10遘帝俣髫斐〒繝√ぉ繝・け
    
    # ========== LINE 繧ｳ繝槭Φ繝牙女菫｡ ==========
    
    AUDIO_CMD_FILE = "/tmp/shipos_audio_cmd.json"
    
    def _line_cmd_worker(self):
        """LINE髻ｳ螢ｰ繧ｳ繝槭Φ繝峨・繝ｼ繝ｪ繝ｳ繧ｰ繝ｯ繝ｼ繧ｫ繝ｼ"""
        import json as _json
        last_timestamp = ""
        
        while self._running:
            try:
                if os.path.exists(self.AUDIO_CMD_FILE):
                    with open(self.AUDIO_CMD_FILE, 'r', encoding='utf-8') as f:
                        cmd = _json.load(f)
                    
                    ts = cmd.get("timestamp", "")
                    if ts != last_timestamp:
                        last_timestamp = ts
                        self._handle_line_cmd(cmd)
                        # 蜃ｦ逅・ｸ医∩繝輔ぃ繧､繝ｫ繧貞炎髯､
                        try:
                            os.remove(self.AUDIO_CMD_FILE)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"[LINE CMD] 繧ｨ繝ｩ繝ｼ: {e}")
            
            time.sleep(2)  # 2遘帝俣髫斐〒繝昴・繝ｪ繝ｳ繧ｰ
    
    def _handle_line_cmd(self, cmd: dict):
        """LINE繧ｳ繝槭Φ繝峨ｒ蜃ｦ逅・""
        action = cmd.get("action", "")
        params = cmd.get("params", {})
        
        if action == "speak":
            text = params.get("text", "")
            if text:
                self.speak(text, Priority.NOTIFICATION, self.conversation_volume)
                logger.info(f"[LINE CMD] 隱ｭ縺ｿ荳翫￡: {text}")
        
        elif action == "monologue_mute":
            if self.monologue:
                self.monologue.muted = True
                self.speak("迢ｬ繧願ｨ繝溘Η繝ｼ繝医＠縺溘ｈ", Priority.NOTIFICATION, self.notification_volume)
        
        elif action == "monologue_unmute":
            if self.monologue:
                self.monologue.muted = False
                self.speak("迢ｬ繧願ｨ蜀埼幕縺吶ｋ縺ｭ", Priority.NOTIFICATION, self.notification_volume)
        
        elif action == "status_read":
            text = get_system_status_text()
            self.speak(text, Priority.NOTIFICATION, self.conversation_volume)
        
        elif action == "change_voice":
            voice = params.get("voice", "nova")
            if self.tts and hasattr(self.tts, 'voice'):
                self.tts.voice = voice
                self.speak(f"螢ｰ繧畜voice}縺ｫ螟峨∴縺溘ｈ", Priority.NOTIFICATION, self.notification_volume)
                logger.info(f"[LINE CMD] 螢ｰ螟画峩: {voice}")
    
    # ========== 繝ｩ繧､繝輔し繧､繧ｯ繝ｫ ==========
    
    def start(self):
        """AudioManager襍ｷ蜍・""
        self._running = True
        
        # 蜈･蜉帙Μ繧ｹ繝翫・髢句ｧ・
        if self.listener:
            self.listener.start()
        
        # 蜀咲函繝ｯ繝ｼ繧ｫ繝ｼ
        threading.Thread(target=self._speak_worker, daemon=True).start()
        
        # 迢ｬ繧願ｨ繝ｯ繝ｼ繧ｫ繝ｼ
        threading.Thread(target=self._monologue_worker, daemon=True).start()
        
        # LINE繧ｳ繝槭Φ繝峨・繝ｼ繝ｪ繝ｳ繧ｰ
        threading.Thread(target=self._line_cmd_worker, daemon=True).start()
        
        logger.info("[AudioManager] 襍ｷ蜍募ｮ御ｺ・)
        self.speak("縺ゅｆ縺ｫ繧・ｓ襍ｷ蜍輔ゅ♀縺ｯ繧医≧縲√・繧ｹ繧ｿ繝ｼ", Priority.NOTIFICATION, self.notification_volume)
    
    def stop(self):
        """AudioManager蛛懈ｭ｢"""
        self._running = False
        if self.listener:
            self.listener.stop()
        logger.info("[AudioManager] 蛛懈ｭ｢")
    
    def run_forever(self):
        """豌ｸ荵・Ν繝ｼ繝暦ｼ・ystemd逕ｨ・・""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


# ========== 繧ｨ繝ｳ繝医Μ繝ｼ繝昴う繝ｳ繝・==========

def main():
    """systemd襍ｷ蜍慕畑"""
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
