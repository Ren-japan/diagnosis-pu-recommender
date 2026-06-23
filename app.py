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

    # ── 出力カード（初見でも"この2つを使えばOK"が一目でわかる構成）──────
    st.divider()
    st.markdown("### ✅ この記事に設置するもの")
    st.caption("下の ① と ② を記事に設定すればOKです。")

    # ▼ カード① 推奨診断 ──────────────────────────────
    with st.container(border=True):
        st.markdown("**① 推奨診断**")
        st.markdown(
            f"<div style='font-size:2rem;font-weight:800;line-height:1.2;margin:2px 0 6px'>{rec['diagnosis_name']}</div>",
            unsafe_allow_html=True,
        )
        if rec.get("diagnosis_group_label"):
            st.caption(f"📌 {rec['diagnosis_group_label']}")
        if rec.get("diagnosis_seo_active") is False:
            st.caption("🆕 この診断はSEOでまだ未使用 → 新しく用意が必要です")

    # ▼ カード② 推奨PUバナー文言 ──────────────────────
    with st.container(border=True):
        st.markdown("**② 推奨PUバナー文言**")
        if rec["pu_status"] == "matched":
            st.caption("✅ 既にあるバナー文言です。そのまま使えます（右上の📋でコピー）")
            items = rec["pu_variants"]
        elif rec["pu_status"] == "template":
            st.caption("✏️ 下書きです。コピーして少しだけ整えてください（右上の📋でコピー）")
            items = rec["template_variants"]
        else:  # escalate
            items = []
            st.warning("🙋 これは自動で出せないケースです → **工藤さんに相談**")
        for v in items:
            st.code(v.get("copy", ""), language=None)
        if items:
            st.caption("↑ どれか1つを選んでバナーに使えばOK")

    # ▼ 詳細（専門用語はここに隠す。普段は見なくていい）──────────
    with st.expander("ℹ️ 判定の詳細を見る（くわしく知りたい人だけ）"):
        st.markdown(
            f"**検索意図：** {INTENT_BADGE.get(cls['intent'], cls['intent'])} — {cls['intent_reason']}"
        )
        st.markdown(
            f"**訴求軸：** {AXIS_BADGE.get(rec['axis'], rec['axis'])} — {cls['axis_reason']}"
        )
        st.markdown(f"**診断の選定根拠：** {rec['diagnosis_basis']}")
        st.caption(f"確信度 {cls.get('confidence','—')}／相性が合えば想定FCVR ×{rec['expected_fcvr_lift']}")
        if rec.get("all_diagnoses"):
            names = "・".join(d["name"] for d in rec["all_diagnoses"])
            st.caption(f"このジャンルの診断カタログ → {names}")
        if rec["pu_status"] == "template" and rec.get("all_pu_variants"):
            st.markdown(f"**参考：このジャンルの既存PU（他の軸）{len(rec['all_pu_variants'])}本**")
            for v in rec["all_pu_variants"]:
                st.markdown(f"- `{v.get('appeal_axis','?')}` 「{v.get('copy','')}」")

    # 注意・警告（あれば目立たせる）
    for w in rec["warnings"]:
        if w.startswith("⚠️"):
            st.warning(w)
        else:
            st.info(w)

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
