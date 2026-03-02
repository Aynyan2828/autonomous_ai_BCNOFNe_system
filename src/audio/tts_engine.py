
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


class HybridTTS(TTSEngine):
    """ハイブリッドTTS（ローカル優先＋クラウドフォールバック＋キャッシュ対応）"""
    
    def __init__(self, local_tts: PiperTTS, cloud_tts: OpenAITTS):
        self.local_tts = local_tts
        self.cloud_tts = cloud_tts
        self.mode = "HYBRID"  # "NURSE", "OPENAI", "HYBRID"
        self.local_fail_count = 0
        self.local_disabled_until = 0.0
        self.local_tts.name = "nurse_robo"
        self.cloud_tts.name = "openai"
        self.speaker_id = self.local_tts.speaker_id  # fallback proxy
        
        # キャッシュディレクトリの準備
        self.cache_dir = "/var/cache/ship_voice/nurse_robo"
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except PermissionError:
            self.cache_dir = "/tmp/ship_voice/nurse_robo"
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.warning(f"[TTS] /var/cache へのアクセス権限がないため、{self.cache_dir} をキャッシュに利用します。")

    def synthesize(self, text: str, output_path: str, speed: float = 1.0, 
                   category: str = "general", priority: int = 3, req_id: str = "req_xxx") -> bool:
        """合成のメインルーチン"""
        import shutil
        import hashlib
        
        # ログ用変数
        trigger = category
        selected_engine = "nurse_robo"
        reason = "rule: default"
        tts_ok = False
        error_msg = ""
        
        # ===== 推論ルールの適用 =====
        if self.mode == "OPENAI":
            selected_engine = "openai"
            reason = "rule: mode_forced_openai"
        elif self.mode == "NURSE":
            selected_engine = "nurse_robo"
            reason = "rule: mode_forced_nurse"
        else:
            # HYBRID mode logic
            if priority == 2:  # EMERGENCY
                selected_engine = "nurse_robo"
                reason = "rule: emergency_fixed"
            elif len(text) > 300:
                selected_engine = "openai"
                reason = "rule: long_text_fallback"
            else:
                # 障害フォールバックの確認
                if time.time() < self.local_disabled_until:
                    selected_engine = "openai"
                    reason = f"fallback: local_disabled (fails={self.local_fail_count})"
                else:
                    selected_engine = "nurse_robo"
                    reason = "rule: hybrid_default"
        
        logger.info(f"[TTS_REQ] id={req_id} trigger={trigger} target={selected_engine} reason='{reason}'")
        
        # ===== 合成パイプライン =====
        if selected_engine == "nurse_robo":
            # キャッシュのチェック
            cache_key = f"{text}|{self.local_tts.speaker_id}|{speed}".encode('utf-8')
            cache_hash = hashlib.sha1(cache_key).hexdigest()
            cache_path = os.path.join(self.cache_dir, f"{cache_hash}.wav")
            
            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
                shutil.copy2(cache_path, output_path)
                logger.info(f"[TTS_RES] id={req_id} engine=nurse_robo status=cache_hit")
                self.local_fail_count = 0  # 成功したらカウントリセット
                return True
            
            # キャッシュになければ生成
            try:
                success = self.local_tts.synthesize(text, output_path, speed)
                if success:
                    # 成功したらキャッシュに保存
                    shutil.copy2(output_path, cache_path)
                    logger.info(f"[TTS_RES] id={req_id} engine=nurse_robo status=generated")
                    self.local_fail_count = 0
                    return True
                else:
                    error_msg = "Piper generation returned False"
            except Exception as e:
                error_msg = str(e)
            
            # ここに来る＝失敗
            self.local_fail_count += 1
            logger.error(f"[TTS_RES] id={req_id} engine=nurse_robo status=fail error='{error_msg}' fails={self.local_fail_count}")
            
            # 3回連続失敗でフォールバック発動
            if self.mode == "HYBRID" and self.local_fail_count >= 3:
                self.local_disabled_until = time.time() + 300  # 5分間
                logger.warning(f"[TTS_SYSTEM] Nurse Roboが3回連続失敗しました。5分間OpenAIに強制フォールバックします。")
            
            # モードがNURSE固定でなければフォールバック実行
            if self.mode != "NURSE":
                logger.info(f"[TTS_REQ] id={req_id} trigger={trigger} target=openai reason='fallback: nurse_failed'")
                selected_engine = "openai"
            else:
                return False

        if selected_engine == "openai":
            try:
                success = self.cloud_tts.synthesize(text, output_path, speed)
                if success:
                    logger.info(f"[TTS_RES] id={req_id} engine=openai status=generated")
                    return True
                else:
                    logger.error(f"[TTS_RES] id={req_id} engine=openai status=fail error='OpenAI generation False'")
                    return False
            except Exception as e:
                logger.error(f"[TTS_RES] id={req_id} engine=openai status=fail error='{e}'")
                return False
        
        return False


def create_tts_engine(config: dict) -> TTSEngine:
    """設定からTTSエンジンを生成"""
    engine_type = config.get("engine", "piper")
    
    cfg_p = config.get("piper", {})
    local_tts = PiperTTS(
        binary=cfg_p.get("binary", "/home/pi/piper/piper"),
        model=cfg_p.get("model", "/home/pi/piper/ja_JP-takumi-medium.onnx"),
        config=cfg_p.get("config", ""),
        speed=cfg_p.get("speed", 1.0),
        speaker_id=cfg_p.get("speaker_id", 0),
    )
    
    cfg_o = config.get("openai_tts", {})
    cloud_tts = OpenAITTS(
        model=cfg_o.get("model", "tts-1"),
        voice=cfg_o.get("voice", "nova"),
    )
    
    if engine_type == "hybrid":
        return HybridTTS(local_tts, cloud_tts)
    elif engine_type == "openai_tts":
        return cloud_tts
    else:
        # デフォルトまたはpiper指定時はそのまま返すもよし、
        # 強制的にHybridにしておき設定でModeを縛る運用でもよい。
        # 要件に合わせてハイブリッドを返す
        return HybridTTS(local_tts, cloud_tts)

