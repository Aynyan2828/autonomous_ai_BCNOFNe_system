#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI状態出力モジュール
AIエージェントの現在の状態をファイルに出力し、OLEDディスプレイで表示できるようにする
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional


class AIStateWriter:
    """AI状態出力クラス"""
    
    # 状態ファイルパス
    STATE_FILE = "/var/run/ai_state.json"
    
    # 状態の種類
    STATE_IDLE = "Idle"
    STATE_PLANNING = "Planning"
    STATE_ACTING = "Acting"
    STATE_MOVING_FILES = "Moving Files"
    STATE_ERROR = "Error"
    STATE_WAITING_APPROVAL = "Wait Approval"
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.current_state = self.STATE_IDLE
        self.current_task = ""
        
        # 状態ファイルのディレクトリを作成
        os.makedirs(os.path.dirname(self.STATE_FILE), exist_ok=True)
        
        # 初期状態を書き込み
        self.update_state(self.STATE_IDLE, "")
    
    def update_state(self, state: str, task: str = ""):
        """
        状態を更新
        
        Args:
            state: 状態（Idle, Planning, Acting, Moving Files, Error, Wait Approval）
            task: 現在のタスク説明
        """
        self.current_state = state
        self.current_task = task
        
        try:
            state_data = {
                "state": state,
                "task": task,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 一時ファイルに書き込んでから移動（アトミック操作）
            temp_file = self.STATE_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            os.replace(temp_file, self.STATE_FILE)
            
            # パーミッション設定（全ユーザーが読めるように）
            os.chmod(self.STATE_FILE, 0o666)
            
        except Exception as e:
            self.logger.error(f"AI状態ファイル書き込みエラー: {e}")
    
    def set_idle(self):
        """アイドル状態に設定"""
        self.update_state(self.STATE_IDLE, "")
    
    def set_planning(self, task: str = ""):
        """計画中状態に設定"""
        self.update_state(self.STATE_PLANNING, task or "タスク計画中")
    
    def set_acting(self, task: str = ""):
        """実行中状態に設定"""
        self.update_state(self.STATE_ACTING, task or "コマンド実行中")
    
    def set_moving_files(self, task: str = ""):
        """ファイル移動中状態に設定"""
        self.update_state(self.STATE_MOVING_FILES, task or "ファイル移動中")
    
    def set_error(self, error_message: str = ""):
        """エラー状態に設定"""
        self.update_state(self.STATE_ERROR, error_message or "エラー発生")
    
    def set_waiting_approval(self, task: str = ""):
        """承認待ち状態に設定"""
        self.update_state(self.STATE_WAITING_APPROVAL, task or "課金承認待ち")
    
    def get_current_state(self) -> dict:
        """
        現在の状態を取得
        
        Returns:
            状態辞書
        """
        return {
            "state": self.current_state,
            "task": self.current_task
        }


# グローバルインスタンス（シングルトン）
_state_writer = None


def get_state_writer() -> AIStateWriter:
    """
    AIStateWriterのグローバルインスタンスを取得
    
    Returns:
        AIStateWriterインスタンス
    """
    global _state_writer
    if _state_writer is None:
        _state_writer = AIStateWriter()
    return _state_writer
