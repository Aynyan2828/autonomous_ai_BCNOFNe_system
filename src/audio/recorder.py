<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
録音モジュール
ALSAでWAV録音。Push-to-talk / トグル両対応。
"""

import os
import subprocess
import tempfile
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Recorder:
    """音声録音"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 device: str = "default", max_duration: int = 30):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.max_duration = max_duration
        
        self._process: Optional[subprocess.Popen] = None
        self._output_path: str = ""
        self._recording = False
        self._lock = threading.Lock()
    
    @property
    def is_recording(self) -> bool:
        return self._recording
    
    def start(self) -> str:
        """
        録音開始
        
        Returns:
            出力WAVファイルパス
        """
        with self._lock:
            if self._recording:
                logger.warning("[Recorder] 既に録音中")
                return self._output_path
            
            fd, self._output_path = tempfile.mkstemp(suffix=".wav", prefix="rec_")
            os.close(fd)
            
            try:
                self._process = subprocess.Popen(
                    [
                        "arecord",
                        "-D", self.device,
                        "-f", "S16_LE",
                        "-r", str(self.sample_rate),
                        "-c", str(self.channels),
                        "-d", str(self.max_duration),
                        self._output_path
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._recording = True
                logger.info(f"[Recorder] 録音開始: {self._output_path}")
                return self._output_path
                
            except Exception as e:
                logger.error(f"[Recorder] 録音開始エラー: {e}")
                self._recording = False
                return ""
    
    def stop(self) -> str:
        """
        録音停止
        
        Returns:
            録音WAVファイルパス
        """
        with self._lock:
            if not self._recording:
                return ""
            
            try:
                if self._process and self._process.poll() is None:
                    self._process.terminate()
                    self._process.wait(timeout=3)
            except Exception as e:
                logger.error(f"[Recorder] 録音停止エラー: {e}")
                if self._process:
                    self._process.kill()
            
            self._recording = False
            path = self._output_path
            
            # ファイル検証
            if os.path.exists(path) and os.path.getsize(path) > 44:  # WAVヘッダ以上
                logger.info(f"[Recorder] 録音完了: {path} ({os.path.getsize(path)} bytes)")
                return path
            else:
                logger.warning("[Recorder] 録音ファイルが空または不正")
                return ""
    
    def cleanup(self):
        """一時ファイル削除"""
        if self._output_path and os.path.exists(self._output_path):
            try:
                os.remove(self._output_path)
            except Exception:
                pass
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
録音モジュール
ALSAでWAV録音。Push-to-talk / トグル両対応。
"""

import os
import subprocess
import tempfile
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Recorder:
    """音声録音"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 device: str = "default", max_duration: int = 30):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.max_duration = max_duration
        
        self._process: Optional[subprocess.Popen] = None
        self._output_path: str = ""
        self._recording = False
        self._lock = threading.Lock()
    
    @property
    def is_recording(self) -> bool:
        return self._recording
    
    def start(self) -> str:
        """
        録音開始
        
        Returns:
            出力WAVファイルパス
        """
        with self._lock:
            if self._recording:
                logger.warning("[Recorder] 既に録音中")
                return self._output_path
            
            fd, self._output_path = tempfile.mkstemp(suffix=".wav", prefix="rec_")
            os.close(fd)
            
            try:
                self._process = subprocess.Popen(
                    [
                        "arecord",
                        "-D", self.device,
                        "-f", "S16_LE",
                        "-r", str(self.sample_rate),
                        "-c", str(self.channels),
                        "-d", str(self.max_duration),
                        self._output_path
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                self._recording = True
                logger.info(f"[Recorder] 録音開始: {self._output_path} (device: {self.device})")
                
                # エラー監視スレッド（オプションだが、ここでは簡易的に開始時のみチェック）
                return self._output_path
                
            except Exception as e:
                logger.error(f"[Recorder] 録音開始エラー: {e}")
                self._recording = False
                return ""
    
    def stop(self) -> str:
        """
        録音停止
        
        Returns:
            録音WAVファイルパス
        """
        with self._lock:
            if not self._recording:
                return ""
            
            try:
                if self._process:
                    if self._process.poll() is None:
                        self._process.terminate()
                    
                    # stderrの読み取り
                    stderr_data = self._process.stderr.read().decode().strip()
                    if stderr_data:
                        logger.warning(f"[Recorder] arecord stderr: {stderr_data}")
                    
                    self._process.wait(timeout=3)
            except Exception as e:
                logger.error(f"[Recorder] 録音停止エラー: {e}")
                if self._process:
                    self._process.kill()
            
            self._recording = False
            path = self._output_path
            
            # ファイル検証
            if os.path.exists(path) and os.path.getsize(path) > 44:  # WAVヘッダ以上
                logger.info(f"[Recorder] 録音完了: {path} ({os.path.getsize(path)} bytes)")
                return path
            else:
                logger.warning("[Recorder] 録音ファイルが空または不正")
                return ""
    
    def cleanup(self):
        """一時ファイル削除"""
        if self._output_path and os.path.exists(self._output_path):
            try:
                os.remove(self._output_path)
            except Exception:
                pass
>>>>>>> Stashed changes
