"""
診断PU推薦ツール

記事本文を貼ってジャンルを選ぶと、相性の良い「診断タイプ」と「PU訴求軸」を吐き出す。
新記事に何のPUを設置すべきかを即答する運用ツール。

ローカル起動: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from lib.classifier import classify, get_api_key
from lib.recommender import recommend
from lib.rules import GENRES

st.set_page_config(page_title="診断PU推薦ツール", page_icon="🎯", layout="centered")

AXIS_BADGE = {
    "cost": "💰 cost（費用軸）",
    "choice": "🔍 choice（選択軸）",
    "method": "🧭 method（方法軸）",
}
INTENT_BADGE = {
    "悩み": "😣 悩み",
    "商標": "🏷️ 商標",
    "指名": "📌 指名",
}

st.title("🎯 診断PU推薦ツール")
st.caption(
    "記事本文を貼ってジャンルを選ぶと、相性の良い**診断タイプ**と**PU訴求軸タグ**を出します。"
    "新記事にどのPUを設置するか迷ったらこれ。"
)

# ── 入力 ────────────────────────────────────────────────
genre = st.selectbox("ジャンルを選択", list(GENRES.keys()))
article = st.text_area(
    "記事本文を貼り付け",
    height=280,
    placeholder="記事のタイトル＋本文をそのまま貼ってください（見出しだけでもOK）",
)

run = st.button("🔎 推奨を取得", type="primary", use_container_width=True)

# APIキー未設定の警告（起動時に気づけるように）
if not get_api_key():
    st.warning(
        "GEMINI_API_KEY が未設定です。`.streamlit/secrets.toml` か環境変数に設定してください。",
        icon="⚠️",
    )

# ── 実行 ────────────────────────────────────────────────
if run:
    if not article.strip():
        st.error("記事本文を貼ってください。")
        st.stop()

    with st.spinner("記事を読んで判定中…"):
        try:
            cls = classify(article, genre)
        except Exception as e:  # noqa: BLE001  分類失敗はそのままユーザーに見せる
            st.error(f"判定に失敗しました: {e}")
            st.stop()
        rec = recommend(cls, genre)

    # ── 出力カード ──────────────────────────────────────
    st.divider()
    st.subheader(f"おすすめ診断：{rec['diagnosis_type']}")
    if rec.get("pu_diagnosis_name"):
        st.caption(f"既存診断名：{rec['pu_diagnosis_name']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("検索意図", INTENT_BADGE.get(cls["intent"], cls["intent"]))
    col2.metric("推奨PU訴求軸", AXIS_BADGE.get(rec["axis"], rec["axis"]))
    col3.metric("確信度", cls.get("confidence", "—"))

    st.markdown(f"**診断タイプの根拠：** {rec['diagnosis_basis']}")
    st.markdown(f"**検索意図の判定理由：** {cls['intent_reason']}")
    st.markdown(f"**訴求軸の判定理由：** {cls['axis_reason']}")
    st.markdown(f"**訴求軸の意味：** {rec['axis_label']}")
    st.caption(f"💡 {rec['rule_reason']}（相性が合えば想定FCVR ×{rec['expected_fcvr_lift']}）")

    # 注意・警告
    for w in rec["warnings"]:
        if w.startswith("⚠️"):
            st.warning(w)
        else:
            st.info(w)

    # PU在庫の状況
    st.divider()
    st.markdown("#### 📌 PU訴求軸タグと在庫")
    st.write(rec["pu_inventory_note"])
    if rec["pu_variants"]:
        st.markdown("**この訴求軸で使える既存PU文言：**")
        for v in rec["pu_variants"]:
            line = f"- 「{v.get('copy', '')}」"
            if v.get("file"):
                line += f"  `{v['file']}`"
            st.markdown(line)

    # ジャンルの実績タイプ（参考）
    if rec["genre_types"]:
        st.caption(f"参考：このジャンルで実際に使われている診断タイプ → {', '.join(rec['genre_types'])}")

    with st.expander("判定の生データ（デバッグ用）"):
        st.json({"classification": cls, "recommendation": rec})
