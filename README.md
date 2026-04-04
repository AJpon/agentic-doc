
# DocAgent PoC

ローカルで動く「コードベース解析 → インデックス化 → Wiki（Markdown）生成」のPoC雛形です。

クイックスタート:（ローカル環境での検証手順）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1) リポジトリを解析して抽出
python -m tools.docagent.cli ingest --repo /path/to/target/repo --out tools/docagent/data/extracted.jsonl

# 2) 抽出結果をインデックス化（埋め込みが利用可能なら埋め込みを作成）
python -m tools.docagent.cli index --input tools/docagent/data/extracted.jsonl --persist tools/docagent/data

# 3) インデックスからMarkdownを生成して docs/wiki/ に出力
python -m tools.docagent.cli generate --out docs/wiki

# 4) プレビュー
mkdocs serve
```

目的: ローカルでのドキュメント作成負荷を下げるため、まずはローカルエージェントでコードを体系的に理解してMarkdown Wikiを生成できることを目指す。
