#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独り言エンジン（環境音）
ランダム間隔で短い独り言を生成し、小音量で再生
"""

import os
import time
import random
import logging
from datetime import datetime
from typing import Optional, Callable, List
from pathlib import Path

logger = logging.getLogger(__name__)


class MonologueEngine:
    """独り言エンジン"""
    
    PERSONA_FILE = os.path.join(
        os.path.dirname(__file__), "prompts", "aynyan_persona.txt"
    )
    
    # 状況別テンプレート（LLMなしでも動作するフォールバック）
    TEMPLATES = {
        "idle": [
            "特に異常なし。ちょっと退屈かも",
            "マスター無理しすぎんとよ",
            "今日は穏やかな航海ばいね〜",
            "ログの整理しとくね、マスター",
            "ん〜、なんもない時間って好き",
            "マスター、今日なんか楽しいことあった？",
        ],
        "cpu_warm": [
            "あ、ちょっとCPU温度上がってきたかも…",
            "CPU温めやけど、まだ大丈夫やけん",
            "エンジンちょっと熱かね〜",
        ],
        "cpu_hot": [
            "ねぇマスター！CPUがアッツアツでやばいっちゃけど！",
            "機関温度高すぎ！ちょっと休ませて〜",
        ],
        "disk_high": [
            "船倉がだいぶ埋まっとるよ…整理しよっか？",
            "ディスクぱんぱんやけん、掃除した方がよかよ",
        ],
        "net_down": [
            "通信途絶…ちょっと寂しかね",
            "ネットつながらんけん、オフラインで頑張るばい",
        ],
        "night": [
            "静かな夜ばい…",
            "マスター、もう遅かよ。寝んね？",
            "夜の航海は落ち着くね〜",
        ],
        "recovery": [
            "ふぅ〜落ち着いたよ。ちょっと焦ったぁ",
            "復旧完了！もう大丈夫ばい♪",
        ],
    }
    
    def __init__(self, min_interval: int = 7, max_interval: int = 25,
                 quiet_start: int = 22, quiet_end: int = 6,
                 enabled: bool = True):
        self.min_interval = min_interval  # 分
        self.max_interval = max_interval  # 分
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end
        self.enabled = enabled
        self.muted = False
        
        self._next_time: float = self._calc_next_time()
        self._last_monologue: str = ""
        
        # システム状態（外部から更新）
        self.cpu_temp: float = 0
        self.disk_percent: float = 0
        self.net_ok: bool = True
    
    def _calc_next_time(self) -> float:
        """次の独り言時刻を計算"""
        interval = random.randint(self.min_interval * 60, self.max_interval * 60)
        return time.time() + interval
    
    def is_quiet_hours(self) -> bool:
        """夜間判定"""
        hour = datetime.now().hour
        if self.quiet_start > self.quiet_end:  # 22-6のように日跨ぎ
            return hour >= self.quiet_start or hour < self.quiet_end
        return self.quiet_start <= hour < self.quiet_end
    
    def update_status(self, cpu_temp: float = 0, disk_percent: float = 0, net_ok: bool = True):
        """システム状態を更新"""
        self.cpu_temp = cpu_temp
        self.disk_percent = disk_percent
        self.net_ok = net_ok
    
    def toggle_mute(self) -> bool:
        """ミュートトグル"""
        self.muted = not self.muted
        logger.info(f"[Monologue] ミュート: {'ON' if self.muted else 'OFF'}")
        return self.muted
    
    def check_and_generate(self) -> Optional[str]:
        """
        独り言のタイミングをチェックし、テキストを生成
        
        Returns:
            独り言テキスト（まだ時間でなければNone）
        """
        if not self.enabled or self.muted:
            return None
        
        if time.time() < self._next_time:
            return None
        
        # 次回タイミングを再計算
        self._next_time = self._calc_next_time()
        
        # 状況に応じたテンプレートを選択
        text = self._select_monologue()
        self._last_monologue = text
        
        return text
    
    def _select_monologue(self) -> str:
        """状況に応じた独り言を選択"""
        # 優先度順にチェック
        if self.cpu_temp >= 75:
            pool = self.TEMPLATES["cpu_hot"]
        elif self.cpu_temp >= 65:
            pool = self.TEMPLATES["cpu_warm"]
        elif not self.net_ok:
            pool = self.TEMPLATES["net_down"]
        elif self.disk_percent >= 85:
            pool = self.TEMPLATES["disk_high"]
        elif self.is_quiet_hours():
            pool = self.TEMPLATES["night"]
        else:
            pool = self.TEMPLATES["idle"]
        
        # 前回と同じものを避ける
        candidates = [t for t in pool if t != self._last_monologue]
        if not candidates:
            candidates = pool
        
        return random.choice(candidates)
    
    def get_volume(self, base_volume: float = 0.25, night_volume: float = 0.15) -> float:
        """現在の音量を取得"""
        if self.is_quiet_hours():
            return night_volume
        return base_volume
