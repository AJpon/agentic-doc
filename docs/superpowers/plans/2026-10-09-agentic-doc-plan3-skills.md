# agentic-doc 計画 3: スキル本文・参照文書・Workflow・縮退動作・help

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 入口スキル `wiki` と `wiki-setup`、フェーズごとの参照文書、フェーズ出力のスキーマ、Claude Code の Workflow `wiki-run` を作る。あわせて、それらが必要とするスクリプトのコマンドを足す。これで `/agentic-doc:wiki` の全モード（help・setup・outline・sync・status・audit・stamp）が、Claude Code では Workflow で、他のハーネスでは縮退動作で動くようにする。

**Architecture:**
- 手順・プロンプト・執筆規約・スキーマは `skills/wiki/references/` と `skills/wiki/schemas/` にだけ置く。
- Workflow は、エージェントに「`<SKILL_DIR>/references/<文書>` を読んで従え」という短い指示と入力の JSON、スキーマだけを渡す。持つのは並列化・検証ループ・記録の制御だけ。
- Workflow はファイルを読めない。そのため、スキーマは `dev/embed_schemas.py` が `wiki-run.js` の生成ブロックに埋め込み、整合テストでファイルとの一致を固定する。
- 縮退動作では、1 体のエージェントが `references/run-<モード>.md` に従って同じ参照文書とスクリプトを順に使う。
- Workflow の制御は、node で動かすスタブのハーネス（`tests/workflow_harness.mjs`）で単体テストする。

**Tech Stack:**
- スクリプト: Python 3.11 以上（uv + PEP 723）、jsonschema 4.23 以上
- テスト: pytest、ruff
- Workflow: Claude Code の Workflow（素の JavaScript）。テストのハーネスは Node.js 20 以上（CI の 3 OS には標準で入っている）
- 動作確認: Claude Code 2.1.285 の `claude -p`

**Spec:** `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`（4、7、8、9、10、11 章）。移植元のプロンプトは `/Users/taka/works/dev/fbxsdk/fbx-view/.claude/workflows/wiki.js`（以下「元 wiki.js」）。

## Global Constraints

- **スクリプトの呼び出し**: `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" <コマンド>`。パスは必ずダブルクォートで囲む。カレントディレクトリは導入先のルート。
- **`<SKILL_DIR>` の記法**: 参照文書とスキル本文では、スキルのファイルを `<SKILL_DIR>/...` と書く。`<SKILL_DIR>` は `skills/wiki/SKILL.md` のあるディレクトリを指す。
  - SKILL.md の冒頭で、「`<SKILL_DIR>` はこのファイルのディレクトリ」と定義する。
  - Workflow は絶対パスを `SKILL_DIR = ...` としてプロンプトに書く。
  - `wiki-setup` からは `<SKILL_DIR>/../wiki/` で wiki スキルのファイルを指す（`<SKILL_DIR>` は wiki-setup のディレクトリ）。
  - `${PLUGIN_ROOT}` は使わない。
- **Workflow の名前と引数**
  - `meta.name` は `wiki-run`。Workflow ツールでの名前は `agentic-doc:wiki-run`。
  - `args` は `{mode: "outline"|"sync"|"audit", plugin_root: string（必須）, pages?: string[], force?: boolean, include_unresolved?: boolean, lint_only?: boolean, today?: "YYYY-MM-DD"}`。
  - `SKILL_DIR` は `plugin_root + "/skills/wiki"`。区切りは常に `/` で連結し、`plugin_root` 側の `\` はそのまま残す。
- **Workflow の制約**
  - ファイルシステム、`import()`、`Date.now()`、`Math.random()`、引数なしの `new Date()` を使わない。
  - `meta` は純粋なリテラルにする。
  - トップレベルの `const` はモード分岐より前に置く（元 wiki.js 27〜30 行の注意）。
- **並列度**: ページの処理は 2 ページずつ（`PAGE_CHUNK_SIZE = 2`）。fix は最大 2 ラウンド（`MAX_FIX_ROUNDS = 2`）。
- **機械的な手順のエージェント**: `model: 'haiku'`、`effort: 'low'`。スキーマは `command-result`。標準出力は Workflow 側で `JSON.parse` する（構造を LLM に転記させない）。
- **終了コード**: 全コマンド共通で 0 = 問題なし、1 = 指摘あり、2 = 拒否・入力エラー。
- **JSON の書式**: 2 スペースインデント、`ensure_ascii=False`、末尾に改行 1 つ。
- **文書の言語**
  - 参照文書とスキル本文は英語で書く。導入先の言語に依存しないため。
  - Wiki 本文の言語は設定の `language` に従う。
  - 言語ごとの固定の文字列（関連ページの見出し、未確認の表記）は `config show` の `strings` から取る。
- **コミット**: Conventional Commits で、description は日本語。末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- **ブランチ**: 作業ブランチは `feat/plan3-skills`（`--no-track` で作成済み）。push は `git push -u origin feat/plan3-skills`。
- **触らないもの**: 未追跡の `.agents/`、`.claude/`、`.opencode/`、`docs/codebase/`、`tools/`。未コミットの `.editorconfig` と `agentic-wiki.code-workspace` もステージしない。

## Review Focus

- **エージェントが途中で死ぬ（レート制限など）**:
  - 想定: research・write・verify・記録のどこで死んでも、そのページは未検証のまま残り、他のページは続き、`failed` に載る。
  - テスト: Task 6 のハーネスで、1 ページの research を `null` にする。
- **検証エージェントが全滅する**:
  - 想定: 「指摘なし」と区別して未検証のまま残す。fix も findings の保存もしない。合成の指摘を保存すると、次の sync で無意味な fix から始まってしまうため。
  - テスト: Task 6。
- **LLM が仕様 6 章に反するカタログを書く**: ID と path の不一致、章の上限超え、存在しない related、0 件マッチの glob などは、`catalogue install` が書き込まずに理由を示す。テスト: Task 2。
- **プラグインのインストール先のパスに空白がある**: Workflow のプロンプトに出るスクリプトのパスが、すべてダブルクォートで囲まれている。テスト: Task 6 のハーネスで `plugin_root` に空白を含める。
- **Workflow が無いハーネスで呼ばれる**: SKILL.md が縮退動作の手順へ振り分け、Workflow の名前を出さずに同じスクリプトを順に呼ぶ。テスト:
  - Task 7 の整合テストで、`references/run-*.md` が使うコマンドと参照文書の実在を固定する。
  - 実機での確認は計画 4 で行う。

---

## ファイル構成

```text
skills/wiki/
├── SKILL.md                         # 入口: <SKILL_DIR> の定義、前提の検査、モードの振り分け、help
├── references/
│   ├── overview.md                  # 全体フロー、状態、モードと引数、次の操作の決め方（help が使う）
│   ├── common.md                    # 全フェーズ共通: config show の読み方、context と instructions の扱い、書いてよい場所
│   ├── writing-rules.md             # 執筆規約（仕様書 9 章）
│   ├── step-command.md              # 機械的な手順: 渡されたコマンドを実行し、出力をそのまま返す
│   ├── outline-areas.md             # outline 1: 調査領域を 3〜5 に分ける
│   ├── outline-survey.md            # outline 2: 1 領域を調査する
│   ├── outline-propose.md           # outline 3: 1 つの切り口で構成案を作る
│   ├── outline-merge.md             # outline 4: 評価・統合し、catalogue install と toc
│   ├── sync-research.md
│   ├── sync-write.md
│   ├── verify-citation.md
│   ├── verify-claim.md
│   ├── sync-fix.md
│   ├── sync-integrate.md            # toc、壊れたリンクの修復、post とその失敗の扱い
│   ├── audit-drift.md
│   ├── run-outline.md               # 縮退動作の手順（1 体のエージェントが直列に実行）
│   ├── run-sync.md
│   └── run-audit.md
├── schemas/
│   ├── config.schema.json           # 既存
│   ├── catalogue.schema.json        # 既存
│   ├── findings.schema.json         # findings save が検証に使う
│   ├── command-result.schema.json
│   ├── survey-areas.schema.json
│   ├── survey.schema.json
│   ├── proposal.schema.json
│   ├── outline-result.schema.json
│   ├── research.schema.json
│   ├── write.schema.json
│   ├── verdict.schema.json
│   ├── fix.schema.json
│   ├── integrate.schema.json
│   └── drift.schema.json            # report も入力の検証に使う
└── scripts/adoc/
    ├── cmd_config.py                # config show を追加
    ├── cmd_plan.py                  # 出力に wiki_dir と work_dir、作業ディレクトリの .gitignore を用意
    ├── cmd_findings.py              # save で findings.schema.json を検証
    ├── cmd_catalogue.py             # 新規: catalogue check / install
    ├── cmd_report.py                # 新規: audit の報告
    ├── catalogue.py                 # replace() を分離
    ├── workdir.py                   # ensure_root() を分離
    └── i18n.py                      # unverified_marker と report の文字列
