# DocAgent PoC

このドキュメントはローカルDocAgentのPoC向けです。

目的:
- コードベースを解析して理解（シンボル、docstring、サンプル）
- ローカル埋め込みとRAGでコンテキスト検索
- Markdown形式のWikiを自動生成・差分更新

ワークフロー（ローカル）:
1. `ingest` でソースコードから情報を抽出
2. `index` で埋め込みを作りローカルDBに保存
3. `generate` で Markdownページを生成

詳細は `tools/docagent/` を参照してください。
