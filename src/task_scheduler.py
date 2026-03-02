#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タスクスケジューラ
カレンダー連動モード切替 + 定期タスク管理
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List, Any


class PeriodicTask:
    """定期タスク"""
    def __init__(self, name: str, func: Callable, interval_sec: int,
                 condition: Optional[Callable] = None, run_in_modes: Optional[List[str]] = None):
        self.name = name
        self.func = func
        self.interval_sec = interval_sec
        self.condition = condition
        self.run_in_modes = run_in_modes  # None=全モード
        self.last_run: float = 0
        self.run_count: int = 0
        self.last_result: Any = None
    
    def is_due(self) -> bool:
        return (time.time() - self.last_run) >= self.interval_sec
    
    def should_run(self, current_mode: str) -> bool:
        if not self.is_due():
            return False
        if self.run_in_modes and current_mode not in self.run_in_modes:
            return False
        if self.condition and not self.condition():
            return False
        return True


class TaskScheduler:
    """タスクスケジューラ"""
    
    def __init__(self, calendar=None, mode_manager=None):
        """
        Args:
            calendar: CalendarSync インスタンス
            mode_manager: ShipMode インスタンス
        """
        self.calendar = calendar
        self.mode_manager = mode_manager
        self.tasks: List[PeriodicTask] = []
        self._last_calendar_check: float = 0
        self._calendar_check_interval: int = 300  # 5分
    
    def register(self, name: str, func: Callable, interval_sec: int,
                 condition: Optional[Callable] = None,
                 run_in_modes: Optional[List[str]] = None):
        """定期タスクを登録"""
        task = PeriodicTask(name, func, interval_sec, condition, run_in_modes)
        self.tasks.append(task)
        print(f"[Scheduler] タスク登録: {name} (間隔: {interval_sec}秒)")
    
    def check_calendar_mode(self) -> Optional[Dict[str, Any]]:
        """カレンダーに基づくモード自動切替"""
        if not self.calendar or not self.mode_manager:
            return None
        
        if (time.time() - self._last_calendar_check) < self._calendar_check_interval:
            return None
        
        self._last_calendar_check = time.time()
        
        try:
            is_work = self.calendar.is_work_time()
            current = self.mode_manager.current_mode
            
            if is_work and current != "autonomous":
                return self.mode_manager.switch(
                    "autonomous",
                    reason="勤務時間検出（カレンダー連動）",
                    source="calendar"
                )
            elif not is_work and current == "autonomous":
                return self.mode_manager.switch(
                    "user_first",
                    reason="勤務終了（カレンダー連動）",
                    source="calendar"
                )
        except Exception as e:
            print(f"[Scheduler] カレンダーチェックエラー: {e}")
        
        return None
    
    def run_due_tasks(self, current_mode: str) -> List[Dict[str, Any]]:
        """期限タスクを実行"""
        results = []
        
        for task in self.tasks:
            if task.should_run(current_mode):
                try:
                    result = task.func()
                    task.last_run = time.time()
                    task.run_count += 1
                    task.last_result = result
                    results.append({
                        "name": task.name,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    task.last_run = time.time()
                    results.append({
                        "name": task.name,
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def get_status(self) -> List[Dict[str, Any]]:
        """全タスクの状態を取得"""
        return [{
            "name": t.name,
            "interval": t.interval_sec,
            "last_run": datetime.fromtimestamp(t.last_run).isoformat() if t.last_run else "未実行",
            "run_count": t.run_count,
            "modes": t.run_in_modes or ["全モード"],
        } for t in self.tasks]