skills/wiki-setup/
├── SKILL.md
└── references/setup.md
com.anthropic.claude-code/workflows/wiki-run.js
dev/embed_schemas.py                 # スキーマを wiki-run.js の生成ブロックに埋め込む（開発用）
tests/
├── workflow_harness.mjs             # Workflow をスタブで実行する node のハーネス
├── test_workflow.py
├── test_catalogue_cmd.py
├── test_report.py
├── test_config_show.py
├── test_skills.py                   # 参照文書・スキル本文の整合テスト
└── （既存のテストに追記）
```

`pyproject.toml` の ruff の `include` に `dev/**/*.py` を足す。

---

### Task 1: スクリプトの補強（`config show`、plan の作業ディレクトリ、findings の検証）

**Files:**
- Modify: `skills/wiki/scripts/adoc/cmd_config.py`
- Modify: `cmd_plan.py`
- Modify: `cmd_findings.py`
- Modify: `workdir.py`
- Modify: `i18n.py`
- Create: `skills/wiki/schemas/findings.schema.json`
- Test: `tests/test_config_show.py`
- Test: `tests/test_plan.py`（追記）
- Test: `tests/test_workdir.py`（追記）

**Interfaces:**
- Consumes:
  - `config.load`
  - `catalogue.select`
  - `workdir.save`
  - `i18n.t`
- Produces:
  - **`config show`**: 標準出力に JSON を出す。パスはすべて `root` からの相対で `/` 区切り。
    ```text
    {"wiki_dir", "catalogue", "catalogue_exists": bool, "language", "audiences", "exclude",
     "context": [{"source": "<file のパス>" | "text", "text": str}], "instructions": [同形],
     "post_commands", "max_pages", "strings": {"related_heading": str, "unverified_marker": str}}
    ```
    - 設定ファイルが無い・不正なときは 2。
    - `file` が無いときは 2（`refused: context file not found: <path> — run setup`）。
  - **`workdir.ensure_root(cfg) -> Path`**: `.agentic-doc/work/` と `.gitignore` を用意する。`save` はこれを使う。
  - **`plan` の出力に足すキー**:
    - `"wiki_dir"`（相対パス）
    - `"work_dir": ".agentic-doc/work"`
    - `plan` は実行のたびに `ensure_root` を呼ぶ。research のノートを置く前に、作業ディレクトリが git から見えなくなっているようにするため。
  - **`findings save`**: 配列を `findings.schema.json` で検証し、合わなければ 2（`refused: findings do not match the schema: <JSON Pointer>: <message>`）。
  - **`findings.schema.json`**: 要素の形は次のとおり。
    - `required: ["severity","location","problem","fix"]`
    - `severity`: `["blocker","major","minor"]` のどれか
    - `lens`: 任意の文字列
    - `additionalProperties: false`
  - **i18n**: `unverified_marker` を足す。
    - en: `(unverified: {what})`
    - ja: `(未確認: {what})`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_config_show.py
def test_show_resolves_context_and_strings(repo):
    repo.write("AGENTS.md", "agent notes\n")
    repo.config(language="ja", instructions=[{"text": "rule"}])
    code, out, _ = run_cli(repo.root, "config", "show")
    d = json.loads(out)
    assert code == 0
    assert d["wiki_dir"] == "docs/wiki" and d["catalogue"] == "docs/wiki/catalogue.json"
    assert d["catalogue_exists"] is False
    assert d["context"] == [{"source": "AGENTS.md", "text": "agent notes\n"}]
    assert d["instructions"] == [{"source": "text", "text": "rule"}]
    assert d["strings"] == {"related_heading": "## 関連ページ", "unverified_marker": "(未確認: {what})"}

def test_show_refuses_missing_context_file(repo):
    repo.config(context=[{"file": "nope.md"}])
    code, _, err = run_cli(repo.root, "config", "show")
    assert code == 2 and "nope.md" in err

def test_show_without_config_is_2(repo):
    assert run_cli(repo.root, "config", "show")[0] == 2
```

```python
# tests/test_plan.py に追記
def test_plan_reports_dirs_and_ignores_workdir(five):
    d = json.loads(run_cli(five.root, "plan")[1])
    assert d["wiki_dir"] == "docs/wiki" and d["work_dir"] == ".agentic-doc/work"
    assert (five.root / ".agentic-doc/work/.gitignore").read_text(encoding="utf-8") == "*\n"
```

```python
# tests/test_workdir.py に追記
def test_save_rejects_findings_off_schema(five):
    pid = page_id_with_file(five)   # 本文ファイルのあるページ。既存のテストと同じ選び方
    bad = json.dumps([{"severity": "fatal", "location": "x", "problem": "p", "fix": "f"}])
    code, _, err = run_cli(five.root, "findings", "save", pid, "-", input=bad)
    assert code == 2 and "/0/severity" in err
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_config_show.py tests/test_plan.py tests/test_workdir.py -v`

Expected: 新しいテストが FAIL（`invalid choice: 'show'`、`KeyError: 'wiki_dir'`、終了コード 0）。

- [ ] **Step 3: 実装する**
  - `config show` は `config.load` の結果から組み立てる。
  - `context` / `instructions` の `file` は `root` 基準で読む。
  - `strings` は `i18n.t(cfg.language, key)` で引く。kwargs を渡さず、テンプレートのまま出す。
  - findings の検証は `Draft202012Validator` で行う。エラーは、パスの順に並べた先頭 1 件を出す。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS、`All checks passed!`。

- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): config show を追加し、plan と findings save を補強"
```

---

### Task 2: `catalogue check` と `catalogue install`

**Files:**
- Create: `skills/wiki/scripts/adoc/cmd_catalogue.py`
- Modify: `catalogue.py`（`replace` を分離）
- Modify: `agentic_doc.py`（`COMMANDS` に `catalogue` を登録）
- Test: `tests/test_catalogue_cmd.py`
- Test: `tests/test_integrity.py`（コマンド集合の期待値を更新）

**Interfaces:**
- Consumes:
  - `config.load`
  - `catalogue.dump`
  - `catalogue.locked`
  - `catalogue.SCHEMA_PATH`
  - `gitutil.ls_files(root, globs, exclude)`
- Produces:
  - **`catalogue.replace(cfg, data) -> None`**: 書式を確かめずに、一時ファイルからの `os.replace` で書く（Windows の再試行も含む）。`save` は `ensure_canonical` のあとにこれを呼ぶ。
  - **`catalogue check [FILE] [--json]`**
    - FILE を省くと設定のカタログを検査する。
    - 指摘の形は `config check` と同じ `{severity: "error"|"warning", code, detail}`。
    - 終了コード: error があれば 1。ファイルが無い・JSON として読めないときは 2。
  - **`catalogue install FILE [--force]`**
    - check で error があれば、指摘を出して 1。何も書かない。
    - 設定のカタログが既にあって `--force` が無ければ 2（`refused: catalogue already exists: <path> — pass --force to overwrite (every source_commit is reset to null)`）。
    - 書くときは全ページの `source_commit` と `reviewed_at` を null にし、ロックの下で `replace` する。
    - 書いたパスを 1 行出して 0。

検査の項目は次の表のとおり（仕様書 6 章）。

| code | severity | 条件 |
|---|---|---|
| `schema` | error | `catalogue.schema.json` に合わない（以降の検査はしない） |
| `format` | error | FILE を省いたときだけ。正規の書式でない |
| `duplicate-id` | error | 同じ `id` が 2 回以上ある |
| `id-form` | error | `id` が `<章>/<ページ>` の 2 区画でない |
| `id-chapter` | error | `id` の章の部分が `chapters[].id` に無い |
| `id-path` | error | `path != id + ".md"` |
| `chapter-count` | error | 章が 6 を超える |
| `chapter-size` | error | 1 章のページが 8 を超える |
| `page-count` | error | ページ数が `max_pages` を超える |
| `audience-unknown` | error | `audience` の値が設定の `audiences[].id` に無い |
| `related-unknown` | error | `related` に存在しない ID がある |
| `related-self` | warning | `related` に自分自身がある |
| `source-glob-empty` | error | glob が対象ファイルに 1 件もマッチしない |
| `chapter-empty` | warning | ページの無い章がある |
| `chapter-order` | warning | 同じ章のページが連続していない |

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_catalogue_cmd.py` を作る。

