I'm using the writing-plans skill to create the implementation plan.

# Agentic Doc Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ローカルで動くAIエージェント（agentic-doc-agent）を作成し、コードベースの解析→インデックス化→Markdown Wiki生成・差分更新を自動化できるようにする。まずはワークスペース内実行（ネットワークLLMはオプション）でPoCを完成させる。

**Architecture:** tools/docagent を実行するローカルエージェント（ワークフロー実行エンジン）を `.github/agents` と `.github/skills` で定義する。エージェントは `tools/docagent/agent_runner.py` を呼び出して `ingest`→`index`→`generate` を実行し、生成された `docs/wiki` を更新する。

**Tech Stack:** Python CLI (typer/argparse), sentence-transformers or local embedder, Chroma/FAISS（ローカル）、MkDocs（Wikiプレビュー）。将来的に Roslyn (.NET) extractor を追加。

---

### Task 1: ワークスペースカスタマイズ（エージェント/スキル/フック）

**Files:**
- Create: `.github/agents/agentic-doc-agent.agent.md`  — エージェント定義
- Create: `.github/skills/agentic-doc-maintenance/SKILL.md` — スキル（ドキュメント生成ルール）
- Create: `.github/hooks/docagent-preindex.json` — ライフサイクルフック（実行例）

- [ ] **Step 1: 上記ファイルを作成する（今回のコミットで追加済）**

```bash
git add .github/agents/agentic-doc-agent.agent.md \
        .github/skills/agentic-doc-maintenance/SKILL.md \
        .github/hooks/docagent-preindex.json
git commit -m "chore: add agentic-doc-agent and skill skeleton"
```

**Notes:** agent ファイルは `description` にトリガー語句を入れ、skill の `description` は `Use when...` で始めること（発見性ルール）。

### Task 2: ローカル実行エントリ（agent_runner）

**Files:**
- Create: `tools/docagent/agent_runner.py` — PoCのオーケストレータ（ingest→index→generate）

- [ ] **Step 1: agent_runner を実装して手動でワークフローを起動できるようにする**

Implementation (file content shown in repository): the runner calls the existing CLI modules and bubbles up errors.

**Run:**
```bash
python -m tools.docagent.agent_runner --repo /path/to/target/repo
```

### Task 3: テストとTDD（PoC検証）

**Files:**
- Create: `tools/docagent/tests/test_generate_index.py` — 簡易スモークテスト

- [ ] **Step 1: ベースラインテストを作る（テストは最初に FAIL させる想定）**
  - テスト内容: 最小サンプルリポジトリを作り、`agent_runner` を実行して `docs/wiki/index.md` が生成されることを期待する。
  - 実行コマンド: `pytest tools/docagent/tests/test_generate_index.py -q`

**TDD Note:** スキルのRED-GREEN-REFACTORを守るなら、最初にエージェント不在の状態で失敗するテストを作り、それを受けてスキル（エージェント）を適用してPASSにする。PoCではまず通るスモークテストを置き、将来のリファインでREDの段階を追加する。

### Task 4: Skill 本文作成と最小ガイドライン

**Files (created):** `.github/skills/agentic-doc-maintenance/SKILL.md` （本文には：When to use, Quick Reference, Prompts, Safety/Constraints）

- [ ] **Step 1: Skillの本文を作り、CLAIUが発見しやすい `description` を設定する**

### Task 5: ローカル検証・微調整

- [ ] **Step 1:** `python -m tools.docagent.agent_runner --repo .` を実行して生成物を確認
- [ ] **Step 2:** `mkdocs serve` で `docs/wiki` をプレビュー
- [ ] **Step 3:** 生成テンプレート（Jinja2）や `generate.py` のレンダリングを改善

### Files Created in this Plan (summary)
- `docs/superpowers/plans/2026-04-04-agentic-doc-agent-plan.md` (this file)
- `.github/agents/agentic-doc-agent.agent.md`
- `.github/skills/agentic-doc-maintenance/SKILL.md`
- `.github/hooks/docagent-preindex.json`
- `tools/docagent/agent_runner.py`
- `tools/docagent/tests/test_generate_index.py`

---

**Execution Handoff**

Plan saved to `docs/superpowers/plans/2026-04-04-agentic-doc-agent-plan.md` (this path).

実行方法を選んでください：
- **1. Subagent-Driven (推奨)** — 各タスクを分割してサブエージェントに実行させ、レビューを挟む
- **2. Inline Execution** — このセッションで順に実行していく（チェックポイントあり）

どちらで進めますか？
