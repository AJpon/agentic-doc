# agentic-doc 計画 1: 未決事項の解消と土台づくり

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 仕様書 14 章の未決事項 4 件を実機の検証で解消して仕様書に反映し、旧 PoC を取り除いてプラグインの骨組みだけが残る状態にする。

**Architecture:** 3 つの検証（Claude Code のプラグイン、Agent Plugins 1.0 の読み込み、スクリプトの実行方式）は、どれも使い捨てのプローブで行う。プローブは `spikes/` に置き、git には入れない（`.git/info/exclude`）。結果は調査記録 1 本にまとめ、その結論で仕様書を更新してから、旧資産の削除と新しいマニフェストの作成を行う。スクリプト群・スキル・Workflow の実装は、この計画の完了後に作る計画 2 以降で扱う。実行方式が決まるまで、それらの言語とシグネチャを決められないため。

**Tech Stack:** Claude Code 2.1.285（`claude plugin validate`、`claude -p --plugin-dir`）、uv 0.12.11、Python 3.13、Node.js 24、VS Code 1.141、PyPI の `deno` パッケージ、git 2.50

**Spec:** `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`

## Global Constraints

- プラグイン名: `agentic-doc`
- 導入先の設定ファイル: `.agentic-doc.config.json`（リポジトリ直下、JSON のみ）
- Agent Plugins 1.0 の `$schema`: `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`
- Agent Plugins 1.0 の `plugin.json` に書けるトップレベル項目: `$schema`, `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `extensions`
- Claude Code 用マニフェスト: `.claude-plugin/plugin.json`。Workflow は `workflows` 項目で `./com.anthropic.claude-code/workflows/` を指す（仕様書 4 章）
- スクリプトの終了コード: 0 = 問題なし、1 = 指摘あり、2 = 拒否・入力エラー
- JSON の書式: 2 スペースインデント、非 ASCII をエスケープしない、末尾に改行 1 つ
- Workflow のスクリプトはファイルシステムとシェルに触れず、`import()` を使えず、`Date.now()` / `Math.random()` / 引数なしの `new Date()` は例外になる（Claude Code の Workflow ドキュメント）。日付とパスは `args` で渡す
- コミットは Conventional Commits。description は日本語。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- 作業ブランチ: `docs/wiki-plugin-design`（既存）。`main` に直接コミットしない
- 未追跡の `.agents/`、`.opencode/`、`docs/codebase/`、`AGENTS.md` と、未コミットの `.editorconfig`、`agentic-wiki.code-workspace` の変更には触れない

## Review Focus

- **インストール先のパスに空白や非 ASCII 文字が含まれる**: スクリプトの呼び出しが壊れずに動くべき。Task 3 のプローブを `spikes/パス に 空白/` 配下からも実行して確かめる。
- **Windows での呼び出し**（パスの区切り文字、引用符、`uv` / `deno` の起動）: macOS と同じコマンド表記で動くべき。手元で試せないので、Task 3 の Step 8 で所有者に Windows での実行を依頼する。
- **初回実行時のダウンロード**（uv や deno のキャッシュが空、ネットワークが遅い・無い）: 2 回目以降と同じ結果になり、オフラインなら原因の分かるエラーで止まるべき。Task 3 でキャッシュを空にした初回と 2 回目の両方を計測する。
- **git が無い、または導入先が git リポジトリでない**: 終了コード 2 と原因の分かるメッセージで止まるべき。Task 3 の各プローブで `git` の無いディレクトリから実行して確かめる。
- **プラグインの読み込み経路の違い**（`--plugin-dir` で直接読む場合と、マーケットプレイスからインストールした場合）: どちらでもスキルからスクリプトのパスを解決できるべき。Task 1 で両方の経路を試す。

---

### Task 1: Claude Code のプラグイン構成を検証する（未決事項 2・3）

**Files:**
- Create: `spikes/cc-plugin/.claude-plugin/plugin.json`
- Create: `spikes/cc-plugin/.claude-plugin/marketplace.json`
- Create: `spikes/cc-plugin/com.anthropic.claude-code/workflows/probe.js`
- Create: `spikes/cc-plugin/skills/probe/SKILL.md`
- Create: `spikes/cc-plugin/skills/probe/references/hello.md`
- Create: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`（この Task では 1 節だけ書く）

