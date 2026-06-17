"""
PU在庫インポーター

LINE離脱防止ツール（Winut）からエクスポートした「離脱防止タグ情報」CSVを読んで、
各ジャンルの実PU文言を抽出し pu_master.json にマージする。

- CSVはShift-JIS(cp932)。離脱防止タグ列に `/{パス}/{記事slug}_{PU文言}` の形でPU文言が入っている
- 同じPU文言は記事をまたいで重複するのでテキストで重複排除する
- PU文言は**そのまま（verbatim）**保存する。捏造・要約はしない
- 訴求軸はキーワードでベストエフォート分類（cost/choice/method/anxiety/benefit/other）

使い方:
    python3 tools/import_pu_inventory.py
    → data/raw_exports/*.csv を全部読んで data/pu_master.json を更新

新しいジャンルを足すとき:
    そのジャンルの「離脱防止タグ情報」CSVを data/raw_exports/ に置いて再実行するだけ。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw_exports"
PU_MASTER = ROOT / "data" / "pu_master.json"

# 離脱防止タグのパス接頭辞 → ジャンル名（pu_master / GENRES の pu_key に対応）
PATH_TO_GENRE = [
    ("/seo_phimo/", "包茎"),
    ("/glp1", "医療ダイエット"),
    ("/diet", "医療ダイエット"),
    ("/seo_ed/", "ED"),
    ("/seo_faga", "FAGA"),
    ("/seo_aga", "AGA"),
    ("/pill_seo", "オンラインピル"),
    ("/hokuro", "ほくろ除去"),
    ("/seo_ibiki", "いびき"),
    ("/mypics", "リカバリーウェア"),
    ("/seo_mypicsc_rw", "リカバリーウェア"),
]

# 訴求軸のキーワード辞書（上から順に判定。最初に当たった軸を採用）
AXIS_KEYWORDS = [
    ("cost", ["費用", "安く", "安い", "料金", "高く", "お得", "コスパ"]),
    ("method", ["治し方", "方法", "やり方", "合った", "合う"]),
    ("anxiety", ["不安", "放置", "放っておいて", "このまま", "気になる", "必要度", "いいのか"]),
    ("benefit", ["自信", "夜の", "モテ", "変わりたい", "見られても"]),
    ("choice", ["見極め", "どこ", "ぴったり", "選び", "わからない", "タイプ", "見つける", "比較"]),
]

JP_RE = re.compile(r"[ぁ-んァ-ヶ一-龯].*")

# 既知の診断名（実物のPU画像・設計書から確認済み）
DIAGNOSIS_NAMES = {
    "包茎": "包茎治し方診断",
    "医療ダイエット": "ダイエット方法診断",
}

# CSVが無い（画像で文言を確認した）ジャンルのシード。捏造ではなく実物PU画像から書き起こし。
MANUAL_SEED = {
    "医療ダイエット": [
        {"copy": "結局、自分に1番合うダイエットが知りたい！", "appeal_axis": "method", "source": "image:seo-diet_ridatsuPU-1"},
        {"copy": "自分にぴったりのダイエットが知りたい！", "appeal_axis": "method", "source": "image:seo-diet_ridatsuPU-2"},
        {"copy": "楽に痩せられるダイエットが知りたい…", "appeal_axis": "method", "source": "image:seo-diet_ridatsuPU-3"},
    ],
}


def detect_genre(tag_path: str) -> str | None:
    """離脱防止タグのパスからジャンルを判定する"""
    for prefix, genre in PATH_TO_GENRE:
        if prefix in tag_path:
            return genre
    return None


def extract_copy(tag_path: str) -> str | None:
    """`/seo_phimo/kasei_包茎を治して自分に自信` → `包茎を治して自分に自信` を取り出す"""
    # パスの最後のセグメント（記事slug＿PU文言）から、最初の日本語以降をPU文言とする
    last = tag_path.rstrip("/").split("/")[-1]
    m = JP_RE.search(last)
    return m.group(0).strip() if m else None


def classify_axis(copy: str) -> str:
    """PU文言を訴求軸に分類（ベストエフォート）"""
    for axis, kws in AXIS_KEYWORDS:
        if any(k in copy for k in kws):
            return axis
    return "other"


def parse_csv(path: Path) -> dict[str, list[dict]]:
    """1つのCSVを読んで {ジャンル: [variant, ...]} を返す"""
    result: dict[str, list[dict]] = {}
    seen: dict[str, set] = {}
    with path.open(encoding="cp932", errors="replace") as f:
        reader = csv.reader(f)
        next(reader, None)  # ヘッダー
        for row in reader:
            if len(row) < 7:
                continue
            tag_path = row[3].strip()
            img_url = row[6].strip()
            if not tag_path.startswith("/"):
                continue
            genre = detect_genre(tag_path)
            if not genre:
                continue
            copy = extract_copy(tag_path)
            if not copy:
                continue
            seen.setdefault(genre, set())
            if copy in seen[genre]:
                continue
            seen[genre].add(copy)
            result.setdefault(genre, []).append(
                {
                    "copy": copy,
                    "appeal_axis": classify_axis(copy),
                    "image_url": img_url,
                    "source": path.name,
                }
            )
    return result


def dedupe_truncated(variants: list[dict]) -> list[dict]:
    """
    タグ文字数制限による途中切れ重複を潰す。
    あるPU文言が別の長い文言の接頭辞になっている場合、短い方（切れ端）を捨てる。
    例: 「包茎を治して夜の自信」は「包茎を治して夜の自信をつけたい!」の切れ端 → 捨てる
    """
    # 長い順に見て、既に採用した文言の接頭辞になっているものは捨てる
    kept: list[dict] = []
    for v in sorted(variants, key=lambda x: len(x["copy"]), reverse=True):
        if any(k["copy"].startswith(v["copy"]) for k in kept):
            continue
        kept.append(v)
    # 元の登場順をなるべく保つ
    order = {id(v): i for i, v in enumerate(variants)}
    return sorted(kept, key=lambda v: order.get(id(v), 0))


def main() -> None:
    master = json.loads(PU_MASTER.read_text(encoding="utf-8"))
    master.setdefault("genres", {})

    imported: dict[str, list[dict]] = {}
    for csv_path in sorted(RAW_DIR.glob("*.csv")):
        for genre, variants in parse_csv(csv_path).items():
            imported.setdefault(genre, [])
            existing_copies = {v["copy"] for v in imported[genre]}
            for v in variants:
                if v["copy"] not in existing_copies:
                    imported[genre].append(v)
                    existing_copies.add(v["copy"])

    # 画像確認済みのシードをマージ（CSVが無いジャンル用）
    for genre, variants in MANUAL_SEED.items():
        imported.setdefault(genre, [])
        existing_copies = {v["copy"] for v in imported[genre]}
        for v in variants:
            if v["copy"] not in existing_copies:
                imported[genre].append(dict(v))
                existing_copies.add(v["copy"])

    # 途中切れ重複を潰す
    for genre in imported:
        imported[genre] = dedupe_truncated(imported[genre])

    # マージ：CSV由来のジャンルは variants を実データで置き換える
    for genre, variants in imported.items():
        entry = master["genres"].get(genre, {})
        entry["diagnosis_name"] = DIAGNOSIS_NAMES.get(
            genre, entry.get("diagnosis_name", "（診断名未設定）")
        )
        entry["variants"] = variants
        # 軸の分布を集計してメモに残す
        dist: dict[str, int] = {}
        for v in variants:
            dist[v["appeal_axis"]] = dist.get(v["appeal_axis"], 0) + 1
        entry["analysis"] = {
            "variant_count": len(variants),
            "axis_distribution": dist,
            "imported_from_csv": True,
        }
        master["genres"][genre] = entry
        print(f"[{genre}] {len(variants)}本のPU文言を取り込み 軸分布={dist}")

    PU_MASTER.write_text(
        json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n→ {PU_MASTER} を更新しました")


if __name__ == "__main__":
    main()
