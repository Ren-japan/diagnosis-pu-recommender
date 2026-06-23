"""
診断PU推薦ツール

記事本文を貼ってジャンルを選ぶと、相性の良い「診断タイプ」と「PU訴求軸」を吐き出す。
新記事に何のPUを設置すべきかを即答する運用ツール。

ローカル起動: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from lib.classifier import classify, get_api_key
from lib.genre_catalog import GENRE_CATALOG
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
    "記事本文を貼ってジャンルを選ぶと、**既存の診断・PUの中から一番マッチするもの**を出します。"
    "どうしても既存に無いものだけ「工藤さんに相談」。"
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

    # ▼ ヒーロー① 設置する診断（カタログ上の実際の診断名）
    st.markdown("##### 🎯 設置する診断")
    st.markdown(
        f"<div style='font-size:2rem;font-weight:800;line-height:1.2;margin:-4px 0 8px'>{rec['diagnosis_name']}</div>",
        unsafe_allow_html=True,
    )
    tags = [f"`検索意図: {INTENT_BADGE.get(cls['intent'], cls['intent'])}`"]
    if rec.get("diagnosis_group"):
        tags.append(f"`{rec['diagnosis_group']}系`")
    tags.append(f"`確信度: {cls.get('confidence','—')}`")
    st.markdown(" &nbsp; ".join(tags), unsafe_allow_html=True)
    if rec.get("diagnosis_seo_active") is False:
        st.caption("🆕 この診断はSEOではまだ未使用 → 新規設置になる")

    # ▼ ヒーロー② 出すPU文言（コピーボタン付きで目立たせる）
    st.markdown("##### 💬 この記事に出すPU文言")
    st.markdown(
        f"推奨訴求軸：**{AXIS_BADGE.get(rec['axis'], rec['axis'])}** — {rec['axis_label']}"
    )
    if rec["pu_status"] == "matched":
        st.caption("↓ この訴求軸の既存文言。右上のアイコンでコピーして使う")
        for v in rec["pu_variants"]:
            st.code(v.get("copy", ""), language=None)
    elif rec["pu_status"] == "closest":
        st.caption("この軸ピッタリは無いが、このジャンルの既存PUから近いものを流用 ↓")
        for v in rec["all_pu_variants"]:
            st.code(v.get("copy", ""), language=None)
    else:  # escalate
        st.warning("🙋 このジャンルは既存PUの在庫が無い → **工藤さんに相談**（新規で作るか判断を仰ぐ）")

    # 判定理由（折りたたみ。普段は結論だけ見たいので隠す）
    with st.expander("なぜこの判定？（根拠を見る）"):
        st.markdown(f"**検索意図の理由：** {cls['intent_reason']}")
        st.markdown(f"**訴求軸の理由：** {cls['axis_reason']}")
        st.markdown(f"**診断の選定根拠：** {rec['diagnosis_basis']}")
        st.caption(f"💡 {rec['rule_reason']}（相性が合えば想定FCVR ×{rec['expected_fcvr_lift']}）")
        if rec.get("all_diagnoses"):
            names = "・".join(d["name"] for d in rec["all_diagnoses"])
            st.caption(f"このジャンルの診断カタログ → {names}")

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

# ── ジャンル別 診断カタログ（いつでも見れる）──────────────────
st.divider()
with st.expander("📚 ジャンル別 診断カタログを見る（全9ジャンル）"):
    st.caption(
        "各ジャンルに今ある診断の一覧。"
        "グループ：方法系 / 薬系 / 選択系（集客・クリニック・選び方は選択系で1グループ）"
    )
    for label, dxs in GENRE_CATALOG.items():
        st.markdown(f"**{label}** … {len(dxs)}種")
        for d in dxs:
            suffix = "" if d.get("seo_active") else "・SEO未使用"
            st.markdown(f"- {d['name']}（{d['group']}系{suffix}）")
