# ingest.agent
短い説明: リポジトリを走査して抽出を行い、JSONLを生成します。

## Parameters
- `repo_path` — スキャン対象のルートパス（例: `.`）
- `out_file` — 出力JSONL（例: `tools/docagent/data/extracted.jsonl`）

## Usage
```bash
python -c "from tools.docagent.ingest import ingest_repo; ingest_repo(repo_path='.', out_file='tools/docagent/data/extracted.jsonl')"
```

実行/テスト: 上記コマンドを実行し、`out_file` が生成されることを確認してください。
