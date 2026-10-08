# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## プロダクトの目的

`agentic-doc` は、コードベースから Markdown の Wiki を生成し、コードの変化に追随させ続けるエージェントプラグイン。Claude Code では Workflow で並列に動き、GitHub Copilot（VS Code）と Codex CLI では同じスキルを 1 体のエージェントが直列に実行する。各ページが依存するファイル（sources）と、最後に検証を通ったコミット（source_commit）をカタログに記録し、git の差分で古くなったページを見つけて書き直す。

旧 DocAgent PoC（`tools/docagent`、`agents/*.agent.md` など）は削除済み。その構成やコマンドを前提にしないこと。

## 正とする文書

| 文書 | 内容 |
| --- | --- |
| `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md` | 設計仕様。設定ファイル、カタログ、モード、スクリプト、執筆規約、エラー処理はすべてここが正 |
| `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md` | 実行方式とハーネスの検証記録。冒頭の「未確認」は検証済みと扱わない |
| `docs/superpowers/plans/` | 実装計画。計画 1（土台づくり）と計画 2（決定的なスクリプト群）は完了済み。計画 3 以降はこれから作る |

## 構成

```text
plugin.json                          # Agent Plugins 1.0（Copilot / Codex が読む）
.claude-plugin/plugin.json           # Claude Code 用。workflows の場所を指す
.claude-plugin/marketplace.json
skills/wiki/                         # 入口スキル（全ハーネス共通）
skills/wiki/scripts/agentic_doc.py   # 決定的なスクリプトの入口（PEP 723）。コマンドの実装は scripts/adoc/cmd_*.py
skills/wiki/schemas/                 # 設定ファイルとカタログの JSON Schema
skills/wiki-setup/                   # 導入先の設定ファイルを作るスキル
com.anthropic.claude-code/workflows/wiki-run.js   # Claude Code 専用のオーケストレーション
```

スクリプトは実装済み。スキル本文と Workflow はまだ仮置き（計画 3 で作る）。

## 守ること

- 手順・プロンプト・執筆規約・スキーマはスキルの中にだけ置く。Workflow には制御だけを書き、プロンプトの本文を書かない。
- スキル本文からスクリプトや参照文書を指すときは「この SKILL.md と同じディレクトリからの相対パス」で書き、パスはダブルクォートで囲む。`${PLUGIN_ROOT}` はスキル本文では展開されないので使わない。
- Workflow はファイルシステムに触れず、日付も取れない。プラグインのパスと日付は、入口スキルが `args.plugin_root`（`${CLAUDE_PLUGIN_ROOT}`）と `args.today` で渡す。Workflow の `meta.name` はスキルと同じ名前にしない。
- スクリプトは uv + PEP 723 の Python。導入先に要求する前提は uv と git だけ。
- `plugin.json`、`.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` の `name` / `version` / `description` はそろえる。

## コマンド

```bash
claude plugin validate .claude-plugin/plugin.json   # Claude Code 用マニフェストの検証
claude plugin validate .                            # marketplace.json の検証
claude -p "/agentic-doc:wiki" --plugin-dir . --allowedTools "Workflow,Skill"   # 読み込みの確認
uv run pytest                                       # テスト（tests/。一時 git リポジトリに対して CLI を実行する）
uv run ruff check .                                 # リント（対象は skills/ と tests/ の Python）
uv run --script skills/wiki/scripts/agentic_doc.py --help   # 導入先と同じ呼び出し方で CLI を確かめる
```

`claude -p` では、値を複数取る `--allowedTools` より前にプロンプトを書く。`lint --mermaid` のテストは、環境変数 `AGENTIC_DOC_MERMAID_MODULES` に mermaid と jsdom の入った `node_modules` を指定したときだけ動く。

スクリプトに新しいコマンドを足すときは、`skills/wiki/scripts/adoc/cmd_<名前>.py` に `COMMAND` を定義して `agentic_doc.py` の `COMMANDS` に登録する。言語に依存する文字列は `adoc/i18n.py` の `ja` と `en` の両方に足す。

## 開発ルール

- コミットは Conventional Commits。description は日本語か英語。
- `main` に直接コミットせず、ブランチを切って PR にする。
- `spikes/` は計画 1 の使い捨ての検証コードで、git の対象外（`.git/info/exclude`）。
- `.editorconfig`: インデント 4 スペース（JSON/YAML は 2）、LF、末尾改行必須。
