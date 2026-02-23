#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メモリ管理モジュール
長期記憶の保存・検索・要約を管理
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib


class MemoryManager:
    """長期記憶管理クラス"""
    
    def __init__(self, base_dir: str = "/home/pi/autonomous_ai/memory"):
        """
        初期化
        
        Args:
            base_dir: メモリデータの保存ディレクトリ
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.diary_path = self.base_dir / "diary.txt"
        self.index_path = self.base_dir / "index.json"
        self.topics_dir = self.base_dir / "topics"
        self.topics_dir.mkdir(exist_ok=True)
        
        # インデックスの初期化
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """インデックスファイルを読み込む"""
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"topics": {}, "total_memories": 0}
    
    def _save_index(self):
        """インデックスファイルを保存"""
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def write_memory(self, filename: str, content: str) -> bool:
        """
        メモリを保存
        
        Args:
            filename: ファイル名（例: topic_20260219_143022.txt）
            content: 保存する内容
            
        Returns:
            成功したらTrue
        """
        try:
            # ファイル名からトピックを抽出
            topic = filename.split('_')[0] if '_' in filename else 'general'
            
            # ファイルパス
            file_path = self.topics_dir / filename
            
            # 内容を保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # インデックス更新
            if topic not in self.index["topics"]:
                self.index["topics"][topic] = []
            
            self.index["topics"][topic].append({
                "filename": filename,
                "created_at": datetime.now().isoformat(),
                "size": len(content),
                "hash": hashlib.md5(content.encode()).hexdigest()
            })
            
            self.index["total_memories"] += 1
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"メモリ保存エラー: {e}")
            return False
    
    def append_diary(self, entry: str) -> bool:
        """
        日誌に追記
        
        Args:
            entry: 追記する内容
            
        Returns:
            成功したらTrue
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.diary_path, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp}]\n{entry}\n")
            return True
        except Exception as e:
            print(f"日誌追記エラー: {e}")
            return False
    
    def read_diary(self, lines: int = 50) -> str:
        """
        日誌を読み込む
        
        Args:
            lines: 読み込む行数（末尾から）
            
        Returns:
            日誌の内容
        """
        try:
            if not self.diary_path.exists():
                return "日誌はまだ空です。"
            
            with open(self.diary_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            print(f"日誌読み込みエラー: {e}")
            return f"エラー: {e}"
    
    def search_memories(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        キーワードでメモリを検索
        
        Args:
            keyword: 検索キーワード
            limit: 最大結果数
            
        Returns:
            検索結果のリスト
        """
        results = []
        
        try:
            for topic_file in self.topics_dir.glob("*.txt"):
                with open(topic_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if keyword.lower() in content.lower():
                        results.append({
                            "filename": topic_file.name,
                            "preview": content[:200] + "..." if len(content) > 200 else content,
                            "match_count": content.lower().count(keyword.lower())
                        })
            
            # マッチ数でソート
            results.sort(key=lambda x: x["match_count"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"検索エラー: {e}")
            return []
    
    def get_recent_memories(self, count: int = 5) -> List[Dict]:
        """
        最近のメモリを取得
        
        Args:
            count: 取得する件数
            
        Returns:
            最近のメモリのリスト
        """
        all_memories = []
        
        for topic, memories in self.index["topics"].items():
            for mem in memories:
                mem["topic"] = topic
                all_memories.append(mem)
        
        # 作成日時でソート
        all_memories.sort(key=lambda x: x["created_at"], reverse=True)
        
        return all_memories[:count]
    
    def get_memory_content(self, filename: str) -> Optional[str]:
        """
        メモリの内容を取得
        
        Args:
            filename: ファイル名
            
        Returns:
            メモリの内容（存在しない場合はNone）
        """
        file_path = self.topics_dir / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"メモリ読み込みエラー: {e}")
            return None
    
    def get_summary(self) -> str:
        """
        メモリの要約を取得
        
        Returns:
            メモリの要約（日本語）
        """
        summary = f"# メモリサマリー\n\n"
        summary += f"総メモリ数: {self.index['total_memories']}\n"
        summary += f"トピック数: {len(self.index['topics'])}\n\n"
        
        summary += "## トピック別メモリ数\n"
        for topic, memories in self.index["topics"].items():
            summary += f"- {topic}: {len(memories)}件\n"
        
        summary += "\n## 最近のメモリ\n"
        recent = self.get_recent_memories(5)
        for mem in recent:
            summary += f"- [{mem['topic']}] {mem['filename']} ({mem['created_at'][:10]})\n"
        
        return summary
    
    def cleanup_old_memories(self, days: int = 90) -> int:
        """
        古いメモリを削除
        
        Args:
            days: 保持する日数
            
        Returns:
            削除したファイル数
        """
        from datetime import timedelta
        
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            for topic, memories in list(self.index["topics"].items()):
                updated_memories = []
                
                for mem in memories:
                    created_at = datetime.fromisoformat(mem["created_at"])
                    
                    if created_at < cutoff_date:
                        # ファイル削除
                        file_path = self.topics_dir / mem["filename"]
                        if file_path.exists():
                            file_path.unlink()
                            deleted_count += 1
                    else:
                        updated_memories.append(mem)
                
                if updated_memories:
                    self.index["topics"][topic] = updated_memories
                else:
                    del self.index["topics"][topic]
            
            self.index["total_memories"] -= deleted_count
            self._save_index()
            
            return deleted_count
            
        except Exception as e:
            print(f"クリーンアップエラー: {e}")
            return 0
    
    def export_all_memories(self, output_path: str) -> bool:
        """
        全メモリをエクスポート
        
        Args:
            output_path: 出力ファイルパス
            
        Returns:
            成功したらTrue
        """
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "index": self.index,
                "diary": self.read_diary(lines=1000),
                "memories": {}
            }
            
            # 全メモリを読み込み
            for topic_file in self.topics_dir.glob("*.txt"):
                with open(topic_file, 'r', encoding='utf-8') as f:
                    export_data["memories"][topic_file.name] = f.read()
            
            # JSON出力
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"エクスポートエラー: {e}")
            return False


# テスト用
if __name__ == "__main__":
    # テスト実行
    memory = MemoryManager(base_dir="/tmp/test_memory")
    
    # メモリ書き込みテスト
    memory.write_memory("test_20260219_120000.txt", "これはテストメモリです。")
    memory.append_diary("システムテスト開始")
    
    # 読み込みテスト
    print(memory.get_summary())
    print("\n日誌:")
    print(memory.read_diary())
