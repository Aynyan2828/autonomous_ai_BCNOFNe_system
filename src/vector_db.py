#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ベクトルデータベース統合モジュール
ChromaDBとFAISSの両方に対応した長期記憶システム
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class VectorDatabase:
    """ベクトルデータベース統合クラス"""
    
    def __init__(
        self,
        db_type: str = "chromadb",
        db_dir: str = "/home/pi/autonomous_ai/vector_db",
        api_key: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        初期化
        
        Args:
            db_type: データベースタイプ（"chromadb" or "faiss"）
            db_dir: データベースディレクトリ
            api_key: OpenAI API Key（埋め込み生成用）
            embedding_model: 埋め込みモデル
        """
        self.logger = logging.getLogger(__name__)
        self.db_type = db_type
        self.db_dir = Path(db_dir)
        self.embedding_model = embedding_model
        
        # ディレクトリ作成
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAIクライアント
        if OPENAI_AVAILABLE and api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            self.logger.warning("OpenAI APIが利用できません。埋め込み生成が制限されます。")
        
        # データベース初期化
        self.db = None
        self.index = None
        self.metadata_store = {}
        
        if db_type == "chromadb":
            self._init_chromadb()
        elif db_type == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"サポートされていないデータベースタイプ: {db_type}")
    
    def _init_chromadb(self):
        """ChromaDB初期化"""
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadbがインストールされていません: pip install chromadb")
        
        try:
            self.db = chromadb.PersistentClient(
                path=str(self.db_dir / "chromadb"),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # コレクション取得または作成
            self.collection = self.db.get_or_create_collection(
                name="autonomous_ai_memory",
                metadata={"description": "自律AIの長期記憶"}
            )
            
            self.logger.info("ChromaDBを初期化しました")
        
        except Exception as e:
            self.logger.error(f"ChromaDB初期化エラー: {e}")
            raise
    
    def _init_faiss(self):
        """FAISS初期化"""
        if not FAISS_AVAILABLE:
            raise ImportError("faissがインストールされていません: pip install faiss-cpu")
        
        try:
            self.dimension = 1536  # text-embedding-3-smallの次元数
            self.index_file = self.db_dir / "faiss" / "index.faiss"
            self.metadata_file = self.db_dir / "faiss" / "metadata.json"
            
            # ディレクトリ作成
            self.index_file.parent.mkdir(parents=True, exist_ok=True)
            
            # インデックス読み込みまたは作成
            if self.index_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                self.logger.info(f"FAISSインデックスを読み込みました: {self.index.ntotal}件")
            else:
                self.index = faiss.IndexFlatL2(self.dimension)
                self.logger.info("新しいFAISSインデックスを作成しました")
            
            # メタデータ読み込み
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata_store = json.load(f)
            
        except Exception as e:
            self.logger.error(f"FAISS初期化エラー: {e}")
            raise
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        テキストから埋め込みベクトルを生成
        
        Args:
            text: テキスト
            
        Returns:
            埋め込みベクトル
        """
        if not self.openai_client:
            self.logger.error("OpenAIクライアントが初期化されていません")
            return None
        
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            embedding = response.data[0].embedding
            return embedding
        
        except Exception as e:
            self.logger.error(f"埋め込み生成エラー: {e}")
            return None
    
    def add(
        self,
        text: str,
        metadata: Optional[Dict] = None,
        doc_id: Optional[str] = None
    ) -> bool:
        """
        テキストをデータベースに追加
        
        Args:
            text: テキスト
            metadata: メタデータ
            doc_id: ドキュメントID
            
        Returns:
            成功したかどうか
        """
        if not doc_id:
            doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        if not metadata:
            metadata = {}
        
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["text"] = text
        
        # 埋め込み生成
        embedding = self.generate_embedding(text)
        if not embedding:
            return False
        
        try:
            if self.db_type == "chromadb":
                self.collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[text]
                )
            
            elif self.db_type == "faiss":
                # FAISSに追加
                embedding_np = np.array([embedding], dtype=np.float32)
                self.index.add(embedding_np)
                
                # メタデータ保存
                index_id = self.index.ntotal - 1
                self.metadata_store[str(index_id)] = {
                    "doc_id": doc_id,
                    "text": text,
                    "metadata": metadata
                }
                
                # 永続化
                self._save_faiss()
            
            self.logger.info(f"ドキュメントを追加しました: {doc_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"ドキュメント追加エラー: {e}")
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        類似検索
        
        Args:
            query: 検索クエリ
            n_results: 取得件数
            filter_metadata: メタデータフィルタ
            
        Returns:
            検索結果リスト
        """
        # クエリの埋め込み生成
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return []
        
        try:
            if self.db_type == "chromadb":
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=filter_metadata
                )
                
                # 結果を整形
                formatted_results = []
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })
                
                return formatted_results
            
            elif self.db_type == "faiss":
                # FAISS検索
                query_np = np.array([query_embedding], dtype=np.float32)
                distances, indices = self.index.search(query_np, n_results)
                
                # 結果を整形
                formatted_results = []
                for i, idx in enumerate(indices[0]):
                    if idx == -1:
                        continue
                    
                    metadata_entry = self.metadata_store.get(str(idx), {})
                    formatted_results.append({
                        "id": metadata_entry.get("doc_id", f"unknown_{idx}"),
                        "text": metadata_entry.get("text", ""),
                        "metadata": metadata_entry.get("metadata", {}),
                        "distance": float(distances[0][i])
                    })
                
                return formatted_results
        
        except Exception as e:
            self.logger.error(f"検索エラー: {e}")
            return []
    
    def _save_faiss(self):
        """FAISSインデックスとメタデータを保存"""
        try:
            faiss.write_index(self.index, str(self.index_file))
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            self.logger.error(f"FAISS保存エラー: {e}")
    
    def get_stats(self) -> Dict:
        """
        データベース統計を取得
        
        Returns:
            統計情報
        """
        if self.db_type == "chromadb":
            count = self.collection.count()
            return {
                "type": "chromadb",
                "count": count
            }
        
        elif self.db_type == "faiss":
            return {
                "type": "faiss",
                "count": self.index.ntotal,
                "dimension": self.dimension
            }


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    # ChromaDBテスト
    print("=== ChromaDBテスト ===")
    db = VectorDatabase(
        db_type="chromadb",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # ドキュメント追加
    db.add("Raspberry Piは小型のシングルボードコンピュータです。", {"category": "hardware"})
    db.add("Pythonは人気のあるプログラミング言語です。", {"category": "programming"})
    db.add("AIは人工知能の略称です。", {"category": "ai"})
    
    # 検索
    results = db.search("コンピュータについて教えて", n_results=2)
    print("\n検索結果:")
    for r in results:
        print(f"- {r['text']} (距離: {r['distance']:.4f})")
    
    # 統計
    stats = db.get_stats()
    print(f"\n統計: {stats}")


if __name__ == "__main__":
    main()