- フィクスチャ `good(repo)`:
  - 対象ファイル `src/a.py` をコミットする。
  - `sources: ["src/*.py"]` を持つ 2 章 3 ページの正しいカタログを `.agentic-doc/work/outline/catalogue.json` に書く。
  - 設定は既定のままにする。
- テストは表の各 code に 1 つずつ書く。名前は `test_<code の - を _ にしたもの>`。
  - 各テストは、正しいカタログを 1 か所だけ壊して FILE を検査し、その code が出ることを確かめる。
  - severity が error の code では、終了コードが 1 になることも確かめる。
- これに次の 5 件を加える。

```python
def test_good_catalogue_passes(good):
    assert run_cli(good.root, "catalogue", "check", WORK)[0] == 0

def test_install_writes_canonical_and_nulls_commits(good):
    mutate(good, lambda d: d["pages"][0].update(source_commit="a" * 40, reviewed_at="2026-01-01"))
    code, out, _ = run_cli(good.root, "catalogue", "install", WORK)
    assert code == 0 and out.strip() == "docs/wiki/catalogue.json"
    text = (good.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8")
    assert text == dump(json.loads(text))
    assert all(p["source_commit"] is None and p["reviewed_at"] is None for p in json.loads(text)["pages"])

def test_install_refuses_existing_without_force(good):
    run_cli(good.root, "catalogue", "install", WORK)
    code, _, err = run_cli(good.root, "catalogue", "install", WORK)
    assert code == 2 and "--force" in err
    assert run_cli(good.root, "catalogue", "install", WORK, "--force")[0] == 0

def test_install_does_not_write_invalid(good):
    mutate(good, lambda d: d["pages"][0].update(path="wrong.md"))
    assert run_cli(good.root, "catalogue", "install", WORK)[0] == 1
    assert not (good.root / "docs/wiki/catalogue.json").exists()

def test_check_default_catalogue_reports_format(good):
    run_cli(good.root, "catalogue", "install", WORK)
    p = good.root / "docs/wiki/catalogue.json"
    p.write_text(p.read_text(encoding="utf-8").replace("  ", "    "), encoding="utf-8")
    assert "format" in codes(run_cli(good.root, "catalogue", "check", "--json")[1])
```

`WORK = ".agentic-doc/work/outline/catalogue.json"`。`mutate` と `codes` はこのファイル内のヘルパーにする。`test_integrity.py` の期待するコマンド集合に `catalogue` を足す（`report` は Task 3 で足す）。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_catalogue_cmd.py -v`

Expected: FAIL（`invalid choice: 'catalogue'`）。

- [ ] **Step 3: 実装する**
  - 各検査は `cmd_catalogue.check_data(cfg, data) -> list[dict]` に置く。
  - `source-glob-empty` は glob ごとに `gitutil.ls_files(cfg.root, [glob], cfg.exclude)` を呼ぶ。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS。

- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): カタログを検査・設置する catalogue check / install を追加"
```

---

### Task 3: `report`（audit の報告）

**Files:**
- Create: `skills/wiki/scripts/adoc/cmd_report.py`
- Create: `skills/wiki/schemas/drift.schema.json`
- Modify: `agentic_doc.py`
- Modify: `i18n.py`
- Test: `tests/test_report.py`
- Test: `tests/test_integrity.py`（コマンド集合に `report` を足す）

**Interfaces:**
- Consumes:
  - `lint` の検査本体。`--json` と同じ issues を関数で得る。無ければ `lint.collect(cfg, pages, mermaid: bool) -> list[dict]` として切り出す。
  - `state.classify`
  - `state.warnings`
- Produces:
  - **CLI**: `report [--drift FILE|-] [--mermaid] [--json]`
  - **drift の入力**: `{"results": [<drift.schema.json>], "failed": [page_id]}`。
    - 省いた場合は `{"results": [], "failed": []}` として扱う。
    - 結果の各要素は `drift.schema.json` で検証する。合わなければ 2。
  - **`drift.schema.json`**:
    - `{page_id: string, issues: [issue]}`
    - issue は `findings.schema.json` の要素と同じ定義を `$defs` に持つ。
  - **`--json` の出力**:
    ```text
    {"pages_checked", "total_issues",
     "by_page": [{"page_id", "issue_count", "worst_severity", "headline"}],
     "needs_update": [{"page_id", "state"}],
     "drift_failed": [...], "next": [str]}
    ```
    - `by_page` は最悪の重大度、件数の順に並べる。
    - `needs_update` は、状態が missing・unverified・unresolved のページ。
  - **テキスト出力**: 言語に合わせて訳す。表と次の操作。
  - **終了コード**: `total_issues > 0` なら 1。

指摘の取り込み方:
- lint の各指摘は、そのページの指摘として数える。`headline` は `[<code>] <detail>` にする。
- drift の各指摘も数える。`headline` は `problem` の最初の文にする（`。` か `. ` で切る）。
- `headline` は 120 文字を超えたら `…` で切る。
- 重大度の順位は blocker > major > minor。

`next` は、次の順に当てはまるものだけを並べる（元 wiki.js 1323〜1348 行を移したもの）。

| 条件 | 案内 |
|---|---|
| lint に `source-uncommitted` がある | `next_commit`（既存の文字列） |
| `needs_update` に missing・unverified がある | `sync --pages <ids>` |
| `needs_update` に unresolved がある | 内容を確認して `stamp --pages <ids>`、または `sync --pages <ids>` |
| `drift_failed` が空でない | `audit` をやり直す |
| drift に major 以上があるページ | `sync --pages <ids>` |
| lint の指摘があるページ | `lint <ids>` で詳細を見て直す |
| 状態が changed で、drift の結果の指摘が空のページ | `stamp --pages <ids>` |

どれにも当たらなければ `next_none` を出す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_report.py` に、`wiki2`（既存の正しい Wiki のフィクスチャ）と `five` を使うテストを書く。

```python
def test_clean_wiki_reports_nothing(wiki2):
    code, out, _ = run_cli(wiki2.root, "report", "--json")
    d = json.loads(out)
    assert code == 0 and d["total_issues"] == 0 and d["next"] == ["nothing to do"]

def test_lint_and_drift_merge_by_page(wiki2):
    drift = {"results": [{"page_id": PID, "issues": [ISSUE("major", "Wrong. More.")]}], "failed": []}
    break_link(wiki2, PID)                     # link-broken (blocker) を 1 件作る
    d = json.loads(run_cli(wiki2.root, "report", "--json", "--drift", "-", input=json.dumps(drift))[1])
    row = d["by_page"][0]
    assert row == {"page_id": PID, "issue_count": 2, "worst_severity": "blocker", "headline": row["headline"]}
    assert row["headline"].startswith("[link-broken]")

