#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム状態読み上げモジュール
F15押下時にCPU温度、メモリ、ディスク使用率等を音声で報告
"""

import os
import subprocess
import psutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_system_status_text() -> str:
    """
    システム状態をaynyan口調のテキストで生成
    
    Returns:
        読み上げ用テキスト
    """
    parts = []
    
    # CPU温度
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
        if temp >= 75:
            parts.append(f"やばい！CPU温度が{temp:.0f}度もあるっちゃけど！冷やした方がよかよ")
        elif temp >= 65:
            parts.append(f"CPU温度は{temp:.0f}度。ちょい温めやけど、まだ大丈夫")
        else:
            parts.append(f"CPU温度は{temp:.0f}度。ぜんぜん余裕やけん安心して")
    except Exception:
        parts.append("CPU温度は取得できんかった…ごめん")
    
    # CPU使用率
    try:
        cpu_pct = psutil.cpu_percent(interval=0.5)
        if cpu_pct >= 80:
            parts.append(f"CPU使用率{cpu_pct:.0f}%！ちょっと忙しすぎるかも")
        elif cpu_pct >= 50:
            parts.append(f"CPU使用率は{cpu_pct:.0f}%。頑張っとるよ")
        else:
            parts.append(f"CPU使用率は{cpu_pct:.0f}%で余裕あり")
    except Exception:
        pass
    
    # メモリ
    try:
        mem = psutil.virtual_memory()
        if mem.percent >= 85:
            parts.append(f"メモリは{mem.percent:.0f}%でちょっとキツか")
        else:
            parts.append(f"メモリは{mem.percent:.0f}%で問題なし")
    except Exception:
        pass
    
    # ディスク（SSD / HDD）
    try:
        ssd = psutil.disk_usage("/")
        if ssd.percent >= 85:
            parts.append(f"SSDが{ssd.percent:.0f}%！整理した方がよかよ")
        else:
            parts.append(f"SSDは{ssd.percent:.0f}%でまだ余裕")
    except Exception:
        pass
    
    try:
        if os.path.ismount("/mnt/hdd") or os.path.exists("/mnt/hdd/archive"):
            hdd = psutil.disk_usage("/mnt/hdd")
            parts.append(f"HDDは{hdd.percent:.0f}%")
        else:
            parts.append("HDDはマウントされとらん")
    except Exception:
        pass
    
    # ネットワーク
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
            capture_output=True, timeout=5
        )
        if r.returncode == 0:
            parts.append("ネットはつながっとるよ")
        else:
            parts.append("ネットが不安定みたい…")
    except Exception:
        parts.append("ネット確認できんかった")
    
    return "。".join(parts) + "。以上、報告終わり！"
