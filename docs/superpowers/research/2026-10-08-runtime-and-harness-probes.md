# 実行方式とハーネスの検証記録

## 結論（2026-10-09、所有者承認済み）

- **実行方式**: uv + PEP 723 の Python スクリプト。導入先の前提は uv と git だけ。
- **スキルからスクリプトを指す書き方**: 「この SKILL.md と同じディレクトリからの相対パス」。Claude Code・VS Code（Copilot）・Codex の 3 つで動いた。`${PLUGIN_ROOT}` はスキル本文では展開されないので使わない。
- **Workflow へのパスの渡し方**: 入口スキルが `${CLAUDE_PLUGIN_ROOT}` を Workflow の `args.plugin_root` に入れて渡す。Workflow の `meta.name` は入口スキルと別の名前にする。
- **マニフェスト**: ルートに Agent Plugins 1.0 の `plugin.json`、`.claude-plugin/plugin.json` に Claude Code 用。Workflow は `workflows` で `./com.anthropic.claude-code/workflows/` を指す。
- **未確認**（計画 4 の受入検証後の状態。5 節に根拠がある。確かめたものは検証済み、残りは理由つきで未確認のまま）:
  - 確かめた: Linux と Windows でのスクリプトとテスト（CI の 3 OS）。Python 本体が未導入の環境での初回実行（CI の `first-run` ジョブ、3 OS）。Claude Code で git のマーケットプレイスからインストールし、キャッシュに置かれた場合。Codex で両方のマニフェストを置いた場合と、本番と同じ `source: "./"` の構成。
  - 未確認（所有者の実機が要る）: VS Code（Copilot）での動作と、両方のマニフェストを置いたときに表示されるプラグイン名（手順書 `docs/superpowers/acceptance/copilot-degraded.md`）。Windows の PowerShell 実機での動作、`core.autocrlf=true` での改行、非 ASCII のファイル名の表示（`docs/superpowers/acceptance/windows-powershell.md`）。
  - 未確認（理由つき）: リポジトリ内のファイル名が非 ASCII の場合のエージェント経由の実行。スクリプトは単体テストで確かめた（`tests/` に非 ASCII と空白を含むファイル名のケースがある）が、Claude Code と Codex の実行では、そのようなファイルを持つ導入先を使っていない。

計画 1（`docs/superpowers/plans/2026-10-08-agentic-doc-plan1-foundation.md`）の Task 1〜3 の結果。プローブは `spikes/` に置いた使い捨てのコードで、git には入れていない。

## 1. Claude Code

環境: Claude Code 2.1.285、macOS（arm64）

| 問い | 結果 | 根拠 |
|---|---|---|
| Q3: `workflows` で名前空間ディレクトリ `./com.anthropic.claude-code/workflows/` を指して読み込めるか | はい | `claude plugin validate` が `Validation passed`。`/agentic-doc-probe:probe` で Workflow が起動した |
| Q2: スキル本文の `${CLAUDE_PLUGIN_ROOT}` が展開され、Workflow の `args` で渡せるか | はい | スキルが `args: {"plugin_root": "${CLAUDE_PLUGIN_ROOT}"}` で Workflow を呼び、Workflow が `plugin_root` を受け取った |
| Q2 補足: Workflow 内のエージェントが `args.plugin_root` 配下のファイルを読めるか | はい | エージェントが `<plugin_root>/skills/run-probe/references/hello.md` の 1 行目 `PROBE-OK-7f3c` を返した |

実行したコマンドと出力:

```
$ claude -p "/agentic-doc-probe:run-probe" --plugin-dir spikes/cc-plugin --allowedTools "Workflow,Read,Skill"
{"plugin_root":"/Users/taka/works/dev/agentic-wiki/spikes/cc-plugin","result":{"line":"PROBE-OK-7f3c"}}

$ claude plugin marketplace add ./spikes/cc-plugin
$ claude plugin install agentic-doc-probe@agentic-doc-probe-market
$ claude -p "/agentic-doc-probe:run-probe" --allowedTools "Workflow,Read,Skill"
{"plugin_root":"/Users/taka/works/dev/agentic-wiki/spikes/cc-plugin","result":{"line":"PROBE-OK-7f3c"}}
```

