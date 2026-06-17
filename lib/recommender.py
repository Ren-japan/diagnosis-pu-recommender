"""
推薦エンジン。

分類結果（検索意図 + 訴求軸）と判定ルール（INTENT_MATCH_RULES）と
ジャンルの実績データ（article_mapping / pu_master）を突き合わせて、
「おすすめ診断タイプ ＋ 推奨PU訴求軸タグ ＋ 理由」を組み立てる。
"""

from __future__ import annotations

from lib.rules import (
    APPEAL_AXES,
    GENRES,
    INTENT_MATCH_RULES,
    genre_diagnosis_types,
    pu_diagnosis_name,
    pu_variants_by_axis,
)


def recommend(classification: dict, genre_label: str) -> dict:
    """
    分類結果とジャンルから推薦を組み立てる。

    Returns: {
      "diagnosis_type": 推奨診断タイプ,
      "diagnosis_basis": 推奨根拠,
      "axis": 推奨訴求軸キー(cost/choice/method),
      "axis_label": 訴求軸の説明,
      "warnings": [注意文...],
      "genre_types": ジャンルの実績診断タイプ,
      "pu_diagnosis_name": 既存PUの診断名 or None,
      "pu_variants": 推奨軸の既存PU文言リスト,
      "pu_inventory_note": 在庫に関する注記,
    }
    """
    intent = classification["intent"]
    axis = classification["axis"]
    cfg = GENRES.get(genre_label, {})
    mapping_key = cfg.get("mapping_key")
    pu_key = cfg.get("pu_key")

    rule = INTENT_MATCH_RULES[intent]
    preferred = rule["preferred"]
    mismatch = rule["mismatch"]
    exceptions = rule["genre_exceptions"]

    genre_types = genre_diagnosis_types(mapping_key)
    warnings: list[str] = []

    # ── 推奨診断タイプの決定 ────────────────────────────────
    # 例外判定は INTENT_MATCH_RULES の表記（article_mapping のジャンルキー）に合わせる。
    # 例: 例外リストは "ピル" だが、ドロップダウン表示名は "オンラインピル"。mapping_key で照合する。
    exception_key = mapping_key or genre_label
    diagnosis_type, basis = _decide_diagnosis_type(
        intent, exception_key, preferred, mismatch, exceptions, genre_types, warnings
    )

    # ── PU訴求軸まわり ──────────────────────────────────────
    variants_by_axis = pu_variants_by_axis(pu_key)
    pu_variants = variants_by_axis.get(axis, [])
    # 全PU文言（軸を問わず一覧表示用）。anxiety/benefitなど3軸外も隠さない
    all_variants = [v for vs in variants_by_axis.values() for v in vs]
    if not pu_key:
        pu_inventory_note = "このジャンルの既存PU在庫は未登録 → この訴求軸で新規作成を推奨"
    elif pu_variants:
        pu_inventory_note = f"既存PUあり：この訴求軸の文言が {len(pu_variants)} 本ストックされている"
    else:
        other = [a for a in variants_by_axis if variants_by_axis[a]]
        pu_inventory_note = (
            f"この訴求軸の既存PUは在庫なし（在庫がある軸：{', '.join(other) or 'なし'}）"
            " → この軸で新規作成を推奨"
        )

    return {
        "diagnosis_type": diagnosis_type,
        "diagnosis_basis": basis,
        "axis": axis,
        "axis_label": APPEAL_AXES.get(axis, axis),
        "warnings": warnings,
        "genre_types": genre_types,
        "pu_diagnosis_name": pu_diagnosis_name(pu_key),
        "pu_variants": pu_variants,
        "all_pu_variants": all_variants,
        "pu_inventory_note": pu_inventory_note,
        "expected_fcvr_lift": rule["expected_fcvr_lift"],
        "rule_reason": rule["reason"],
    }


def _decide_diagnosis_type(
    intent, genre_label, preferred, mismatch, exceptions, genre_types, warnings
) -> tuple[str, str]:
    """推奨診断タイプと根拠を決める。warnings には注意文を追記する（副作用）。"""

    # 指名: どの診断でもOK。ジャンル実績があればそれを優先
    if intent == "指名":
        if genre_types:
            return genre_types[0], f"指名KWはどの診断でもCV可。このジャンルの実績タイプ「{genre_types[0]}」を踏襲"
        return "（既存診断のいずれか）", "指名KWはどの診断タイプでもCVしやすい"

    # ジャンル実績と「相性の良いタイプ」の積集合を優先
    if genre_types:
        hit = [t for t in preferred if t in genre_types]
        if hit:
            return hit[0], f"検索意図「{intent}」× このジャンルの実績タイプの両方を満たす"

        # 相性の良いタイプの実績が無い → ミスマッチかどうか確認
        only_mismatch = [t for t in genre_types if t in mismatch]
        if only_mismatch:
            if genre_label in exceptions:
                return (
                    genre_types[0],
                    f"通常「{intent}」× {genre_types[0]} は飛躍があるが、{genre_label}は例外ジャンルなのでOK",
                )
            warnings.append(
                f"⚠️ ミスマッチ注意：このジャンルの実績タイプは「{', '.join(genre_types)}」だが、"
                f"検索意図「{intent}」とは相性が悪い（{', '.join(mismatch)}は飛躍がある）。"
                f"記事KWの検索意図を再確認するか、{', '.join(preferred)}系の診断設置を検討"
            )
            # 相性の良い側を推奨として出す
            return (preferred[0] if preferred else genre_types[0]), \
                f"検索意図「{intent}」には {', '.join(preferred)} が本来相性◎"

        # ミスマッチでもないが preferred とも一致しない
        return genre_types[0], f"このジャンルの実績タイプ「{genre_types[0]}」を踏襲"

    # ジャンル実績が無い（FAGA/AGA/ほくろ/いびき等）→ ルールのpreferredで推奨
    warnings.append(
        "ℹ️ このジャンルは記事→診断タイプの実績マッピングが未登録。"
        "検索意図ベースの推奨のみ（実績で補強できていない）"
    )
    if preferred:
        return preferred[0], f"検索意図「{intent}」に相性の良いタイプ（実績データなし）"
    return "（既存診断のいずれか）", f"検索意図「{intent}」はどのタイプでも可"
