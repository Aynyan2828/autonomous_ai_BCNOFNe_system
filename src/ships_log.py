<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
航海日誌（Ship's Log）
日次行動要約・統計・週次レポート・自己理解
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import Counter


class ShipsLog:
    """航海日誌"""
    
    LOG_DIR = "/home/pi/autonomous_ai/state/ships_log"
    
    def __init__(self):
        os.makedirs(self.LOG_DIR, exist_ok=True)
    
    def _today_file(self, date: Optional[datetime] = None) -> str:
        d = date or datetime.now()
        return os.path.join(self.LOG_DIR, f"{d.strftime('%Y%m%d')}.jsonl")
    
    # ===== 記録 =====
    
    def record_action(self, action_type: str, detail: str, success: bool = True,
                      duration: float = 0, metadata: Optional[Dict] = None):
        """
        アクションを記録
        
        Args:
            action_type: "command", "query", "goal", "maintenance", "error", "mode_switch"
            detail: 内容
            success: 成功/失敗
            duration: 所要時間(秒)
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": action_type,
            "detail": detail,
            "success": success,
            "duration": round(duration, 2),
        }
        if metadata:
            entry["meta"] = metadata
        
        try:
            with open(self._today_file(), 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ShipsLog] 記録エラー: {e}")
    
    # ===== 読み取り =====
    
    def get_today_entries(self) -> List[Dict]:
        """今日のエントリを全取得"""
        return self._read_entries(self._today_file())
    
    def _read_entries(self, path: str) -> List[Dict]:
        entries = []
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entries.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass
        return entries
    
    # ===== 統計 =====
    
    def get_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """日次統計"""
        entries = self._read_entries(self._today_file(date))
        
        if not entries:
            return {"total": 0, "success_rate": 0, "types": {}, "commands_top5": []}
        
        total = len(entries)
        success = sum(1 for e in entries if e.get("success", True))
        types = Counter(e.get("type", "unknown") for e in entries)
        
        # コマンド分析
        commands = [e["detail"] for e in entries if e.get("type") == "command"]
        cmd_counter = Counter(commands)
        top5 = cmd_counter.most_common(5)
        
        # 長時間タスク
        long_tasks = [e for e in entries if e.get("duration", 0) > 30]
        
        return {
            "total": total,
            "success": success,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "types": dict(types),
            "commands_top5": top5,
            "long_tasks": len(long_tasks),
            "total_duration": round(sum(e.get("duration", 0) for e in entries), 1),
        }
    
    # ===== 要約 =====
    
    def generate_daily_summary(self, date: Optional[datetime] = None) -> str:
        """日次航海日誌サマリー（航海用語）"""
        stats = self.get_stats(date)
        d = date or datetime.now()
        
        if stats["total"] == 0:
            return f"📔 航海日誌 {d.strftime('%Y/%m/%d')}\n本日は静かな航海でした。目立った出来事なし。"
        
        lines = [
            f"📔 航海日誌 {d.strftime('%Y/%m/%d')}",
            f"",
            f"⚓ 行動回数: {stats['total']}回",
            f"✅ 成功率: {stats['success_rate']}%",
            f"⏱️ 総稼働時間: {stats['total_duration']:.0f}秒",
        ]
        
        if stats["types"]:
            type_str = ", ".join(f"{k}:{v}回" for k, v in stats["types"].items())
            lines.append(f"📊 内訳: {type_str}")
        
        if stats["commands_top5"]:
            top_cmds = ", ".join(f"{cmd[0]}({cmd[1]}回)" for cmd in stats["commands_top5"][:3])
            lines.append(f"🔧 よく使った操舵: {top_cmds}")
        
        if stats["long_tasks"] > 0:
            lines.append(f"🐌 長時間タスク: {stats['long_tasks']}件")
        
        return "\n".join(lines)
    
    def generate_weekly_summary(self) -> str:
        """週次航海報告"""
        lines = ["📊 週間航海報告", ""]
        week_total = 0
        week_success = 0
        
        for i in range(7):
            d = datetime.now() - timedelta(days=i)
            stats = self.get_stats(d)
            week_total += stats["total"]
            week_success += stats["success"]
            
            if stats["total"] > 0:
                lines.append(
                    f"  {d.strftime('%m/%d(%a)')}: {stats['total']}回 "
                    f"(成功率{stats['success_rate']}%)"
                )
        
        if week_total > 0:
            rate = round(week_success / week_total * 100, 1)
            lines.insert(2, f"⚓ 週間合計: {week_total}回 (成功率{rate}%)")
        
        return "\n".join(lines)
    
    def answer_what_did_i_do(self) -> str:
        """「今日なにした？」への回答"""
        entries = self.get_today_entries()
        stats = self.get_stats()
        
        if not entries:
            return "今日はまだ何もしてないよ。のんびり航海中〜"
        
        # 最近の3件
        recent = entries[-3:]
        recent_str = "、".join(e.get("detail", "")[:20] for e in recent)
        
        return (
            f"今日は{stats['total']}回動いたよ！成功率は{stats['success_rate']}%。\n"
            f"最近やったこと: {recent_str}\n"
            f"よく使った操舵: {', '.join(c[0] for c in stats['commands_top5'][:3]) if stats['commands_top5'] else 'なし'}"
        )
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
航海日誌（Ship's Log）
日次行動要約・統計・週次レポート・自己理解
"""

import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import Counter


