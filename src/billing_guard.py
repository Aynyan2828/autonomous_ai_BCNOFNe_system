#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課金安全制御モジュール
API課金の監視と自動停止
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple


class BillingGuard:
    """課金安全制御クラス"""
    
    # 通常日の閾値
    NORMAL_DAY_THRESHOLDS = {
        "warning": 200,   # 注意通知
        "stop": 300       # 自動停止
    }
    
    # 特別日の閾値（0, 6, 12, 18, 24, 30日目）
    SPECIAL_DAY_THRESHOLDS = {
        "warning": 500,   # 注意通知
        "alert": 900,     # 警告通知
        "stop": 1000      # 自動停止
    }
    
    # 特別日の周期
    SPECIAL_DAY_CYCLE = 6
    
    # GPTモデルの料金（1000トークンあたりの円）
    MODEL_PRICING = {
        "gpt-4.1-mini": {
            "input": 0.015,   # $0.15/1M tokens = 0.015円/1K tokens (1ドル=100円換算)
            "output": 0.060   # $0.60/1M tokens = 0.060円/1K tokens
        },
        "gpt-4": {
            "input": 3.0,
            "output": 6.0
        }
    }
    
    def __init__(
        self,
        data_dir: str = "/home/pi/autonomous_ai/billing",
        start_date: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            data_dir: データ保存ディレクトリ
            start_date: 開始日（YYYY-MM-DD形式、指定しない場合は今日）
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.usage_file = self.data_dir / "usage.json"
        self.confirmations_dir = self.data_dir / "confirmations"
        self.confirmations_dir.mkdir(exist_ok=True)
        
        # 使用量データの読み込み
        self.usage_data = self._load_usage()
        
        # 開始日の設定
        if start_date:
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            self.start_date = self.usage_data.get("start_date")
            if self.start_date:
                self.start_date = datetime.fromisoformat(self.start_date)
            else:
                self.start_date = datetime.now()
                self.usage_data["start_date"] = self.start_date.isoformat()
                self._save_usage()
    
    def _load_usage(self) -> Dict:
        """使用量データを読み込み"""
        if self.usage_file.exists():
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 初期データ
        return {
            "start_date": None,
            "daily_usage": {},
            "total_cost": 0.0,
            "total_requests": 0
        }
    
    def _save_usage(self):
        """使用量データを保存"""
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(self.usage_data, f, ensure_ascii=False, indent=2)
    
    def get_days_since_start(self) -> int:
        """
        開始日からの経過日数を取得
        
        Returns:
            経過日数
        """
        delta = datetime.now() - self.start_date
        return delta.days
    
    def is_special_day(self, days: Optional[int] = None) -> bool:
        """
        特別日かどうかを判定
        
        Args:
            days: 判定する日数（指定しない場合は今日）
            
        Returns:
            特別日ならTrue
        """
        if days is None:
            days = self.get_days_since_start()
        
        # 0日目（初回起動日）は特別日
        if days == 0:
            return True
        
        # 6日周期で特別日（6, 12, 18, 24, 30...）
        return days % self.SPECIAL_DAY_CYCLE == 0
    
    def get_thresholds(self) -> Dict:
        """
        現在の閾値を取得
        
        Returns:
            閾値の辞書
        """
        if self.is_special_day():
            return self.SPECIAL_DAY_THRESHOLDS.copy()
        else:
            return self.NORMAL_DAY_THRESHOLDS.copy()
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        コストを計算
        
        Args:
            model: モデル名
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            
        Returns:
            コスト（円）
        """
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["gpt-4.1-mini"])
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: Optional[float] = None
    ) -> Dict:
        """
        使用量を記録
        
        Args:
            model: モデル名
            input_tokens: 入力トークン数
            output_tokens: 出力トークン数
            cost: コスト（指定しない場合は自動計算）
            
        Returns:
            更新後の使用量情報
        """
        if cost is None:
            cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        # 今日の日付
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 日次使用量を更新
        if today not in self.usage_data["daily_usage"]:
            self.usage_data["daily_usage"][today] = {
                "cost": 0.0,
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0
            }
        
        daily = self.usage_data["daily_usage"][today]
        daily["cost"] += cost
        daily["requests"] += 1
        daily["input_tokens"] += input_tokens
        daily["output_tokens"] += output_tokens
        
        # 累計を更新
        self.usage_data["total_cost"] += cost
        self.usage_data["total_requests"] += 1
        
        # 保存
        self._save_usage()
        
        return {
            "today_cost": daily["cost"],
            "today_requests": daily["requests"],
            "total_cost": self.usage_data["total_cost"],
            "total_requests": self.usage_data["total_requests"]
        }
    
    def get_today_cost(self) -> float:
        """
        今日のコストを取得
        
        Returns:
            今日のコスト（円）
        """
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self.usage_data["daily_usage"].get(today, {})
        return daily.get("cost", 0.0)
    
    def check_threshold(self) -> Optional[Dict]:
        """
        閾値チェック
        
        Returns:
            警告情報（問題なければNone）
        """
        today_cost = self.get_today_cost()
        thresholds = self.get_thresholds()
        is_special = self.is_special_day()
        
        # 停止閾値チェック
        if today_cost >= thresholds["stop"]:
            return {
                "level": "stop",
                "message": "自動停止",
                "today_cost": today_cost,
                "threshold": thresholds["stop"],
                "is_special_day": is_special,
                "action": "システムを停止します"
            }
        
        # 特別日の警告閾値チェック
        if is_special and "alert" in thresholds and today_cost >= thresholds["alert"]:
            return {
                "level": "alert",
                "message": "警告通知",
                "today_cost": today_cost,
                "threshold": thresholds["alert"],
                "is_special_day": is_special,
                "action": "コストが警告レベルに達しました"
            }
        
        # 注意閾値チェック
        if today_cost >= thresholds["warning"]:
            return {
                "level": "warning",
                "message": "注意通知",
                "today_cost": today_cost,
                "threshold": thresholds["warning"],
                "is_special_day": is_special,
                "action": "コストが注意レベルに達しました"
            }
        
        return None
    
    def request_confirmation(
        self,
        action_description: str,
        estimated_cost: float,
        timeout_seconds: int = 600
    ) -> Tuple[bool, str]:
        """
        LINE経由で確認をリクエスト
        
        Args:
            action_description: アクションの説明
            estimated_cost: 見積もりコスト（円）
            timeout_seconds: タイムアウト（秒）、デフォルト10分
            
        Returns:
            (許可されたか, メッセージ)
        """
        import uuid
        
        # 確認IDを生成
        confirmation_id = str(uuid.uuid4())
        
        # LINE通知を送信（別モジュールから呼び出す想定）
        # ここでは確認ファイルを作成するのみ
        confirmation_file = self.confirmations_dir / f"{confirmation_id}.json"
        
        confirmation_data = {
            "confirmation_id": confirmation_id,
            "action": action_description,
            "estimated_cost": estimated_cost,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        with open(confirmation_file, 'w', encoding='utf-8') as f:
            json.dump(confirmation_data, f, ensure_ascii=False, indent=2)
        
        print(f"確認リクエスト送信: {action_description} (¥{estimated_cost:.2f})")
        print(f"確認ID: {confirmation_id}")
        
        # タイムアウトまで待機
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # 確認結果をチェック
            if confirmation_file.exists():
                with open(confirmation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get("response"):
                    response = data["response"]
                    
                    if response == "許可":
                        return True, "ユーザーが許可しました"
                    elif response == "拒否":
                        return False, "ユーザーが拒否しました"
            
            # 1秒待機
            time.sleep(1)
        
        # タイムアウト
        return False, f"{timeout_seconds}秒以内に応答がなかったため自動キャンセルしました"
    
    def estimate_cost(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> float:
        """
        コストを見積もり
        
        Args:
            model: モデル名
            estimated_input_tokens: 推定入力トークン数
            estimated_output_tokens: 推定出力トークン数
            
        Returns:
            見積もりコスト（円）
        """
        return self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)
    
    def get_summary(self) -> str:
        """
        使用量サマリーを取得
        
        Returns:
            サマリー文字列
        """
        today_cost = self.get_today_cost()
        thresholds = self.get_thresholds()
        is_special = self.is_special_day()
        days_since_start = self.get_days_since_start()
        
        summary = "# 課金サマリー\n\n"
        summary += f"## 基本情報\n"
        summary += f"- 開始日: {self.start_date.strftime('%Y年%m月%d日')}\n"
        summary += f"- 経過日数: {days_since_start}日目\n"
        summary += f"- 特別日: {'はい' if is_special else 'いいえ'}\n\n"
        
        summary += f"## 今日のコスト\n"
        summary += f"- 使用額: ¥{today_cost:.2f}\n"
        summary += f"- 注意閾値: ¥{thresholds['warning']}\n"
        if "alert" in thresholds:
            summary += f"- 警告閾値: ¥{thresholds['alert']}\n"
        summary += f"- 停止閾値: ¥{thresholds['stop']}\n\n"
        
        summary += f"## 累計\n"
        summary += f"- 総コスト: ¥{self.usage_data['total_cost']:.2f}\n"
        summary += f"- 総リクエスト数: {self.usage_data['total_requests']}回\n"
        
        # 警告チェック
        alert = self.check_threshold()
        if alert:
            summary += f"\n⚠️ **{alert['message']}**: {alert['action']}\n"
        
        return summary
    
    def reset_daily_usage(self):
        """日次使用量をリセット（テスト用）"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today in self.usage_data["daily_usage"]:
            del self.usage_data["daily_usage"][today]
        self._save_usage()


# テスト用
if __name__ == "__main__":
    guard = BillingGuard(data_dir="/tmp/test_billing")
    
    print("=== 課金サマリー ===")
    print(guard.get_summary())
    
    print("\n=== 使用量記録テスト ===")
    result = guard.record_usage(
        model="gpt-4.1-mini",
        input_tokens=1000,
        output_tokens=500
    )
    print(f"今日のコスト: ¥{result['today_cost']:.2f}")
    
    print("\n=== 閾値チェック ===")
    alert = guard.check_threshold()
    if alert:
        print(f"警告: {alert['message']}")
    else:
        print("問題なし")
    
    print("\n=== 特別日判定 ===")
    for day in [0, 1, 6, 12, 18, 24, 30]:
        is_special = guard.is_special_day(day)
        print(f"{day}日目: {'特別日' if is_special else '通常日'}")
