# 🎯 診断PU推薦ツール

記事本文を貼ってジャンルを選ぶと、相性の良い **診断タイプ** と **PU訴求軸タグ** を吐き出す独立ツール。
新記事に「何のPUを設置すべきか」を即答する運用ツール。インターン・チームに「このURL開いて記事貼って」で使わせる想定。

## 何をするか

```
記事本文 ＋ ジャンル選択
   │
   ▼ Geminiが本文を読む
   ├─ 検索意図：悩み / 商標 / 指名      → INTENT_MATCH_RULES で診断タイプ確定
   └─ 訴求の重心：cost / choice / method → 推奨PU訴求軸タグ確定
   │
   ▼
出力：おすすめ診断タイプ ＋ 推奨PU訴求軸タグ ＋ 理由
      ＋（在庫があれば）使える既存PU文言
```

## 判定の根拠（既存資産を流用）

| データ | 役割 | 出所 |
|--------|------|------|
| `INTENT_MATCH_RULES` (lib/rules.py) | 検索意図→相性の良い診断タイプ | line-dashboard/lib/constants.py |
| `data/article_mapping.csv` | ジャンルの実績診断タイプ | line-dashboard 同梱コピー |
| `data/pu_master.json` | 既存PU文言の在庫（訴求軸別） | line-dashboard 同梱コピー |

> ⚠️ 既存PU在庫(`pu_master.json`)は旧ジャンル中心。管轄9ジャンルの在庫が揃っていないため、
> 訴求軸は「在庫から選ぶ」のではなく「記事から推論する」設計。在庫があれば併せて表示する。

## ローカル起動

```bash
cd diagnosis-pu-recommender
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # → GEMINI_API_KEY を記入
streamlit run app.py
```

## Streamlit Cloud デプロイ（新URL発行）

1. このフォルダを GitHub リポジトリにpush
2. https://share.streamlit.io → New app → リポジトリ・ブランチ・`app.py` を指定
3. アプリ設定の **Secrets** に `GEMINI_API_KEY = "..."` を貼る（line-image-generatorと同じキー流用可）
4. Deploy → 新URLが発行される

## データ更新

`data/article_mapping.csv` と `data/pu_master.json` は line-dashboard からのコピー。
元データが更新されたら再コピーする（将来は同期スクリプト化を検討）。