**Interfaces:**
- Produces: 調査記録の「1. Claude Code」節。次の 3 つの問いへの答え（はい／いいえと、根拠になったコマンド出力）
  - Q2: スキルの本文で `${CLAUDE_PLUGIN_ROOT}` が展開され、その値を Workflow の `args` で渡せるか
  - Q3: `workflows` 項目で名前空間ディレクトリを指したとき、`/agentic-doc-probe:probe` として実行できるか
  - Q2 補足: Workflow の中のエージェントが `args.plugin_root + "/skills/probe/references/hello.md"` を読めるか

- [ ] **Step 1: `spikes/` を git から除外する**

Run: `printf 'spikes/\n' >> .git/info/exclude && git status --short | grep spikes || echo ok`
Expected: `ok`

- [ ] **Step 2: プローブのプラグインを作る**

- `plugin.json`: `name` は `agentic-doc-probe`、`workflows` は `["./com.anthropic.claude-code/workflows/"]`
- `probe.js`: `meta.name` は `probe`。`args.plugin_root` を受け取り、`agent()` を 1 回呼ぶ。プロンプトは「`<args.plugin_root>/skills/probe/references/hello.md` を読み、1 行目をそのまま返せ」、スキーマは `{type:'object', required:['line'], properties:{line:{type:'string'}}}`。結果を `return` する
- `SKILL.md`: 「Workflow ツールで `agentic-doc-probe:probe` を `args: {plugin_root: "${CLAUDE_PLUGIN_ROOT}"}` で実行し、結果をそのまま報告せよ」
- `hello.md`: 1 行目は `PROBE-OK-7f3c`

- [ ] **Step 3: マニフェストを検証する**

Run: `claude plugin validate spikes/cc-plugin`
Expected: `Validation passed`（警告は記録する）

- [ ] **Step 4: `--plugin-dir` 経由で実行する**

Run: `claude -p --plugin-dir spikes/cc-plugin --allowedTools "Workflow,Read,Skill" "/agentic-doc-probe:probe スキルを実行して"`
Expected: 出力に `PROBE-OK-7f3c` が含まれる。含まれない場合は、どの段（スキルの読み込み、`${CLAUDE_PLUGIN_ROOT}` の展開、Workflow の読み込み、エージェントの Read）で止まったかを出力から特定して記録する

- [ ] **Step 5: マーケットプレイス経由で実行する**

`marketplace.json` に `spikes/cc-plugin` を 1 件だけ載せ、`claude plugin marketplace add ./spikes/cc-plugin` → `claude plugin install agentic-doc-probe@<マーケットプレイス名>` でインストールしてから Step 4 と同じプロンプトを `--plugin-dir` なしで実行する。
Expected: `PROBE-OK-7f3c`。展開された `plugin_root` の値（インストール先のパス）も記録する。確認後 `claude plugin uninstall agentic-doc-probe` で戻す

- [ ] **Step 6: 失敗した場合の代替案を試す**

Step 4 か 5 が失敗した場合だけ行う。代替案は「Claude Code のスキルのドキュメント（https://code.claude.com/docs/en/skills）で、スキル本文に使える `${CLAUDE_PLUGIN_ROOT}` 以外の変数を確認し、あればそれで渡す」「Workflow を名前空間ではなくルートの `workflows/` に置く」の順に試し、通ったものを記録する。どれも通らなければ、その事実と出力を記録して次の Task に進む

- [ ] **Step 7: 調査記録の 1 節を書いてコミットする**

各問いに「はい／いいえ」、実行したコマンド、出力の該当部分を書く。