class ShipsLog:
    """航海日誌"""
    
    LOG_DIR = "/home/pi/autonomous_ai/state/ships_log"
    
    def __init__(self):
        os.makedirs(self.LOG_DIR, exist_ok=True)
    
    def _today_file(self, date: Optional[datetime] = None) -> str:
        d = date or datetime.now()
        return os.path.join(self.LOG_DIR, f"{d.strftime('%Y%m%d')}.jsonl")
    
    # ===== 記録 =====
    
    def record_action(self, action_type: str, detail: str, success: bool = True,
                      duration: float = 0, metadata: Optional[Dict] = None):
        """
        アクションを記録
        
        Args:
            action_type: "command", "query", "goal", "maintenance", "error", "mode_switch"
            detail: 内容
            success: 成功/失敗
            duration: 所要時間(秒)
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "type": action_type,
            "detail": detail,
            "success": success,
            "duration": round(duration, 2),
        }
        if metadata:
            entry["meta"] = metadata
        
        try:
            with open(self._today_file(), 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[ShipsLog] 記録エラー: {e}")
    
    # ===== 読み取り =====
    
    def get_today_entries(self) -> List[Dict]:
        """今日のエントリを全取得"""
        return self._read_entries(self._today_file())
    
    def _read_entries(self, path: str) -> List[Dict]:
        entries = []
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entries.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass
        return entries
    
    # ===== 統計 =====
    
    def get_stats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """日次統計"""
        entries = self._read_entries(self._today_file(date))
        
        if not entries:
            return {
                "total": 0, 
                "success": 0,
                "success_rate": 0, 
                "types": {}, 
                "commands_top5": [],
                "long_tasks": 0,
                "total_duration": 0
            }
        
        total = len(entries)
        success = sum(1 for e in entries if e.get("success", True))
        types = Counter(e.get("type", "unknown") for e in entries)
        
        # コマンド分析
        commands = [e["detail"] for e in entries if e.get("type") == "command"]
        cmd_counter = Counter(commands)
        top5 = cmd_counter.most_common(5)
        
        # 長時間タスク
        long_tasks = [e for e in entries if float(e.get("duration", 0)) > 30]
        
        return {
            "total": total,
            "success": success,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "types": dict(types),
            "commands_top5": top5,
            "long_tasks": len(long_tasks),
            "total_duration": round(sum(float(e.get("duration", 0)) for e in entries), 1),
        }
    
    # ===== 要約 =====
    
    def generate_daily_summary(self, date: Optional[datetime] = None) -> str:
        """日次航海日誌サマリー（航海用語）"""
        stats = self.get_stats(date)
        d = date or datetime.now()
        
        if stats["total"] == 0:
            return f"📔 航海日誌 {d.strftime('%Y/%m/%d')}\n本日は静かな航海でした。目立った出来事なし。"
        
        lines = [
            f"📔 航海日誌 {d.strftime('%Y/%m/%d')}",
            f"",
            f"⚓ 行動回数: {stats['total']}回",
            f"✅ 成功率: {stats['success_rate']}%",
            f"⏱️ 総稼働時間: {stats['total_duration']:.0f}秒",
        ]
        
        if stats["types"]:
            type_str = ", ".join(f"{k}:{v}回" for k, v in stats["types"].items())
            lines.append(f"📊 内訳: {type_str}")
        
        if stats["commands_top5"]:
            top_cmds = ", ".join(f"{cmd[0]}({cmd[1]}回)" for cmd in stats["commands_top5"][:3])
            lines.append(f"🔧 よく使った操舵: {top_cmds}")
        
        if stats["long_tasks"] > 0:
            lines.append(f"🐌 長時間タスク: {stats['long_tasks']}件")
        
        return "\n".join(lines)
    
    def generate_weekly_summary(self) -> str:
        """週次航海報告"""
        lines = ["📊 週間航海報告", ""]
        week_total = 0
        week_success = 0
        
        for i in range(7):
            d = datetime.now() - timedelta(days=i)
            stats = self.get_stats(d)
            week_total += stats["total"]
            week_success += stats["success"]
            
            if stats["total"] > 0:
                lines.append(
                    f"  {d.strftime('%m/%d(%a)')}: {stats['total']}回 "
                    f"(成功率{stats['success_rate']}%)"
                )
        
        if week_total > 0:
            rate = round(week_success / week_total * 100, 1)
            lines.insert(2, f"⚓ 週間合計: {week_total}回 (成功率{rate}%)")
        
        return "\n".join(lines)
    
    def generate_daily_report(self) -> str:
        """システム状態も含めた包括的な日次レポート"""
        summary = self.generate_daily_summary()
        
        # ディスク情報の追加
        storage_info = "\n\n🚢 船体（ストレージ）状態"
        try:
            import psutil
            ssd = psutil.disk_usage("/")
            storage_info += f"\n- SSD: {ssd.percent}%使用中"
            
            if os.path.exists("/mnt/hdd"):
                hdd = psutil.disk_usage("/mnt/hdd")
                storage_info += f"\n- HDD: {hdd.percent}%使用中"
            else:
                storage_info += "\n- HDD: 未検出"
        except Exception:
            storage_info += "\n- ストレージ情報取得エラー"
        
        return summary + storage_info

    def answer_what_did_i_do(self) -> str:
        """「今日なにした？」への回答"""
        entries = self.get_today_entries()
        stats = self.get_stats()
        
        if not entries:
            return "今日はまだ何もしてないよ。のんびり航海中〜"
        
        # 最近の3件
        recent = entries[-3:]
        recent_str = "、".join(e.get("detail", "")[:20] for e in recent)
        
        return (
            f"今日は{stats['total']}回動いたよ！成功率は{stats['success_rate']}%。\n"
            f"最近やったこと: {recent_str}\n"
            f"よく使った操舵: {', '.join(c[0] for c in stats['commands_top5'][:3]) if stats['commands_top5'] else 'なし'}"
        )
>>>>>>> Stashed changes
