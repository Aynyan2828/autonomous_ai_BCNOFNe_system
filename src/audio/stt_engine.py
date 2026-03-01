<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STTエンジン（音声認識）抽象化 + 実装
whisper.cpp（オフライン優先） / Whisper API（フォールバック）
"""

import os
import subprocess
import tempfile
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class STTEngine(ABC):
    """STTエンジン抽象基底クラス"""
    
    @abstractmethod
    def transcribe(self, wav_path: str) -> str:
        """
        WAVファイルをテキストに変換
        
        Args:
            wav_path: 録音WAVファイルパス
            
        Returns:
            認識テキスト（空文字列=認識失敗）
        """
        pass


class WhisperCppSTT(STTEngine):
    """whisper.cpp ローカルSTT"""
    
    def __init__(self, binary: str, model: str, language: str = "ja", threads: int = 4):
        self.binary = binary
        self.model = model
        self.language = language
        self.threads = threads
        
        if not os.path.exists(binary):
            raise FileNotFoundError(f"whisper.cpp binary not found: {binary}")
        if not os.path.exists(model):
            raise FileNotFoundError(f"whisper model not found: {model}")
    
    def transcribe(self, wav_path: str) -> str:
        """whisper.cppでテキスト化"""
        start = time.time()
        try:
            result = subprocess.run(
                [
                    self.binary,
                    "-m", self.model,
                    "-f", wav_path,
                    "-l", self.language,
                    "-t", str(self.threads),
                    "--no-timestamps",
                    "-otxt",
                ],
                capture_output=True, text=True, timeout=30
            )
            
            elapsed = time.time() - start
            logger.info(f"[STT] whisper.cpp 処理時間: {elapsed:.1f}秒")
            
            # 出力テキストファイルを読む
            txt_path = wav_path + ".txt"
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                os.remove(txt_path)
                return text
            
            # stdout fallback
            text = result.stdout.strip()
            # whisper.cppの出力からテキスト部分を抽出
            lines = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith('[')]
            return " ".join(lines)
            
        except subprocess.TimeoutExpired:
            logger.error("[STT] whisper.cpp タイムアウト")
            return ""
        except Exception as e:
            logger.error(f"[STT] whisper.cpp エラー: {e}")
            return ""


class WhisperAPISTT(STTEngine):
    """OpenAI Whisper API STT（フォールバック）"""
    
    def __init__(self, model: str = "whisper-1"):
        self.model = model
    
    def transcribe(self, wav_path: str) -> str:
        """Whisper APIでテキスト化"""
        try:
            import openai
            client = openai.OpenAI()
            
            with open(wav_path, 'rb') as f:
                result = client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language="ja"
                )
            return result.text.strip()
            
        except Exception as e:
            logger.error(f"[STT] Whisper API エラー: {e}")
            return ""


def create_stt_engine(config: dict) -> STTEngine:
    """設定からSTTエンジンを生成"""
    engine_type = config.get("engine", "whisper_cpp")
    
    if engine_type == "whisper_cpp":
        cfg = config.get("whisper_cpp", {})
        return WhisperCppSTT(
            binary=cfg.get("binary", "/home/pi/whisper.cpp/main"),
            model=cfg.get("model", "/home/pi/whisper.cpp/models/ggml-tiny.bin"),
            language=cfg.get("language", "ja"),
            threads=cfg.get("threads", 4),
        )
    elif engine_type == "whisper_api":
        cfg = config.get("whisper_api", {})
        return WhisperAPISTT(model=cfg.get("model", "whisper-1"))
    else:
        raise ValueError(f"未知のSTTエンジン: {engine_type}")
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STTエンジン（音声認識）抽象化 + 実装
whisper.cpp（オフライン優先） / Whisper API（フォールバック）
"""

import os
import subprocess
import tempfile
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class STTEngine(ABC):
    """STTエンジン抽象基底クラス"""
    
    @abstractmethod
    def transcribe(self, wav_path: str) -> str:
        """
        WAVファイルをテキストに変換
        
        Args:
            wav_path: 録音WAVファイルパス
            
        Returns:
            認識テキスト（空文字列=認識失敗）
        """
        pass


class WhisperCppSTT(STTEngine):
    """whisper.cpp ローカルSTT"""
    
    def __init__(self, binary: str, model: str, language: str = "ja", threads: int = 4):
        self.binary = binary
        self.model = model
        self.language = language
        self.threads = threads
        
        if not os.path.exists(binary):
            raise FileNotFoundError(f"whisper.cpp binary not found: {binary}")
        if not os.path.exists(model):
            raise FileNotFoundError(f"whisper model not found: {model}")
    
    def transcribe(self, wav_path: str) -> str:
        """whisper.cppでテキスト化"""
        start = time.time()
        try:
            result = subprocess.run(
                [
                    self.binary,
                    "-m", self.model,
                    "-f", wav_path,
                    "-l", self.language,
                    "-t", str(self.threads),
                    "--no-timestamps",
                    "-otxt",
                ],
                capture_output=True, text=True, timeout=30
            )
            
            elapsed = time.time() - start
            logger.info(f"[STT] whisper.cpp 処理時間: {elapsed:.1f}秒")
            
            # 出力テキストファイルを読む
            txt_path = wav_path + ".txt"
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                os.remove(txt_path)
                return text
            
            # stdout fallback
            text = result.stdout.strip()
            # whisper.cppの出力からテキスト部分を抽出
            lines = [l.strip() for l in text.split('\n') if l.strip() and not l.startswith('[')]
            return " ".join(lines)
            
        except subprocess.TimeoutExpired:
            logger.error("[STT] whisper.cpp タイムアウト")
            return ""
        except Exception as e:
            logger.error(f"[STT] whisper.cpp エラー: {e}")
            return ""


class WhisperAPISTT(STTEngine):
    """OpenAI Whisper API STT（フォールバック）"""
    
    def __init__(self, model: str = "whisper-1"):
        self.model = model
    
    def transcribe(self, wav_path: str) -> str:
        """Whisper APIでテキスト化"""
        try:
            import openai
            client = openai.OpenAI()
            
            with open(wav_path, 'rb') as f:
                result = client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language="ja"
                )
            return result.text.strip()
            
        except Exception as e:
            logger.error(f"[STT] Whisper API エラー: {e}")
            return ""


def create_stt_engine(config: dict) -> STTEngine:
    """設定からSTTエンジンを生成"""
    engine_type = config.get("engine", "whisper_cpp")
    
    if engine_type == "whisper_cpp":
        cfg = config.get("whisper_cpp", {})
        return WhisperCppSTT(
            binary=cfg.get("binary", "/home/pi/whisper.cpp/main"),
            model=cfg.get("model", "/home/pi/whisper.cpp/models/ggml-tiny.bin"),
            language=cfg.get("language", "ja"),
            threads=cfg.get("threads", 4),
        )
    elif engine_type == "whisper_api":
        cfg = config.get("whisper_api", {})
        return WhisperAPISTT(model=cfg.get("model", "whisper-1"))
    else:
        raise ValueError(f"未知のSTTエンジン: {engine_type}")
>>>>>>> Stashed changes
