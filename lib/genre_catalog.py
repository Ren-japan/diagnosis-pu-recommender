"""
ジャンル別 診断カタログ（ツールの土台＝唯一の真実）

renから直接確認した「各ジャンルに何の診断があるか」の正式カタログ。
article_mapping.csv（記事への設置実績）より優先する。
  - 例: ピルは article_mapping では「薬診断」だが、実際の診断は「選び方診断」（ren修正）

各診断の group は3グループに正規化（INTENT_MATCH_RULES と接続するため）:
  - 方法診断 : 方法診断 / 薄毛方法対策診断 / いびきタイプ診断
  - 薬診断   : 薬診断
  - 集客診断 : 集客診断 / クリニック診断 / 選び方診断（全部「選択軸の診断」で1グループ）

seo_active=False は「診断としては存在するがSEO記事ではまだ未使用」。
"""

from __future__ import annotations

# 表示名 → 正規化グループ（INTENT_MATCH_RULES のキーに合わせる）
DIAGNOSIS_GROUP = {
    "方法診断": "方法診断",
    "薄毛方法対策診断": "方法診断",
    "いびきタイプ診断": "方法診断",
    "薬診断": "薬診断",
    "集客診断": "集客診断",
    "クリニック診断": "集客診断",
    "選び方診断": "集客診断",
}

# グループの説明（UI表示用）
GROUP_LABEL = {
    "方法診断": "方法系（自分に合うやり方を出す）",
    "薬診断": "薬系（商品・薬の比較／商標KW向き）",
    "集客診断": "選択系（クリニック・商品の選び方を出す）",
}


def _dx(name: str, seo_active: bool = True) -> dict:
    """診断1件を作る（グループは表示名から自動判定）"""
    return {"name": name, "group": DIAGNOSIS_GROUP[name], "seo_active": seo_active}


# ジャンル → 持っている診断のリスト（renカタログ）
GENRE_CATALOG: dict[str, list[dict]] = {
    "医療ダイエット(GLP-1)": [
        _dx("方法診断"),
        _dx("薬診断"),
        _dx("クリニック診断", seo_active=False),  # SEOではまだ未使用
    ],
    "包茎手術": [
        _dx("集客診断"),  # ＝包茎治し方診断
    ],
    "ED": [
        _dx("薬診断"),
    ],
    "オンラインピル": [
        _dx("選び方診断"),  # ※薬診断ではない（ren修正）
    ],
    "AGA": [
        _dx("クリニック診断"),
        _dx("薬診断"),
        _dx("薄毛方法対策診断"),
    ],
    "FAGA": [
        _dx("クリニック診断"),
    ],
    "ほくろ除去": [
        _dx("クリニック診断"),
    ],
    "いびき": [
        _dx("いびきタイプ診断"),
    ],
    "リカバリーウェア": [
        _dx("方法診断"),
    ],
}


# 各ジャンルの既存PU在庫(pu_master)が「どの診断グループのPUか」。
# 例: ダイエットの離脱PU在庫はすべて「ダイエット方法診断」のもの＝方法系。
#     なので薬診断・クリニック診断の記事には流用しない（診断とPUのミスマッチ防止）。
STOCK_DIAGNOSIS_GROUP = {
    "医療ダイエット(GLP-1)": "方法診断",
    "包茎手術": "集客診断",
    "AGA": "集客診断",  # AGAクリニック診断のPU
}


def diagnoses_for(genre_label: str) -> list[dict]:
    """指定ジャンルの診断リストを返す（未登録なら空）"""
    return GENRE_CATALOG.get(genre_label, [])


def stock_group_for(genre_label: str) -> str | None:
    """ジャンルの既存PU在庫が属する診断グループ（無ければNone）"""
    return STOCK_DIAGNOSIS_GROUP.get(genre_label)
