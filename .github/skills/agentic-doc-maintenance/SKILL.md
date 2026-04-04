---
name: agentic-doc-maintenance
description: Use when you need to generate or update Markdown Wiki from a local codebase using the DocAgent PoC
---

# agentic-doc-maintenance

## Overview

This skill documents how to keep a repository's Markdown-based Wiki up-to-date by running the local DocAgent PoC pipeline (`ingest` → `index` → `generate`) and how to repair common issues (outdated snippets, broken links, missing examples).

## When to Use

- Use when the repository's `docs/wiki` is out of sync with source code or README files.
- Use when you want a reproducible local workflow to regenerate docs after edits.

## Quick Reference

Run full pipeline locally:

```bash
python -m tools.docagent.agent_runner --repo .
```

Generate pages only (existing index):

```bash
python -m tools.docagent.cli generate --out docs/wiki
```

## Core Pattern

1. Ingest: ソース/README/サンプルを抽出してJSONLを作る
2. Index: 抽出結果をチャンク化→埋め込み→ローカルDBに保存
3. Generate: テンプレートを適用してMarkdownを出力

**Safety/Constraints:**
- Agent はローカル環境で実行することを前提とする（ネイティブ依存やライセンス資産は手動確認が必要）
- 生成されたドキュメントは、最初は手動確認（diff）を推奨する

## Implementation notes

- The agent invokes `tools/docagent.agent_runner` (this repo) and expects `docs/wiki` as output
- For C# projects, prefer adding a Roslyn-based extractor producing the same JSON schema as other extractors

## Quick Troubleshooting

- If `docs/wiki/index.md` missing: run `python -m tools.docagent.cli index` then `generate`
- If code snippets are truncated: increase `extractors/*` source snippet limits
