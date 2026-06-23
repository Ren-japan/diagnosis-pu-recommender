"""
推薦エンジン（診断カタログ駆動）。

分類結果（検索意図 + 訴求軸）と、
ジャンル別診断カタログ（genre_catalog.GENRE_CATALOG）と、
検索意図ルール（INTENT_MATCH_RULES）を突き合わせて、
「このジャンルで設置すべき実際の診断名 ＋ 推奨PU訴求軸 ＋ 理由」を出す。
"""

from __future__ import annotations

from lib.genre_catalog import GROUP_LABEL, diagnoses_for
from lib.rules import (
    APPEAL_AXES,
    GENRES,
    INTENT_MATCH_RULES,
    pu_variants_by_axis,
)


def _prefer_active(diagnoses: list[dict]) -> dict:
    """SEO稼働中の診断を優先して1件返す（無ければ先頭）"""
    active = [d for d in diagnoses if d.get("seo_active")]
    return active[0] if active else diagnoses[0]


def _is_exception(genre_label: str, exceptions: list[str]) -> bool:
    """ジャンルが例外指定に該当するか（"ピル" は "オンラインピル" にも一致させる）"""
    return any(e in genre_label for e in exceptions)


def _choose_diagnosis(intent, genre_label, diagnoses, rule, warnings) -> tuple[dict | None, str]:
    """設置すべき診断を1件選ぶ。warnings に注意文を追記（副作用）。"""
    if not diagnoses:
        warnings.append("ℹ️ このジャンルは診断カタログ未登録。検索意図ベースの一般推奨のみ")
        return None, "カタログ未登録"

    preferred = rule["preferred"]
    mismatch = rule["mismatch"]
    exceptions = rule["genre_exceptions"]

    # 指名: どの診断でもCV可。稼働中を優先
    if intent == "指名":
        d = _prefer_active(diagnoses)
        return d, f"指名KWはどの診断でもCV可。このジャンルの診断「{d['name']}」を設置"

    # 検索意図に相性の良いグループの診断があればそれ
    matches = [d for d in diagnoses if d["group"] in preferred]
    if matches:
        d = _prefer_active(matches)
        note = "" if d.get("seo_active") else "（※SEO未使用＝新規設置になる）"
        return d, f"検索意図「{intent}」に相性◎の{d['group']}系 → 「{d['name']}」{note}"

    # 相性グループの診断が無い → 手持ちから選ぶ
    d = _prefer_active(diagnoses)
    if d["group"] in mismatch:
        if _is_exception(genre_label, exceptions):
            return d, f"通常「{intent}」×{d['group']}系は飛躍があるが、{genre_label}は例外なのでOK → 「{d['name']}」"
        warnings.append(
            f"⚠️ ミスマッチ注意：この記事は「{intent}」だが、{genre_label}の手持ちは"
            f"{d['group']}系の「{d['name']}」のみ。検索意図を再確認するか、"
            f"{ '・'.join(preferred) }系の診断を新設するか検討"
        )
        return d, f"このジャンルの手持ちは「{d['name']}」のみ（本来「{intent}」には{'・'.join(preferred)}系が相性◎）"

    return d, f"このジャンルの診断「{d['name']}」を設置"


def recommend(classification: dict, genre_label: str) -> dict:
    intent = classification["intent"]
    axis = classification["axis"]
    rule = INTENT_MATCH_RULES[intent]
    diagnoses = diagnoses_for(genre_label)
    warnings: list[str] = []

    chosen, basis = _choose_diagnosis(intent, genre_label, diagnoses, rule, warnings)

    # ── PU訴求軸まわり（既存からマッチング。基本"作れ"とは言わない）─────
    # pu_status: matched=推奨軸に既存あり / closest=他軸の既存から流用 / escalate=在庫ゼロ→工藤相談
    pu_key = GENRES.get(genre_label, {}).get("pu_key")
    variants_by_axis = pu_variants_by_axis(pu_key)
    pu_variants = variants_by_axis.get(axis, [])
    all_variants = [v for vs in variants_by_axis.values() for v in vs]
    if pu_variants:
        pu_status = "matched"
        pu_inventory_note = f"この訴求軸の既存PU文言が {len(pu_variants)} 本。これを使う"
    elif all_variants:
        pu_status = "closest"
        pu_inventory_note = "この軸ピッタリの既存PUは無いが、下の既存PUから一番近いものを流用する"
    else:
        pu_status = "escalate"
        pu_inventory_note = "このジャンルはPU在庫が空 → 工藤さんに相談"

    return {
        "diagnosis_name": chosen["name"] if chosen else "（カタログ未登録）",
        "diagnosis_group": chosen["group"] if chosen else None,
        "diagnosis_group_label": GROUP_LABEL.get(chosen["group"], "") if chosen else "",
        "diagnosis_seo_active": chosen.get("seo_active") if chosen else None,
        "diagnosis_basis": basis,
        "all_diagnoses": diagnoses,
        "axis": axis,
        "axis_label": APPEAL_AXES.get(axis, axis),
        "warnings": warnings,
        "pu_variants": pu_variants,
        "all_pu_variants": all_variants,
        "pu_status": pu_status,
        "pu_inventory_note": pu_inventory_note,
        "expected_fcvr_lift": rule["expected_fcvr_lift"],
        "rule_reason": rule["reason"],
    }
