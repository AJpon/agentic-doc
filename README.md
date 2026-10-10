# agentic-doc

agentic-doc は、コードベースから Markdown の Wiki を生成し、コードの変化に追随させ続けるためのエージェントプラグインです。

- 各ページが依存するファイル（sources）と、最後に検証を通ったコミット（source_commit）をカタログに記録します。
- git の差分から古くなったページを見つけ、そのページだけを書き直します。

## 動作環境

導入先に必要なのは [uv](https://docs.astral.sh/uv/) と git だけです。Python 本体は uv が用意します。

| ハーネス | 動き方 |
| --- | --- |
| Claude Code | Workflow で並列に動きます。2 ページずつ処理し、2 つの観点の検証を別々のエージェントが並列に行います |
| GitHub Copilot（VS Code）、Codex CLI | 同じスキルを 1 体のエージェントが直列に実行します（縮退動作）。成果物は Claude Code と同じです |

## 導入

### Claude Code

```bash
claude plugin marketplace add AJpon/agentic-doc
claude plugin install agentic-doc@agentic-doc-dev
```

Workflow のエージェントはスクリプトを `uv run --script` で実行します。実行のたびに許可を求められないよう、導入先の `.claude/settings.json` で許可しておくと便利です。

```json
{ "permissions": { "allow": ["Bash(uv run --script:*)", "Bash(git ls-files:*)", "Bash(git diff:*)"] } }
```

### GitHub Copilot（VS Code）

このリポジトリを clone します。設定 `chat.pluginLocations` に、clone したディレクトリを追加します。

### Codex CLI

`.claude-plugin/marketplace.json` を持つこのリポジトリを、マーケットプレイスとして追加してからインストールします。

## 使い方

`/agentic-doc:wiki <モード> [引数]` で呼び出します。ハーネスによって表記は異なります。

| モード | 内容 |
| --- | --- |
| （なし）/ `help` | 現在の状態と、次に実行するコマンドを示す |
| `setup` | 設定ファイル `.agentic-doc.config.json` を作成・更新する |
| `outline [--force]` | Wiki の章とページの構成を設計し、カタログを置く |
| `sync [--pages <id>...] [--include-unresolved]` | 未生成・未検証・変更ありのページを書く／書き直す |
| `status [<id>...] [--state <状態>] [--verbose]` | 各ページの状態を表で示す（LLM を使わない） |
| `audit [--lint-only]` | 機械検査と、本文とコードの食い違いを監査する（書き換えない） |
| `stamp [--sha <rev>] [--pages <id>...] [--dry-run]` | 本文を変えずに、確認済みの印を付け直す |

最初は `setup` → `outline` → （カタログを人が確認）→ `sync` の順に進めます。以後は `status` で状態を確かめ、`sync` で更新します。

スクリプトは直接も実行できます。

```bash
uv run --script "<プラグインのパス>/skills/wiki/scripts/agentic_doc.py" --help
```

## 設計

- [設計仕様](docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md)
- [実行方式とハーネスの検証記録](docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md)
- 開発者向けの説明は [AGENTS.md](AGENTS.md) にあります。
