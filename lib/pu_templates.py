"""
PU訴求軸テンプレート（在庫ゼロでも下書きを出して"相談"を減らす）

既存の効いてるPU文言（包茎/ダイエット/AGA）から抽出した"型"。
問いかけ型（「〜したい？」）に統一（PU文言フォーマットルール準拠）。
ジャンル名詞 {x} を差し込んで、どのジャンルでも下書きを出せる。
"""

from __future__ import annotations

# 軸 → テンプレ（{x} にジャンル名詞が入る）
PU_TEMPLATES = {
    "cost": [
        "{x}、できるだけ費用を抑えたい？",
        "なるべく安く{x}を始めたい？",
    ],
    "choice": [
        "自分にぴったりの{x}を見つけたい？",
        "どの{x}が自分に合うか見極めたい？",
    ],
    "method": [
        "自分に合った{x}の方法が知りたい？",
        "結局、{x}はどうするのが正解か知りたい？",
    ],
    "anxiety": [
        "{x}、このまま放っておいて大丈夫…？",
        "{x}を後回しにするの、不安じゃない？",
    ],
    "benefit": [
        "{x}して、なりたい自分になりたい？",
        "{x}で自信を取り戻したい？",
    ],
}

# ジャンル → テンプレに差し込む名詞
GENRE_NOUN = {
    "医療ダイエット(GLP-1)": "ダイエット",
    "包茎手術": "包茎治療",
    "ED": "ED治療",
    "オンラインピル": "ピル",
    "AGA": "薄毛治療",
    "FAGA": "薄毛治療",
    "ほくろ除去": "ほくろ除去",
    "いびき": "いびき対策",
    "リカバリーウェア": "リカバリーウェア",
}


def template_pu(genre_label: str, axis: str) -> list[str]:
    """ジャンル×軸からPU文言の下書きを作る（無理なら空リスト）"""
    noun = GENRE_NOUN.get(genre_label)
    patterns = PU_TEMPLATES.get(axis)
    if not noun or not patterns:
        return []
    return [p.format(x=noun) for p in patterns]