def test_needs_update_and_next_steps(five):
    d = json.loads(run_cli(five.root, "report", "--json")[1])
    assert {(n["page_id"], n["state"]) for n in d["needs_update"]} >= {("g/missing", "missing"), ("g/unresolved", "unresolved")}
    assert any(s.startswith("sync --pages") for s in d["next"])
    assert any("stamp --pages" in s for s in d["next"])

def test_quiet_drift_suggests_stamp(five):
    drift = {"results": [{"page_id": "g/changed", "issues": []}], "failed": ["g/fresh"]}
    d = json.loads(run_cli(five.root, "report", "--json", "--drift", "-", input=json.dumps(drift))[1])
    assert any("stamp --pages g/changed" in s for s in d["next"])
    assert d["drift_failed"] == ["g/fresh"]

def test_drift_off_schema_is_2(wiki2):
    bad = json.dumps({"results": [{"page_id": PID}], "failed": []})
    assert run_cli(wiki2.root, "report", "--drift", "-", input=bad)[0] == 2

def test_text_output_is_localized(five):
    five.config(language="ja")
    assert "次の操作" in run_cli(five.root, "report")[1]
```

`five` のページ ID は既存の conftest のものに合わせる。`ISSUE` と `break_link` はこのファイル内のヘルパーにする。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_report.py -v`

Expected: FAIL（`invalid choice: 'report'`）。

- [ ] **Step 3: 実装する**
  - 案内の文字列は i18n に足す。en と ja の両方に入れる。
    - `report_sync`
    - `report_stamp_or_sync`
    - `report_rerun_audit`
    - `report_fix_lint`
    - `report_stamp_quiet`
    - `report_header`
  - `next` の各文字列に含めるコマンドの部分（例 `sync --pages a b`）は訳さない。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS。

- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): lint と drift の結果から audit の報告を組み立てる report を追加"
```

---

### Task 4: sync の参照文書とフェーズのスキーマ

**Files:**
- Create: `skills/wiki/references/` の次の 9 本
  - `common.md`
  - `writing-rules.md`
  - `step-command.md`
  - `sync-research.md`
  - `sync-write.md`
  - `verify-citation.md`
  - `verify-claim.md`
  - `sync-fix.md`
  - `sync-integrate.md`
- Create: `skills/wiki/schemas/` の次の 6 本
  - `command-result.schema.json`
  - `research.schema.json`
  - `write.schema.json`
  - `verdict.schema.json`
  - `fix.schema.json`
  - `integrate.schema.json`
- Create: `tests/test_skills.py`

**Interfaces:**
- Consumes: Task 1〜3 のコマンド（`config show`、`plan`、`findings`、`lint --citations`、`checkpoint`、`toc`、`post`）
- Produces（後の Task が使う）:
  - **各参照文書の冒頭**: `Inputs:` 節で、エージェントが受け取る入力のキーを列挙する。末尾の `Output:` 節で、返すスキーマのファイル名を示す。
  - **入力のキー**（Workflow と `run-sync.md` がこの名前で渡す）

    | 参照文書 | 入力のキー |
    |---|---|
    | `sync-research.md` | `page`（plan の target）、`note_path` |
    | `sync-write.md` | `page`、`research`、`today` |
    | `verify-citation.md` / `verify-claim.md` | `page` |
    | `sync-fix.md` | `page`、`findings`、`round`、`note_path`（無い場合あり） |
    | `sync-integrate.md` | `pages`（今回処理したページの `{id, path, result}`）、`written_files` |
    | `step-command.md` | `command`、`stdin`（任意） |

  - **スキーマ**

    | ファイル | 中身 |
    |---|---|
    | `command-result` | `{exit_code: integer, stdout: string, stderr: string}`（すべて必須） |
    | `research` | 元 wiki.js の `RESEARCH_SCHEMA` と同じ。`note_path` は、渡された値を返す |
    | `write` | 元 `WRITE_SCHEMA` |
    | `verdict` | 元 `VERDICT_SCHEMA`。`lens` は `["citation","claim"]` のどれか。issue は findings と同じ定義 |
    | `fix` | 元 `FIX_SCHEMA` |
    | `integrate` | `{toc_files: string[], links_fixed: integer, broken_links_remaining: string[], post_ran: boolean, post_passed: boolean, reverted: string[], notes: string}`（`notes` 以外は必須） |

各参照文書に書くこと。移植元は元 wiki.js の行番号で示す。fbx-view 固有の記述（FBX、Qt、`docs/superpowers`、cspell、VitePress、pre-commit の具体名）は一般化するか削る。

| 文書 | 必ず含める内容 |
|---|---|
| `common.md` | ・最初に `config show` を実行して読む<br>・`context` は検証すべき前提で、コードで確かめてから使い、引き写さない<br>・`instructions` は従うべきルール（仕様書 5.2 の表）<br>・Wiki の言語は `language`。識別子・パス・コマンドは原語のまま<br>・書いてよいのは、その文書が許すファイルだけ<br>・作業ノートは `.agentic-doc/work/<page-id>/` に置く<br>・ユーザーに質問しない |
| `writing-rules.md` | 仕様書 9 章の全項目と、元 wiki.js 67〜112 行の理由の説明（ダブルクォートが必要な理由など）。見出し名と未確認の表記は `config show` の `strings` を使う（`{what}` を埋める）。`no_code` の読者層だけを持つページの扱い。`updated` には入力の `today` を使い、`date` を実行しない |
| `step-command.md` | ・渡された `command` を 1 回だけそのまま実行し、終了コード・標準出力・標準エラーを一字一句変えずに返す。直さない、再実行しない、解釈しない<br>・`stdin` があれば標準入力として渡す。手順: `.agentic-doc/work/stdin-<乱数>.json` に書き、シェルのリダイレクト（POSIX は `< file`、PowerShell は `Get-Content -Raw file \| ...`）で渡し、実行後に削除する |
| `sync-research.md` | 元 681〜727 行。sources を `git ls-files` で展開してから読む。ノートは `note_path` に書く。設計文書の扱いは「context と instructions に従う」に置き換える |
| `sync-write.md` | 元 729〜787 行。出力先は `<wiki_dir>/<page.path>`。関連ページの相対リンクはカタログの `path` から作る |
| `verify-citation.md` | 元 789〜832 行。実行するのは `lint --skip-sources --mermaid <id>` と `lint --citations <id>` の 2 つだけ。`--mermaid` の skipped の警告は issue にしない。ファイルを書き換えない |
| `verify-claim.md` | 元 834〜864 行。no_code ページの例外（関連ページへのリンクは対象外）。迷ったら issue にする。ファイルを書き換えない |
| `sync-fix.md` | 元 920〜949 行。図の指摘は図を直す。`round` が 2 なら前回と同じ直し方をしない。指摘が誤りなら `disputed` に入れて本文を変えない。`note_path` が無い（未解決の指摘から再開した）場合は sources を読み直す |
| `sync-integrate.md` | 下に手順を示す |

`sync-integrate.md` の手順:

1. `toc` を実行し、出力されたファイルを記録する。
2. `lint --json --skip-sources` の `link-broken` を Wiki のファイルだけで直す。直せないものは `broken_links_remaining` に入れる。
3. `post` の準備:
   - `post_commands` が空なら `post` を飛ばす（`post_ran: false`）。
   - 空でなければ、実行前に `git status --porcelain` を記録する。
4. `post <written_files と 1 の出力>` を実行する。
5. 失敗したときの扱い（仕様書 11 章）:
   - Wiki のファイルが原因なら、直して 4 から最大 3 回まで繰り返す。
   - 既存のファイルが原因なら、直さずに `notes` に書く。
   - 実行前に変更の無かった Wiki 以外のファイルがフックで変わったら、`git checkout -- <path>` で戻して `reverted` に入れる。実行前から変更のあったファイルには触れない。

`tests/test_skills.py` には、この Task の時点で次を書く。Task 5 と 7 で項目を足す。

```python
REFS = ROOT / "skills/wiki/references"

