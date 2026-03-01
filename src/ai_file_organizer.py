<<<<<<< Updated upstream
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI自動ファイル整理モジュール
ファイルの内容を解析して自動分類・整理
"""

import os
import json
import logging
import hashlib
import shutil
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import mimetypes


class AIFileOrganizer:
    """AI自動ファイル整理クラス"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        base_dir: str = "/home/pi/autonomous_ai/nas",
        organized_dir: str = "/home/pi/autonomous_ai/nas/organized"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            base_dir: 整理対象のベースディレクトリ
            organized_dir: 整理後のディレクトリ
        """
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.base_dir = Path(base_dir)
        self.organized_dir = Path(organized_dir)
        
        # ディレクトリ作成
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.organized_dir.mkdir(parents=True, exist_ok=True)
        
        # カテゴリディレクトリ
        self.categories = {
            "images": {
                "landscape": "風景",
                "people": "人物",
                "food": "食べ物",
                "animals": "動物",
                "objects": "物体",
                "screenshots": "スクリーンショット",
                "other": "その他"
            },
            "documents": {
                "work": "仕事",
                "personal": "プライベート",
                "study": "学習",
                "finance": "財務",
                "receipts": "領収書",
                "other": "その他"
            },
            "music": {
                "rock": "ロック",
                "pop": "ポップ",
                "classical": "クラシック",
                "jazz": "ジャズ",
                "electronic": "エレクトロニック",
                "other": "その他"
            },
            "videos": {
                "movies": "映画",
                "tutorials": "チュートリアル",
                "recordings": "録画",
                "other": "その他"
            },
            "archives": {
                "backups": "バックアップ",
                "downloads": "ダウンロード",
                "other": "その他"
            }
        }
        
        # カテゴリディレクトリを作成
        for main_cat, sub_cats in self.categories.items():
            for sub_cat in sub_cats.keys():
                cat_dir = self.organized_dir / main_cat / sub_cat
                cat_dir.mkdir(parents=True, exist_ok=True)
        
        # 重複ファイル記録
        self.duplicate_log = self.organized_dir / "duplicates.json"
        self.duplicates = self._load_duplicates()
        
        # ファイルハッシュキャッシュ
        self.hash_cache = {}
        
        self.logger.info("AI自動ファイル整理システムを初期化しました")
    
    def _load_duplicates(self) -> Dict:
        """重複ファイル記録を読み込み"""
        try:
            if self.duplicate_log.exists():
                with open(self.duplicate_log, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"重複ファイル記録読み込みエラー: {e}")
        
        return {}
    
    def _save_duplicates(self):
        """重複ファイル記録を保存"""
        try:
            with open(self.duplicate_log, 'w', encoding='utf-8') as f:
                json.dump(self.duplicates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"重複ファイル記録保存エラー: {e}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        ファイルのハッシュ値を計算
        
        Args:
            file_path: ファイルパス
            
        Returns:
            SHA256ハッシュ値
        """
        if str(file_path) in self.hash_cache:
            return self.hash_cache[str(file_path)]
        
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            
            hash_value = sha256.hexdigest()
            self.hash_cache[str(file_path)] = hash_value
            return hash_value
        
        except Exception as e:
            self.logger.error(f"ハッシュ計算エラー: {file_path}: {e}")
            return ""
    
    def detect_file_type(self, file_path: Path) -> Tuple[str, str]:
        """
        ファイルタイプを検出
        
        Args:
            file_path: ファイルパス
            
        Returns:
            (メインカテゴリ, MIMEタイプ)
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type is None:
            return "other", "application/octet-stream"
        
        if mime_type.startswith("image/"):
            return "images", mime_type
        elif mime_type.startswith("video/"):
            return "videos", mime_type
        elif mime_type.startswith("audio/"):
            return "music", mime_type
        elif mime_type in ["application/pdf", "text/plain", "application/msword",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return "documents", mime_type
        elif mime_type in ["application/zip", "application/x-tar", "application/gzip"]:
            return "archives", mime_type
        else:
            return "other", mime_type
    
    def analyze_image(self, file_path: Path) -> str:
        """
        画像を解析してサブカテゴリを判定
        
        Args:
            file_path: 画像ファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名から判定
            filename = file_path.name.lower()
            
            if "screenshot" in filename or "screen" in filename:
                return "screenshots"
            
            # GPT-4 Visionを使った解析（オプション）
            # 実装する場合は、画像をbase64エンコードしてAPIに送信
            
            # デフォルト
            return "other"
        
        except Exception as e:
            self.logger.error(f"画像解析エラー: {file_path}: {e}")
            return "other"
    
    def analyze_document(self, file_path: Path) -> str:
        """
        ドキュメントを解析してサブカテゴリを判定
        
        Args:
            file_path: ドキュメントファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名から判定
            filename = file_path.name.lower()
            
            if any(word in filename for word in ["invoice", "receipt", "領収書", "請求書"]):
                return "receipts"
            elif any(word in filename for word in ["work", "仕事", "業務", "project"]):
                return "work"
            elif any(word in filename for word in ["study", "学習", "tutorial", "course"]):
                return "study"
            elif any(word in filename for word in ["finance", "財務", "tax", "税金"]):
                return "finance"
            
            # テキストファイルの場合は内容を読んで判定
            if file_path.suffix in [".txt", ".md"]:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # 最初の1000文字
                    
                    category = self._classify_text_content(content)
                    if category:
                        return category
                
                except Exception:
                    pass
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"ドキュメント解析エラー: {file_path}: {e}")
            return "other"
    
    def _classify_text_content(self, content: str) -> Optional[str]:
        """
        テキスト内容を分類
        
        Args:
            content: テキスト内容
            
        Returns:
            サブカテゴリ
        """
        try:
            prompt = f"""以下のテキストを読んで、最も適切なカテゴリを1つ選んでください。

