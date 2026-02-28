#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTSエンジン（音声合成）抽象化 + 実装
Piper TTS（オフライン優先） / OpenAI TTS（フォールバック）
"""

import os
import subprocess
import tempfile
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """TTSエンジン抽象基底クラス"""
    
    @abstractmethod
    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """
        テキストをWAVに変換
        
        Args:
            text: 合成テキスト
            output_path: 出力WAVパス
            speed: 速度倍率
            
        Returns:
            成功したらTrue
        """
        pass


class PiperTTS(TTSEngine):
    """Piper TTS ローカル音声合成"""
    
    def __init__(self, binary: str, model: str, config: str = "",
                 speed: float = 1.0, speaker_id: int = 0):
        self.binary = binary
        self.model = model
        self.config = config
        self.default_speed = speed
        self.speaker_id = speaker_id
        
        if not os.path.exists(binary):
            raise FileNotFoundError(f"Piper binary not found: {binary}")
        if not os.path.exists(model):
            raise FileNotFoundError(f"Piper model not found: {model}")
    
    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """Piperでテキスト→WAV生成"""
        start = time.time()
        try:
            cmd = [
                self.binary,
                "--model", self.model,
                "--output_file", output_path,
                "--length_scale", str(1.0 / (speed or self.default_speed)),
            ]
            if self.config and os.path.exists(self.config):
                cmd.extend(["--config", self.config])
            if self.speaker_id > 0:
                cmd.extend(["--speaker", str(self.speaker_id)])
            
            proc = subprocess.run(
                cmd,
                input=text,
                capture_output=True, text=True,
                timeout=15
            )
            
            elapsed = time.time() - start
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"[TTS] Piper 合成完了: {elapsed:.1f}秒")
                return True
            
            logger.error(f"[TTS] Piper 出力ファイルなし: {proc.stderr}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error("[TTS] Piper タイムアウト")
            return False
        except Exception as e:
            logger.error(f"[TTS] Piper エラー: {e}")
            return False


class OpenAITTS(TTSEngine):
    """OpenAI TTS API（フォールバック）"""
    
    def __init__(self, model: str = "tts-1", voice: str = "nova"):
        self.model = model
        self.voice = voice
    
    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """OpenAI TTSでテキスト→音声"""
        try:
            import openai
            client = openai.OpenAI()
            
            response = client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                speed=speed,
                response_format="wav"
            )
            response.stream_to_file(output_path)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info("[TTS] OpenAI TTS 合成完了")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[TTS] OpenAI TTS エラー: {e}")
            return False


def create_tts_engine(config: dict) -> TTSEngine:
    """設定からTTSエンジンを生成"""
    engine_type = config.get("engine", "piper")
    
    if engine_type == "piper":
        cfg = config.get("piper", {})
        return PiperTTS(
            binary=cfg.get("binary", "/home/pi/piper/piper"),
            model=cfg.get("model", "/home/pi/piper/ja_JP-takumi-medium.onnx"),
            config=cfg.get("config", ""),
            speed=cfg.get("speed", 1.0),
            speaker_id=cfg.get("speaker_id", 0),
        )
    elif engine_type == "openai_tts":
        cfg = config.get("openai_tts", {})
        return OpenAITTS(
            model=cfg.get("model", "tts-1"),
            voice=cfg.get("voice", "nova"),
        )
    else:
        raise ValueError(f"未知のTTSエンジン: {engine_type}")
