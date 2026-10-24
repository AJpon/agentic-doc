# agentic-doc 計画 4: 受入検証と fbx-view の移行

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 仕様 12 章の受入検証を、4 リポジトリ・OS・初回実行・配布経路のすべてで実施し、結果を記録する。その前提として、事前の試行で見つかった不具合（git の pathspec の問題）と移行の穴（旧カタログの形式）を直し、計画 3 で先送りした軽微な指摘を片付ける。

**Architecture:**
- Task 1〜5 はコードの変更で、TDD で進める。Task 6〜10 は実機での受入検証で、結果を研究記録の 5 節に書く。Task 11 で文書を仕上げる。
- 受入検証は、導入先のリポジトリを汚さないよう、スクラッチパッドへの clone か git worktree で行う。導入先へのコミット・push・PR は所有者に確認してから行う。
- 所有者にしかできない確認（VS Code の Copilot、Windows の PowerShell）は、手順書を渡して結果を返してもらう。

**Tech Stack:** 計画 3 と同じ（Python 3.11 以上 + uv + PEP 723、pytest、ruff、Node.js 20 以上）。実機: Claude Code 2.1.285 以上、Codex CLI 0.162.0、VS Code + Copilot Chat（所有者）。

**Spec:** `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`（7.1、8、12、13 章）。研究記録: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`。

## 事前の試行で分かったこと（2026-10-10）

fbx-view（`docs/reorganize-architecture-docs`、HEAD 6a377f9）をスクラッチパッドに clone し、手で移行して `config check` / `catalogue check` / `status` / `lint` / `toc` を流した。

- **git の pathspec の不具合**: Apple Git 2.50.1 では、`git ls-files` の肯定の pathspec が「サブディレクトリの中の 1 ファイル」だけで、除外の pathspec が 1 つでもあると、0 件を返す（`git ls-files -- ':(glob)a/b/c.py' ':(exclude,glob)zzz/**'` → 空）。肯定が 2 つ以上か、`a/**` のようなワイルドカードなら正しく返る。`diff`、`status`、`ls-files --others` では起きない。
  - 影響: 設定に `exclude` があると、`catalogue check` と `lint` が実在するファイルを「0 件マッチ」と誤報する。fbx-view では 40 件の誤報が出た。
  - git の既知の問題の系統（共通の前置部分で読み込みを省く最適化と、除外の pathspec の組み合わせ）。git の版を問わず避けられる形に直す（Task 1）。
- **旧カタログの形式**: fbx-view の `_catalogue.json` は、`chapters` が無く、`language` と `citation_style` を持つ。名前を変えるだけでは `catalogue check` を通らない。章は ID の前半（`overview` / `import` / `render` / `app` / `dev`）から作れる。変換するコマンドを足す（Task 2）。
- **`toc` での見た目の変化**: `<wiki_dir>/README.md` が作り直され、元の前書き（Wiki の位置づけ、`docs/superpowers` は履歴であること）が消える。関連ページのリンクから `./` が取れ、フロントマターの `updated` がカタログの `reviewed_at` にそろう。これは仕様どおりの動作として受け入れる。前書きの内容は、設定の `instructions` と `overview/reading-guide` ページに既にある。
- **内容の問題**（移行後に `lint` が出す。移行の作業で直す）: `overview/reading-guide` が `docs/wiki/_catalogue.json:16-24` を、`dev/workflow` が `.venv/.../pre_commit/commands/run.py:65-69` を引用している（どちらも追跡されていない）。

## Global Constraints

- **スクリプトの呼び出し**: `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" <コマンド>`。終了コードは 0 = 問題なし、1 = 指摘あり、2 = 拒否・入力エラー。
- **新しいコマンド**: `adoc/cmd_<名前>.py` に置き、`agentic_doc.py` の `COMMANDS` に登録する。言語に依存する文字列は `adoc/i18n.py` の `ja` と `en` の両方に足す。`tests/test_integrity.py` のコマンド一覧も更新する。
- **JSON の書式**: 2 スペースインデント、`ensure_ascii=False`、末尾に改行 1 つ。
- **Workflow**: 制御だけを書く。スキーマを変えたら `uv run python dev/embed_schemas.py` で埋め込み直す。
- **参照文書とスキル本文**: 英語。スクリプトの呼び出しを変えたら `tests/test_skills.py` が通ること。
- **コミット**: Conventional Commits で、description は日本語。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。ファイルはパスを 1 つずつ指定してステージする（`git add docs` などディレクトリ単位は禁止）。
- **ブランチ**: `docs/plan4-acceptance`（origin/main から `--no-track` で作成済み）。コードの変更もこのブランチに積む。
- **触らないもの**: 未追跡の `.agents/`、`.claude/`、`.opencode/`、`docs/codebase/`、`tools/`。未コミットの `.editorconfig` と `agentic-wiki.code-workspace`。
- **導入先のリポジトリ**: fbx-view・BetterExperience へのコミット・push・PR は、所有者に確認してから行う。それまではスクラッチパッドの clone か worktree の中だけで作業する。

## Review Focus

- **除外の pathspec と 1 ファイルの肯定**: `exclude` がある設定で、`sources` にサブディレクトリの中の 1 ファイルだけを書いたページが、`catalogue check`・`lint`・`plan` で正しく扱われる。テスト: Task 1。
- **旧カタログの変換で情報が落ちる**: `source_commit` と `reviewed_at` を保ったまま移す（移行直後の `status` が移行前と同じ状態を示す）。テスト: Task 2。
- **変換先に既にカタログがある**: 上書きせず、終了コード 2 で止まる。テスト: Task 2。
- **再開したページの整形**: 保存された指摘から再開して書き直したページも `post_commands` の対象に入る。テスト: Task 4 のハーネス。
- **初回実行**: Python 本体も uv のキャッシュも無い状態で、`--help` と `status` が通る。テスト: Task 5 の CI ジョブ。

---

## ファイル構成

```text
skills/wiki/scripts/adoc/gitutil.py          # Task 1: ls_files の除外を Python 側で引く
skills/wiki/scripts/adoc/cmd_catalogue.py    # Task 2: migrate、Task 3: 章 ID の検査と作業ディレクトリ
skills/wiki/scripts/adoc/cmd_report.py       # Task 3: 次の操作の不足
skills/wiki/scripts/adoc/cmd_plan.py         # Task 4: target_count
skills/wiki/scripts/agentic_doc.py           # Task 3: バイトコードを書かない
skills/wiki/references/run-sync.md           # Task 4: integrate の条件
skills/wiki-setup/references/setup.md        # Task 2: 旧カタログの移行
com.anthropic.claude-code/workflows/wiki-run.js  # Task 4
.github/workflows/tests.yml                  # Task 5: first-run ジョブ
docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md  # Task 6〜10 の結果（5 節）
docs/superpowers/acceptance/                  # Task 9・10 で所有者に渡す手順書
```

---

### Task 1: 除外の pathspec で 1 ファイルの肯定が 0 件になる問題を直す

**Files:**
- Modify: `skills/wiki/scripts/adoc/gitutil.py`（`ls_files`）
- Test: `tests/test_gitutil.py`、`tests/test_catalogue_cmd.py`、`tests/test_lint.py`

**Interfaces:**
- Produces: `ls_files(root, globs, exclude) -> list[str]` のシグネチャと意味は変えない。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_ls_files_single_nested_literal_with_exclude(repo):
    repo.write("src/pkg/main.py", "a")
    repo.write("vendor/x.py", "x")
    repo.commit()
    assert gitutil.ls_files(repo.root, ["src/pkg/main.py"], ["vendor/**"]) == ["src/pkg/main.py"]
    assert gitutil.ls_files(repo.root, ["vendor/x.py"], ["vendor/**"]) == []
```

`test_catalogue_cmd.py` と `test_lint.py` には、設定の `exclude` を `["vendor/**"]` にし、ページの `sources` を `["src/pkg/main.py"]` だけにしたとき、`source-glob-empty` が出ないテストを足す（`set_sources` と既存のフィクスチャを使う）。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_gitutil.py tests/test_catalogue_cmd.py tests/test_lint.py -k "exclude" -v`
Expected: macOS の Apple Git では、新しいテストが `[] != ['src/pkg/main.py']` で FAIL。別の git で FAIL しない場合は、git の版を研究記録に書き、テストは回帰の防止として残す。

- [ ] **Step 3: 実装する**

`ls_files` は、肯定の pathspec だけで `git ls-files` を呼び、`exclude` が空でなければ、除外の glob を肯定の pathspec にしてもう 1 回呼んで、その集合を引く。順序は 1 回目の出力の順を保つ。`diff`・`status`・`--others` は今のまま（問題が起きないことを事前の試行で確認済み）。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`
Expected: 全件 PASS。

- [ ] **Step 5: コミット**

`fix(scripts): 除外の pathspec があると 1 ファイルの sources が 0 件と判定される問題を修正`

---

### Task 2: 旧カタログを変換する `catalogue migrate`

**Files:**
- Modify: `skills/wiki/scripts/adoc/cmd_catalogue.py`、`skills/wiki/scripts/adoc/i18n.py`
- Modify: `skills/wiki-setup/references/setup.md`（更新の 4）、仕様 7.1・8・12 章
- Test: `tests/test_catalogue_cmd.py`

**Interfaces:**
- Consumes: `check_data(cfg, data)`、`catalogue.replace(cfg, data)`（計画 3）。
- Produces: `catalogue migrate <old> [--force] [--json]`。

仕様:
- 入力: `{"version": 1, "pages": [...]}` に `language`・`citation_style` などの余分なキーが付き、`chapters` が無いもの。`pages` の各要素は現行の形式と同じ。
- 出力のカタログ:
  - `chapters` は、ページ ID の前半を最初に現れた順に並べる。`title` は ID と同じ、`description` は空文字列。
  - `title` は、`<wiki_dir>/README.md` の最初の `# ` 見出しがあればそれ、無ければ付けない。
  - `pages` はそのまま。`source_commit` と `reviewed_at` も保つ。
  - 余分なトップレベルのキーは捨てる。`language` が設定の `language` と違えば警告を出す。
- 書き込み先は設定の `catalogue`。既にファイルがあれば、`--force` が無い限り終了コード 2 で止まる。
- 書く前に `check_data` を通す。error があれば書かずに一覧を出して終了コード 1。warning だけなら書いて終了コード 0。
- 書けたら、入力ファイルが書き込み先と別なら削除する（git のステージはしない）。
- 出力: 書いた先のパス、章の数、ページ数、警告、そして「章の `title` と `description` を埋めること」という次の操作。`--json` で同じ内容を JSON にする。

- [ ] **Step 1: 失敗するテストを書く**（`wiki` フィクスチャのカタログを旧形式に書き換えて使う）

- `test_migrate_builds_chapters_from_ids`: 章の ID と順序、`title` が ID。
- `test_migrate_keeps_source_commit`: 移行の前後で `status --json` の各ページの状態が同じ。
- `test_migrate_takes_title_from_readme`: README の H1 がカタログの `title` になる。
- `test_migrate_refuses_existing_without_force`: 終了コード 2、既存のファイルは変わらない。
- `test_migrate_reports_errors_without_writing`: 存在しない `related` を含むと終了コード 1、何も書かない、入力も残る。
- `test_migrate_removes_old_file`: 成功すると `_catalogue.json` が消える。
- `test_migrate_warns_language_mismatch`。

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_catalogue_cmd.py -k migrate -v` / Expected: 引数 `migrate` が無いエラーで FAIL。
- [ ] **Step 3: 実装する**
- [ ] **Step 4: setup.md の更新の 4 を書き換える**: 旧名のファイルが見つかったら、移動の代わりに `catalogue migrate "<見つかったパス>"` を提案する。実行後、旧 README の章立てから章の `title` と `description` の案を作って、ユーザーの承認を得てカタログに書く。仕様 7.1 の 4、8 章のコマンド表、12 章の「fbx-view の移行」を同じ内容に直す。
- [ ] **Step 5: 通ることを確かめる** — Run: `uv run pytest -q && uv run ruff check .` / Expected: 全件 PASS（`test_skills.py` が `catalogue migrate` の呼び出しを受け入れる）。
- [ ] **Step 6: コミット** — `feat(scripts): 旧形式のカタログを変換する catalogue migrate を追加`

---

### Task 3: スクリプトの軽微な指摘（計画 3 の先送り分）

**Files:**
- Modify: `cmd_catalogue.py`、`cmd_report.py`、`i18n.py`、`agentic_doc.py`
- Test: `tests/test_catalogue_cmd.py`、`tests/test_report.py`、`tests/test_cli.py`

直すもの:
1. `catalogue check` が章 ID の重複（`duplicate-chapter`、error）と、ID に使えない文字（`id-chars`、error。章 ID・ページ ID の各部分は `^[a-z0-9][a-z0-9-]*$`）を検査する。
2. `catalogue install` が `workdir.ensure_root(cfg)` を呼び、`.agentic-doc/.gitignore` を作る（outline の後に `.agentic-doc/` が無視されないまま残る問題）。
3. `report` の次の操作: minor だけの drift があるページには `report_stamp_or_sync` を、`--lint-only` で `changed` のページがあれば `report_rerun_audit` を出す。
4. `agentic_doc.py` が `adoc` を import する前に `sys.dont_write_bytecode = True` にする（導入先やプラグインのキャッシュに `__pycache__` を残さない）。

- [ ] **Step 1: 失敗するテストを書く**: 項目ごとに 1 つ。4 は、CLI を実行した後に `skills/wiki/scripts/adoc/__pycache__` が増えないことを、一時ディレクトリへ `skills/wiki/scripts` をコピーして確かめる。
- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest -q` / Expected: 新しいテストだけ FAIL。
- [ ] **Step 3: 実装する**
- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -q && uv run ruff check .` / Expected: 全件 PASS。
- [ ] **Step 5: コミット** — `fix(scripts): 章 ID の検査・作業ディレクトリの .gitignore・report の次の操作・__pycache__ を修正`

---

### Task 4: Workflow と縮退動作の軽微な指摘

**Files:**
- Modify: `cmd_plan.py`、`wiki-run.js`、`skills/wiki/references/run-sync.md`
- Test: `tests/test_plan.py`、`tests/test_workflow.py`、`tests/test_skills.py`

直すもの:
1. `plan` の出力に `target_count`（`targets` の件数）を足す。Workflow は、転記された `targets.length` が `target_count` と違えば、stderr 相当の説明付きで throw する。
2. Workflow の integrate の `written_files` に、保存された指摘から再開したページのパスも入れる。
3. `run-sync.md` の 3 節の条件を、Workflow と同じ「1 ページでも処理した（結果が verified・unresolved・unverified のどれかになった）とき」にそろえる。「go straight to step 5」を「skip steps 2–4 and start at step 5 with these findings」と書き直す。

- [ ] **Step 1: 失敗するテストを書く**:
  - `test_plan_reports_target_count`。
  - ハーネス: plan の転記で `targets` を 1 件落とすと throw する。
  - ハーネス: `pending > 0` のページの integrate の入力に、そのページのパスが入る。
- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_plan.py tests/test_workflow.py -v` / Expected: 新しい 3 件が FAIL。
- [ ] **Step 3: 実装する**。スキーマを変えた場合は `uv run python dev/embed_schemas.py`。
- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -q && uv run ruff check . && uv run python dev/embed_schemas.py --check` / Expected: 全件 PASS、埋め込みは最新。
- [ ] **Step 5: コミット** — `fix(workflow): plan の転記の欠落を検知し、再開したページを整形の対象に含める`

---

### Task 5: 初回実行の CI ジョブ

**Files:**
- Modify: `.github/workflows/tests.yml`

`first-run` ジョブを 3 OS で足す。`astral-sh/setup-uv` で uv だけを入れ、`UV_CACHE_DIR` と `UV_PYTHON_INSTALL_DIR` を空の一時ディレクトリに向け、`UV_PYTHON_PREFERENCE=only-managed` にする。そのうえで、`tests` のフィクスチャと同じ形の小さな git リポジトリを作り、`uv run --script skills/wiki/scripts/agentic_doc.py --help` と `config check`、`status` を実行する。シェルは Windows では `pwsh`。

- [ ] **Step 1: ジョブを書く**
- [ ] **Step 2: push して CI で確かめる** — Expected: 3 OS の `first-run` が成功し、ログに uv による Python のダウンロードが出る。
- [ ] **Step 3: コミット** — `ci: Python と uv のキャッシュが無い状態での初回実行を確かめるジョブを追加`

---

### Task 6: 受入検証 — agentic-doc 自身と、Claude Code の git マーケットプレイス

場所: スクラッチパッドに `git clone https://github.com/AJpon/agentic-doc`（このブランチを push した後）。

- [ ] **Step 1: git のマーケットプレイスからインストール**: `claude plugin marketplace add AJpon/agentic-doc`、`claude plugin install agentic-doc@agentic-doc-dev`。キャッシュに置かれたパスを記録する。終わったら、開発中の `--plugin-dir` と混ざらないよう、どちらで動いたかを `config show` の出力のパスで確かめる。
- [ ] **Step 2: setup**: clone の中で `/agentic-doc:wiki setup` を対話で実行する（`claude -p` では質問に答えられないので、所有者に頼むか、推定値をそのまま承認する指示をプロンプトに含める）。`config check` が通ること。
- [ ] **Step 3: outline → sync**: outline の後、カタログを読んで明らかな誤りだけ直し、`sync` を全ページで実行する。
- [ ] **Step 4: 確かめる**: `status` が全ページ「最新」、`lint` の指摘 0、`audit --lint-only` が終了コード 0。失敗したページがあれば `failed` の理由と再実行の結果を記録する。
- [ ] **Step 5: 記録**: 研究記録 5 節に、所要時間、ページ数、失敗と再試行、目についた品質の問題を書く。

---

### Task 7: 受入検証 — fbx-view の移行

場所: `git -C /Users/taka/works/dev/fbxsdk/fbx-view worktree add <スクラッチパッド>/fbx-view-migrate -b docs/migrate-agentic-doc docs/reorganize-architecture-docs`。fbx-view 本体の作業ツリーには触れない。

- [ ] **Step 1: setup の更新フロー**: worktree で `/agentic-doc:wiki setup` を実行し、`catalogue migrate` で旧カタログを変換する。章の `title` と `description` は旧 README の章立てから採る。`exclude` は `resources/**` と `typings/**`、`instructions` に「`docs/superpowers/` は履歴で、現在の振る舞いの根拠として引用しない」を入れる。`post_commands` は fbx-view の pre-commit を推定どおりに設定する。
- [ ] **Step 2: 機械的な検査**: `status`（移行前の `wiki_repin.py` の判定と同じであること）、`lint`（Task 1 の後、`source-glob-empty` が 0 件であること）、`toc`。事前の試行で見つかった 2 件の引用の問題を直す。
- [ ] **Step 3: audit**: `/agentic-doc:wiki audit` を実行し、drift の報告を記録する。
- [ ] **Step 4: sync と品質の比較**: 次の 2 ページを `sync --pages` で書き直し、元の本文と比べる: `render/skinning`（コードの詳細が多い）、`overview/product`（`no_code` の読者）。比べる観点: 引用の数と正しさ（`lint` と目視）、元にあって新しい版で落ちた事実、新しい版の誤り。落ちたものがあれば、執筆規約か参照文書の問題として記録する。
- [ ] **Step 5: 記録**: 研究記録 5 節。
- [ ] **Step 6: 所有者に確認**: worktree のブランチを fbx-view に push して PR にするか、所有者に尋ねる。元の `.claude/workflows/wiki.js` と `scripts/` を消すかもあわせて尋ねる。

---

### Task 8: 受入検証 — BetterExperience（構成の異なるリポジトリ）

場所: スクラッチパッドに `gh repo clone AJpon/BetterExperience`。コミットしない。

- [ ] **Step 1: setup**: 推定値と根拠を記録する。妥当性の基準: `language` がリポジトリの文書の言語と一致する、`exclude` に `bin/`・`obj/` などの生成物が入る、`post_commands` が存在しないツールを指さない。
- [ ] **Step 2: outline**: 妥当性の基準: `catalogue check` が通る、章が 6 以下、各ページの `sources` が C# のプロジェクト構成（`.csproj` 単位）に沿っている、生成物を `sources` に含めない。
- [ ] **Step 3: 1 章だけ sync**: 最初の章のページを `sync --pages` で書き、`lint` の指摘 0 を確かめる。
- [ ] **Step 4: 記録**: 研究記録 5 節。基準を満たさなかったものは、参照文書（`setup.md`・`outline-*.md`）の直すべき点として書く。

---

### Task 9: 受入検証 — 縮退動作（Codex CLI と VS Code の Copilot）

サンプルリポジトリ: スクラッチパッドに、Python の小さな CLI（5〜8 ファイル、README あり）を作って commit する。非 ASCII と空白を含むファイル名を 1 つ入れる。

- [ ] **Step 1: Codex のインストール**: このリポジトリの `.claude-plugin/marketplace.json`（`source: "./"`）を Codex のマーケットプレイスとして追加し、`agentic-doc` をインストールする。キャッシュのパスを記録する。
- [ ] **Step 2: Codex で一連の流れ**: `codex exec` で setup → outline → sync → status → audit → stamp（`--dry-run`）。各段階で `references/run-*.md` に従ったこと（Workflow の名前を出さず、スクリプトを順に呼んだこと）をログで確かめる。終わりに `status` が全ページ「最新」、`lint` の指摘 0。
- [ ] **Step 3: Copilot の手順書**: `docs/superpowers/acceptance/copilot-degraded.md` に、所有者が VS Code で行う手順（インストール、上と同じ一連のコマンド、確かめること、記録する欄）を書いて渡す。所有者の結果を待つ間、Task 10・11 を進める。
- [ ] **Step 4: 記録**: 研究記録 5 節。両方のマニフェストを置いたとき VS Code が読み込む名前（研究記録の未確認事項）も、所有者の結果から書く。

---

### Task 10: 受入検証 — Windows（PowerShell）と Linux

- [ ] **Step 1: Linux**: Task 5 の CI（ubuntu）と既存の `test` ジョブの結果で確かめたことを記録する。
- [ ] **Step 2: Windows の手順書**: `docs/superpowers/acceptance/windows-powershell.md` に、所有者が PowerShell で行う手順を書く: Task 9 のサンプルリポジトリを clone、`uv run --script ... status` / `lint` / `plan` / `catalogue check` の出力を macOS の出力と比べる、Copilot か Claude Code で `sync --pages` を 1 ページ実行して日本語の指摘が化けないこと（計画 3 の修正の実機確認）。
- [ ] **Step 3: 記録**: 所有者の結果を研究記録 5 節と、冒頭の「未確認」の一覧に反映する。

---

### Task 11: 文書の仕上げ

- [ ] **Step 1: 研究記録**: 冒頭の「未確認」を、確かめたものは結果に、確かめられなかったものは理由付きで残す。
- [ ] **Step 2: README**: Codex と Copilot でのインストール手順、fbx-view のような旧形式からの移行手順、受入検証で分かった注意点を書く。
- [ ] **Step 3: マニフェストの `license`**: リポジトリに LICENSE が無い。ライセンスの種類を所有者に尋ね、決まったら LICENSE を置いて 3 つのマニフェストに `license` を足す（`claude plugin validate` を通す）。
- [ ] **Step 4: AGENTS.md と `.github/copilot-instructions.md`**: 計画 4 完了、`catalogue migrate`、受入検証の手順書の場所。
- [ ] **Step 5: 確かめる** — Run: `uv run pytest -q && uv run ruff check . && claude plugin validate .claude-plugin/plugin.json && claude plugin validate .` / Expected: すべて成功。
- [ ] **Step 6: コミット** — `docs: 受入検証の結果を記録し、README と AGENTS.md を仕上げる`

---

## 計画に含めないもの

- sync の結果名 `unresolved` とページの状態名の衝突（計画 3 の先送り）: 名前を変えるとスキーマ・Workflow・参照文書・利用者への報告がすべて変わる。受入検証で利用者が実際に混乱したら別の計画で扱う。
- audit の `plan` が作業ディレクトリを作ること（同）: `.gitignore` 付きで作られるので害がない。
- `outline --force` 後に旧カタログにしか無いページのファイルが残ること（計画 3 の判断どおり）。
