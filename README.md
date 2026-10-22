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

このリポジトリを clone します。設定 `chat.pluginLocations` に、clone したディレクトリを追加します。VS Code での動作は、所有者の実機での確認待ちです（手順書は [`docs/superpowers/acceptance/copilot-degraded.md`](docs/superpowers/acceptance/copilot-degraded.md)）。

### Codex CLI

このリポジトリをマーケットプレイスとして追加し、インストールします。

```bash
codex plugin marketplace add AJpon/agentic-doc
codex plugin add agentic-doc@agentic-doc-dev
```

Codex では、実行時に uv のキャッシュ（`~/.cache/uv`）への書き込みとネットワークが要ります。`codex exec` で使うときは、`-s workspace-write --add-dir ~/.cache/uv -c sandbox_workspace_write.network_access=true` を付けます。

## 旧形式の Wiki からの移行

`_catalogue.json` を持つ旧形式の Wiki（fbx-view の PR #21 のもの）は、次の順でカタログを変換します。ページ本文と `source_commit` は変わりません。

1. `/agentic-doc:wiki setup` で設定ファイルを作ります。
2. `catalogue` コマンドの `migrate` に旧ファイル（`docs/wiki/_catalogue.json`）を渡して実行します。章はページ ID から作られ、元のファイルは消えます。今の `exclude` で全て除外される `sources` は、警告になります。
3. `/agentic-doc:wiki audit --lint-only` で、引用の指摘（除外されたファイルへの引用など）を確かめて直します。
4. 章の `title` と `description` をカタログに書きます。`toc` は `<wiki_dir>/README.md` を再生成するので、手で書いた導入文は残りません。

## 使うときの注意

- Claude Code の `claude -p` は、バックグラウンドの Workflow を 600 秒で止めます。`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` を付けてください。
- 利用制限で `sync` が止まったら、同じコマンドをもう一度実行します。検証を通ったページは「最新」で残り、research の結果と書き込み済みの本文は再利用されます。止まったときのログは 1 行だけなので、どこまで進んだかは `status` で見ます。
- 作業クローンを `~/.claude` の下に置かないでください。書き込みが「sensitive file」として拒否されることがあります。終了コードは 0 のままなので、成否は `status` で確かめます。
- Codex と Copilot の縮退動作では、検証が Claude Code より弱くなります（観点ごとの独立した検証パスがありません）。

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

## ライセンス

[MIT](LICENSE)

## 設計

- [設計仕様](docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md)
- [実行方式とハーネスの検証記録](docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md)
- 開発者向けの説明は [AGENTS.md](AGENTS.md) にあります。
