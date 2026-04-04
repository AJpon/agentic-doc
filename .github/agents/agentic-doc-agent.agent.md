---
name: agentic-doc-agent
description: Use when maintaining or regenerating Markdown Wiki from a local codebase using the DocAgent PoC
---

# agentic-doc-agent

Purpose: ローカルで動くエージェント。`tools/docagent/agent_runner.py` を呼び出してリポジトリを解析し、`docs/wiki` を生成・更新します。

Capabilities:
- `ingest` (抽出)
- `index` (埋め込み生成)
- `generate` (Markdown生成)

Parameters:
- `repo_path` (string) - 対象リポジトリパス（デフォルト: ワークスペースルート）
- `dry_run` (bool) - 変更を実際に書き込まないモード

Required skills:
- **REQUIRED SKILL:** agentic-doc-maintenance

Usage examples:
```text
Run full pipeline (default repo):
python -m tools.docagent.agent_runner

Run for specific repo:
python -m tools.docagent.agent_runner --repo /path/to/repo
```