def test_reference_script_calls_are_quoted_and_exist():
    # 全 .md と wiki-run.js の中の `agentic_doc.py` の出現が `"<SKILL_DIR>/scripts/agentic_doc.py"`
    # （wiki-setup では `"<SKILL_DIR>/../wiki/scripts/agentic_doc.py"`、JS では文字列連結の結果）であること。
    # 直後のコマンド名（とサブコマンド）が build_parser() に存在し、同じ行の --option が
    # そのサブパーサの option_strings にあること
    ...

def test_reference_links_resolve():
    # 文書中の `<SKILL_DIR>/references/*.md` と `<SKILL_DIR>/schemas/*.json` がすべて実在する
    ...

def test_each_reference_has_inputs_and_output_sections():
    for p in REFS.glob("*.md"):
        if p.name in {"overview.md", "common.md", "writing-rules.md"} or p.name.startswith("run-"):
            continue
        text = p.read_text(encoding="utf-8")
        assert "## Inputs" in text and "## Output" in text, p.name

def test_phase_schemas_share_issue_definition():
    # verdict / drift の issue 定義が findings.schema.json の items と一致する
    ...

def test_writing_rules_cover_spec_chapter_9():
    text = (REFS / "writing-rules.md").read_text(encoding="utf-8")
    for needle in ["title", "description", "audience", "updated", "style", "classDef", "fill:", "stroke:",
                   "<br/>", "5", "related_heading", "unverified_marker", "no_code"]:
        assert needle in text
```

`...` の 3 つは本文の正規表現で実装する。コマンド名の検査は `agentic_doc.build_parser()` の `_subparsers` から、コマンド名とオプションの対応表を作って行う。

- [ ] **Step 1: テストを書き、失敗を確かめる**

Run: `uv run pytest tests/test_skills.py -v`

Expected: FAIL（参照文書が無い）。

- [ ] **Step 2: スキーマと参照文書を書く**

- [ ] **Step 3: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS。スキーマは既存の `test_schemas_are_valid_json_schema` でも検査される。このテストの `len(paths) == 2` は、`>= 2` に直す。

- [ ] **Step 4: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(skills): sync の参照文書とフェーズ出力のスキーマを追加"
```

---

### Task 5: outline・audit の参照文書、縮退動作の手順、overview

**Files:**
- Create: `skills/wiki/references/` の次の 9 本
  - `outline-areas.md`
  - `outline-survey.md`
  - `outline-propose.md`
  - `outline-merge.md`
  - `audit-drift.md`
  - `run-outline.md`
  - `run-sync.md`
  - `run-audit.md`
  - `overview.md`
- Create: `skills/wiki/schemas/` の次の 4 本
  - `survey-areas.schema.json`
  - `survey.schema.json`
  - `proposal.schema.json`
  - `outline-result.schema.json`
- Modify: `tests/test_skills.py`

**Interfaces:**
- Consumes:
  - Task 2 の `catalogue check` / `install`
  - Task 3 の `report`
  - Task 4 の参照文書と、入力のキーの約束
- Produces:
  - **入力のキー**

    | 参照文書 | 入力のキー |
    |---|---|
    | `outline-areas.md` | なし |
    | `outline-survey.md` | `area` |
    | `outline-propose.md` | `angle`（`"layer"`、`"flow"`、`"audience"` のどれか）、`surveys` |
    | `outline-merge.md` | `surveys`、`proposals`、`force` |
    | `audit-drift.md` | `page`（plan の target。`sources`、`source_commit`、`reason` を含む） |

  - **スキーマ**

    | ファイル | 中身 |
    |---|---|
    | `survey-areas` | `{areas: [{key, title, scope: string[], questions: string[]}]}`。`minItems 3`、`maxItems 5` |
    | `survey` | 元 `SURVEY_SCHEMA` |
    | `proposal` | `{rationale, chapters: [{id,title,description}], pages: [{id,path,title,audience,brief,sources,related}]}` |
    | `outline-result` | `{installed: boolean, catalogue: string, page_count: integer, rationale: string, issues: string[]}` |

  - `drift`（Task 3 で作成済み）は `audit-drift.md` の出力になる。

各参照文書に書くこと:

| 文書 | 必ず含める内容 |
|---|---|
| `outline-areas.md` | ・トップレベルの構成、ビルド設定、テスト、既存のドキュメントを見て、調査領域を 3〜5 に分ける（元 351〜405 行の 4 領域は例として示し、固定しない）<br>・各領域の `scope`（glob）と、調べるべき `questions` |
| `outline-survey.md` | 元 549〜568 行。evidence は `path:line` で 1 件以上。`doc_gaps`。既存文書と現行コードの食い違いは evidence 付きで挙げる |
| `outline-propose.md` | 元 407〜459 行。切り口 3 種の説明（`layer` = アーキテクチャの層、`flow` = データの流れ、`audience` = 読者層）。制約は仕様書 6 章（`config show` の `audiences` と `max_pages` を使う）。`path = id + ".md"`、連番禁止 |
| `outline-merge.md` | 元 461〜528 行。下に手順を示す |
| `audit-drift.md` | 元 1266〜1292 行。`git diff <source_commit>..HEAD -- <sources>` は `:(glob)` の pathspec で渡す。重大度の基準。ファイルを書き換えない |
| `run-outline.md` | 縮退動作で outline を行う手順。下に示す |
| `run-sync.md` | 縮退動作で sync を行う手順。下に示す |
| `run-audit.md` | 縮退動作で audit を行う手順。下に示す |
| `overview.md` | 仕様書 7 章のモード表とフロー図、状態の表（7.4）、各モードの引数、エラー時の案内（11 章）。次の操作は `status --json` の `next` を基本にし、設定・カタログが無い場合の案内も示す |

`outline-merge.md` の手順:

1. 3 点（目的のページに辿り着けるか、陳腐化を特定しやすいか、章の粒度が揃っているか）で評価し、ベース案に他案の良い点を取り込む。
2. カタログを `.agentic-doc/work/outline/catalogue.json` に書く。カタログの全キーを含め、`source_commit` と `reviewed_at` は null にする。任意の `title` も書ける。
3. `catalogue check .agentic-doc/work/outline/catalogue.json` が 0 で終わるまで直す（最大 3 回）。
4. `catalogue install .agentic-doc/work/outline/catalogue.json` を実行する。入力の `force` が真のときだけ `--force` を付ける。
   - 2 で止まったら `installed: false` を返し、理由を `issues` に入れる。
5. 4 が成功したら `toc` を実行する。

`run-outline.md`（縮退動作）の手順:

1. `areas`: `outline-areas.md` に従う。
2. 各領域を直列に `outline-survey.md` で調べる。
3. 3 つの切り口を直列に `outline-propose.md` で作る。
4. `outline-merge.md` で評価・統合する。

各段で該当の参照文書を読み直す。スキーマの形の結果は自分の作業メモに保つ。

`run-sync.md`（縮退動作）の手順:

1. `plan` を実行する。引数のマッピングは overview.md に従う。
2. 各 target を直列に処理する（a〜f）。
   - a. `pending > 0` なら `findings show <id>` を実行する。配列が返ったら、research と write を飛ばして e へ進む。
   - b. `sync-research.md` に従う。`note_path` は `<work_dir>/<id>/research.md`。
   - c. `sync-write.md` に従う。
   - d. `verify-citation.md` に従い、次に `verify-claim.md` を読み直して従う。どちらの検証でも本文を書き換えない。
   - e. blocker と major があれば `sync-fix.md` に従い、d に戻る（最大 2 ラウンド）。
   - f. 結果を記録する。
     - 残りが無ければ `checkpoint --pages <id> --sha <head> --today <today>` を実行する。
     - 残れば、blocker と major の配列を `findings save <id> -` に渡す。