カテゴリ:
- work: 仕事関連
- personal: プライベート
- study: 学習・教育
- finance: 財務・金融
- receipts: 領収書・請求書
- other: その他

テキスト:
{content}

カテゴリ名のみを返してください（説明不要）。
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたはテキスト分類の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            if category in self.categories["documents"]:
                return category
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"テキスト分類エラー: {e}")
            return None
    
    def analyze_music(self, file_path: Path) -> str:
        """
        音楽ファイルを解析してサブカテゴリを判定
        
        Args:
            file_path: 音楽ファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名やディレクトリ名から判定
            filename = file_path.name.lower()
            parent_dir = file_path.parent.name.lower()
            
            for genre in ["rock", "pop", "classical", "jazz", "electronic"]:
                if genre in filename or genre in parent_dir:
                    return genre
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"音楽解析エラー: {file_path}: {e}")
            return "other"
    
    def organize_file(self, file_path: Path, dry_run: bool = False) -> Dict:
        """
        ファイルを整理
        
        Args:
            file_path: ファイルパス
            dry_run: 実際には移動せず、結果のみを返す
            
        Returns:
            整理結果
        """
        result = {
            "file": str(file_path),
            "success": False,
            "action": None,
            "destination": None,
            "reason": None
        }
        
        try:
            # ファイルが存在するか確認
            if not file_path.exists():
                result["reason"] = "ファイルが存在しません"
                return result
            
            # ファイルハッシュを計算
            file_hash = self.calculate_file_hash(file_path)
            
            # 重複チェック
            if file_hash in self.duplicates:
                result["action"] = "duplicate"
                result["reason"] = f"重複ファイル: {self.duplicates[file_hash]}"
                
                if not dry_run:
                    # 重複ファイルを削除
                    file_path.unlink()
                    self.logger.info(f"重複ファイルを削除: {file_path}")
                
                result["success"] = True
                return result
            
            # ファイルタイプを検出
            main_category, mime_type = self.detect_file_type(file_path)
            
            # サブカテゴリを判定
            if main_category == "images":
                sub_category = self.analyze_image(file_path)
            elif main_category == "documents":
                sub_category = self.analyze_document(file_path)
            elif main_category == "music":
                sub_category = self.analyze_music(file_path)
            else:
                sub_category = "other"
            
            # 移動先を決定
            destination = self.organized_dir / main_category / sub_category / file_path.name
            
            # ファイル名が重複する場合はタイムスタンプを追加
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = destination.stem
                suffix = destination.suffix
                destination = destination.parent / f"{stem}_{timestamp}{suffix}"
            
            result["action"] = "move"
            result["destination"] = str(destination)
            result["category"] = f"{main_category}/{sub_category}"
            
            if not dry_run:
                # ファイルを移動
                shutil.move(str(file_path), str(destination))
                
                # ハッシュを記録
                self.duplicates[file_hash] = str(destination)
                self._save_duplicates()
                
                self.logger.info(f"ファイルを移動: {file_path} -> {destination}")
            
            result["success"] = True
            return result
        
        except Exception as e:
            result["reason"] = f"エラー: {e}"
            self.logger.error(f"ファイル整理エラー: {file_path}: {e}")
            return result
    
    def organize_directory(
        self,
        target_dir: Optional[Path] = None,
        recursive: bool = True,
        dry_run: bool = False
    ) -> Dict:
        """
        ディレクトリ全体を整理
        
        Args:
            target_dir: 対象ディレクトリ（Noneの場合はbase_dir）
            recursive: 再帰的に処理するか
            dry_run: 実際には移動せず、結果のみを返す
            
        Returns:
            整理結果の統計
        """
        if target_dir is None:
            target_dir = self.base_dir
        
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
            "moved": 0,
            "categories": {}
        }
        
        try:
            # ファイル一覧を取得
            if recursive:
                files = list(target_dir.rglob("*"))
            else:
                files = list(target_dir.glob("*"))
            
            # ファイルのみをフィルタ
            files = [f for f in files if f.is_file()]
            
            self.logger.info(f"整理対象ファイル数: {len(files)}")
            
            for file_path in files:
                # organized_dir配下のファイルはスキップ
                if str(file_path).startswith(str(self.organized_dir)):
                    continue
                
                stats["total"] += 1
                
                # ファイルを整理
                result = self.organize_file(file_path, dry_run=dry_run)
                
                if result["success"]:
                    stats["success"] += 1
                    
                    if result["action"] == "duplicate":
                        stats["duplicates"] += 1
                    elif result["action"] == "move":
                        stats["moved"] += 1
                        
                        category = result.get("category", "unknown")
                        stats["categories"][category] = stats["categories"].get(category, 0) + 1
                else:
                    stats["failed"] += 1
            
            self.logger.info(f"整理完了: {stats}")
            return stats
        
        except Exception as e:
            self.logger.error(f"ディレクトリ整理エラー: {e}")
            return stats
    
    def get_statistics(self) -> Dict:
        """
        整理状況の統計を取得
        
        Returns:
            統計情報
        """
        stats = {
            "total_files": 0,
            "categories": {}
        }
        
        try:
            for main_cat, sub_cats in self.categories.items():
                stats["categories"][main_cat] = {}
                
                for sub_cat in sub_cats.keys():
                    cat_dir = self.organized_dir / main_cat / sub_cat
                    
                    if cat_dir.exists():
                        files = list(cat_dir.rglob("*"))
                        file_count = len([f for f in files if f.is_file()])
                        
                        stats["categories"][main_cat][sub_cat] = file_count
                        stats["total_files"] += file_count
            
            stats["duplicates_count"] = len(self.duplicates)
            
            return stats
        
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return stats


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEYが設定されていません")
        return
    
    organizer = AIFileOrganizer(api_key=api_key)
    
    # ディレクトリ全体を整理（ドライラン）
    print("=== ドライラン（実際には移動しません） ===")
    stats = organizer.organize_directory(dry_run=True)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 統計を表示
    print("\n=== 整理状況の統計 ===")
    stats = organizer.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI自動ファイル整理モジュール
ファイルの内容を解析して自動分類・整理
"""