### 分かったこと

- **スキルと Workflow の名前の衝突**: スキルと Workflow がどちらも `probe` という名前だと、`/agentic-doc-probe:probe` は Workflow を直接起動した。スキルは経由しないので `args` が渡らず、`plugin_root` は `undefined` になった。本番では、入口スキル `wiki` と Workflow の `meta.name` を別の名前にする必要がある（例: Workflow は `wiki-run`）。
- **`claude -p` の引数の順序**: `--allowedTools` は値を複数取るので、プロンプトはその前に書く必要がある。
- **ローカルパスのマーケットプレイス**: ローカルパスから追加したマーケットプレイスでは、プラグインはキャッシュにコピーされずにその場で読み込まれる（`plugin_root` が `spikes/cc-plugin` のまま）。git や URL のマーケットプレイスからインストールした場合のキャッシュ先パスでは試していない。`${CLAUDE_PLUGIN_ROOT}` はどちらでも展開される仕組みなので同じく動くと見込むが、未確認。

## 2. Agent Plugins 1.0

環境: VS Code 1.141（Copilot Chat のエージェントモード、所有者が実施）、Codex CLI 0.161.0、Claude Code 2.1.285

| 問い | VS Code（Copilot） | Codex CLI | Claude Code |
|---|---|---|---|
| ルートの `plugin.json`（Agent Plugins 1.0）だけのプラグインからスキルを読み込めるか | はい（`chat.pluginLocations` で追加） | はい（ローカルのマーケットプレイス経由でインストール） | はい（`--plugin-dir`） |
| スキルと同じディレクトリの `scripts/hello.py` を実行できるか | はい（`SCRIPT-OK-91ad`） | はい（`SCRIPT-OK-91ad`） | はい（`SCRIPT-OK-91ad`） |
| スキルからスクリプトを指せた書き方 | 「この SKILL.md と同じディレクトリの `scripts/hello.py`」。エージェントが絶対パスに解決した | 同左。インストール先のキャッシュ（`~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/`）の絶対パスに解決した | 同左。スキルのベースディレクトリから解決した |
| スキル本文の `${PLUGIN_ROOT}` が展開されるか | いいえ（文字列のまま） | いいえ（文字列のまま） | いいえ（文字列のまま） |
| 両方のマニフェストを置いたとき、どちらで読み込むか | スキルは読み込まれたが、プラグイン名の表示を確認できていない（未確認） | 試していない | `.claude-plugin/plugin.json` |

### 分かったこと

- **3 ハーネスとも「SKILL.md と同じディレクトリからの相対パス」で動く。** 変数の展開に頼らず、この書き方に統一すればよい。
- **`${PLUGIN_ROOT}` はスキル本文では展開されない。** VS Code のドキュメントでもトークンはフックのコマンド用とされている。スキル本文では使わない。Claude Code の `${CLAUDE_PLUGIN_ROOT}` はスキル本文で展開される（1 節）が、Claude Code 専用なので、使うのは Workflow にパスを渡す箇所だけにする。
- **Codex はプラグインをキャッシュにコピーしてから読み込む。** スクリプトはプラグイン内の相対位置だけを前提にし、リポジトリ内の位置を前提にしてはならない。Codex のローカルマーケットプレイスは `.claude-plugin/marketplace.json` の形式をそのまま読んだ。
- VS Code では、1 回目の実行でスクリプトの出力に端末のプロンプト文字列が混ざった（`SCRIPT-OK-91adok-Air:`）。2 回目は正しく出た。エージェントがターミナルの出力を読む際の揺れとみられ、プラグインの構成とは関係しない。

Claude Code で補足的に確かめたこと:

- ルートに Agent Plugins 1.0 の `plugin.json`（`$schema` 付き）だけを置いたプラグインは、`claude plugin validate` を通る。
- ルートの `plugin.json` と `.claude-plugin/plugin.json` の両方を置いた場合、Claude Code は `.claude-plugin/plugin.json` の名前（`agentic-doc-probe-cc`）で読み込む。validate の警告は `author` が無いことだけ。
- Claude Code では、スキル本文の `${PLUGIN_ROOT}` は展開されずに文字列のまま残る。一方、スキルのベースディレクトリはエージェントに渡されるので、「この SKILL.md と同じディレクトリの `scripts/hello.py`」という書き方で絶対パスに解決して実行できた。
- VS Code のドキュメントでは、プラグインの形式は `plugin.json`（Agent Plugins 1.0 の `$schema` 付き）→ `.claude-plugin/plugin.json` → `.plugin/plugin.json` → `plugin.json`（スキーマなし）の順に判定され、プラグインのルートを指すトークンは Agent Plugins 1.0 形式なら `${PLUGIN_ROOT}`、Claude 形式なら `${CLAUDE_PLUGIN_ROOT}` とされている（記載はフックのコマンドについて）。ローカルのプラグインは設定 `chat.pluginLocations` で読み込む。

## 3. 実行方式

### 3.1 プローブ

3 方式で同じ処理を書いた。仕様書 7.4 の `status` を縮めたもので、5 状態（missing / unverified / unresolved / changed / fresh）の判定、`.agentic-doc.config.json` と `catalogue.json` の読み込み、YAML の読み込み、git の呼び出しを含む。フィクスチャのリポジトリは 5 状態が 1 ページずつ出るように作った。

| 方式 | プローブ | 起動コマンド | YAML |
|---|---|---|---|
| A. uv + PEP 723 | `spikes/runtime/uv-pep723/probe.py` | `uv run --script probe.py` | PyYAML（PEP 723 で宣言） |
| B. uv + PyPI の deno | `spikes/runtime/uv-deno/probe.ts` | `uv run --no-project --with deno deno run --allow-read --allow-run=git probe.ts` | `jsr:@std/yaml@1` |
| C. Node.js の MCP サーバー | `spikes/runtime/mcp-node/server.ts` | MCP クライアントから stdio で起動（Node 24 は `.ts` をそのまま実行） | npm の `yaml` |

3 方式とも期待値と完全に一致した。C は `claude -p --mcp-config` 経由と、LLM を介さない直接の JSON-RPC 呼び出しの両方で一致した。

### 3.2 計測（macOS arm64、Apple Git 2.50）

| 項目 | A. uv + PEP 723 | B. uv + deno | C. MCP（Node） |
|---|---|---|---|
| 初回（uv・deno・npm のキャッシュ空。uv 管理の Python は導入済み） | 4.4 秒 | 20.2 秒 | 依存のインストール 22.8 秒 ＋ 起動と呼び出し 2.3 秒 |
| 2 回目以降（3 回） | 1.2 / 0.9 / 1.2 秒 | 3.1 / 1.7 / 1.0 秒 | 2.3 / 1.8 / 1.7 秒（起動込み。常駐後の呼び出しはこれより短い） |
| 初回にダウンロードされる量 | 1.8 MB（PyYAML） | 162 MB（deno の wheel）＋ 2.1 MB（jsr のモジュール） | 27 MB（node_modules） |
| git リポジトリ外で実行 | 終了コード 2、「not a git repository: <パス>」 | 同左 | ツールがエラーを返す（直接呼び出しでは終了コード 2） |
| git が PATH に無い | 終了コード 2、「git not found on PATH」 | 同等の処理を実装 | 同等の処理を実装 |
| 空白と非 ASCII を含むパス（リポジトリとスクリプトの置き場所 `spikes/パス に 空白/`。リポジトリ内のファイル名は ASCII のみ） | 一致 | 一致 | 一致 |
| オフラインかつキャッシュ空 | 失敗。「network was disabled」と原因の分かるヒントが出る | uv の段階で同じヒント。deno のキャッシュだけ空なら「Specifier not found in cache」 | `npm ci --offline` が失敗。メッセージはログを見ないと分かりにくい |

計測時間は数回のばらつきが大きく、1 秒前後の差には意味がない。初回の差とダウンロード量の差ははっきりしている。

### 3.3 比較