3. 1 ページの失敗で全体を止めない。
4. `sync-integrate.md` に従う。
5. 結果を報告し、`status` で次の操作を示す。

`run-audit.md`（縮退動作）の手順:

1. `--lint-only` なら `report` だけを実行して終える。
2. そうでなければ `plan` を実行し、targets のうち `state` が `changed` のページを選ぶ。
3. 各ページについて `audit-drift.md` に従う。
4. 結果を `{"results": [...], "failed": [...]}` にまとめ、`report --drift -` に渡す。

`tests/test_skills.py` に足すこと:

- **`test_run_docs_reference_every_phase_doc`**:
  - `run-sync.md` は `sync-research.md`、`sync-write.md`、`verify-citation.md`、`verify-claim.md`、`sync-fix.md`、`sync-integrate.md` に言及する。
  - `run-outline.md` は 4 つの `outline-*.md` に言及する。
  - `run-audit.md` は `audit-drift.md` と `report` に言及する。
- **`test_overview_lists_all_modes`**: overview.md に、`help`、`setup`、`outline`、`sync`、`status`、`audit`、`stamp` と、5 状態の内部名がすべて出る。

- [ ] **Step 1: テストを足し、失敗を確かめる**

Run: `uv run pytest tests/test_skills.py -v`

Expected: 新しいテストが FAIL。

- [ ] **Step 2: スキーマと参照文書を書く**

- [ ] **Step 3: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS。

- [ ] **Step 4: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(skills): outline と audit の参照文書、縮退動作の手順、overview を追加"
```

---

### Task 6: Workflow `wiki-run.js` とそのテストのハーネス

**Files:**
- Modify: `com.anthropic.claude-code/workflows/wiki-run.js`（置き換え）
- Create: `dev/embed_schemas.py`
- Create: `tests/workflow_harness.mjs`
- Create: `tests/test_workflow.py`
- Modify: `pyproject.toml`（ruff の include に `dev/**/*.py`）

**Interfaces:**
- Consumes:
  - Task 4・5 の参照文書の名前と入力のキー
  - スキーマのファイル
  - `plan` の出力（Task 1）
- Produces:
  - **sync の戻り値**:
    ```text
    {mode, head, today,
     pages: [{id, result: "verified"|"unresolved"|"unverified", findings: int, disputed: string[]}],
     failed: [id], skipped, integrate}
    ```
  - **outline の戻り値**: `outline-result`。
  - **audit の戻り値**: `{mode: "audit", lint_only, drift: [drift], drift_failed: [id]}`。報告は入口スキルが `report` で組み立てる。

**生成ブロック**:
- `wiki-run.js` の `// BEGIN GENERATED SCHEMAS` と `// END GENERATED SCHEMAS` の間に、`const SCHEMAS = <JSON>` を 1 行で置く。
- JSON はファイル名から `.schema.json` を除いた名前をキーにし、`config` と `catalogue` 以外の全スキーマを入れる。
- `dev/embed_schemas.py` は、このブロックを書き換える。`--check` を付けると、書き換えずに一致を確かめ、不一致なら 1 を返す。

**ラベルとエージェント**:

| ラベル | 参照文書 | スキーマ | model / effort |
|---|---|---|---|
| `plan` | `step-command.md` | `command-result` | haiku / low |
| `findings:<id>` | `step-command.md` | `command-result` | haiku / low |
| `research:<id>` | `sync-research.md` | `research` | 既定 |
| `write:<id>` | `sync-write.md` | `write` | 既定 |
| `verify:citation:<id>` / `verify:claim:<id>` | `verify-*.md` | `verdict` | 既定 |
| `fix<round>:<id>` | `sync-fix.md` | `fix` | 既定 |
| `record:<id>` | `step-command.md` | `command-result` | haiku / low |
| `integrate` | `sync-integrate.md` | `integrate` | 既定 |
| `areas` | `outline-areas.md` | `survey-areas` | 既定 |
| `survey:<key>` | `outline-survey.md` | `survey` | 既定 |
| `propose:<angle>` | `outline-propose.md` | `proposal` | 既定 |
| `merge` | `outline-merge.md` | `outline-result` | 既定 |
| `drift:<id>` | `audit-drift.md` | `drift` | 既定 |

**プロンプトの組み立て**: `task(ref, inputs)` が次の行を返す。これ以外の文章を Workflow に書かない。

```text
You are one step of the agentic-doc wiki workflow. The repository root is the current directory.
SKILL_DIR = <絶対パス>
Read "<SKILL_DIR>/references/common.md", then "<SKILL_DIR>/references/<ref>", and follow them exactly.
Inputs (JSON):
<JSON.stringify(inputs)>
```

`step-command.md` のときは `common.md` を読ませない。`command` は `cmd(...)` で組み立てる。`cmd(...)` は `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" ...` を返し、空白を含む引数はダブルクォートで囲む。

**sync の制御**:
1. `plan` を実行する。
   - 引数: `--pages`、`--include-unresolved`、`--today` を `args` から渡す。
   - 失敗とみなす条件（throw する）:
     - 終了コードが 0 でない
     - `JSON.parse` できない
     - `head` が `/^[0-9a-f]{40}$/` に合わない
     - `today` が `/^\d{4}-\d{2}-\d{2}$/` に合わない
   - `warnings` に未コミットや未追跡のファイルがあれば `log` する。
2. targets が空なら、`integrate` を呼ばずに戻る。
3. `PAGE_CHUNK_SIZE` ずつ `pipeline(chunk, prep, write, verifyFixRecord)` を回す。チャンク全体が throw しても、他のチャンクの結果は失わない（元 1178〜1187 行）。
   - **prep**:
     - `pending > 0` なら `findings:<id>`（`findings show`）を実行し、配列が得られたら `{resume: findings}` にする。
     - そうでなければ research を行う。`note_path` は `<work_dir>/<id>/research.md`。
     - research が null なら throw する。
   - **write**: `resume` のときは飛ばす。null か `written === false` なら throw する。
   - **verifyFixRecord**:
     - 2 レンズを `parallel` で実行する。
     - 全滅したら fix も record もせずに `result: "unverified"` を返し、`log` する。
     - blocker と major が残る間は fix を最大 2 ラウンド繰り返す。`resume` のときは、round 1 の findings として保存されていたものを使う。
     - 残りが 0 なら、`record:<id>` で `checkpoint --pages <id> --sha <head> --today <today>` を実行する。
       - 終了コードが 0 でなければ `result: "unverified"` にし、`log` する。
     - 残れば、`record:<id>` に `command: findings save <id> -` と `stdin: <blocker と major の JSON 配列>` を渡す。結果は `result: "unresolved"`。標準入力の渡し方は step-command.md に任せ、Workflow はシェルごとの引用符の規則を持たない。
4. 処理できたページが 1 件以上あれば `integrate` を呼ぶ。`written_files` は write が成功したページのファイル。
5. 戻り値の `failed` は、targets のうち pipeline の結果が null だったページ。

**outline の制御**:
1. `areas` を実行する。
2. `pipeline(areas, survey)` を回す。成功が 0 件なら throw する。
3. 3 つの angle を `parallel` で回す。成功が 0 件なら throw する。
4. `merge` に `force: !!args.force` を渡す。

**audit の制御**:
- `lint_only` なら、エージェントを呼ばずに `{mode, lint_only: true, drift: [], drift_failed: []}` を返す。
- そうでなければ、`plan`（引数なし）を実行し、targets のうち `state === "changed"` のページだけを `drift:<id>` に渡す。plan の target はカタログの全キー（`sources`、`source_commit` を含む）と `reason` を持つので、追加の呼び出しは要らない。
- drift は 2 件ずつ `parallel` で回し、null は `drift_failed` に入れる。

**`args` の検証**:
- `plugin_root` が無ければ throw する。メッセージは `args.plugin_root is required (pass ${CLAUDE_PLUGIN_ROOT} from the wiki skill)`。
- `mode` が `outline`・`sync`・`audit` のどれでもなければ throw する。

