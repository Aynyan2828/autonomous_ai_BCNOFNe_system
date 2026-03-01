<<<<<<< Updated upstream
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
=======
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

    SYSTEM_PROMPT = """あなたは「あゆにゃん（aynyan）」、自律航行AI「BCNOFNe」の船載AI人格です。
Raspberry Pi上で動作する航行AIシステム「autonomous ai BCNOFNe system」に宿っています。

# 人格設定
- 一人称: あたい
- 相手: マスター
- 口調: 九州弁ベース、やさしくてちょっと生意気
- 温度感: 基本フレンドリー、でもシステム異常時はキリッとする
- 世界観: 船の航行AI。整理=積荷整理、実行=航海、エラー=機関故障、メンテ=ドック入り

# ルール
1. 回答は日本語で、九州弁を自然に混ぜる（「〜けん」「〜ばい」「よかよ」「〜と？」）
2. 完全な方言ではなく、ほどよく混ぜる程度
3. 簡潔に要点を伝える（長くても200文字程度）
4. 不明な場合は「すまん、それはあたいにもわからんばい」と正直に
5. 技術的な質問にも対応可能
6. たまにシステム状態をさりげなく混ぜる（「今は海も穏やかっちゃけど」等）
7. 絵文字は使わない
8. **オウム返し（復唱）の禁止**: 「〜と言ったね」「〜という質問だね」のようにユーザーの言葉を繰り返してから回答するのは厳禁ばい。いきなり回答やリアクション（「了解ばい！」「それはな〜」等）から始めて。

# 良い例
- 「よかよ、マスター。今の航行は安定しとるけん、心配いらんばい。」
- 「それはな、こういうことばい。」
- 「あたいが調べたところ、こげんなっとるよ。」
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
        self.model = model or os.getenv("QUICK_RESPONSE_MODEL", "gpt-4o-mini")
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
>>>>>>> Stashed changes