```bash
git add docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md
git commit -m "docs(research): Claude Code のプラグイン構成の検証結果を記録"
```

---

### Task 2: Agent Plugins 1.0 の読み込みを検証する（未決事項 4）

**Files:**
- Create: `spikes/ap-plugin/plugin.json`
- Create: `spikes/ap-plugin/skills/probe/SKILL.md`
- Create: `spikes/ap-plugin/skills/probe/scripts/hello.py`
- Modify: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`（「2. Agent Plugins 1.0」節を追加）

**Interfaces:**
- Consumes: なし
- Produces: 調査記録の「2. Agent Plugins 1.0」節。VS Code（Copilot）と Codex CLI それぞれについて
  - スキルが一覧に出て呼び出せるか
  - スキルの本文から、同じスキル内の `scripts/hello.py` をどう指せば実行できたか（相対パス、変数など、実際に通った書き方）
  - `.claude-plugin/plugin.json` が同じディレクトリにあっても、ルートの `plugin.json` が優先されるか

- [ ] **Step 1: プローブのプラグインを作る**

- `plugin.json`: `$schema` は Global Constraints の URL、`name` は `agentic-doc-probe`、`version` は `0.0.1`
- `hello.py`: 標準ライブラリだけで `print("SCRIPT-OK-91ad")` するだけ
- `SKILL.md`: `name: probe`。本文は「このスキルと同じディレクトリにある `scripts/hello.py` を python3 で実行し、出力をそのまま報告せよ」

- [ ] **Step 2: VS Code に読み込ませる**

https://code.visualstudio.com/docs/agent-customization/agent-plugins の手順に従い、ローカルのディレクトリ `spikes/ap-plugin` をプラグインとして追加する。Copilot Chat のエージェントモードで「probe スキルを実行して」と頼む。
Expected: 出力に `SCRIPT-OK-91ad`。スキルの一覧に `probe` が出ていることのスクリーンショットか、チャットの出力を記録する

- [ ] **Step 3: Codex CLI で読み込ませる（所有者の作業）**

Codex CLI は手元に無い。所有者に次を依頼し、結果を受け取る: v0.147.0 以上の Codex CLI をインストールしてログインし、`spikes/ap-plugin` をプラグインとして追加して「probe スキルを実行して」と頼む。
Expected: 出力に `SCRIPT-OK-91ad`。追加に使ったコマンドと Codex のバージョンを記録する

- [ ] **Step 4: 両方のマニフェストを置いた場合を確かめる**

`spikes/ap-plugin/.claude-plugin/plugin.json`（`name` は `agentic-doc-probe-cc`）を追加して Step 2 をやり直し、VS Code がどちらの名前で読み込むかを記録する。あわせて `claude plugin validate spikes/ap-plugin` で、ルートの `plugin.json` が Claude Code の妨げにならないこと（警告の有無）を記録する

- [ ] **Step 5: 調査記録を追記してコミットする**

```bash
git add docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md
git commit -m "docs(research): Agent Plugins 1.0 の読み込みの検証結果を記録"
```

---

### Task 3: スクリプトの実行方式を比較する（未決事項 1）

**Files:**
- Create: `spikes/runtime/fixture/`（下記の手順で作る git リポジトリ）
- Create: `spikes/runtime/uv-pep723/probe.py`
- Create: `spikes/runtime/uv-deno/probe.ts`
- Create: `spikes/runtime/mcp-node/`（`package.json`、`server.ts`、`mcp.json`）
- Modify: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`（「3. 実行方式」節を追加）

**Interfaces:**
- Consumes: Task 1・2 の結論（スキルからスクリプトのパスを指す書き方）
- Produces: 調査記録の「3. 実行方式」節。3 方式の比較表と推奨案

3 つのプローブは同じ仕事をする。仕様書 7.4 の `status` を縮小したもので、次の入出力を持つ。

