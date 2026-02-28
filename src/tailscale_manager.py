#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tailscale統合モジュール
Tailscaleのインストール、設定、管理
"""

import os
import json
import logging
import subprocess
from typing import Dict, Optional, List
from pathlib import Path


class TailscaleManager:
    """Tailscale管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
        self.config_file = Path("/home/pi/autonomous_ai/tailscale_config.json")
        self.config = self._load_config()
        
        self.logger.info("Tailscale管理システムを初期化しました")
    
    def _load_config(self) -> Dict:
        """設定を読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
        
        return {
            "installed": False,
            "enabled": False,
            "ip_address": None,
            "hostname": None
        }
    
    def _save_config(self):
        """設定を保存"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
    
    def is_installed(self) -> bool:
        """
        Tailscaleがインストールされているか確認
        
        Returns:
            インストール済みかどうか
        """
        try:
            result = subprocess.run(
                ["which", "tailscale"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"インストール確認エラー: {e}")
            return False
    
    def install(self) -> bool:
        """
        Tailscaleをインストール
        
        Returns:
            成功したかどうか
        """
        try:
            if self.is_installed():
                self.logger.info("Tailscaleは既にインストールされています")
                self.config["installed"] = True
                self._save_config()
                return True
            
            self.logger.info("Tailscaleをインストール中...")
            
            # インストールスクリプトをダウンロードして実行
            result = subprocess.run(
                ["curl", "-fsSL", "https://tailscale.com/install.sh"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"ダウンロードエラー: {result.stderr.decode()}")
                return False
            
            # インストールスクリプトを実行
            result = subprocess.run(
                ["sudo", "sh", "-c", result.stdout.decode()],
                capture_output=True,
                timeout=300
            )
            
            if result.returncode != 0:
                self.logger.error(f"インストールエラー: {result.stderr.decode()}")
                return False
            
            self.logger.info("Tailscaleのインストールが完了しました")
            self.config["installed"] = True
            self._save_config()
            return True
        
        except Exception as e:
            self.logger.error(f"インストールエラー: {e}")
            return False
    
    def start(self, auth_key: Optional[str] = None) -> bool:
        """
        Tailscaleを起動
        
        Args:
            auth_key: 認証キー（オプション）
            
        Returns:
            成功したかどうか
        """
        try:
            if not self.is_installed():
                self.logger.error("Tailscaleがインストールされていません")
                return False
            
            self.logger.info("Tailscaleを起動中...")
            
            # 起動コマンド
            cmd = ["sudo", "tailscale", "up"]
            
            # 認証キーがある場合は追加
            if auth_key:
                cmd.extend(["--authkey", auth_key])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60
            )
            
            if result.returncode != 0:
                stderr = result.stderr.decode()
                
                # 既に起動している場合は成功とみなす
                if "already logged in" in stderr or "already running" in stderr:
                    self.logger.info("Tailscaleは既に起動しています")
                else:
                    self.logger.error(f"起動エラー: {stderr}")
                    return False
            
            self.logger.info("Tailscaleの起動が完了しました")
            self.config["enabled"] = True
            self._save_config()
            
            # IPアドレスとホスト名を取得
            self._update_status()
            
            return True
        
        except Exception as e:
            self.logger.error(f"起動エラー: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Tailscaleを停止
        
        Returns:
            成功したかどうか
        """
        try:
            if not self.is_installed():
                self.logger.error("Tailscaleがインストールされていません")
                return False
            
            self.logger.info("Tailscaleを停止中...")
            
            result = subprocess.run(
                ["sudo", "tailscale", "down"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"停止エラー: {result.stderr.decode()}")
                return False
            
            self.logger.info("Tailscaleを停止しました")
            self.config["enabled"] = False
            self._save_config()
            return True
        
        except Exception as e:
            self.logger.error(f"停止エラー: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Tailscaleの状態を取得
        
        Returns:
            状態情報
        """
        try:
            if not self.is_installed():
                return {
                    "installed": False,
                    "running": False,
                    "ip_address": None,
                    "hostname": None
                }
            
            # ステータスを取得
            result = subprocess.run(
                ["sudo", "tailscale", "status", "--json"],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "installed": True,
                    "running": False,
                    "ip_address": None,
                    "hostname": None
                }
            
            status = json.loads(result.stdout.decode())
            
            # 自分のIPアドレスを取得
            self_peer = status.get("Self", {})
            ip_address = self_peer.get("TailscaleIPs", [None])[0]
            hostname = self_peer.get("HostName")
            
            return {
                "installed": True,
                "running": True,
                "ip_address": ip_address,
                "hostname": hostname,
                "peers": len(status.get("Peer", {}))
            }
        
        except Exception as e:
            self.logger.error(f"ステータス取得エラー: {e}")
            return {
                "installed": self.is_installed(),
                "running": False,
                "ip_address": None,
                "hostname": None
            }
    
    def _update_status(self):
        """状態を更新"""
        status = self.get_status()
        self.config["ip_address"] = status.get("ip_address")
        self.config["hostname"] = status.get("hostname")
        self._save_config()
    
    def get_ip_address(self) -> Optional[str]:
        """
        Tailscale IPアドレスを取得
        
        Returns:
            IPアドレス
        """
        status = self.get_status()
        return status.get("ip_address")
    
    def get_peers(self) -> List[Dict]:
        """
        接続されているピアの一覧を取得
        
        Returns:
            ピア一覧
        """
        try:
            result = subprocess.run(
                ["sudo", "tailscale", "status", "--json"],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return []
            
            status = json.loads(result.stdout.decode())
            peers = []
            
            for peer_id, peer_info in status.get("Peer", {}).items():
                peers.append({
                    "id": peer_id,
                    "hostname": peer_info.get("HostName"),
                    "ip_address": peer_info.get("TailscaleIPs", [None])[0],
                    "online": peer_info.get("Online", False)
                })
            
            return peers
        
        except Exception as e:
            self.logger.error(f"ピア一覧取得エラー: {e}")
            return []
    
    def enable_exit_node(self) -> bool:
        """
        Exit Nodeを有効化
        
        Returns:
            成功したかどうか
        """
        try:
            self.logger.info("Exit Nodeを有効化中...")
            
            result = subprocess.run(
                ["sudo", "tailscale", "up", "--advertise-exit-node"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"Exit Node有効化エラー: {result.stderr.decode()}")
                return False
            
            self.logger.info("Exit Nodeを有効化しました")
            return True
        
        except Exception as e:
            self.logger.error(f"Exit Node有効化エラー: {e}")
            return False
    
    def enable_ssh(self) -> bool:
        """
        Tailscale SSHを有効化
        
        Returns:
            成功したかどうか
        """
        try:
            self.logger.info("Tailscale SSHを有効化中...")
            
            result = subprocess.run(
                ["sudo", "tailscale", "up", "--ssh"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"SSH有効化エラー: {result.stderr.decode()}")
                return False
            
            self.logger.info("Tailscale SSHを有効化しました")
            return True
        
        except Exception as e:
            self.logger.error(f"SSH有効化エラー: {e}")
            return False


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    manager = TailscaleManager()
    
    # インストール確認
    if manager.is_installed():
        print("✅ Tailscaleはインストール済みです")
    else:
        print("❌ Tailscaleはインストールされていません")
        print("インストールしますか? (y/n): ", end="")
        
        if input().lower() == 'y':
            if manager.install():
                print("✅ インストールが完了しました")
            else:
                print("❌ インストールに失敗しました")
                return
    
    # ステータスを表示
    status = manager.get_status()
    print("\n=== Tailscale ステータス ===")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # ピア一覧を表示
    peers = manager.get_peers()
    print("\n=== 接続されているピア ===")
    for peer in peers:
        print(f"- {peer['hostname']} ({peer['ip_address']}) - {'オンライン' if peer['online'] else 'オフライン'}")


if __name__ == "__main__":
    main()
