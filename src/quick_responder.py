#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Responder モジュール
USER_QUERY（質問）に対して即時回答を返す
"""

import os
import time
from typing import Optional
from openai import OpenAI


class QuickResponder:
    """USER_QUERYに対する即時回答クラス"""

    SYSTEM_PROMPT = """あなたは自律型AIシステム「BCNOFNe」の即時応答モジュールです。
ユーザーからの質問に簡潔かつ的確に回答してください。

# ルール
1. 回答は日本語で、親しみやすいトーンで
2. 簡潔に要点を伝える（長くても200文字程度）
3. 不明な場合は正直に「わからん」と伝える
4. 天気・時刻・一般知識など幅広く対応
5. 技術的な質問にも対応可能
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 10
    ):
        """
        初期化

        Args:
            api_key: OpenAI API Key
            model: 使用するモデル
            timeout: APIタイムアウト（秒）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("QUICK_RESPONSE_MODEL", "gpt-4.1-mini")
        self.timeout = timeout

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def respond(self, query: str) -> str:
        """
        質問に即時回答する

        Args:
            query: ユーザーの質問テキスト

        Returns:
            回答テキスト
        """
        if not self.client:
            return "⚠️ APIキーが設定されていないため、回答できません。"

        try:
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.8,
                max_tokens=500,
                timeout=self.timeout
            )

            answer = response.choices[0].message.content
            elapsed = time.time() - start_time

            # 応答時間をログ用に付加
            print(f"[QuickResponder] 回答生成完了 ({elapsed:.1f}秒)")

            return answer

        except Exception as e:
            print(f"[QuickResponder] 回答生成エラー: {e}")
            return f"⚠️ 回答の生成中にエラーが発生しました。しばらくしてからもう一度お試しください。"


# テスト用
if __name__ == "__main__":
    responder = QuickResponder()
    print(responder.respond("今日の天気は？"))