**ハーネス `tests/workflow_harness.mjs`**:
- 呼び出し: `node workflow_harness.mjs <script> <scenario.json>`。
- スクリプトの `export const meta` を `const meta` に置き換え、`AsyncFunction('agent','parallel','pipeline','phase','log','args','budget', body)` で実行する。
- `agent` の振る舞い:
  - `{label, phase, model, effort, schema のキー, prompt}` を記録する。
  - scenario の `responses` から、`label` の正規表現に最初に合うものを返す。値の配列なら呼ばれるたびに次を返す。
  - 合うものが無ければ throw する。
  - 同時に実行中のエージェント数の最大値を記録する。`await` の前後で増減させ、`setTimeout(0)` で 1 tick 譲る。
- `parallel` と `pipeline` は、Workflow の仕様どおりに実装する。throw したものは null にする。
- 標準出力に `{calls, logs, result, error, max_in_flight}` を JSON で出す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_workflow.py`:
- node が無ければ `pytest.skip` する。
- ヘルパー `run_wf(args, responses) -> dict` を作る。
- 応答の雛形として、関数 `ok_plan(targets)`、`verdict(lens, issues)`、`cmdres(stdout, code=0)` を用意する。

```python
ROOT_SP = "/tmp/plug in/root"   # 空白入り

def labels(r): return [c["label"] for c in r["calls"]]

def test_requires_plugin_root():
    assert "plugin_root" in run_wf({"mode": "sync"}, [])["error"]

def test_no_targets_skips_integrate():
    r = run_wf({"mode": "sync", "plugin_root": ROOT_SP}, [("^plan$", cmdres(ok_plan([])))])
    assert r["result"]["pages"] == [] and "integrate" not in labels(r)

def test_clean_page_is_checkpointed_with_quoted_script():
    r = run_wf(SYNC, CLEAN_RESPONSES(["a/x"]))
    rec = next(c for c in r["calls"] if c["label"] == "record:a/x")
    assert f'"{ROOT_SP}/skills/wiki/scripts/agentic_doc.py" checkpoint --pages a/x --sha {HEAD} --today 2026-10-09' in rec["prompt"]
    assert r["result"]["pages"][0]["result"] == "verified" and "integrate" in labels(r)

def test_persistent_blocker_runs_two_fix_rounds_then_saves_findings():
    r = run_wf(SYNC, BLOCKED_RESPONSES("a/x"))
    assert labels(r).count("fix1:a/x") == 1 and labels(r).count("fix2:a/x") == 1
    rec = next(c for c in r["calls"] if c["label"] == "record:a/x")
    assert "findings save a/x -" in rec["prompt"]
    assert r["result"]["pages"][0]["result"] == "unresolved"

def test_all_verifiers_dead_leaves_page_unverified_without_fix():
    r = run_wf(SYNC, DEAD_VERIFY_RESPONSES("a/x"))
    assert not any(l.startswith(("fix", "record")) for l in labels(r))
    assert r["result"]["pages"][0]["result"] == "unverified"

def test_pending_findings_skip_research_and_write():
    r = run_wf(SYNC, PENDING_RESPONSES("a/x"))
    assert "research:a/x" not in labels(r) and "write:a/x" not in labels(r) and "fix1:a/x" in labels(r)

def test_stale_pending_findings_fall_back_to_research():
    r = run_wf(SYNC, PENDING_NULL_RESPONSES("a/x"))
    assert "research:a/x" in labels(r)

def test_failed_research_marks_failed_and_others_continue():
    r = run_wf(SYNC, CLEAN_RESPONSES(["a/x", "a/y"], dead={"research:a/x"}))
    assert r["result"]["failed"] == ["a/x"] and r["result"]["pages"][0]["id"] == "a/y"

def test_at_most_two_pages_in_flight():
    r = run_wf(SYNC, CLEAN_RESPONSES(["a/1", "a/2", "a/3", "a/4", "a/5"]))
    assert r["max_in_flight"] <= 4

def test_bad_head_throws():
    r = run_wf(SYNC, [("^plan$", cmdres(json.dumps({**json.loads(ok_plan([])), "head": "HEAD"})))])
    assert "head" in r["error"]

def test_outline_force_flag_reaches_merge():
    r = run_wf({"mode": "outline", "plugin_root": ROOT_SP, "force": True}, OUTLINE_RESPONSES)
    merge = next(c for c in r["calls"] if c["label"] == "merge")
    assert '"force":true' in merge["prompt"].replace(" ", "")
    assert sum(l.startswith("survey:") for l in labels(r)) == 3

def test_outline_without_surveys_throws():
    assert run_wf({"mode": "outline", "plugin_root": ROOT_SP}, OUTLINE_DEAD_SURVEYS)["error"]

def test_audit_lint_only_calls_no_agent():
    r = run_wf({"mode": "audit", "plugin_root": ROOT_SP, "lint_only": True}, [])
    assert r["calls"] == [] and r["result"]["lint_only"] is True

def test_audit_collects_drift_and_failures():
    r = run_wf({"mode": "audit", "plugin_root": ROOT_SP}, AUDIT_RESPONSES(ok=["a/x"], dead=["a/y"]))
    assert [d["page_id"] for d in r["result"]["drift"]] == ["a/x"] and r["result"]["drift_failed"] == ["a/y"]

def test_prompts_carry_no_procedure_text():
    # 全プロンプトが task() の 4 要素だけからなる: 参照文書のパスを含み、各行が既定の 4 種の行頭で始まるか JSON
    ...

def test_embedded_schemas_match_files():
    assert subprocess.run([sys.executable, "dev/embed_schemas.py", "--check"], cwd=ROOT).returncode == 0
```

`SYNC`、`CLEAN_RESPONSES`、`BLOCKED_RESPONSES` などの応答の組は、テストのファイル内で組み立てる。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_workflow.py -v`

Expected: FAIL。今の wiki-run.js は `{todo: true}` を返すだけなので。

- [ ] **Step 3: `dev/embed_schemas.py` と `wiki-run.js` を実装する**

`meta.phases` には次を置く。phase() の呼び出しと一字一句そろえる。

- Plan
- Research
- Write
- Verify
- Fix
- Record
- Integrate
- Areas
- Survey
- Propose
- Merge
- Drift

- [ ] **Step 4: 通ることを確かめる**

Run:
```bash
uv run python dev/embed_schemas.py
uv run pytest -q
uv run ruff check .
claude plugin validate .claude-plugin/plugin.json
```

Expected: 全 PASS、`Validation passed`。

- [ ] **Step 5: コミット**

```bash
git add com.anthropic.claude-code dev tests pyproject.toml
git commit -m "feat(workflow): outline・sync・audit を制御する wiki-run を実装"
```

---

### Task 7: 入口スキル `wiki` と `wiki-setup`

**Files:**
- Modify: `skills/wiki/SKILL.md`（置き換え）
- Modify: `skills/wiki-setup/SKILL.md`（置き換え）
- Create: `skills/wiki-setup/references/setup.md`
- Modify: `tests/test_skills.py`

**Interfaces:**
- Consumes:
  - Task 1〜6 のすべて
  - Workflow の `args` の約束（Global Constraints）
- Produces: ユーザーから見た `/agentic-doc:wiki <mode> [args]` と `/agentic-doc:wiki-setup`

`skills/wiki/SKILL.md` に書くこと（英語）:

- **フロントマター**: `name: wiki`。`description` は既存の文言を保ちつつ、help と次の操作の案内も含める。
- **`<SKILL_DIR>` の定義**: このファイルのディレクトリ。スクリプトの呼び出し例を 1 つ示す。
- **前提の検査（全モード共通、help を除く）**:
  1. `config check` が 2 または 1 なら、理由を示して `setup` を案内し、止まる。`setup` モード自体はこの検査をしない。
  2. `outline` 以外で `config show` の `catalogue_exists` が偽なら、`outline` を案内して止まる。
  3. `outline` で、カタログがあり `--force` が無ければ、上書きしない理由（全ページの `source_commit` が null に戻る）を示して止まる。

