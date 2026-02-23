#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ブラウザ操作モジュール
Playwrightを使用したWeb自動操作
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext


class BrowserController:
    """ブラウザ操作クラス"""
    
    def __init__(
        self,
        headless: bool = True,
        user_data_dir: str = "/home/pi/autonomous_ai/browser_data",
        screenshots_dir: str = "/home/pi/autonomous_ai/screenshots"
    ):
        """
        初期化
        
        Args:
            headless: ヘッドレスモードで起動するか
            user_data_dir: ユーザーデータディレクトリ（Cookie等の保存先）
            screenshots_dir: スクリーンショット保存ディレクトリ
        """
        self.headless = headless
        self.user_data_dir = Path(user_data_dir)
        self.screenshots_dir = Path(screenshots_dir)
        
        # ディレクトリ作成
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def start(self) -> bool:
        """
        ブラウザを起動
        
        Returns:
            成功したらTrue
        """
        try:
            self.playwright = sync_playwright().start()
            
            # Chromiumを起動
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # コンテキストを作成（Cookie等を保持）
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ja-JP',
                timezone_id='Asia/Tokyo'
            )
            
            # 保存されたCookieを読み込み
            self._load_cookies()
            
            # 新しいページを開く
            self.page = self.context.new_page()
            
            return True
            
        except Exception as e:
            print(f"ブラウザ起動エラー: {e}")
            return False
    
    def stop(self):
        """ブラウザを停止"""
        try:
            # Cookieを保存
            self._save_cookies()
            
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            print(f"ブラウザ停止エラー: {e}")
    
    def _save_cookies(self):
        """Cookieを保存"""
        try:
            if self.context:
                cookies = self.context.cookies()
                cookie_file = self.user_data_dir / "cookies.json"
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cookie保存エラー: {e}")
    
    def _load_cookies(self):
        """Cookieを読み込み"""
        try:
            cookie_file = self.user_data_dir / "cookies.json"
            if cookie_file.exists():
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    if self.context and cookies:
                        self.context.add_cookies(cookies)
        except Exception as e:
            print(f"Cookie読み込みエラー: {e}")
    
    def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        URLに移動
        
        Args:
            url: 移動先URL
            wait_until: 待機条件（load/domcontentloaded/networkidle）
            
        Returns:
            成功したらTrue
        """
        try:
            if not self.page:
                print("エラー: ブラウザが起動していません")
                return False
            
            self.page.goto(url, wait_until=wait_until, timeout=30000)
            return True
            
        except Exception as e:
            print(f"ページ移動エラー: {e}")
            return False
    
    def screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        スクリーンショットを撮影
        
        Args:
            filename: ファイル名（指定しない場合は自動生成）
            
        Returns:
            保存したファイルパス（失敗時はNone）
        """
        try:
            if not self.page:
                print("エラー: ブラウザが起動していません")
                return None
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            filepath = self.screenshots_dir / filename
            self.page.screenshot(path=str(filepath), full_page=True)
            
            return str(filepath)
            
        except Exception as e:
            print(f"スクリーンショットエラー: {e}")
            return None
    
    def get_text(self, selector: str) -> Optional[str]:
        """
        要素のテキストを取得
        
        Args:
            selector: CSSセレクタ
            
        Returns:
            テキスト（失敗時はNone）
        """
        try:
            if not self.page:
                return None
            
            element = self.page.query_selector(selector)
            if element:
                return element.inner_text()
            return None
            
        except Exception as e:
            print(f"テキスト取得エラー: {e}")
            return None
    
    def click(self, selector: str) -> bool:
        """
        要素をクリック
        
        Args:
            selector: CSSセレクタ
            
        Returns:
            成功したらTrue
        """
        try:
            if not self.page:
                return False
            
            self.page.click(selector, timeout=10000)
            return True
            
        except Exception as e:
            print(f"クリックエラー: {e}")
            return False
    
    def fill(self, selector: str, text: str) -> bool:
        """
        フォームに入力
        
        Args:
            selector: CSSセレクタ
            text: 入力テキスト
            
        Returns:
            成功したらTrue
        """
        try:
            if not self.page:
                return False
            
            self.page.fill(selector, text, timeout=10000)
            return True
            
        except Exception as e:
            print(f"入力エラー: {e}")
            return False
    
    def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """
        要素が表示されるまで待機
        
        Args:
            selector: CSSセレクタ
            timeout: タイムアウト（ミリ秒）
            
        Returns:
            成功したらTrue
        """
        try:
            if not self.page:
                return False
            
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
            
        except Exception as e:
            print(f"待機エラー: {e}")
            return False
    
    def execute_script(self, script: str) -> Optional[any]:
        """
        JavaScriptを実行
        
        Args:
            script: JavaScriptコード
            
        Returns:
            実行結果（失敗時はNone）
        """
        try:
            if not self.page:
                return None
            
            return self.page.evaluate(script)
            
        except Exception as e:
            print(f"スクリプト実行エラー: {e}")
            return None
    
    def get_page_info(self) -> Dict:
        """
        現在のページ情報を取得
        
        Returns:
            ページ情報の辞書
        """
        try:
            if not self.page:
                return {}
            
            return {
                "url": self.page.url,
                "title": self.page.title(),
                "content": self.page.content()[:1000]  # 最初の1000文字
            }
            
        except Exception as e:
            print(f"ページ情報取得エラー: {e}")
            return {}
    
    def auto_login(self, site: str, credentials: Dict) -> bool:
        """
        自動ログイン
        
        Args:
            site: サイト名（twitter/github等）
            credentials: 認証情報（username/password等）
            
        Returns:
            成功したらTrue
        """
        # サイト別のログイン処理
        login_handlers = {
            "twitter": self._login_twitter,
            "github": self._login_github,
            # 他のサイトを追加可能
        }
        
        handler = login_handlers.get(site.lower())
        if not handler:
            print(f"エラー: {site}のログイン処理は未実装です")
            return False
        
        try:
            return handler(credentials)
        except Exception as e:
            print(f"自動ログインエラー: {e}")
            return False
    
    def _login_twitter(self, credentials: Dict) -> bool:
        """Twitter自動ログイン"""
        # 実装例（実際のセレクタは変更される可能性があります）
        self.navigate("https://twitter.com/login")
        self.wait_for_selector("input[name='text']")
        self.fill("input[name='text']", credentials.get("username", ""))
        self.click("button[type='submit']")
        self.wait_for_selector("input[name='password']")
        self.fill("input[name='password']", credentials.get("password", ""))
        self.click("button[type='submit']")
        return True
    
    def _login_github(self, credentials: Dict) -> bool:
        """GitHub自動ログイン"""
        self.navigate("https://github.com/login")
        self.wait_for_selector("input[name='login']")
        self.fill("input[name='login']", credentials.get("username", ""))
        self.fill("input[name='password']", credentials.get("password", ""))
        self.click("input[type='submit']")
        return True


# テスト用
if __name__ == "__main__":
    browser = BrowserController(headless=False)
    
    print("ブラウザを起動...")
    browser.start()
    
    print("Googleに移動...")
    browser.navigate("https://www.google.com")
    
    print("スクリーンショットを撮影...")
    screenshot_path = browser.screenshot()
    print(f"保存先: {screenshot_path}")
    
    print("ページ情報を取得...")
    info = browser.get_page_info()
    print(f"タイトル: {info.get('title')}")
    print(f"URL: {info.get('url')}")
    
    print("ブラウザを停止...")
    browser.stop()
    
    print("テスト完了")
