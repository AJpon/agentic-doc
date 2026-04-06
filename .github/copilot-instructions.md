---
name: agent-plugin-contribution
description: "エージェントプラグイン（DocAgent PoC）開発者向けのドメイン知識と貢献ルール"
---

# 概要
このファイルは、このリポジトリでエージェントプラグインを開発・拡張するための「ドメイン知識」と貢献ルールをまとめます。
対象は Claude Code / GitHub Copilot と連携するローカル実行型のエージェント（DocAgent PoC）です。

## 目的
- コードベースを解析して Markdown ベースの Wiki を自動生成・保守するための共通ルールを示す。
- 新しい抽出器（言語対応）、スキル、エージェントを一貫性を持って追加できるようにする。

## 前提（Assumptions）
- ローカル環境での実行を前提とする（外部 API キーや商用モデルを利用する場合は明示して環境変数で管理する）。
- 生成されたドキュメントは「自動生成→差分確認→PR」で人間のレビューを必ず受ける。
- このリポジトリは Python 3.9 以上で動作する（`pyproject.toml` を参照）。

## 技術スタック
- 言語: Python (>=3.9)
- ビルド/パッケージ: `pyproject.toml` / `uv_build`（`tools/docagent` をビルドバックエンドのモジュールルートとして使用）
- 開発依存: `mkdocs`, `pylint`, `pytest`, `ruff`（`pyproject.toml` の dev group を参照）
- 主要モジュール: `tools/docagent/`（ingest → index → generate の実装）
- テンプレート: `tools/templates/basic_page.tpl.md`
- エージェント定義: `agents/*.agent.md`
- スキル: `skills/<name>/SKILL.md`

## リポジトリ構造と責務
- `tools/docagent/` — PoC の実装（抽出器、インデックス化、生成ロジック）。
- `tools/docagent/extractors/` — 言語別抽出器（`py_extractor.py`, `ts_extractor.py`, `cs_extractor.py`）。抽出物は JSONL に書きだされ、各項目は少なくとも `{lang,type,name,signature?,doc,file,line,source}` を持つ。既存の実装を踏襲すること。
- `tools/templates/` — Markdown テンプレート。新しいテンプレートはここに追加。
- `agents/` — エージェント定義（メタ情報、パラメータ、使用例）。ドキュメント生成の実行方法もここに書く。
- `skills/` — スキル定義。`SKILL.md` を置き、`description` に検索キーワードと "Use when:" を含める。
- `docs/wiki/` — 生成出力（PR でレビューしてマージする）。
- `tests/` — 単体テスト。コード変更はテストを追加/更新すること。

## 開発ルール（必須）
1. 変更前にローカルで検証する
   - 仮想環境を作成し、依存をインストールしてから作業する（README のクイックスタート参照）。
   - `python -m tools.docagent.agent_runner --repo .` でパイプラインを実行し、生成結果を確認する。
2. 自動生成物の扱い
   - 生成される `docs/wiki` は自動生成物であるため、差分を必ず確認してから PR に含める。
   - 大規模な生成変更は小さな段階に分けてレビューしやすくする。
3. コード品質
   - 変更はテストで検証する。`pytest` を用いること。
   - 静的解析を実行する（`ruff` や `pylint`）。CI にリンターを追加することを推奨。
4. 抽出器を追加/変更する際
   - 出力 JSONL のスキーマを既存 `tools/docagent/ingest.py` の形式に合わせる（`lang,type,name,signature,doc,file,line,source`）。
   - 既存の `py_extractor.py` 等の実装スタイルを参考にする。
5. スキル・エージェントの作成
   - スキルは `skills/<name>/SKILL.md` に配置し、`name`, `description`, `Use when:` を明確に記載する。
   - エージェント定義は `agents/<name>.agent.md` に記載し、`Purpose`, `Capabilities`, `Parameters`, `Required skills`, `Usage examples` を含める。

## PR・ブランチ運用
- ブランチ命名: `feature/<短い説明>`, `fix/<issue-id>`, `chore/<task>`。
- PR 説明に以下を含めること:
  - 何を変更したか（要約）
  - 再現手順（ローカルでの実行コマンド）
  - 生成結果の差分（重要な変更点を箇条書き）
  - テストと静的解析の結果（手順やスクリーンショット）
- レビュー: 少なくとも1人のレビュワーを付ける。大きな設計変更は設計メモ（docs/ に短い説明）を添える。

## コミットメッセージとスタイル
- Conventional Commits を基本とする（例: `feat: add ts extractor`, `fix: correct doc rendering`）。

## テスト・CI 推奨
- CI は最低限次を行う: `pytest`, `ruff`, `pylint`。
- 可能であれば「dry-run のドキュメント生成（差分出力）」を CI に追加し、自動生成物の意図しない差分を検出する。

## セキュリティとシークレット管理
- API キーやシークレットはリポジトリにコミットしない。`env` や GitHub Secrets を使用する。
- `.env.example` を用意して、必要な環境変数名をドキュメント化する。

## 追加のガイドライン（実務的助言）
- 小さな変更であれば `tools/docagent` 内で局所検証し、生成結果を最小単位で確認する。
- 抽出スコープやスニペット長は言語ごとに妥当なデフォルトを設定する（既存実装は `source[:2000]` などの例あり）。
- スキルの `description` フィールドには検索されやすいキーワードを含める（例: "wiki, docs, ingest, index, generate"）。

## 参考ファイル
- 実行用オーケストレーター: `tools/docagent/agent_runner.py`
- テンプレート: `tools/templates/basic_page.tpl.md`
- 抽出器サンプル: `tools/docagent/extractors/` 内の `py_extractor.py`, `ts_extractor.py`, `cs_extractor.py`
- スキルの例: `skills/agentic-doc-maintenance/SKILL.md`
- エージェント定義の例: `agents/agentic-doc-agent.agent.md`

---
この指針は必要に応じて更新してください。変更提案は PR で提出してください。
