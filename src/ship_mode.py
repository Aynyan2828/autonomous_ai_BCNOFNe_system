#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS モードシステム
5つの航行モードを管理し、システム全体の振る舞いを制御する
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class ShipMode:
    """shipOS モード管理クラス"""
    
    # モード定義
    MODES = {
        "autonomous": {
            "name": "自律航海",
            "icon": "⛵",
            "desc": "自律思考・整理・学習・保守",
            "iteration_interval": 30,
            "line_notify": "minimal",     # 最小通知
            "autonomous_tasks": True,
            "priority": "system",
        },
        "user_first": {
            "name": "入港待機",
            "icon": "🏠",
            "desc": "ユーザー対話・支援優先",
            "iteration_interval": 10,
            "line_notify": "responsive",  # 即応
            "autonomous_tasks": False,
            "priority": "user",
        },
        "maintenance": {
            "name": "ドック入り",
            "icon": "🔧",
            "desc": "保守・メンテナンス専用",
            "iteration_interval": 60,
            "line_notify": "status",      # 状態のみ
            "autonomous_tasks": True,
            "priority": "maintenance",
        },
        "power_save": {
            "name": "停泊",
            "icon": "🌙",
            "desc": "省電力・最小稼働",
            "iteration_interval": 300,
            "line_notify": "critical",    # 重大のみ
            "autonomous_tasks": False,
            "priority": "none",
        },
        "safe": {
            "name": "救難信号",
            "icon": "🆘",
            "desc": "安全モード・最小機能",
            "iteration_interval": 60,
            "line_notify": "all",         # 全通知
            "autonomous_tasks": False,
            "priority": "safety",
        },
    }
    
    DEFAULT_MODE = "autonomous"
    STATE_FILE = "/home/pi/autonomous_ai_BCNOFNe_system/state/ship_mode.json"
    HISTORY_FILE = "/home/pi/autonomous_ai_BCNOFNe_system/state/mode_history.jsonl"
    
    def __init__(self):
        """初期化"""
        self.current_mode = self.DEFAULT_MODE
        self.mode_since = datetime.now().isoformat()
        self.override_active = False
        self.override_until = None
        
        # 状態ディレクトリ
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        
        # 永続状態の復元
        self._load_state()
    
    def _load_state(self):
        """永続状態を復元"""
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.current_mode = state.get("mode", self.DEFAULT_MODE)
                self.mode_since = state.get("since", datetime.now().isoformat())
                self.override_active = state.get("override", False)
                self.override_until = state.get("override_until")
        except Exception:
            pass
    
    def _save_state(self):
        """状態を永続化"""
        try:
            state = {
                "mode": self.current_mode,
                "since": self.mode_since,
                "override": self.override_active,
                "override_until": self.override_until,
                "updated": datetime.now().isoformat()
            }
            tmp = self.STATE_FILE + ".tmp"
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.STATE_FILE)
        except Exception as e:
            print(f"モード状態保存エラー: {e}")
    
    def switch(self, mode: str, reason: str = "", source: str = "system") -> Dict[str, Any]:
        """
        モードを切り替える
        
        Args:
            mode: 切替先モード名
            reason: 切替理由
            source: 発生元 ("calendar", "user", "system", "health", "failsafe")
            
        Returns:
            切替結果 {success, old_mode, new_mode, message}
        """
        if mode not in self.MODES:
            return {"success": False, "message": f"不明なモード: {mode}"}
        
        old_mode = self.current_mode
        if old_mode == mode:
            return {"success": True, "old_mode": old_mode, "new_mode": mode,
                    "message": "既に同じモードです"}
        
        # オーバーライド中はカレンダー自動切替を無視
        if source == "calendar" and self.override_active:
            if self.override_until and datetime.now().isoformat() < self.override_until:
                return {"success": False, "message": "手動オーバーライド中（自動切替を無視）"}
            else:
                self.override_active = False
                self.override_until = None
        
        self.current_mode = mode
        self.mode_since = datetime.now().isoformat()
        self._save_state()
        
        # 履歴記録
        self._record_history(old_mode, mode, reason, source)
        
        old_info = self.MODES[old_mode]
        new_info = self.MODES[mode]
        
        return {
            "success": True,
            "old_mode": old_mode,
            "new_mode": mode,
            "old_name": f"{old_info['icon']} {old_info['name']}",
            "new_name": f"{new_info['icon']} {new_info['name']}",
            "reason": reason,
            "source": source,
        }
    
    def override(self, mode: str, duration_minutes: int = 60, source: str = "user"):
        """
        手動オーバーライド（カレンダー自動切替を一時停止）
        
        Args:
            mode: 強制切替先
            duration_minutes: オーバーライド時間（分）
            source: 発生元
        """
        from datetime import timedelta
        self.override_active = True
        self.override_until = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
        result = self.switch(mode, f"手動オーバーライド（{duration_minutes}分間）", source)
        self._save_state()
        return result
    
    def get_config(self) -> Dict[str, Any]:
        """現在モードの振る舞い設定を取得"""
        return self.MODES.get(self.current_mode, self.MODES[self.DEFAULT_MODE])
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        config = self.get_config()
        return {
            "mode": self.current_mode,
            "name": config["name"],
            "icon": config["icon"],
            "desc": config["desc"],
            "since": self.mode_since,
            "override": self.override_active,
            "override_until": self.override_until,
        }
    
    def _record_history(self, old_mode: str, new_mode: str, reason: str, source: str):
        """モード切替履歴を記録"""
        try:
            with open(self.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "from": old_mode,
                    "to": new_mode,
                    "reason": reason,
                    "source": source,
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
