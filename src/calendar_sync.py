<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iCloudカレンダー同期モジュール
ICS公開URLからカレンダーを同期し、勤務判定を行う
"""

import os
import time
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    import requests
    from icalendar import Calendar as iCalendar
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False


class CalendarEvent:
    """カレンダーイベント"""
    def __init__(self, summary: str, start: datetime, end: datetime, location: str = ""):
        self.summary = summary
        self.start = start
        self.end = end
        self.location = location
    
    def is_active(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now()
        return self.start <= dt <= self.end
    
    def __repr__(self):
        return f"<Event '{self.summary}' {self.start}~{self.end}>"


class CalendarSync:
    """iCloudカレンダー同期"""
    
    WORK_KEYWORDS = ["仕事", "勤務", "work", "出勤", "シフト", "shift", "業務", "会議"]
    CACHE_FILE = "/home/pi/autonomous_ai/state/calendar_cache.json"
    SYNC_INTERVAL = 900  # 15分
    
    def __init__(
        self,
        ics_url: Optional[str] = None,
    ):
        self.ics_url = ics_url or os.getenv("CALENDAR_ICS_URL", "")
        self._events_cache: List[CalendarEvent] = []
        self._last_sync: float = 0
        
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        self._load_cache()
    
    def _load_cache(self):
        """キャッシュから復元"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._events_cache = [
                    CalendarEvent(
                        e["summary"],
                        datetime.fromisoformat(e["start"]),
                        datetime.fromisoformat(e["end"]),
                        e.get("location", "")
                    ) for e in data.get("events", [])
                ]
                self._last_sync = data.get("last_sync", 0)
        except Exception:
            pass
    
    def _save_cache(self):
        """キャッシュ保存"""
        try:
            data = {
                "events": [
                    {
                        "summary": e.summary,
                        "start": e.start.isoformat(),
                        "end": e.end.isoformat(),
                        "location": e.location
                    } for e in self._events_cache
                ],
                "last_sync": self._last_sync
            }
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def sync(self, force: bool = False) -> bool:
        """
        カレンダーを同期
        
        Returns:
            成功したらTrue
        """
        if not force and (time.time() - self._last_sync) < self.SYNC_INTERVAL:
            return True  # キャッシュ有効
        
        if not self.ics_url:
            return False
        
        if not ICAL_AVAILABLE:
            print("[CalendarSync] icalendarが未インストール")
            return False
        
        try:
            resp = requests.get(self.ics_url, timeout=15)
            resp.raise_for_status()
            
            cal = iCalendar.from_ical(resp.text)
            events = []
            now = datetime.now()
            window_start = now - timedelta(days=1)
            window_end = now + timedelta(days=7)
            
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue
                
                summary = str(component.get("summary", ""))
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")
                location = str(component.get("location", ""))
                
                if not dtstart or not dtend:
                    continue
                
                start = dtstart.dt
                end = dtend.dt
                
                # date -> datetime変換
                if not isinstance(start, datetime):
                    start = datetime.combine(start, datetime.min.time())
                if not isinstance(end, datetime):
                    end = datetime.combine(end, datetime.max.time().replace(microsecond=0))
                
                # タイムゾーン除去（ローカル比較用）
                if hasattr(start, 'tzinfo') and start.tzinfo:
                    start = start.replace(tzinfo=None)
                if hasattr(end, 'tzinfo') and end.tzinfo:
                    end = end.replace(tzinfo=None)
                
                if end >= window_start and start <= window_end:
                    events.append(CalendarEvent(summary, start, end, location))
            
            self._events_cache = sorted(events, key=lambda e: e.start)
            self._last_sync = time.time()
            self._save_cache()
            print(f"[CalendarSync] 同期完了: {len(events)}件のイベント")
            return True
            
        except Exception as e:
            print(f"[CalendarSync] 同期エラー: {e}")
            return False
    
    def fetch_events(self, date: Optional[datetime] = None) -> List[CalendarEvent]:
        """指定日のイベントを取得"""
        self.sync()
        target = date or datetime.now()
        return [e for e in self._events_cache
                if e.start.date() <= target.date() <= e.end.date()]
    
    def is_work_time(self, dt: Optional[datetime] = None) -> bool:
        """勤務時間かどうか判定"""
        self.sync()
        dt = dt or datetime.now()
        
        for event in self._events_cache:
            if event.is_active(dt):
                summary_lower = event.summary.lower()
                if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                    return True
        return False
    
    def get_next_transition(self) -> Optional[Dict[str, Any]]:
        """次のモード切替時刻を取得"""
        self.sync()
        now = datetime.now()
        
        if self.is_work_time(now):
            # 勤務中 → 終了時刻を探す
            for event in self._events_cache:
                if event.is_active(now):
                    summary_lower = event.summary.lower()
                    if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                        return {
                            "time": event.end,
                            "from_mode": "autonomous",
                            "to_mode": "user_first",
                            "event": event.summary
                        }
        else:
            # 非勤務 → 次の勤務開始を探す
            for event in self._events_cache:
                if event.start > now:
                    summary_lower = event.summary.lower()
                    if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                        return {
                            "time": event.start,
                            "from_mode": "user_first",
                            "to_mode": "autonomous",
                            "event": event.summary
                        }
        return None
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iCloudカレンダー同期モジュール
ICS公開URLからカレンダーを同期し、勤務判定を行う
"""

import os
import time
import json
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    import requests
    from icalendar import Calendar as iCalendar
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False


class CalendarEvent:
    """カレンダーイベント"""
    def __init__(self, summary: str, start: datetime, end: datetime, location: str = ""):
        self.summary = summary
        self.start = start
        self.end = end
        self.location = location
    
    def is_active(self, dt: Optional[datetime] = None) -> bool:
        dt = dt or datetime.now()
        return self.start <= dt <= self.end
    
    def __repr__(self):
        return f"<Event '{self.summary}' {self.start}~{self.end}>"


class CalendarSync:
    """iCloudカレンダー同期"""
    
    WORK_KEYWORDS = ["仕事", "勤務", "work", "出勤", "シフト", "shift", "業務", "会議"]
    CACHE_FILE = "/home/pi/autonomous_ai/state/calendar_cache.json"
    SYNC_INTERVAL = 900  # 15分
    
    def __init__(
        self,
        ics_url: Optional[str] = None,
    ):
        self.ics_url = ics_url or os.getenv("CALENDAR_ICS_URL", "")
        self._events_cache: List[CalendarEvent] = []
        self._last_sync: float = 0
        
        os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
        self._load_cache()
    
    def _load_cache(self):
        """キャッシュから復元"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._events_cache = [
                    CalendarEvent(
                        e["summary"],
                        datetime.fromisoformat(e["start"]),
                        datetime.fromisoformat(e["end"]),
                        e.get("location", "")
                    ) for e in data.get("events", [])
                ]
                self._last_sync = data.get("last_sync", 0)
        except Exception:
            pass
    
    def _save_cache(self):
        """キャッシュ保存"""
        try:
            data = {
                "events": [
                    {
                        "summary": e.summary,
                        "start": e.start.isoformat(),
                        "end": e.end.isoformat(),
                        "location": e.location
                    } for e in self._events_cache
                ],
                "last_sync": self._last_sync
            }
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def sync(self, force: bool = False) -> bool:
        """
        カレンダーを同期
        
        Returns:
            成功したらTrue
        """
        if not force and (time.time() - self._last_sync) < self.SYNC_INTERVAL:
            return True  # キャッシュ有効
        
        if not self.ics_url:
            return False
        
        if not ICAL_AVAILABLE:
            print("[CalendarSync] icalendarが未インストール")
            return False
        
        try:
            resp = requests.get(self.ics_url, timeout=15)
            resp.raise_for_status()
            
            cal = iCalendar.from_ical(resp.text)
            events = []
            now = datetime.now()
            window_start = now - timedelta(days=1)
            window_end = now + timedelta(days=7)
            
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue
                
                summary = str(component.get("summary", ""))
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")
                location = str(component.get("location", ""))
                
                if not dtstart or not dtend:
                    continue
                
                start = dtstart.dt
                end = dtend.dt
                
                # date -> datetime変換
                if not isinstance(start, datetime):
                    start = datetime.combine(start, datetime.min.time())
                if not isinstance(end, datetime):
                    end = datetime.combine(end, datetime.max.time().replace(microsecond=0))
                
                # タイムゾーン除去（ローカル比較用）
                if hasattr(start, 'tzinfo') and start.tzinfo:
                    start = start.replace(tzinfo=None)
                if hasattr(end, 'tzinfo') and end.tzinfo:
                    end = end.replace(tzinfo=None)
                
                if end >= window_start and start <= window_end:
                    events.append(CalendarEvent(summary, start, end, location))
            
            self._events_cache = sorted(events, key=lambda e: e.start)
            self._last_sync = time.time()
            self._save_cache()
            print(f"[CalendarSync] 同期完了: {len(events)}件のイベント")
            return True
            
        except Exception as e:
            print(f"[CalendarSync] 同期エラー: {e}")
            return False
    
    def fetch_events(self, date: Optional[datetime] = None) -> List[CalendarEvent]:
        """指定日のイベントを取得"""
        self.sync()
        target = date or datetime.now()
        return [e for e in self._events_cache
                if e.start.date() <= target.date() <= e.end.date()]
    
    def is_work_time(self, dt: Optional[datetime] = None) -> bool:
        """勤務時間かどうか判定"""
        self.sync()
        dt = dt or datetime.now()
        
        for event in self._events_cache:
            if event.is_active(dt):
                summary_lower = event.summary.lower()
                if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                    return True
        return False
    
    def get_next_transition(self) -> Optional[Dict[str, Any]]:
        """次のモード切替時刻を取得"""
        self.sync()
        now = datetime.now()
        
        if self.is_work_time(now):
            # 勤務中 → 終了時刻を探す
            for event in self._events_cache:
                if event.is_active(now):
                    summary_lower = event.summary.lower()
                    if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                        return {
                            "time": event.end,
                            "from_mode": "autonomous",
                            "to_mode": "user_first",
                            "event": event.summary
                        }
        else:
            # 非勤務 → 次の勤務開始を探す
            for event in self._events_cache:
                if event.start > now:
                    summary_lower = event.summary.lower()
                    if any(kw in summary_lower for kw in self.WORK_KEYWORDS):
                        return {
                            "time": event.start,
                            "from_mode": "user_first",
                            "to_mode": "autonomous",
                            "event": event.summary
                        }
        return None
>>>>>>> Stashed changes