import os
import json
import logging
import hashlib
import shutil
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import mimetypes


class AIFileOrganizer:
    """AI自動ファイル整理クラス"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_dir: str = "/home/pi/autonomous_ai/nas",
        organized_dir: str = "/home/pi/autonomous_ai/nas/organized"
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            base_dir: 整理対象のベースディレクトリ
            organized_dir: 整理後のディレクトリ
        """
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.base_dir = Path(base_dir)
        self.organized_dir = Path(organized_dir)
        
        # ディレクトリ作成
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.organized_dir.mkdir(parents=True, exist_ok=True)
        
        # カテゴリディレクトリ
        self.categories = {
            "images": {
                "landscape": "風景",
                "people": "人物",
                "food": "食べ物",
                "animals": "動物",
                "objects": "物体",
                "screenshots": "スクリーンショット",
                "other": "その他"
            },
            "documents": {
                "work": "仕事",
                "personal": "プライベート",
                "study": "学習",
                "finance": "財務",
                "receipts": "領収書",
                "other": "その他"
            },
            "music": {
                "rock": "ロック",
                "pop": "ポップ",
                "classical": "クラシック",
                "jazz": "ジャズ",
                "electronic": "エレクトロニック",
                "other": "その他"
            },
            "videos": {
                "movies": "映画",
                "tutorials": "チュートリアル",
                "recordings": "録画",
                "other": "その他"
            },
            "archives": {
                "backups": "バックアップ",
                "downloads": "ダウンロード",
                "other": "その他"
            }
        }
        
        # カテゴリディレクトリを作成
        for main_cat, sub_cats in self.categories.items():
            for sub_cat in sub_cats.keys():
                cat_dir = self.organized_dir / main_cat / sub_cat
                cat_dir.mkdir(parents=True, exist_ok=True)
        
        # 重複ファイル記録
        self.duplicate_log = self.organized_dir / "duplicates.json"
        self.duplicates = self._load_duplicates()
        
        # ファイルハッシュキャッシュ
        self.hash_cache = {}
        
        self.logger.info("AI自動ファイル整理システムを初期化しました")
    
    def _load_duplicates(self) -> Dict:
        """重複ファイル記録を読み込み"""
        try:
            if self.duplicate_log.exists():
                with open(self.duplicate_log, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"重複ファイル記録読み込みエラー: {e}")
        
        return {}
    
    def _save_duplicates(self):
        """重複ファイル記録を保存"""
        try:
            with open(self.duplicate_log, 'w', encoding='utf-8') as f:
                json.dump(self.duplicates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"重複ファイル記録保存エラー: {e}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        ファイルのハッシュ値を計算
        
        Args:
            file_path: ファイルパス
            
        Returns:
            SHA256ハッシュ値
        """
        if str(file_path) in self.hash_cache:
            return self.hash_cache[str(file_path)]
        
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            
            hash_value = sha256.hexdigest()
            self.hash_cache[str(file_path)] = hash_value
            return hash_value
        
        except Exception as e:
            self.logger.error(f"ハッシュ計算エラー: {file_path}: {e}")
            return ""
    
    def detect_file_type(self, file_path: Path) -> Tuple[str, str]:
        """
        ファイルタイプを検出
        
        Args:
            file_path: ファイルパス
            
        Returns:
            (メインカテゴリ, MIMEタイプ)
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type is None:
            return "other", "application/octet-stream"
        
        if mime_type.startswith("image/"):
            return "images", mime_type
        elif mime_type.startswith("video/"):
            return "videos", mime_type
        elif mime_type.startswith("audio/"):
            return "music", mime_type
        elif mime_type in ["application/pdf", "text/plain", "application/msword",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return "documents", mime_type
        elif mime_type in ["application/zip", "application/x-tar", "application/gzip"]:
            return "archives", mime_type
        else:
            return "other", mime_type
    
    def analyze_image(self, file_path: Path) -> str:
        """
        画像を解析してサブカテゴリを判定
        
        Args:
            file_path: 画像ファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名から判定
            filename = file_path.name.lower()
            
            if "screenshot" in filename or "screen" in filename:
                return "screenshots"
            
            # GPT-4 Visionを使った解析（オプション）
            # 実装する場合は、画像をbase64エンコードしてAPIに送信
            
            # デフォルト
            return "other"
        
        except Exception as e:
            self.logger.error(f"画像解析エラー: {file_path}: {e}")
            return "other"
    
    def analyze_document(self, file_path: Path) -> str:
        """
        ドキュメントを解析してサブカテゴリを判定
        
        Args:
            file_path: ドキュメントファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名から判定
            filename = file_path.name.lower()
            
            if any(word in filename for word in ["invoice", "receipt", "領収書", "請求書"]):
                return "receipts"
            elif any(word in filename for word in ["work", "仕事", "業務", "project"]):
                return "work"
            elif any(word in filename for word in ["study", "学習", "tutorial", "course"]):
                return "study"
            elif any(word in filename for word in ["finance", "財務", "tax", "税金"]):
                return "finance"
            
            # テキストファイルの場合は内容を読んで判定
            if file_path.suffix in [".txt", ".md"]:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # 最初の1000文字
                    
                    category = self._classify_text_content(content)
                    if category:
                        return category
                
                except Exception:
                    pass
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"ドキュメント解析エラー: {file_path}: {e}")
            return "other"
    
    def _classify_text_content(self, content: str) -> Optional[str]:
        """
        テキスト内容を分類
        
        Args:
            content: テキスト内容
            
        Returns:
            サブカテゴリ
        """
        try:
            prompt = f"""以下のテキストを読んで、最も適切なカテゴリを1つ選んでください。

カテゴリ:
- work: 仕事関連
- personal: プライベート
- study: 学習・教育
- finance: 財務・金融
- receipts: 領収書・請求書
- other: その他

テキスト:
{content}

カテゴリ名のみを返してください（説明不要）。
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたはテキスト分類の専門家です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            if category in self.categories["documents"]:
                return category
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"テキスト分類エラー: {e}")
            return None
    
    def analyze_music(self, file_path: Path) -> str:
        """
        音楽ファイルを解析してサブカテゴリを判定
        
        Args:
            file_path: 音楽ファイルパス
            
        Returns:
            サブカテゴリ
        """
        try:
            # ファイル名やディレクトリ名から判定
            filename = file_path.name.lower()
            parent_dir = file_path.parent.name.lower()
            
            for genre in ["rock", "pop", "classical", "jazz", "electronic"]:
                if genre in filename or genre in parent_dir:
                    return genre
            
            return "other"
        
        except Exception as e:
            self.logger.error(f"音楽解析エラー: {file_path}: {e}")
            return "other"
    
    def organize_file(self, file_path: Path, dry_run: bool = False) -> Dict:
        """
        ファイルを整理
        
        Args:
            file_path: ファイルパス
            dry_run: 実際には移動せず、結果のみを返す
            
        Returns:
            整理結果
        """
        result = {
            "file": str(file_path),
            "success": False,
            "action": None,
            "destination": None,
            "reason": None
        }
        
        try:
            # ファイルが存在するか確認
            if not file_path.exists():
                result["reason"] = "ファイルが存在しません"
                return result
            
            # ファイルハッシュを計算
            file_hash = self.calculate_file_hash(file_path)
            
            # 重複チェック
            if file_hash in self.duplicates:
                result["action"] = "duplicate"
                result["reason"] = f"重複ファイル: {self.duplicates[file_hash]}"
                
                if not dry_run:
                    # 重複ファイルを削除
                    file_path.unlink()
                    self.logger.info(f"重複ファイルを削除: {file_path}")
                
                result["success"] = True
                return result
            
            # ファイルタイプを検出
            main_category, mime_type = self.detect_file_type(file_path)
            
            # サブカテゴリを判定
            if main_category == "images":
                sub_category = self.analyze_image(file_path)
            elif main_category == "documents":
                sub_category = self.analyze_document(file_path)
            elif main_category == "music":
                sub_category = self.analyze_music(file_path)
            else:
                sub_category = "other"
            
            # 移動先を決定
            destination = self.organized_dir / main_category / sub_category / file_path.name
            
            # ファイル名が重複する場合はタイムスタンプを追加
            if destination.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = destination.stem
                suffix = destination.suffix
                destination = destination.parent / f"{stem}_{timestamp}{suffix}"
            
            result["action"] = "move"
            result["destination"] = str(destination)
            result["category"] = f"{main_category}/{sub_category}"
            
            if not dry_run:
                # ファイルを移動
                shutil.move(str(file_path), str(destination))
                
                # ハッシュを記録
                self.duplicates[file_hash] = str(destination)
                self._save_duplicates()
                
                self.logger.info(f"ファイルを移動: {file_path} -> {destination}")
            
            result["success"] = True
            return result
        
        except Exception as e:
            result["reason"] = f"エラー: {e}"
            self.logger.error(f"ファイル整理エラー: {file_path}: {e}")
            return result
    
    def organize_directory(
        self,
        target_dir: Optional[Path] = None,
        recursive: bool = True,
        dry_run: bool = False
    ) -> Dict:
        """
        ディレクトリ全体を整理
        
        Args:
            target_dir: 対象ディレクトリ（Noneの場合はbase_dir）
            recursive: 再帰的に処理するか
            dry_run: 実際には移動せず、結果のみを返す
            
        Returns:
            整理結果の統計
        """
        if target_dir is None:
            target_dir = self.base_dir
        
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
            "moved": 0,
            "categories": {}
        }
        
        try:
            # ファイル一覧を取得
            if recursive:
                files = list(target_dir.rglob("*"))
            else:
                files = list(target_dir.glob("*"))
            
            # ファイルのみをフィルタ
            files = [f for f in files if f.is_file()]
            
            self.logger.info(f"整理対象ファイル数: {len(files)}")
            
            for file_path in files:
                # organized_dir配下のファイルはスキップ
                if str(file_path).startswith(str(self.organized_dir)):
                    continue
                
                stats["total"] += 1
                
                # ファイルを整理
                result = self.organize_file(file_path, dry_run=dry_run)
                
                if result["success"]:
                    stats["success"] += 1
                    
                    if result["action"] == "duplicate":
                        stats["duplicates"] += 1
                    elif result["action"] == "move":
                        stats["moved"] += 1
                        
                        category = result.get("category", "unknown")
                        stats["categories"][category] = stats["categories"].get(category, 0) + 1
                else:
                    stats["failed"] += 1
            
            self.logger.info(f"整理完了: {stats}")
            return stats
        
        except Exception as e:
            self.logger.error(f"ディレクトリ整理エラー: {e}")
            return stats
    
    def get_statistics(self) -> Dict:
        """
        整理状況の統計を取得
        
        Returns:
            統計情報
        """
        stats = {
            "total_files": 0,
            "categories": {}
        }
        
        try:
            for main_cat, sub_cats in self.categories.items():
                stats["categories"][main_cat] = {}
                
                for sub_cat in sub_cats.keys():
                    cat_dir = self.organized_dir / main_cat / sub_cat
                    
                    if cat_dir.exists():
                        files = list(cat_dir.rglob("*"))
                        file_count = len([f for f in files if f.is_file()])
                        
                        stats["categories"][main_cat][sub_cat] = file_count
                        stats["total_files"] += file_count
            
            stats["duplicates_count"] = len(self.duplicates)
            
            return stats
        
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return stats


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEYが設定されていません")
        return
    
    organizer = AIFileOrganizer(api_key=api_key)
    
    # ディレクトリ全体を整理（ドライラン）
    print("=== ドライラン（実際には移動しません） ===")
    stats = organizer.organize_directory(dry_run=True)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 統計を表示
    print("\n=== 整理状況の統計 ===")
    stats = organizer.get_statistics()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
