<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合ヘルスモニタ
7項目監視 + 異常レベル判定 + 通知ルーティング
"""

import os
import subprocess
import time
import json
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class HealthStatus:
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class HealthCheck:
    """個別チェック結果"""
    def __init__(self, name: str, status: str, value: Any, message: str = ""):
        self.name = name
        self.status = status
        self.value = value
        self.message = message
        self.timestamp = datetime.now().isoformat()


class HealthMonitor:
    """統合ヘルスモニタ"""
    
    HISTORY_FILE = "/home/pi/autonomous_ai/state/health_history.jsonl"
    
    def __init__(self):
        self.last_results: List[HealthCheck] = []
        self.ai_heartbeat: float = time.time()
        os.makedirs(os.path.dirname(self.HISTORY_FILE), exist_ok=True)
    
    def update_heartbeat(self):
        """AIループのハートビートを更新"""
        self.ai_heartbeat = time.time()
    
    # ===== 個別チェック =====
    
    def check_cpu_temp(self) -> HealthCheck:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
            if temp >= 80:
                return HealthCheck("CPU温度", HealthStatus.CRITICAL, temp, f"{temp:.1f}℃ 危険域！")
            elif temp >= 70:
                return HealthCheck("CPU温度", HealthStatus.WARN, temp, f"{temp:.1f}℃ 高温注意")
            return HealthCheck("CPU温度", HealthStatus.OK, temp, f"{temp:.1f}℃ 正常")
        except Exception:
            return HealthCheck("CPU温度", HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_ram(self) -> HealthCheck:
        try:
            mem = psutil.virtual_memory()
            if mem.percent >= 90:
                return HealthCheck("RAM", HealthStatus.CRITICAL, mem.percent, f"{mem.percent:.1f}% 逼迫！")
            elif mem.percent >= 80:
                return HealthCheck("RAM", HealthStatus.WARN, mem.percent, f"{mem.percent:.1f}% 注意")
            return HealthCheck("RAM", HealthStatus.OK, mem.percent, f"{mem.percent:.1f}% 正常")
        except Exception:
            return HealthCheck("RAM", HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_disk(self, path: str = "/", name: str = "SSD") -> HealthCheck:
        try:
            usage = psutil.disk_usage(path)
            pct = usage.percent
            if pct >= 90:
                return HealthCheck(name, HealthStatus.CRITICAL, pct, f"{pct:.1f}% 容量逼迫！")
            elif pct >= 80:
                return HealthCheck(name, HealthStatus.WARN, pct, f"{pct:.1f}% 注意")
            return HealthCheck(name, HealthStatus.OK, pct, f"{pct:.1f}% 正常")
        except Exception:
            return HealthCheck(name, HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_hdd_mount(self) -> HealthCheck:
        hdd_path = "/mnt/hdd/archive"
        if os.path.ismount("/mnt/hdd") or os.path.exists(hdd_path):
            try:
                usage = psutil.disk_usage(hdd_path)
                return HealthCheck("HDD", HealthStatus.OK, usage.percent, f"マウント済 {usage.percent:.1f}%")
            except Exception:
                return HealthCheck("HDD", HealthStatus.WARN, 0, "マウント済だがアクセス不可")
        return HealthCheck("HDD", HealthStatus.CRITICAL, 0, "未マウント！")
    
    def check_network(self) -> HealthCheck:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return HealthCheck("ネットワーク", HealthStatus.OK, True, "接続正常")
            return HealthCheck("ネットワーク", HealthStatus.WARN, False, "応答なし")
        except Exception:
            return HealthCheck("ネットワーク", HealthStatus.WARN, False, "チェック失敗")
    
    def check_ai_loop(self) -> HealthCheck:
        elapsed = time.time() - self.ai_heartbeat
        if elapsed > 300:  # 5分以上無反応
            return HealthCheck("AIループ", HealthStatus.CRITICAL, elapsed, f"{elapsed:.0f}秒無応答！")
        elif elapsed > 120:
            return HealthCheck("AIループ", HealthStatus.WARN, elapsed, f"{elapsed:.0f}秒経過")
        return HealthCheck("AIループ", HealthStatus.OK, elapsed, "正常稼働")
    
    def check_service(self, service: str = "autonomous-ai") -> HealthCheck:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            status = result.stdout.strip()
            if status == "active":
                return HealthCheck(f"サービス({service})", HealthStatus.OK, status, "稼働中")
            return HealthCheck(f"サービス({service})", HealthStatus.CRITICAL, status, f"状態: {status}")
        except Exception:
            return HealthCheck(f"サービス({service})", HealthStatus.UNKNOWN, "", "確認不可")
    
    # ===== 統合チェック =====
    
    def run_all_checks(self) -> List[HealthCheck]:
        """全チェックを実行"""
        checks = [
            self.check_cpu_temp(),
            self.check_ram(),
            self.check_disk("/", "SSD"),
            self.check_hdd_mount(),
            self.check_network(),
            self.check_ai_loop(),
            self.check_service(),
        ]
        self.last_results = checks
        self._record(checks)
        return checks
    
    def get_overall_status(self) -> str:
        """全体ステータスを取得"""
        if not self.last_results:
            return HealthStatus.UNKNOWN
        statuses = [c.status for c in self.last_results]
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.WARN in statuses:
            return HealthStatus.WARN
        return HealthStatus.OK
    
    def get_summary(self) -> str:
        """状態サマリー文字列"""
        if not self.last_results:
            self.run_all_checks()
        
        lines = []
        for c in self.last_results:
            icon = {"OK": "🟢", "WARN": "🟡", "CRITICAL": "🔴"}.get(c.status, "⚪")
            lines.append(f"{icon} {c.name}: {c.message}")
        return "\n".join(lines)
    
    def get_alerts(self) -> List[HealthCheck]:
        """WARN/CRITICAL のチェックだけ返す"""
        return [c for c in self.last_results if c.status in (HealthStatus.WARN, HealthStatus.CRITICAL)]
    
    def _record(self, checks: List[HealthCheck]):
        """履歴記録"""
        try:
            with open(self.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "checks": [{
                        "name": c.name, "status": c.status,
                        "value": c.value, "message": c.message
                    } for c in checks]
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合ヘルスモニタ
7項目監視 + 異常レベル判定 + 通知ルーティング
"""

