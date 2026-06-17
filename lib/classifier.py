"""
記事本文の分類器（Gemini）。

記事本文を読んで2軸を判定する:
  1. 検索意図   : 悩み / 商標 / 指名
  2. 訴求の重心 : cost(費用) / choice(選択) / method(方法)

line-image-generator と同じく google-genai（gemini-2.5-flash）を使う。
APIキーは os.getenv → st.secrets の順で取得（Cloud/ローカル両対応）。
"""

from __future__ import annotations

import json
import os
import re

MODEL = "gemini-2.5-flash"


def get_api_key() -> str | None:
    """環境変数 or st.secrets から GEMINI_API_KEY を取得（Cloud/ローカル両対応）"""
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return None


CLASSIFY_PROMPT = """あなたはLINE友だち獲得の診断設計者です。
以下の記事本文を読んで、この記事に訪れた検索ユーザーの「検索意図」と「訴求の重心」を判定してください。

== 判定軸1: 検索意図（必ず1つ） ==
- 悩み : 問題を認識して解決方法を探している段階。「痩せたい」「治したい」など。商品はまだ知らない
- 商標 : 特定の商品・薬・サービス名を認知済みで調べている。「マンジャロ 通販」「リベルサス 副作用」など固有名詞ベース
- 指名 : クリニック名・ブランド名など特定の指名検索。「〇〇クリニック 評判」など

== 判定軸2: 訴求の重心（必ず1つ） ==
- cost   : 記事が費用・料金・相場・安さに重点を置いている
- choice : 記事がクリニック/商品の選び方・比較・見極めに重点を置いている
- method : 記事が方法・やり方・自分に合うやり方に重点を置いている

== ジャンル ==
{genre}

== 記事本文 ==
{article}

== 出力形式（JSONのみ。前後に説明文をつけない） ==
{{
  "intent": "悩み" or "商標" or "指名",
  "intent_reason": "そう判断した根拠を本文の語に触れて1文で",
  "axis": "cost" or "choice" or "method",
  "axis_reason": "そう判断した根拠を本文の語に触れて1文で",
  "confidence": "高" or "中" or "低"
}}"""


def _parse_json(text: str) -> dict:
    """Geminiの応答からJSONを抽出してパースする（コードフェンス除去対応）"""
    cleaned = text.strip()
    # ```json ... ``` のコードフェンスを除去
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    # 最初の { から最後の } までを抜く（前後にゴミがあっても拾える）
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(0)
    return json.loads(cleaned)


def classify(article: str, genre: str, api_key: str | None = None) -> dict:
    """
    記事本文を分類して {intent, intent_reason, axis, axis_reason, confidence} を返す。
    APIキー未設定や応答異常時は ValueError を投げる。
    """
    key = api_key or get_api_key()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。"
            ".streamlit/secrets.toml か環境変数に設定してください。"
        )

    from google import genai  # 遅延import（キー未設定でも起動できるように）

    client = genai.Client(api_key=key)
    prompt = CLASSIFY_PROMPT.format(genre=genre, article=article.strip())
    resp = client.models.generate_content(model=MODEL, contents=prompt)
    result = _parse_json(resp.text)

    # 最低限のバリデーション（想定外の値が来たら気づけるように）
    if result.get("intent") not in ("悩み", "商標", "指名"):
        raise ValueError(f"検索意図の判定結果が不正です: {result.get('intent')}")
    if result.get("axis") not in ("cost", "choice", "method"):
        raise ValueError(f"訴求軸の判定結果が不正です: {result.get('axis')}")
    return result
