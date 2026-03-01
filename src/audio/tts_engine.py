<<<<<<< Updated upstream
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
=======
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
            # APIキーの改行混入を防止
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            client = openai.OpenAI(api_key=api_key)
            
            with client.audio.speech.with_streaming_response.create(
                model=self.model,
                voice=self.voice,
                input=text,
                speed=speed,
                response_format="wav"
            ) as response:
                response.stream_to_file(output_path)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info("[TTS] OpenAI TTS 合成完了")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[TTS] OpenAI TTS エラー: {e}")
            return False

class VoicevoxTTS(TTSEngine):
    """VOICEVOX ローカル音声合成（萌えボイス対応）"""
    
    SPEAKER_NAMES = {
        0: "四国めたん（あまあま）",
        1: "ずんだもん（あまあま）",
        2: "四国めたん（ノーマル）",
        3: "ずんだもん（ノーマル）",
        4: "四国めたん（セクシー）",
        5: "ずんだもん（セクシー）",
        6: "四国めたん（ツンツン）",
        7: "ずんだもん（ツンツン）",
        8: "春日部つむぎ",
        10: "雨晴はう",
        14: "冥鳴ひまり",
        47: "ナースロボ＿タイプT（ノーマル）",
        48: "ナースロボ＿タイプT（楽々）",
        49: "ナースロボ＿タイプT（恐怖）",
        50: "ナースロボ＿タイプT（内緒話）",
    }
    
    def __init__(self, core_dir: str = "/home/pi/voicevox/voicevox_core",
                 speaker_id: int = 1, speed: float = 1.0):
        self.core_dir = core_dir
        self.speaker_id = speaker_id
        self.default_speed = speed
        self._synthesizer = None
        self._initialized = False
    
    def _init_engine(self):
        """遅延初期化"""
        if self._initialized:
            return
        try:
            from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
            import glob
            
            # ONNX Runtime ロード
            ort_path = glob.glob(os.path.join(self.core_dir, "onnxruntime", "lib", "libvoicevox_onnxruntime*"))
            if ort_path:
                ort = Onnxruntime.load_once(filename=ort_path[0])
            else:
                ort = Onnxruntime.load_once()
            
            # Open JTalk 辞書
            dict_dir = os.path.join(self.core_dir, "dict", "open_jtalk_dic_utf_8-1.11")
            ojt = OpenJtalk(dict_dir)
            
            # Synthesizer (0.16.x API: ort, ojt)
            self._synthesizer = Synthesizer(ort, ojt)
            
            # 音声モデルロード
            model_files = glob.glob(os.path.join(self.core_dir, "models", "vvms", "*.vvm"))
            for mf in model_files:
                model = VoiceModelFile.open(mf)
                self._synthesizer.load_voice_model(model)
            
            self._initialized = True
            name = self.SPEAKER_NAMES.get(self.speaker_id, f"ID:{self.speaker_id}")
            logger.info(f"[TTS] VOICEVOX 初期化完了: {name}")
            
        except Exception as e:
            logger.error(f"[TTS] VOICEVOX 初期化エラー: {e}")
            self._initialized = False
    
    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """VOICEVOXでテキスト→WAV生成"""
        start = time.time()
        try:
            self._init_engine()
            if not self._synthesizer:
                logger.error("[TTS] VOICEVOX 未初期化")
                return False
            
            wav_data = self._synthesizer.tts(text, style_id=self.speaker_id)
            
            with open(output_path, 'wb') as f:
                f.write(wav_data)
            
            elapsed = time.time() - start
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"[TTS] VOICEVOX 合成完了: {elapsed:.1f}秒")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[TTS] VOICEVOX エラー: {e}")
            return False

class HybridTTS(TTSEngine):
    """ハイブリッドTTS: VOICEVOXキャッシュ + OpenAI TTSフォールバック"""
    
    def __init__(self, cache_dir: str = "/home/pi/autonomous_ai_BCNOFNe_system/src/audio/cache",
                 openai_model: str = "tts-1", openai_voice: str = "shimmer"):
        self.cache_dir = cache_dir
        self.openai = OpenAITTS(model=openai_model, voice=openai_voice)
        os.makedirs(cache_dir, exist_ok=True)
    
    def _cache_key(self, text: str) -> str:
        """テキストからキャッシュキーを生成"""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def synthesize(self, text: str, output_path: str, speed: float = 1.0) -> bool:
        """キャッシュにあればそれを使用、なければOpenAI TTS"""
        cache_file = os.path.join(self.cache_dir, f"{self._cache_key(text)}.wav")
        
        if os.path.exists(cache_file):
            # キャッシュヒット（VOICEVOX事前生成）
            import shutil
            shutil.copy2(cache_file, output_path)
            logger.info(f"[TTS] キャッシュヒット: {text[:20]}...")
            return True
        
        # キャッシュミス → OpenAI TTS
        logger.info(f"[TTS] OpenAIフォールバック: {text[:20]}...")
        return self.openai.synthesize(text, output_path, speed)


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
    elif engine_type == "voicevox":
        cfg = config.get("voicevox", {})
        return VoicevoxTTS(
            core_dir=cfg.get("core_dir", "/home/pi/voicevox/voicevox_core"),
            speaker_id=cfg.get("speaker_id", 47),
            speed=cfg.get("speed", 1.0),
        )
    elif engine_type == "hybrid":
        cfg = config.get("hybrid", {})
        return HybridTTS(
            cache_dir=cfg.get("cache_dir", "/home/pi/autonomous_ai_BCNOFNe_system/src/audio/cache"),
            openai_model=cfg.get("openai_model", "tts-1"),
            openai_voice=cfg.get("openai_voice", "shimmer"),
        )
    else:
        raise ValueError(f"未知のTTSエンジン: {engine_type}")
>>>>>>> Stashed changes
