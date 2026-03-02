#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ストレージ管理モジュール
SSD/HDD階層化とNAS共有
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json


class StorageManager:
    """ストレージ管理クラス"""
    
    def __init__(
        self,
        ssd_path: str = "/home/pi/autonomous_ai",
        hdd_path: str = "/mnt/hdd/archive",
        access_threshold_days: int = 30,
        config_file: str = "/home/pi/autonomous_ai/storage_config.json"
    ):
        """
        初期化
        
        Args:
            ssd_path: SSDのパス
            hdd_path: HDDのパス
            access_threshold_days: 未アクセス日数の閾値
            config_file: 設定ファイルのパス
        """
        self.ssd_path = Path(ssd_path)
        self.hdd_path = Path(hdd_path)
        self.access_threshold_days = access_threshold_days
        self.config_file = Path(config_file)
        
        # ディレクトリ作成
        self.ssd_path.mkdir(parents=True, exist_ok=True)
        self.hdd_path.mkdir(parents=True, exist_ok=True)
        
        # 設定読み込み
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """設定ファイルを読み込み"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            "exclude_patterns": [
                "*.log",
                "*.tmp",
                ".git/*",
                "__pycache__/*"
            ],
            "archive_extensions": [
                ".zip", ".tar", ".gz", ".bz2", ".7z"
            ],
            "large_file_threshold_mb": 100
        }
    
    def _save_config(self):
        """設定ファイルを保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get_disk_usage(self, path: str) -> Dict:
        """
        ディスク使用量を取得
        
        Args:
            path: チェックするパス
            
        Returns:
            使用量情報の辞書
        """
        try:
            stat = shutil.disk_usage(path)
            return {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "percent": (stat.used / stat.total) * 100 if stat.total > 0 else 0
            }
        except Exception as e:
            print(f"ディスク使用量取得エラー: {e}")
            return {}
    
    def find_old_files(self, days: int = None) -> List[Path]:
        """
        古いファイルを検索
        
        Args:
            days: 未アクセス日数（指定しない場合は設定値を使用）
            
        Returns:
            古いファイルのリスト
        """
        if days is None:
            days = self.access_threshold_days
        
        threshold_time = datetime.now() - timedelta(days=days)
        old_files = []
        
        try:
            for file_path in self.ssd_path.rglob("*"):
                # ディレクトリはスキップ
                if not file_path.is_file():
                    continue
                
                # 除外パターンチェック
                if self._should_exclude(file_path):
                    continue
                
                # アクセス時間チェック
                atime = datetime.fromtimestamp(file_path.stat().st_atime)
                if atime < threshold_time:
                    old_files.append(file_path)
            
            return old_files
            
        except Exception as e:
            print(f"古いファイル検索エラー: {e}")
            return []
    
    def _should_exclude(self, file_path: Path) -> bool:
        """
        ファイルを除外すべきかチェック
        
        Args:
            file_path: ファイルパス
            
        Returns:
            除外すべきならTrue
        """
        for pattern in self.config.get("exclude_patterns", []):
            if file_path.match(pattern):
                return True
        return False
    
    def move_to_hdd(self, file_path: Path) -> bool:
        """
        ファイルをHDDに移動
        
        Args:
            file_path: 移動するファイル
            
        Returns:
            成功したらTrue
        """
        try:
            # 相対パスを計算
            relative_path = file_path.relative_to(self.ssd_path)
            
            # HDD上の保存先
            hdd_file_path = self.hdd_path / relative_path
            
            # ディレクトリ作成
            hdd_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル移動
            shutil.move(str(file_path), str(hdd_file_path))
            
            # シンボリックリンク作成（オプション）
            # file_path.symlink_to(hdd_file_path)
            
            print(f"移動完了: {file_path} -> {hdd_file_path}")
            return True
            
        except Exception as e:
            print(f"ファイル移動エラー: {e}")
            return False
    
    def archive_old_files(self, dry_run: bool = False) -> Dict:
        """
        古いファイルをHDDにアーカイブ
        
        Args:
            dry_run: 実際には移動せずに確認のみ
            
        Returns:
            実行結果の辞書
        """
        old_files = self.find_old_files()
        
        result = {
            "total_files": len(old_files),
            "moved_files": 0,
            "failed_files": 0,
            "total_size": 0,
            "dry_run": dry_run,
            "moved_details": []  # 各ファイルのsrc/dst/size
        }
        
        for file_path in old_files:
            try:
                file_size = file_path.stat().st_size
                result["total_size"] += file_size
                
                if not dry_run:
                    relative_path = file_path.relative_to(self.ssd_path)
                    hdd_dest = self.hdd_path / relative_path
                    if self.move_to_hdd(file_path):
                        result["moved_files"] += 1
                        result["moved_details"].append({
                            "src": str(file_path),
                            "dst": str(hdd_dest),
                            "size": file_size
                        })
                    else:
                        result["failed_files"] += 1
                else:
                    print(f"[DRY RUN] 移動予定: {file_path} ({file_size} bytes)")
                    result["moved_files"] += 1
                    result["moved_details"].append({
                        "src": str(file_path),
                        "dst": "(dry-run)",
                        "size": file_size
                    })
                    
            except Exception as e:
                print(f"ファイル処理エラー: {e}")
                result["failed_files"] += 1
        
        return result
    
    def setup_nas(self, share_name: str = "autonomous_ai") -> bool:
        """
        NAS共有を設定（Samba）
        
        Args:
            share_name: 共有名
            
        Returns:
            成功したらTrue
        """
        try:
            # Sambaがインストールされているか確認
            result = subprocess.run(
                ["which", "smbd"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("エラー: Sambaがインストールされていません")
                print("インストール: sudo apt-get install samba")
                return False
            
            # Samba設定ファイルに追記
            samba_config = f"""
[{share_name}]
    path = {self.hdd_path}
    browseable = yes
    read only = no
    guest ok = no
    valid users = pi
    create mask = 0644
    directory mask = 0755
"""
            
            print("以下の設定を /etc/samba/smb.conf に追加してください:")
            print(samba_config)
            print("\n設定後、以下のコマンドを実行してください:")
            print("sudo systemctl restart smbd")
            print("sudo smbpasswd -a pi")
            
            return True
            
        except Exception as e:
            print(f"NAS設定エラー: {e}")
            return False
    
    def get_storage_summary(self) -> str:
        """
        ストレージの要約を取得
        
        Returns:
            要約文字列
        """
        ssd_usage = self.get_disk_usage(str(self.ssd_path))
        hdd_usage = self.get_disk_usage(str(self.hdd_path))
        
        summary = "# ストレージサマリー\n\n"
        
        summary += "## SSD使用量\n"
        if ssd_usage:
            summary += f"- 合計: {ssd_usage['total'] / (1024**3):.2f} GB\n"
            summary += f"- 使用: {ssd_usage['used'] / (1024**3):.2f} GB\n"
            summary += f"- 空き: {ssd_usage['free'] / (1024**3):.2f} GB\n"
            summary += f"- 使用率: {ssd_usage['percent']:.1f}%\n"
        
        summary += "\n## HDD使用量\n"
        if hdd_usage:
            summary += f"- 合計: {hdd_usage['total'] / (1024**3):.2f} GB\n"
            summary += f"- 使用: {hdd_usage['used'] / (1024**3):.2f} GB\n"
            summary += f"- 空き: {hdd_usage['free'] / (1024**3):.2f} GB\n"
            summary += f"- 使用率: {hdd_usage['percent']:.1f}%\n"
        
        # 古いファイル数
        old_files = self.find_old_files()
        summary += f"\n## アーカイブ候補\n"
        summary += f"- {self.access_threshold_days}日以上未アクセス: {len(old_files)}ファイル\n"
        
        return summary
    
    def cleanup_temp_files(self) -> int:
        """
        一時ファイルを削除
        
        Returns:
            削除したファイル数
        """
        deleted_count = 0
        temp_patterns = ["*.tmp", "*.temp", "*.cache"]
        
        try:
            for pattern in temp_patterns:
                for file_path in self.ssd_path.rglob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        deleted_count += 1
                        print(f"削除: {file_path}")
            
            return deleted_count
            
        except Exception as e:
            print(f"一時ファイル削除エラー: {e}")
            return deleted_count
    
    def monitor_storage(self, threshold_percent: float = 80.0) -> Optional[Dict]:
        """
        ストレージを監視し、閾値を超えたら警告
        
        Args:
            threshold_percent: 警告閾値（パーセント）
            
        Returns:
            警告情報（問題なければNone）
        """
        ssd_usage = self.get_disk_usage(str(self.ssd_path))
        
        if ssd_usage and ssd_usage["percent"] > threshold_percent:
            return {
                "level": "warning",
                "message": f"SSD使用率が{ssd_usage['percent']:.1f}%に達しました",
                "usage": ssd_usage,
                "recommendation": "古いファイルのアーカイブを実行してください"
            }
        
        return None


# テスト用
if __name__ == "__main__":
    storage = StorageManager(
        ssd_path="/tmp/test_ssd",
        hdd_path="/tmp/test_hdd"
    )
    
    print("=== ストレージサマリー ===")
    print(storage.get_storage_summary())
    
    print("\n=== 古いファイル検索 ===")
    old_files = storage.find_old_files(days=7)
    print(f"見つかったファイル: {len(old_files)}個")
    
    print("\n=== アーカイブ実行（ドライラン） ===")
    result = storage.archive_old_files(dry_run=True)
    print(f"対象ファイル: {result['total_files']}個")
    print(f"合計サイズ: {result['total_size'] / (1024**2):.2f} MB")
    
    print("\n=== ストレージ監視 ===")
    alert = storage.monitor_storage(threshold_percent=50.0)
    if alert:
        print(f"警告: {alert['message']}")
    else:
        print("問題なし")
