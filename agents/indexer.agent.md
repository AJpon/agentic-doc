# indexer.agent
短い説明: 抽出済みJSONLを読み込み、`index.json`（埋め込みなし）または`index_with_embeddings.json`を生成します。

## Parameters
- `input_file` — 抽出済みJSONL（例: `tools/docagent/data/extracted.jsonl`）
- `persist_dir` — 出力ディレクトリ（例: `tools/docagent/data`）

## Usage
```bash
python -c "from tools.docagent.index import index_jsonl; index_jsonl(input_file='tools/docagent/data/extracted.jsonl', persist_dir='tools/docagent/data')"
```

実行/テスト: 上記コマンドで `index.json` または `index_with_embeddings.json` が生成されることを確認。
