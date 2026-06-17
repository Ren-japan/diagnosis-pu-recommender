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

    # ▼ ヒーロー① 設置する診断（実物の診断名を最優先で大きく。無ければタイプ）
    has_existing = bool(rec.get("pu_diagnosis_name"))
    install_name = rec["pu_diagnosis_name"] if has_existing else f"{rec['diagnosis_type']}（新規作成）"
    st.markdown("##### 🎯 設置する診断")
    st.markdown(
        f"<div style='font-size:2rem;font-weight:800;line-height:1.2;margin:-4px 0 8px'>{install_name}</div>",
        unsafe_allow_html=True,
    )
    # 補助タグ（診断名と競合しないよう「相性タイプ」として格下げ表示）
    st.markdown(
        f"`検索意図: {INTENT_BADGE.get(cls['intent'], cls['intent'])}` &nbsp; "
        f"`相性タイプ: {rec['diagnosis_type']}` &nbsp; "
        f"`確信度: {cls.get('confidence','—')}`",
        unsafe_allow_html=True,
    )

    # ▼ ヒーロー② 出すPU文言（コピーボタン付きで目立たせる）
    st.markdown("##### 💬 この記事に出すPU文言")
    st.markdown(
        f"推奨訴求軸：**{AXIS_BADGE.get(rec['axis'], rec['axis'])}** — {rec['axis_label']}"
    )
    if rec["pu_variants"]:
        st.caption("↓ この訴求軸の既存文言。右上のアイコンでコピーできる")
        for v in rec["pu_variants"]:
            st.code(v.get("copy", ""), language=None)
    elif rec.get("all_pu_variants"):
        st.warning(
            f"この訴求軸（{rec['axis']}）の既存PUは無し。"
            "下の「既存PU文言一覧」から近い軸を流用するか、この軸で新規作成。"
        )
    else:
        st.info(f"このジャンルは既存PU未登録 → 上の訴求軸で新規作成を推奨")

    # 判定理由（折りたたみ。普段は結論だけ見たいので隠す）
    with st.expander("なぜこの判定？（根拠を見る）"):
        st.markdown(f"**検索意図の理由：** {cls['intent_reason']}")
        st.markdown(f"**訴求軸の理由：** {cls['axis_reason']}")
        st.markdown(f"**診断タイプの根拠：** {rec['diagnosis_basis']}")
        st.caption(f"💡 {rec['rule_reason']}（相性が合えば想定FCVR ×{rec['expected_fcvr_lift']}）")
        if rec["genre_types"]:
            st.caption(f"このジャンルの実績診断タイプ → {', '.join(rec['genre_types'])}")

    # 注意・警告（あれば目立たせる）
    for w in rec["warnings"]:
        if w.startswith("⚠️"):
            st.warning(w)
        else:
            st.info(w)

    # このジャンルの全PU文言（軸を問わず。anxiety/benefitなど3軸外も見せる）
    if rec.get("all_pu_variants"):
        with st.expander(f"このジャンルの既存PU文言 全{len(rec['all_pu_variants'])}本を見る"):
            for v in rec["all_pu_variants"]:
                st.markdown(f"- `{v.get('appeal_axis','?')}` 「{v.get('copy','')}」")