- 入力: カレントディレクトリの `.agentic-doc.config.json`（`wiki_dir` だけ読む）、`<wiki_dir>/catalogue.json`、加えて YAML 読み込みの確認用に `extra.yaml`
- 処理: 各ページを仕様書 7.4 の表の順に「未生成 / 未検証 / 解決不能 / 変更あり / 最新」に判定する（`git cat-file -e <sha>^{commit}` と `git diff --name-only <sha>..HEAD -- <sources>` を使う）
- 出力: 標準出力に `{"pages":[{"id":..., "state":...}], "yaml_keys":[...]}`（Global Constraints の JSON 書式）。終了コードは 0。git が無い、または git リポジトリでない場所では、標準エラーに理由を出して終了コード 2

- [ ] **Step 1: フィクスチャのリポジトリを作る**

`spikes/runtime/fixture` に git リポジトリを作り、5 状態がそれぞれ 1 ページずつ出るようにする: `src/a.py` と `src/b.py` をコミット（C1）、`src/b.py` を変更してコミット（C2）。カタログの 5 ページは、`source_commit` が C2 で sources が `src/a.py`（最新）、C1 で `src/b.py`（変更あり）、`0000000000000000000000000000000000000000`（解決不能）、null（未検証。本文ファイルはある）、C2 だが本文ファイルが無い（未生成）。`extra.yaml` は `a: 1` と `b: [x, y]` の 2 キー。

- [ ] **Step 2: 期待値を書く**

`spikes/runtime/expected.json` に Step 1 の 5 ページの `{id, state}` と `yaml_keys: ["a","b"]` を書く。各プローブの出力をこれと `diff` で比べる

- [ ] **Step 3: uv + PEP 723 のプローブ**

`probe.py` は先頭に PEP 723 のブロック（`requires-python = ">=3.11"`、`dependencies = ["pyyaml>=6"]`）を持つ。
Run: `cd spikes/runtime/fixture && uv run --script ../uv-pep723/probe.py | diff - ../expected.json && echo same`
Expected: `same`

- [ ] **Step 4: uv + PyPI の deno のプローブ**

`probe.ts` は YAML の読み込みに `jsr:@std/yaml` を使う。
Run: `cd spikes/runtime/fixture && uv run --no-project --with deno deno run --allow-read --allow-run=git ../uv-deno/probe.ts | diff - ../expected.json && echo same`
Expected: `same`。`uv run --no-project --with deno` で `deno` コマンドが使えない場合。なお `--no-project` を付けないと、このリポジトリの `pyproject.toml` の同期が走るは、パッケージが提供する起動方法（`python -m deno` など）をパッケージのページで確かめて、通った書き方を記録する

- [ ] **Step 5: Node.js の MCP サーバーのプローブ**

`server.ts` は stdio の MCP サーバーで、ツール `status`（引数 `cwd: string`）が上の JSON をテキストで返す。YAML は npm の `yaml` パッケージで読む。`mcp.json` で登録し、Claude Code から使う。
Run: `claude -p --mcp-config spikes/runtime/mcp-node/mcp.json --allowedTools "mcp__probe__status" "probe の status ツールを cwd=$(pwd)/spikes/runtime/fixture で呼び、返ってきた JSON だけを出力せよ"`
Expected: 出力の JSON が `expected.json` と同じ内容

- [ ] **Step 6: 失敗系と計測**

各方式について次を実行し、結果を記録する。
- キャッシュを空にした初回と 2 回目の実行時間（`uv cache clean` などで空にする。`time` で計測）
- git リポジトリでないディレクトリ（`spikes/runtime`）からの実行で、終了コード 2 と原因の分かるメッセージが出るか
- フィクスチャを `spikes/パス に 空白/` にコピーして同じコマンドが通るか
- キャッシュが空の状態でのオフライン実行（uv は `UV_OFFLINE=1`、Deno は `deno run --cached-only`、Node は `npm ci --offline`）でどう失敗するか

- [ ] **Step 7: 比較表を書く**