| 観点 | A. uv + PEP 723 | B. uv + deno | C. MCP（Node） |
|---|---|---|---|
| 導入先に要求する前提 | uv だけ（Python は uv が用意する） | uv だけ | Node.js と、依存のインストール（またはビルド済みの 1 ファイルを同梱） |
| Windows / macOS / Linux | macOS で確認。Windows と Linux は未確認（計画 4 の受入検証で確かめる） | 同左 | 同左 |
| 外部ライブラリ | PyPI。PEP 723 で宣言すればインストール手順が要らない | jsr と npm。URL で宣言すればインストール手順が要らない | npm。インストールかバンドルが必要 |
| Agent Plugins 1.0 での配布 | スキル内の `scripts/` に置くだけ。スキルから相対パスで呼べる（Task 2 の結果） | 同左 | `mcp.json` は移植できる部品なので、ツールとして全ハーネスから使える。ただし依存の扱いが要る |
| 人間が CLI として直接使う（`--help`、`status`） | そのまま使える | そのまま使える | MCP サーバーとは別に CLI の入口が必要 |
| Workflow のエージェントから使う | Bash で呼ぶ | Bash で呼ぶ | MCP のツールとして呼ぶ（Bash の権限が不要） |
| Mermaid の構文検査 | Node と mermaid が別途必要（任意の検査として扱う） | `npm:mermaid` を Deno で動かせる可能性がある（未確認） | 同じ Node で mermaid を使える |
| 元実装からの移植 | `wiki_lint.py` と `wiki_repin.py` をそのまま流用できる | TypeScript への書き直しが必要 | 同左 |
| 初回の速さとダウンロード量 | 最も速く、最も小さい | 最も遅く、最も大きい（deno 本体） | 中間 |

### 3.4 推奨

**A. uv + PEP 723 を推奨する。**

- 前提が uv だけで済み、初回の待ち時間とダウンロード量が 3 方式で最も小さい。
- 元実装の `wiki_lint.py` と `wiki_repin.py` を流用でき、移植の手間とリスクが最も小さい。
- スキル内の `scripts/` に置けば、Claude Code では相対パスで呼び出せることを確認済み（Copilot と Codex は Task 2 で確認）。人間がそのまま CLI として使える。
- C の利点（`mcp.json` での移植性、Bash の権限が要らないこと）は、A のスクリプトを薄い MCP サーバーで包めば後から得られる。逆に C を先に選ぶと、人間向けの CLI を別に作る必要がある。
- B は TypeScript で書ける点を除き、A に対する利点が見当たらない。deno 本体の 162 MB のダウンロードが初回の体験を損なう。

Mermaid の構文検査は、Node と mermaid がある環境でだけ動く任意の検査とする（仕様書 8 章のとおり）。

## 4. 計画 3 の実機確認（2026-10-10）

環境: Claude Code（`claude -p --plugin-dir`）、macOS。小さな導入先（`src/calc/` の Python 6 本、1 章 1 ページのカタログ、`language: "ja"`）で確かめた。

| 確かめたこと | 結果 |
| --- | --- |
| `/agentic-doc:wiki help` | `status` を実行し、「未生成 1 ページ、次は sync」と引数付きで案内した |
| 入口スキルから Workflow `agentic-doc:wiki-run` を `args.plugin_root` 付きで起動できるか | はい。research → write → 2 レンズの verify → checkpoint → integrate まで通り、ページは「最新」になった。`lint` の指摘は 0 件 |
| 中断からの再開 | 1 回目はセッションの利用上限（429）で write の後に止まった。ページは「未検証」のまま残り、2 回目の `sync` で処理し直して「最新」になった |

分かったこと:

- 入口スキルは Workflow をバックグラウンドで起動し、完了の通知を受けてから結果を報告した。`claude -p` でも、通知を待ってから終了した。
- エージェントがソースを import して確かめたため、導入先に `__pycache__/` が残った（導入先の `.gitignore` で無視されていなければ未追跡ファイルになる）。
- `checkpoint` が作業ディレクトリのページを消したあと、章の空ディレクトリ（`.agentic-doc/work/overview/`）が残る。git からは見えない。

## 5. 計画 4 の受入検証（2026-10-10〜10-23）

環境: macOS（arm64）、Claude Code 2.1.x（`claude -p`）、Codex CLI 0.162.0、CI は GitHub Actions（ubuntu・macos・windows）。