import os
import subprocess
import time
import json
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class HealthStatus:
    OK = "OK"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class HealthCheck:
    """個別チェック結果"""
    def __init__(self, name: str, status: str, value: Any, message: str = ""):
        self.name = name
        self.status = status
        self.value = value
        self.message = message
        self.timestamp = datetime.now().isoformat()


class HealthMonitor:
    """統合ヘルスモニタ"""
    
    HISTORY_FILE = "/home/pi/autonomous_ai/state/health_history.jsonl"
    
    def __init__(self):
        self.last_results: List[HealthCheck] = []
        self.ai_heartbeat: float = time.time()
        os.makedirs(os.path.dirname(self.HISTORY_FILE), exist_ok=True)
    
    def update_heartbeat(self):
        """AIループのハートビートを更新"""
        self.ai_heartbeat = time.time()
    
    # ===== 個別チェック =====
    
    def check_cpu_temp(self) -> HealthCheck:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
            if temp >= 80:
                return HealthCheck("CPU温度", HealthStatus.CRITICAL, temp, f"{temp:.1f}℃ 危険域！")
            elif temp >= 70:
                return HealthCheck("CPU温度", HealthStatus.WARN, temp, f"{temp:.1f}℃ 高温注意")
            return HealthCheck("CPU温度", HealthStatus.OK, temp, f"{temp:.1f}℃ 正常")
        except Exception:
            return HealthCheck("CPU温度", HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_ram(self) -> HealthCheck:
        try:
            mem = psutil.virtual_memory()
            if mem.percent >= 90:
                return HealthCheck("RAM", HealthStatus.CRITICAL, mem.percent, f"{mem.percent:.1f}% 逼迫！")
            elif mem.percent >= 80:
                return HealthCheck("RAM", HealthStatus.WARN, mem.percent, f"{mem.percent:.1f}% 注意")
            return HealthCheck("RAM", HealthStatus.OK, mem.percent, f"{mem.percent:.1f}% 正常")
        except Exception:
            return HealthCheck("RAM", HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_disk(self, path: str = "/", name: str = "SSD") -> HealthCheck:
        try:
            usage = psutil.disk_usage(path)
            pct = usage.percent
            if pct >= 90:
                return HealthCheck(name, HealthStatus.CRITICAL, pct, f"{pct:.1f}% 容量逼迫！")
            elif pct >= 80:
                return HealthCheck(name, HealthStatus.WARN, pct, f"{pct:.1f}% 注意")
            return HealthCheck(name, HealthStatus.OK, pct, f"{pct:.1f}% 正常")
        except Exception:
            return HealthCheck(name, HealthStatus.UNKNOWN, 0, "取得不可")
    
    def check_hdd_mount(self) -> HealthCheck:
        hdd_path = "/mnt/hdd/archive"
        if os.path.ismount("/mnt/hdd") or os.path.exists(hdd_path):
            try:
                usage = psutil.disk_usage(hdd_path)
                return HealthCheck("HDD", HealthStatus.OK, usage.percent, f"マウント済 {usage.percent:.1f}%")
            except Exception:
                return HealthCheck("HDD", HealthStatus.WARN, 0, "マウント済だがアクセス不可")
        return HealthCheck("HDD", HealthStatus.CRITICAL, 0, "未マウント！")
    
    def check_network(self) -> HealthCheck:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return HealthCheck("ネットワーク", HealthStatus.OK, True, "接続正常")
            return HealthCheck("ネットワーク", HealthStatus.WARN, False, "応答なし")
        except Exception:
            return HealthCheck("ネットワーク", HealthStatus.WARN, False, "チェック失敗")
    
    def check_ai_loop(self) -> HealthCheck:
        elapsed = time.time() - self.ai_heartbeat
        if elapsed > 300:  # 5分以上無反応
            return HealthCheck("AIループ", HealthStatus.CRITICAL, elapsed, f"{elapsed:.0f}秒無応答！")
        elif elapsed > 120:
            return HealthCheck("AIループ", HealthStatus.WARN, elapsed, f"{elapsed:.0f}秒経過")
        return HealthCheck("AIループ", HealthStatus.OK, elapsed, "正常稼働")
    
    def check_service(self, service: str = "autonomous-ai") -> HealthCheck:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            status = result.stdout.strip()
            if status == "active":
                return HealthCheck(f"サービス({service})", HealthStatus.OK, status, "稼働中")
            return HealthCheck(f"サービス({service})", HealthStatus.CRITICAL, status, f"状態: {status}")
        except Exception:
            return HealthCheck(f"サービス({service})", HealthStatus.UNKNOWN, "", "確認不可")
    
    # ===== 統合チェック =====
    
    def run_all_checks(self) -> List[HealthCheck]:
        """全チェックを実行"""
        checks = [
            self.check_cpu_temp(),
            self.check_ram(),
            self.check_disk("/", "SSD"),
            self.check_hdd_mount(),
            self.check_network(),
            self.check_ai_loop(),
            self.check_service(),
        ]
        self.last_results = checks
        self._record(checks)
        return checks
    
    def get_overall_status(self) -> str:
        """全体ステータスを取得"""
        if not self.last_results:
            return HealthStatus.UNKNOWN
        statuses = [c.status for c in self.last_results]
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        if HealthStatus.WARN in statuses:
            return HealthStatus.WARN
        return HealthStatus.OK
    
    def get_summary(self) -> str:
        """状態サマリー文字列"""
        if not self.last_results:
            self.run_all_checks()
        
        lines = []
        for c in self.last_results:
            icon = {"OK": "🟢", "WARN": "🟡", "CRITICAL": "🔴"}.get(c.status, "⚪")
            lines.append(f"{icon} {c.name}: {c.message}")
        return "\n".join(lines)
    
    def get_alerts(self) -> List[HealthCheck]:
        """WARN/CRITICAL のチェックだけ返す"""
        return [c for c in self.last_results if c.status in (HealthStatus.WARN, HealthStatus.CRITICAL)]
    
    def _record(self, checks: List[HealthCheck]):
        """履歴記録"""
        try:
            with open(self.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "checks": [{
                        "name": c.name, "status": c.status,
                        "value": c.value, "message": c.message
                    } for c in checks]
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
>>>>>>> Stashed changes
