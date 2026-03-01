#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS グローバルAI状態管理
各モジュール（main, line_bot, audio）間で状態を共有する
ファイルベースIPC: /tmp/shipos_ai_state.json
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE = "/tmp/shipos_ai_state.json"


class AIState:
    """グローバルAI状態"""
    
    # AI状態（顔文字マッピング用）
    STATUS_IDLE = "idle"
    STATUS_THINKING = "thinking"
    STATUS_ACTIVE = "active"
    STATUS_LINE_RECV = "line_recv"
    STATUS_LINE_SEND = "line_send"
    STATUS_LISTENING = "listening"
    STATUS_ERROR = "error"
    STATUS_BILLING_STOP = "billing_stop"
    
    # 顔文字マップ
    FACE_MAP = {
        "idle":         "(-_-)",
        "thinking":     "( ..)phi",
        "active":       "(`-w-')",
        "line_recv":    "(-_-)no<<",
        "line_send":    ">>(^_^)",
        "listening":    "(o_o)",
        "error":        "(x_x)",
        "billing_stop": "($_$)!",
    }
    
    # 航行状態ASCII
    SAIL_MAP = {
        "autonomous":  ">===>",
        "user_first":  "[=]",
        "maintenance": "{=}",
        "power_save":  "---",
        "safe":        "!!!",
    }
    
    def __init__(self):
        self.mode = "autonomous"
        self.ai_status = self.STATUS_IDLE
        self.goal = ""
        self.line_status = "idle"
        self.cpu_temp = 0.0
        self.disk_percent = 0.0
        self.lan_ip = "---"
        self.ts_ip = "OFFLINE"
        self._load()
    
    def _load(self):
        """ファイルから状態を読み込み"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.mode = data.get("mode", self.mode)
                self.ai_status = data.get("ai_status", self.ai_status)
                self.goal = data.get("goal", self.goal)
                self.line_status = data.get("line_status", self.line_status)
                self.cpu_temp = data.get("cpu_temp", 0.0)
                self.disk_percent = data.get("disk_percent", 0.0)
                self.lan_ip = data.get("lan_ip", "---")
                self.ts_ip = data.get("ts_ip", "OFFLINE")
        except Exception:
            pass
    
    def save(self):
        """状態をファイルに書き出し"""
        try:
            data = {
                "mode": self.mode,
                "ai_status": self.ai_status,
                "goal": self.goal,
                "line_status": self.line_status,
                "cpu_temp": self.cpu_temp,
                "disk_percent": self.disk_percent,
                "lan_ip": self.lan_ip,
                "ts_ip": self.ts_ip,
                "updated": datetime.now().isoformat(),
            }
            tmp = STATE_FILE + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            logger.error(f"AIState保存エラー: {e}")
    
    def set_status(self, status: str):
        """AI状態を更新して保存"""
        self.ai_status = status
        self.save()
    
    def get_face(self) -> str:
        """現在の顔文字を取得"""
        return self.FACE_MAP.get(self.ai_status, "(-_-)")
    
    def get_sail(self) -> str:
        """航行状態ASCII記号を取得"""
        return self.SAIL_MAP.get(self.mode, ">===>")
    
    def get_mode_name(self) -> str:
        """航行モード表示名"""
        names = {
            "autonomous": "SAIL",
            "user_first": "PORT",
            "maintenance": "DOCK",
            "power_save": "ANCHOR",
            "safe": "SOS",
        }
        return names.get(self.mode, "SAIL")
    
    def build_telop(self) -> str:
        """テロップ用文字列を構築"""
        mode_name = self.get_mode_name()
        sail = self.get_sail()
        dest = self.goal if self.goal else "NONE"
        face = self.get_face()
        
        return (
            f"shipOS: {mode_name} {sail}   "
            f"DEST: {dest}   "
            f"AI: {face}   "
        )
    
    def build_ip_telop(self) -> str:
        """IP行テロップ文字列を構築"""
        return f"LAN: {self.lan_ip}  TS: {self.ts_ip}   "
    
    def build_hw_line(self) -> str:
        """ハードウェア行（固定）"""
        return f"TEMP:{self.cpu_temp:.0f}C DISK:{self.disk_percent:.0f}%"


# シングルトン
_global_state: Optional[AIState] = None

def get_state() -> AIState:
    """グローバルAIStateを取得"""
    global _global_state
    if _global_state is None:
        _global_state = AIState()
    return _global_state