| 確かめたこと | 結果 |
| --- | --- |
| Python 本体とキャッシュが無い状態での初回実行 | CI の `first-run` ジョブ（pwsh、3 OS）が通った。uv が管理の Python を取得し、`config check` が ok になる |
| Claude Code で git のマーケットプレイスからインストール | `AJpon/agentic-doc@docs/plan4-acceptance` から導入できた。キャッシュ（`~/.claude/plugins/cache/agentic-doc-dev/agentic-doc/0.1.0`）から `setup`、`outline`、`sync` が動いた |
| agentic-doc 自身（日本語、`uv.lock` を除外） | `setup`、`outline`（6 章）、`sync` を通して、20 ページが「最新」、`lint` 0 件、`catalogue check` ok、`audit --lint-only` が終了コード 0 になった。`sync` は利用制限で何度も止まり、そのたびに同じコマンドで再開して完了した。生成ページの点検（定数、テスト名、コマンド数、出典の行番号）で、実コードとの食い違いはなかった |
| Codex（`codex plugin marketplace add`、`codex plugin add`） | 両方のマニフェスト、`source: "./"` の構成で導入できた。`setup`、`outline`（4 ページ）、`sync`（4 ページ検証済み、95 秒）、`status`、`audit`、`stamp --dry-run` が通った |
| 別言語・別規模（BetterExperience、C#、英語、Codex で実行） | `outline` が 3 章 5 ページ。`sync` で app 章の 2 ページが検証済み（3 分 14 秒）、`lint` 0 件 |
| fbx-view の旧形式からの移行 | `catalogue migrate` で 5 章 24 ページに変換し、`status` が旧ツールと同じ「24 ページ最新」になった。`lint` の 4 件は引用の修正で解消した。移行後に 2 ページを書き直して旧版と比べると、記述量は同水準（`render/skinning` 16.7 KB→14.2 KB、出典 39→43 件。`overview/product` 9.7 KB→11.7 KB）で、抜き取りの出典は実コードと一致した |
| 中断と再開 | `unverify` と `checkpoint` により、中断したページは「未検証」で残り、次の `sync` が続きから処理した。計画 4 で、research の結果と書き込み済みの本文のキャッシュを入れた。8 回の再開で、キャッシュ済みの research がやり直されたことはなかった |

分かったこと（計画 4 で直したもの）:

- 除外の pathspec があると、肯定の pathspec が 1 ファイルだけのときに `git ls-files` が 0 件を返すことがある（Apple Git 2.50.1）。除外は Python 側で引くようにした。
- `catalogue migrate` は、今の `exclude` で全て除外される `sources` を、エラーではなく警告にした。
- `plan` の出力の転記で、エージェントが対象を落とすのを検知する（`target_count`）。再開したページは整形の対象に含める。
- `cache show` が、本文の無いページを「書き込み済み」と判定しないようにした。

分かったこと（利用者への注意）:

- `claude -p` は、バックグラウンドの Workflow を 600 秒で止める。`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` を付ける。
- 作業クローンを `.claude` の下に置くと、Write が `docs/wiki/*.md` を「sensitive file」として拒否することがある。未信頼のワークスペースでは `.claude/settings.json` の許可も読まれない。`sync` を試すクローンは `.claude` の外に置く。
- 書き込みが全て拒否されても、`claude -p` は終了コード 0 で終わる。成否は `status` で確かめる。
- 利用制限で止まった `sync` のログは、制限の 1 行だけになる。どのページが済んだかは `status` で見る。
- Codex の縮退動作では、検証が一括になり、観点ごとの独立した検証パスがない。検証は Claude Code より弱い。
- `toc` は `<wiki_dir>/README.md` を再生成する。手で書いた導入文は残らない。
- fbx-view の worktree では、`pre-commit` の `uv-sync` が失敗する（ライセンス上、`fbx` の wheel をコミットしていないため）。環境の問題で、agentic-doc の問題ではない。

先送り（計画 4 に含めない）: `unresolved` の名前の衝突、`audit` の `plan` が作業ディレクトリを作ること、`outline --force` 後に旧カタログにしかないページのファイルが残ること。進捗のログ（`log.jsonl`）、`status --verbose` の段階表示、`checkpoint` が検証の通過を確かめる門、`outline` と `audit` のキャッシュ、`sync --limit N` は計画 5 で扱う。