調査記録に、仕様書 14 章の観点（導入先に要求する前提、Windows / macOS / Linux での動作、外部ライブラリの使いやすさ、Agent Plugins 1.0 での配布のしやすさ、Mermaid の構文検査との相性）に、Step 6 の計測と「スキルからの呼び出しの書き方」（Task 1・2 の結論を各方式に当てはめたもの）を加えた表を書く。最後に推奨案を 1 つと、その理由を書く

- [ ] **Step 8: Windows での確認を依頼する（所有者の作業）**

所有者に、Windows の PowerShell で Step 3〜5 のコマンドを実行してもらう（fbx-view の AGENTS.md にあるとおり、Git Bash ではなく PowerShell）。結果を比較表に反映する。所有者が実施できない場合は、比較表の Windows 列を「未確認」と明記して進める

- [ ] **Step 9: コミットする**

```bash
git add docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md
git commit -m "docs(research): スクリプトの実行方式の比較結果を記録"
```

---

### Task 4: 結論を仕様書に反映する

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`（4 章、8 章、14 章、必要なら 5.1 と 10.1）
- Modify: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`（冒頭に「結論」節）

**Interfaces:**
- Consumes: Task 1〜3 の調査記録
- Produces: 未決事項の無い仕様書。計画 2 以降はこの版を前提に書く

- [ ] **Step 1: 所有者に推奨案の承認をもらう**

調査記録の推奨案（実行方式、スキルからの呼び出しの書き方、Workflow へのパスの渡し方、マニフェストの構成）を所有者に示し、承認か変更の指示を受ける。承認されるまで次の Step に進まない

- [ ] **Step 2: 仕様書を更新する**

- 14 章の 4 項目を削除し、決定内容を本文へ移す。実行方式は 8 章の冒頭に、スキルからの呼び出しと Workflow へのパスの渡し方は 4 章と 10.1 に、マニフェストの構成は 4 章に書く
- 決定によって前提が変わる記述（例: YAML 対応を 15 章で「実行方式の決定後に判断」としている箇所、13 章の `pyproject.toml` と `uv.lock` の扱い）を書き直す
- 冒頭の「状態」を「設計確定」にする

- [ ] **Step 3: 未決事項が残っていないことを確かめる**

Run: `grep -nE '未決|保留|TBD|TODO' docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`
Expected: 出力なし（「未決事項」という章自体も無くなっている）

- [ ] **Step 4: コミットする**

```bash
git add docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md
git commit -m "docs(spec): 検証結果をもとに未決事項を確定"
```

---

### Task 5: 旧 PoC を削除し、プラグインの骨組みを作る

**Files:**
- Delete: `tools/`、`agents/`、`skills/`、`hooks/`、`outputs/`、`tests/`、`mkdocs.yml`、`docs/poctodo.md`、`docs/superpowers/context/`、`docs/superpowers/plans/2026-04-04-agentic-doc-agent-plan.md`
- Delete or Modify: `pyproject.toml`、`uv.lock`、`.python-version`（Task 4 で確定した 13 章の扱いに従う）
- Create: `plugin.json`
- Modify: `.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`
- Create: `skills/wiki/SKILL.md`、`skills/wiki-setup/SKILL.md`（中身は 1 段落の仮置き。下記）
- Create: `com.anthropic.claude-code/workflows/wiki.js`（`meta` と、`args` を `log()` して返すだけの仮置き）
- Create: `skills/wiki/assets/work/.gitignore.in`（中身は `*` の 1 行。仕様書 10.2）
- Modify: `.gitignore`（旧 PoC 用の行を削除）
- Modify: `README.md`（下記の 3 項目だけ）

**Interfaces:**
- Consumes: Task 4 で確定した仕様書 4 章（マニフェストの構成、Workflow の配置）
- Produces: 計画 2 以降が中身を足していく骨組み。`claude plugin validate .` が通り、スキル `wiki` / `wiki-setup` と Workflow `wiki` が読み込まれる状態

- [ ] **Step 1: 旧 PoC を削除する**