- **モードの振り分け**:

  | 入力 | 動作 |
  |---|---|
  | （なし）/ `help` / 質問 | `config check` → `status`（あれば）→ `references/overview.md` を読み、現在地と次のコマンドを引数まで示す。CLI の詳細が要るときは `--help` |
  | `setup` | `wiki-setup` スキルを使うよう指示する（Skill ツールがあれば起動し、無ければ `<SKILL_DIR>/../wiki-setup/SKILL.md` を読んで従う） |
  | `status [ids] [--state S] [--verbose]` | `status` をそのまま実行して出力を示す |
  | `stamp [--sha] [--pages] [--dry-run]` | `stamp` をそのまま実行して出力を示す |
  | `outline [--force]` / `sync [--pages ...] [--include-unresolved]` / `audit [--lint-only]` | 下の「実行方式」 |

- **実行方式**:
  - **Workflow ツールがあるとき（Claude Code）**:
    - `agentic-doc:wiki-run` を `args: {"mode": ..., "plugin_root": "${CLAUDE_PLUGIN_ROOT}", ...}` で実行する。
    - `${CLAUDE_PLUGIN_ROOT}` を書くのはこの 1 か所だけ。
    - 結果の扱い:
      - sync: ページごとの結果と `failed` を表にし、最後に `status` を実行して次の操作を示す。
      - audit: `drift` と `drift_failed` を `report --drift -` に渡し、その出力を示す。
      - outline: `installed` が真なら、カタログを人が確認してから `sync` するよう案内する。
  - **Workflow ツールが無いとき**: `references/run-<mode>.md` を読んで従う。

- **書き込みの約束**:
  - 書いてよいのは Wiki のディレクトリ、カタログ、`.agentic-doc/` だけ。例外は、post の失敗時に戻す操作。
  - コミットはしない。ユーザーに任せる。

`skills/wiki-setup/SKILL.md` と `references/setup.md` に書くこと:

- **初回と更新の手順**: 仕様書 7.1 のとおり。
- **推定の根拠**:
  - `language`: README とドキュメントの言語、`git log -n 50 --format=%s` の言語。
  - `post_commands`:
    - `.pre-commit-config.yaml` があれば `pre-commit run --files {files}`。uv のプロジェクトなら `uv run pre-commit run --files {files}`。
    - prettier や markdownlint の設定があれば、それぞれの CLI。
  - `exclude`: vendor、third_party、生成物、大きなフィクスチャのディレクトリ。
  - `audiences`: 既定の 2 層。製品向けの説明が要るリポジトリなら、`no_code: true` の層を提案する。
- **ユーザーへの質問**: ハーネスの質問ツールがあれば使い、無ければ箇条書きで尋ねて回答を待つ。
- **設定ファイル**:
  - `"$schema": "https://raw.githubusercontent.com/AJpon/agentic-doc/main/skills/wiki/schemas/config.schema.json"` を先頭に書く。
  - 書いたあと `config check` を通す。
- **更新時の追加の確認**:
  - `exclude` が変わったら、`lint --json` の `source-glob-empty` と `cite-excluded` から影響するページを示す。
  - カタログが設定の場所に無く、`<wiki_dir>/_catalogue.json` か既定の場所にある場合は、移動か設定の変更を提案する。
- **スクリプトのパス**: `"<SKILL_DIR>/../wiki/scripts/agentic_doc.py"`。

`tests/test_skills.py` に足すこと:

```python
def test_skill_frontmatter():
    for name in ["wiki", "wiki-setup"]:
        fm = yaml.safe_load((ROOT / f"skills/{name}/SKILL.md").read_text(encoding="utf-8").split("---")[1])
        assert fm["name"] == name and 20 < len(fm["description"]) < 1024

def test_wiki_skill_routes_every_mode_and_both_harnesses():
    text = (ROOT / "skills/wiki/SKILL.md").read_text(encoding="utf-8")
    for needle in ["agentic-doc:wiki-run", "${CLAUDE_PLUGIN_ROOT}", "run-outline.md", "run-sync.md", "run-audit.md",
                   "overview.md", "report --drift -", "config check"]:
        assert needle in text
    assert text.count("${CLAUDE_PLUGIN_ROOT}") == 1

def test_plugin_root_token_not_used():
    for p in (ROOT / "skills").rglob("*.md"):
        assert "${PLUGIN_ROOT}" not in p.read_text(encoding="utf-8"), p
```

- [ ] **Step 1: テストを足し、失敗を確かめる**

Run: `uv run pytest tests/test_skills.py -v`

Expected: 新しいテストが FAIL。

- [ ] **Step 2: 2 つの SKILL.md と setup.md を書く**

- [ ] **Step 3: 通ることを確かめる**

Run:
```bash
uv run pytest -q
uv run ruff check .
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .
```

Expected: 全 PASS、`Validation passed` が 2 回。

- [ ] **Step 4: コミット**

```bash
git add skills tests
git commit -m "feat(skills): 入口スキル wiki と wiki-setup を実装"
```

---

### Task 8: 実機での確認と文書の更新

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1〜7 のすべて

- [ ] **Step 1: 小さな導入先を作る**
  - スクラッチパッドに、`src/` に Python ファイル 6 本と `README.md` を持つ git リポジトリを作る。
  - 設定ファイルを置く: `{"version": 1, "language": "ja"}`。
  - カタログは 1 章 1 ページにする。sources は `src/**/*.py`。

- [ ] **Step 2: help・status・sync を Claude Code で動かす**

Run（導入先のディレクトリで）:
```bash
claude -p "/agentic-doc:wiki help" --plugin-dir <このリポジトリ> --allowedTools "Workflow,Skill,Bash,Read,Write,Edit"
claude -p "/agentic-doc:wiki sync" --plugin-dir <このリポジトリ> --allowedTools "Workflow,Skill,Bash,Read,Write,Edit"
uv run --script <このリポジトリ>/skills/wiki/scripts/agentic_doc.py status
```

Expected:
- help: 「未生成 1 ページ、次は sync」と案内する。
- sync: Workflow `agentic-doc:wiki-run` が起動し、ページが書かれる。
- status: ページが「最新」になる。検証の指摘が残った場合は「未検証」で、保留中の指摘が表示される。
- どちらの場合も結果を記録する。
- うまくいかなかった場合の扱い:
  - Workflow の名前が `agentic-doc:wiki-run` で解決できなかった場合は、実際の名前を確かめて SKILL.md とこの計画の Global Constraints を直す。Ruling に残す。
  - Workflow のエージェントに Bash の許可が要った場合は、README に許可の設定を書く。

- [ ] **Step 3: 文書を更新する**
  - 仕様書:
    - 8 章のコマンド表に `config show`、`catalogue check` / `install`、`report` を足す。
    - `plan` の出力に `wiki_dir` と `work_dir` が加わったこと、`findings save` がスキーマで検証することを書く。
    - 4 章に `<SKILL_DIR>` の記法、参照文書の言語（英語）、`args.today` が任意になったこと（`plan` が日付を出すため）を書く。
    - 7.2 に、outline の書き込みが `catalogue install` 経由であることを書く。
    - 7.5 に、報告は `report` が組み立てることを書く。
    - 11 章に、検証が全滅したページの扱いを書く（指摘を保存せず未検証のまま残す）。
  - `AGENTS.md`: 計画 3 を完了済みにする。構成に `references/`、`dev/`、Workflow のテストのハーネスを足す。コマンドに `uv run python dev/embed_schemas.py` を足す。
  - `README.md`: 導入手順（Claude Code、Copilot、Codex）、`/agentic-doc:wiki` の使い方、Workflow のエージェントに必要な許可。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -q && uv run ruff check .`

Expected: 全 PASS。

- [ ] **Step 5: コミット**

```bash
git add docs AGENTS.md README.md skills
git commit -m "docs: 計画 3 の決定を仕様に反映し、README と AGENTS.md を更新"
```
