#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
起動通知の重複を防ぐためのフラグ管理
"""

import os
from datetime import datetime, timedelta


class StartupFlag:
    """起動フラグ管理クラス"""
    
    def __init__(self, flag_file: str = "/home/pi/autonomous_ai/.startup_flag"):
        """
        初期化
        
        Args:
            flag_file: フラグファイルのパス
        """
        self.flag_file = flag_file
    
    def should_send_startup_notification(self, cooldown_minutes: int = 5) -> bool:
        """
        起動通知を送信すべきかチェック
        
        Args:
            cooldown_minutes: クールダウン時間（分）
            
        Returns:
            送信すべきならTrue
        """
        # フラグファイルが存在しない場合は送信
        if not os.path.exists(self.flag_file):
            self._create_flag()
            return True
        
        # フラグファイルの最終更新時刻を確認
        try:
            with open(self.flag_file, 'r') as f:
                timestamp_str = f.read().strip()
            
            last_startup = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            
            # クールダウン時間が経過していれば送信
            if now - last_startup > timedelta(minutes=cooldown_minutes):
                self._create_flag()
                return True
            else:
                return False
        
        except Exception:
            # エラーが発生した場合は送信
            self._create_flag()
            return True
    
    def _create_flag(self):
        """フラグファイルを作成"""
        os.makedirs(os.path.dirname(self.flag_file), exist_ok=True)
        
        with open(self.flag_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def clear_flag(self):
        """フラグファイルを削除"""
        if os.path.exists(self.flag_file):
            os.remove(self.flag_file)


# テスト用
if __name__ == "__main__":
    flag = StartupFlag("/tmp/test_startup_flag")
    
    print("1回目:", flag.should_send_startup_notification())  # True
    print("2回目:", flag.should_send_startup_notification())  # False
    
    flag.clear_flag()
