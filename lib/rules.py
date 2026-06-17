"""
判定ルールとマスターデータのローダー。

このツールの「脳ミソ」の定義部分。
- INTENT_MATCH_RULES: 検索意図 → 相性の良い診断タイプ（line-dashboard/lib/constants.py から移植）
- APPEAL_AXES: PU訴求軸の定義（pu_master.json の common_structure から移植）
- GENRES: 管轄9ジャンルの設定（ジャンル名 → article_mapping / pu_master のキー対応）
- load_*(): 同梱データ（article_mapping.csv / pu_master.json）の読み込み
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ── 検索意図 × 診断タイプのミスマッチルール ─────────────────────
# line-dashboard/lib/constants.py の INTENT_MATCH_RULES と同一。
# 検索意図（悩み/商標/指名）に対して、相性の良い診断タイプ・悪い診断タイプを定義。
INTENT_MATCH_RULES = {
    "悩み": {
        "preferred": ["方法診断", "集客診断"],
        "mismatch": ["薬診断"],
        "genre_exceptions": ["ED", "ピル"],  # このジャンルは悩みKWでも薬診断でOK
        "expected_fcvr_lift": 1.5,
        "reason": "悩みKWのユーザーは問題認識段階。薬診断は商品比較前提のため飛躍がある。",
    },
    "商標": {
        "preferred": ["薬診断"],
        "mismatch": ["方法診断"],
        "genre_exceptions": [],
        "expected_fcvr_lift": 1.3,
        "reason": "商標KWのユーザーは特定商品を認知済み。方法診断は検索意図より一歩後退。",
    },
    "指名": {
        "preferred": [],
        "mismatch": [],
        "genre_exceptions": [],
        "expected_fcvr_lift": 1.0,
        "reason": "指名KWはどの診断タイプでもCVしやすい。",
    },
}


# ── PU訴求軸の定義 ──────────────────────────────────────────
# pu_master.json の common_structure.appeal_axes と同一。
APPEAL_AXES = {
    "cost": "費用軸：安くしたい/費用を抑えたい → 金銭的不安に訴求",
    "choice": "選択軸：ぴったりのを見つけたい/見極めたい → 選択不安に訴求",
    "method": "方法軸：自分に合った方法を知りたい → 情報不足に訴求",
}


# ── 管轄9ジャンルの設定 ───────────────────────────────────────
# label        : ドロップダウン表示名
# mapping_key  : article_mapping.csv のジャンル列の値（None=実績マッピング未登録）
# pu_key       : pu_master.json の genres キー（None=既存PU在庫なし）
GENRES = {
    "医療ダイエット(GLP-1)": {"mapping_key": "医療ダイエット", "pu_key": None},
    "包茎手術": {"mapping_key": "包茎", "pu_key": None},
    "ED": {"mapping_key": "ED", "pu_key": None},
    "FAGA": {"mapping_key": None, "pu_key": None},
    "AGA": {"mapping_key": None, "pu_key": "AGA"},
    "オンラインピル": {"mapping_key": "ピル", "pu_key": None},
    "ほくろ除去": {"mapping_key": None, "pu_key": None},
    "いびき": {"mapping_key": None, "pu_key": None},
    "リカバリーウェア": {"mapping_key": "リカバリーウェア", "pu_key": None},
}


def load_article_mapping() -> list[dict]:
    """article_mapping.csv を読み込む（記事→診断タイプ/KWタイプの実績データ）"""
    path = DATA_DIR / "article_mapping.csv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_pu_master() -> dict:
    """pu_master.json を読み込む（ジャンル別の既存PUクリエイティブ在庫）"""
    path = DATA_DIR / "pu_master.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def genre_diagnosis_types(mapping_key: str | None) -> list[str]:
    """
    指定ジャンルで実際に使われている診断タイプを article_mapping から集計する。
    実績が無い（mapping_key=None or 該当行なし）場合は空リストを返す。
    """
    if not mapping_key:
        return []
    rows = load_article_mapping()
    types: list[str] = []
    for r in rows:
        if r.get("ジャンル") == mapping_key:
            dt = (r.get("診断タイプ") or "").strip()
            if dt and dt not in types:
                types.append(dt)
    return types


def pu_variants_by_axis(pu_key: str | None) -> dict[str, list[dict]]:
    """
    指定ジャンルの既存PU文言を訴求軸(cost/choice/method)別にまとめる。
    在庫が無い場合は空dictを返す。
    """
    if not pu_key:
        return {}
    master = load_pu_master()
    genre = master.get("genres", {}).get(pu_key)
    if not genre:
        return {}
    out: dict[str, list[dict]] = {}
    for v in genre.get("variants", []):
        axis = v.get("appeal_axis", "unknown")
        out.setdefault(axis, []).append(v)
    return out


def pu_diagnosis_name(pu_key: str | None) -> str | None:
    """既存PU在庫から診断名を取得（あれば）"""
    if not pu_key:
        return None
    master = load_pu_master()
    genre = master.get("genres", {}).get(pu_key)
    return genre.get("diagnosis_name") if genre else None
