#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS ナレーター（演出）
航海用語でシステムイベントを表現する
"""

from datetime import datetime
from typing import Optional, Dict, List


class ShipNarrator:
    """航海用語変換・演出テキスト生成"""
    
    # イベント別テンプレート
    TEMPLATES = {
        # 起動/停止
        "startup": "🚢 全機関始動。出港準備完了。\nshipOS BCNOFNe、航海を開始します。",
        "shutdown": "⚓ 投錨。全機関停止。\nお疲れ様でした、船長。航海記録を保存しました。",
        
        # モード切替
        "mode_autonomous": "⛵ 自律航海モードへ移行。\n大海原へ出航！自律思考で航路を切り開きます。",
        "mode_user_first": "🏠 入港待機モードへ。\n船長の指示をお待ちしています。何でもどうぞ。",
        "mode_maintenance": "🔧 ドック入り。定期整備を開始します。\n機関と船体の点検中...",
        "mode_power_save": "🌙 停泊モードへ。静かな夜の航海です。\n最小機関で待機中。",
        "mode_safe": "🆘 救難信号！セーフモードへ移行。\n全航行を一時停止、最小機能で待機。",
        
        # 目標
        "goal_set": "📋 新たな航路を設定しました。\n🧭 目的地: {goal}",
        "goal_complete": "✅ 航路完了！\n📝 報告: {result}",
        "goal_replaced": "🔄 航路変更。旧航路を航海日誌に記録しました。\n🧭 新航路: {goal}",
        
        # ヘルス
        "health_ok": "🟢 全機関正常。航行に支障なし。",
        "health_warn": "⚠️ 機関注意: {item} — {detail}",
        "health_critical": "🔴 機関異常！ {item} — {detail}\n直ちに対応が必要です。",
        
        # メンテナンス
        "maintenance_start": "🔧 定期整備を開始します。",
        "maintenance_done": "✅ 整備完了。全機関を正常状態に復帰。",
        "archive_done": "📦 船倉整理完了。{count}件のファイルをアーカイブ庫へ移動。",
        
        # 自己修復
        "recovery_start": "🛠️ 機関異常を検知。自動修復を開始...",
        "recovery_done": "✅ 修復完了。航行を再開します。",
        "recovery_fail": "❌ 修復失敗。船長の介入が必要です。",
        
        # カレンダー
        "work_start": "⛵ 船長が勤務開始。自律航海モードに切り替えます。\nAIは自由に航海します。",
        "work_end": "🏠 船長が帰港しました。入港待機モードへ。\nお帰りなさい！何かお手伝いしましょうか？",
        
        # 質問応答
        "query_received": "🔍 質問を受信。回答を準備中...",
        "query_answered": "💬 回答: {answer}",
        
        # 航海日誌
        "daily_report": "📔 本日の航海日誌\n{summary}",
        "weekly_report": "📊 週間航海報告\n{summary}",
    }
    
    # OLED用の省略表記
    OLED_STATE_MAP = {
        "autonomous": "SAIL",    # 航海中
        "user_first": "PORT",    # 入港
        "maintenance": "DOCK",   # ドック
        "power_save": "ANCHOR",  # 停泊
        "safe": "SOS",           # 救難
    }
    
    OLED_TASK_MAP = {
        "thinking": "HELM",     # 操舵中
        "executing": "ENGINE",  # 機関稼働
        "idle": "WATCH",        # 見張り
        "error": "ALARM",       # 警報
        "query": "RADIO",       # 通信中
        "maintenance": "REPAIR",# 修繕中
    }
    
    @classmethod
    def narrate(cls, event: str, **kwargs) -> str:
        """
        イベントに応じた演出テキストを生成
        
        Args:
            event: イベント名
            **kwargs: テンプレート変数
            
        Returns:
            演出テキスト
        """
        template = cls.TEMPLATES.get(event, f"[{event}]")
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    
    @classmethod
    def oled_lines(cls, mode: str, goal: str, task: str, ip: str) -> List[str]:
        """
        OLED 5行表示を航海用語で生成
        
        Args:
            mode: 現在モード名
            goal: 現在の目標
            task: 現在タスク
            ip: IPアドレス
            
        Returns:
            5行のリスト
        """
        mode_disp = cls.OLED_STATE_MAP.get(mode, mode[:6].upper())
        goal_short = goal[:14] if goal else "---"
        task_short = task[:14] if task else "WATCH"
        
        return [
            f"shipOS: {mode_disp}",
            f"DEST:{goal_short}",
            f"HELM:{mode_disp}",
            f"TASK:{task_short}",
            f"IP:{ip}",
        ]
    
    @classmethod
    def mode_switch_message(cls, old_mode: str, new_mode: str, reason: str = "") -> str:
        """モード切替の演出メッセージ"""
        template_key = f"mode_{new_mode}"
        msg = cls.TEMPLATES.get(template_key, f"モード切替: {new_mode}")
        if reason:
            msg += f"\n理由: {reason}"
        return msg
    
    @classmethod
    def startup_message(cls) -> str:
        """起動演出メッセージ"""
        now = datetime.now()
        greeting = "おはようございます" if now.hour < 12 else "こんにちは" if now.hour < 18 else "こんばんは"
        return (
            f"{cls.TEMPLATES['startup']}\n"
            f"\n{greeting}、船長。\n"
            f"現在時刻: {now.strftime('%H:%M')}\n"
            f"航海日誌を開始します。"
        )
    
    @classmethod
    def shutdown_message(cls) -> str:
        """停止演出メッセージ"""
        return cls.TEMPLATES["shutdown"]