Run: `git rm -r -q tools agents skills hooks outputs tests mkdocs.yml docs/poctodo.md docs/superpowers/context docs/superpowers/plans/2026-04-04-agentic-doc-agent-plan.md`
（`pyproject.toml`、`uv.lock`、`.python-version` は Task 4 の決定どおりに削除するか残す）
Expected: `git ls-files | grep -E '^(tools|agents|hooks|outputs|tests)/|mkdocs.yml'` の出力が無い

- [ ] **Step 2: マニフェストを書く**

- `plugin.json`: Global Constraints の Agent Plugins 1.0 の項目だけを使う。`name` は `agentic-doc`、`version` は `0.1.0`、`description` は「コードベースから Markdown Wiki を生成し、コードの変化に追随させ続ける」、`repository` は既存の `.claude-plugin/plugin.json` の値、`license` は所有者に確認した値（未定なら書かない）
- `.claude-plugin/plugin.json`: 上と同じメタデータに、Task 4 で確定した `workflows` の指定を足す。旧来の `keywords`（skills, workflows, documentation, wiki）は引き継ぐ
- `.claude-plugin/marketplace.json`: 既存のエントリの説明文を新しい `description` に合わせる

- [ ] **Step 3: スキルと Workflow の仮置きを作る**

- `skills/wiki/SKILL.md`: `name: wiki`、`description` は「Use when generating, updating, auditing, or checking the status of a codebase Markdown wiki (setup, outline, sync, status, audit, stamp).」。本文は「未実装。計画 2 以降で実装する」の 1 行
- `skills/wiki-setup/SKILL.md`: `name: wiki-setup`、`description` は「Use when creating or updating the .agentic-doc.config.json for the codebase wiki.」。本文は同じ 1 行
- `wiki.js`: `meta` は `{ name: 'wiki', description: 'コードベース Wiki の生成・更新' }`。本体は `log(JSON.stringify(args))` して `return { todo: true }` するだけ

- [ ] **Step 4: 検証する**

Run: `claude plugin validate .`
Expected: `Validation passed`（警告があれば内容を確認し、Task 2 で記録した既知の警告以外は直す）

Run: `claude -p --plugin-dir . --allowedTools "Workflow,Skill" "/agentic-doc:wiki を実行して、何が返ったかだけ報告して"`
Expected: スキル `wiki` が読み込まれ、「未実装」の旨が報告される

- [ ] **Step 5: README を書き直す**

README には次の 3 項目だけを書く。詳しい使い方は計画 2 以降で、実装と一緒に書く。
1. このプラグインの目的（仕様書 1 章の 1 段落）
2. 現状は開発中であること
3. 設計は仕様書を参照すること（相対リンク）

- [ ] **Step 6: コミットする**

```bash
git add -A plugin.json .claude-plugin skills com.anthropic.claude-code README.md .gitignore
git commit -m "refactor!: 旧 PoC を削除し、agentic-doc プラグインの骨組みを作成"
```

（`git rm` 済みの削除も同じコミットに入る。未追跡の `.agents/`、`.opencode/`、`docs/codebase/`、`AGENTS.md` を `git add` しないこと）

---

## この計画の完了後

Task 4 で確定した実行方式で、計画 2 以降を writing-plans スキルで作る。想定している分け方は次のとおり（実行方式によって変わりうる）。

| 計画 | 範囲 | 仕様書の章 |
|---|---|---|
| 計画 2 | 決定的なスクリプト群（`config check`、`status`、`plan`、`lint`、`checkpoint`、`stamp`、`toc`、`post`）、JSON Schema、単体テスト | 5、6、7.4、7.6、8、9（lint が検査する部分）、10.2、12 |
| 計画 3 | スキル（`wiki`、`wiki-setup`）、参照文書、Workflow、縮退動作、help | 4、7.1〜7.3、7.5、9、10、11 |
| 計画 4 | 受入検証（4 リポジトリ）と fbx-view の移行、README とエージェント向け文書の仕上げ | 12、13 |
