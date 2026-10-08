# agentic-doc 計画 2: 決定的なスクリプト群

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 仕様書 8 章の決定的なスクリプト（`config check`、`status`、`plan`、`checkpoint`、`stamp`、`findings`、`lint`、`toc`、`post`）を、uv + PEP 723 の Python CLI として単体テスト付きで実装する。

**Architecture:** 入口 `skills/wiki/scripts/agentic_doc.py` が PEP 723 で依存を宣言し、同じディレクトリのパッケージ `adoc/` の各モジュールを呼ぶ。git の呼び出し・設定・カタログ・ページ状態の判定を共通の土台にし、各コマンドはその上に薄く載せる。テストは一時ディレクトリに作った git リポジトリに対して、モジュールの関数を直接呼ぶものと、CLI をサブプロセスで実行するものの 2 種類。

**Tech Stack:** Python 3.11 以上、uv（`uv run --script`）、PyYAML 6、jsonschema 4.23 以上、pytest 8、ruff、git

**Spec:** `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`（5、6、7.4、7.5 の 1、7.6、8、9、10.2、11、12 章）

## Global Constraints

- 入口: `skills/wiki/scripts/agentic_doc.py`。呼び出しは `uv run --script "<スキルのディレクトリ>/scripts/agentic_doc.py" <コマンド> [引数]`。カレントディレクトリは導入先のルート
- PEP 723 ブロック: `requires-python = ">=3.11"`、`dependencies = ["pyyaml>=6", "jsonschema>=4.23"]`
- 導入先に要求する前提: uv と git だけ
- 終了コード: 0 = 問題なし、1 = 指摘あり、2 = 拒否・入力エラー（全コマンド共通）
- 入口で `sys.stdout` と `sys.stderr` を UTF-8 に再設定する
- git でファイルパスを出力させる呼び出しには必ず `-c core.quotepath=false` を付ける
- 設定ファイル: `.agentic-doc.config.json`（カレントディレクトリ直下、JSON のみ）。相対パスは設定ファイルのディレクトリ（`root`）基準
- 設定の既定値: `wiki_dir` = `docs/wiki`、`catalogue` = `<wiki_dir>/catalogue.json`、`language` = `en`、`exclude` = `[]`、`context` = README.md / AGENTS.md / CLAUDE.md のうち存在するもの、`instructions` = `[]`、`post_commands` = `[]`、`max_pages` = `24`、`audiences` = contributor / agent（仕様書 5.2 の JSON そのまま）
- JSON の書式: 2 スペースインデント、`ensure_ascii=False`、末尾に改行 1 つ
- 対象ファイル: `git ls-files` の追跡済みファイルから `exclude` を除いたもの
- glob の解釈: `sources` と `exclude` は git の pathspec の `:(glob)` 規則（`*` は `/` を越えない、`**` は越える）。`git ls-files` と `git diff` の両方に同じ pathspec を渡す
- 作業ディレクトリ: `<root>/.agentic-doc/work/<page-id>/findings.json`。初回作成時に `skills/wiki/assets/work/.gitignore.in` を `<root>/.agentic-doc/work/.gitignore` にコピー（既にあれば上書きしない）
- 言語に依存する文字列は `ja` と `en` の表を持ち、表に無い言語は `en`
- コミットは Conventional Commits、description は日本語、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。作業ブランチは `feat/plan2-scripts`

## Review Focus

- **非 ASCII や空白を含むファイル名が sources・引用・変更ファイルに出る**: 状態判定と lint が ASCII 名と同じに動くべき。Task 3 と Task 6 のテストに含める。
- **導入先が squash merge・rebase 後で source_commit が消えている**: `status` は「解決不能」、`stamp` が打ち直し、`sync` の既定対象には入らない。Task 3・4・5 のテストに含める。
- **カタログを人が手で編集して書式（インデント、キー順）が崩れている**: 書き込むコマンドは黙って書式を変えず、終了コード 2 で理由を示すべき。Task 5 のテストに含める。
- **導入先のカレントディレクトリに `pyproject.toml` や `uv.toml` がある**: スクリプトの実行が導入先のプロジェクト設定の影響を受けないべき。Task 1 のテストに含める。
- **fbx-view から移行したカタログの `sources` が `*` で深い階層を指していた**: `:(glob)` 規則では `*` が `/` を越えないため、マッチ数が減る。`config check` と `lint` が 0 件マッチを警告して気付けるべき。Task 6 のテストに含める。

---

## ファイル構成

```text
skills/wiki/
├── scripts/
│   ├── agentic_doc.py          # 入口。PEP 723、UTF-8、引数の定義、終了コード
│   └── adoc/
│       ├── __init__.py
│       ├── errors.py           # Refused（終了コード 2）
│       ├── i18n.py             # ja / en の文字列表
│       ├── gitutil.py          # git の呼び出し
│       ├── config.py           # 設定の読み込みと検査
│       ├── catalogue.py        # カタログの読み書き
│       ├── state.py            # ページ状態の判定
│       ├── workdir.py          # 作業ディレクトリと findings
│       ├── cmd_status.py
│       ├── cmd_plan.py
│       ├── cmd_checkpoint.py
│       ├── cmd_stamp.py
│       ├── cmd_findings.py
│       ├── lint.py             # lint の検査本体と --citations
│       ├── mermaid_check.mjs   # 任意の Mermaid 構文検査
│       ├── cmd_toc.py
│       └── cmd_post.py
└── schemas/
    ├── config.schema.json
    └── catalogue.schema.json
pyproject.toml                  # 開発用。パッケージは作らない
tests/
├── conftest.py                 # Repo フィクスチャと run_cli
└── test_*.py
```

---

### Task 1: 開発環境と CLI の入口

**Files:**
- Create: `pyproject.toml`
- Create: `skills/wiki/scripts/agentic_doc.py`
- Create: `skills/wiki/scripts/adoc/__init__.py`、`errors.py`、`i18n.py`
- Create: `tests/conftest.py`、`tests/test_cli.py`
- Modify: `.gitignore`（`.pytest_cache/`、`.ruff_cache/` を追加）

**Interfaces:**
- Produces:
  - `adoc.errors.Refused(Exception)`: 入口が捕まえて標準エラーに `refused: <message>` を出し、終了コード 2 を返す
  - `adoc.i18n.t(lang: str, key: str, **kw) -> str`: 表に無い言語は `en`、表に無いキーは `KeyError`
  - `agentic_doc.COMMANDS: dict[str, Command]`。`Command` は `help: str`（1 行）、`add_args(parser)`、`run(args) -> int` を持つ。サブコマンドは argparse のサブパーサで、`--help` は `COMMANDS` の `help` から組み立てる。Task 2 以降は `COMMANDS` にエントリを足す
  - `tests/conftest.py`:
    - フィクスチャ `repo(tmp_path) -> Repo`。`Repo.root: Path`、`Repo.write(rel: str, text: str) -> None`、`Repo.commit(msg: str = "c") -> str`（全ファイルを add してコミットし、SHA を返す）、`Repo.git(*args) -> str`、`Repo.config(**overrides) -> None`（`{"version": 1, **overrides}` を書く）、`Repo.catalogue(pages: list[dict], chapters: list[dict] | None = None, path: str = "docs/wiki/catalogue.json") -> None`（ページの省略キーを補う。補う値は `title` = id、`audience` = `["contributor"]`、`brief` = `"b"`、`related` = `[]`、`reviewed_at` = `None`。`chapters` の既定は、ページ id の章部分ごとに `{"id": 章, "title": 章, "description": "d"}`）
    - `run_cli(cwd: Path, *args: str) -> tuple[int, str, str]`: `[sys.executable, <agentic_doc.py>, *args]` を `cwd` で実行する（テストでは uv を介さない）

- [ ] **Step 1: 開発用の pyproject.toml を作る**

`[project]` は `name = "agentic-doc-dev"`、`version = "0.0.0"`、`requires-python = ">=3.11"`、`dependencies = []`。`[dependency-groups] dev = ["pytest>=8", "ruff>=0.15", "pyyaml>=6", "jsonschema>=4.23"]`。`[tool.uv] package = false`。`[tool.pytest.ini_options] testpaths = ["tests"]`、`pythonpath = ["skills/wiki/scripts"]`。

Run: `uv sync && uv run pytest --version`
Expected: `pytest 8.` で始まる行

- [ ] **Step 2: 失敗するテストを書く（`tests/test_cli.py`）**

```python
def test_help_lists_every_command(tmp_path):
    code, out, _ = run_cli(tmp_path, "--help")
    assert code == 0
    for name in COMMANDS:
        assert name in out

def test_unknown_command_exits_2(tmp_path):
    code, _, err = run_cli(tmp_path, "nope")
    assert code == 2

def test_refused_exits_2_with_message(tmp_path, monkeypatch):
    # COMMANDS に一時的に Refused("boom") を投げるコマンドを足して main() を直接呼ぶ
    assert agentic_doc.main(["_boom"]) == 2   # 標準エラーに "refused: boom"

def test_runs_under_uv_script_ignoring_target_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\nversion="0"\ndependencies=["nonexistent-pkg-zzz"]\n')
    (tmp_path / "uv.toml").write_text('index-url = "http://127.0.0.1:9/"\n')
    r = subprocess.run(["uv", "run", "--script", str(SCRIPT), "--help"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0
```

最後のテストが `uv.toml` の影響で失敗した場合は、呼び出しに `--no-config` を足す必要があるということ。その場合は Step 3 で入口の docstring と仕様書 8 章の呼び出し例を `uv run --no-config --script` に直し、テストも同じ形にする（Ruling を台帳に記録）。

- [ ] **Step 2b: 失敗を確かめる**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL（`agentic_doc.py` が無い）

- [ ] **Step 3: 入口と errors / i18n を実装する**

`agentic_doc.py` の先頭は PEP 723 ブロック（Global Constraints の値）。`main(argv: list[str] | None = None) -> int` が UTF-8 の再設定、argparse の組み立て、`Refused` の捕捉を行い、`if __name__ == "__main__": sys.exit(main())`。argparse の使い方エラーも終了コード 2（argparse の既定と同じ）。この Task では `COMMANDS` は空でよい。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest tests/test_cli.py -v && uv run ruff check .`
Expected: PASS、ruff は `All checks passed!`

- [ ] **Step 5: コミット**

```bash
git add pyproject.toml uv.lock .gitignore skills/wiki/scripts tests
git commit -m "feat(scripts): CLI の入口と開発環境を追加"
```

---

### Task 2: git の呼び出しと設定の検査（`config check`）

**Files:**
- Create: `skills/wiki/scripts/adoc/gitutil.py`、`config.py`
- Create: `skills/wiki/schemas/config.schema.json`
- Modify: `skills/wiki/scripts/agentic_doc.py`（`config` コマンドを登録）
- Test: `tests/test_gitutil.py`、`tests/test_config.py`

**Interfaces:**
- Consumes: Task 1 の `Refused`、`COMMANDS`、`repo`、`run_cli`
- Produces:
  - `gitutil.git(root: Path, *args: str) -> GitResult`（`GitResult.code: int`、`GitResult.out: str`）。常に `git -c core.quotepath=false` で実行。git が PATH に無ければ `Refused("git not found on PATH")`
  - `gitutil.ensure_repo(root: Path) -> None`: git リポジトリ外なら `Refused("not a git repository: <root>")`
  - `gitutil.head(root) -> str`（40 桁）、`gitutil.resolve_commit(root, rev) -> str | None`、`gitutil.is_ancestor(root, sha, head) -> bool`
  - `gitutil.pathspecs(globs: list[str], exclude: list[str]) -> list[str]`: `[":(glob)<g>" ...] + [":(exclude,glob)<e>" ...]`。`globs` が空なら `[":(glob)**"]` を先頭にする
  - `gitutil.ls_files(root, globs, exclude) -> list[str]`（`-z` で読む）
  - `gitutil.changed_since(root, sha, globs, exclude) -> list[str] | None`: `git diff --name-only -z <sha>..HEAD -- <pathspecs>`。解決できなければ `None`
  - `gitutil.dirty(root, globs, exclude) -> list[str]`: `git status --porcelain -z -- <pathspecs>` の変更・追加・削除のパス
  - `gitutil.untracked(root, globs, exclude) -> list[str]`: `git ls-files -z --others --exclude-standard -- <pathspecs>`
  - `config.Config`（dataclass、frozen）: `root: Path`、`wiki_dir: Path`、`catalogue: Path`（どちらも絶対パス）、`language: str`、`audiences: list[dict]`、`exclude: list[str]`、`context: list[dict]`、`instructions: list[dict]`、`post_commands: list[str]`、`max_pages: int`
  - `config.CONFIG_NAME = ".agentic-doc.config.json"`
  - `config.load(root: Path) -> Config`: ファイルが無ければ `Refused("config not found: .agentic-doc.config.json — run setup")`。JSON として読めない、または schema に合わなければ `Refused`（理由に JSON Pointer を含める）。既定値を補う
  - `config.check(root: Path) -> list[Issue]`: `Issue` は `{"severity": "error"|"warning", "code": str, "detail": str}`。コード: `schema`（error）、`file-missing`（error、`context`/`instructions` の `file`）、`post-no-files`（error、`{files}` を含まない要素）、`exclude-empty`（warning、0 件マッチ）、`audience-duplicate`（error、`audiences[].id` の重複）
  - CLI `config check [--json]`: error があれば 1、warning だけなら 0、設定ファイルが無ければ 2

`config.schema.json` は仕様書 5.2 の表どおり（`version` は `const: 1` で必須、他は任意、`additionalProperties: false`）。`context` / `instructions` の要素は `oneOf: [{required: [text]}, {required: [file]}]` で、どちらも `additionalProperties: false`。`audiences` の要素は `id`・`title`・`description`・`no_code` すべて必須。`max_pages` は 1 以上の整数。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_gitutil.py`:

```python
def test_git_outside_repo_refused(tmp_path):
    with pytest.raises(Refused, match="not a git repository"):
        gitutil.ensure_repo(tmp_path)

def test_changed_since_reports_non_ascii_and_space_paths(repo):
    repo.write("src/日本語 ファイル.py", "a"); base = repo.commit()
    repo.write("src/日本語 ファイル.py", "b"); repo.commit()
    assert gitutil.changed_since(repo.root, base, ["src/**"], []) == ["src/日本語 ファイル.py"]

def test_changed_since_unresolvable_returns_none(repo):
    repo.write("a.py", "a"); repo.commit()
    assert gitutil.changed_since(repo.root, "0" * 40, ["**"], []) is None

def test_glob_star_does_not_cross_slash(repo):
    repo.write("src/a.py", "a"); repo.write("src/deep/b.py", "b"); repo.commit()
    assert gitutil.ls_files(repo.root, ["src/*.py"], []) == ["src/a.py"]
    assert sorted(gitutil.ls_files(repo.root, ["src/**/*.py"], [])) == ["src/a.py", "src/deep/b.py"]

def test_exclude_applies(repo):
    repo.write("src/a.py", "a"); repo.write("vendor/x.py", "x"); repo.commit()
    assert gitutil.ls_files(repo.root, [], ["vendor/**"]) == ["src/a.py"]

def test_untracked_lists_new_unignored_files(repo):
    repo.write(".gitignore", "*.log\n"); repo.commit()
    repo.write("new.py", "n"); repo.write("x.log", "l")
    assert gitutil.untracked(repo.root, [], []) == ["new.py"]
```

`tests/test_config.py`:

```python
def test_load_applies_defaults(repo):
    repo.config(); c = config.load(repo.root)
    assert c.wiki_dir == repo.root / "docs/wiki"
    assert c.catalogue == repo.root / "docs/wiki/catalogue.json"
    assert c.language == "en" and c.max_pages == 24
    assert [a["id"] for a in c.audiences] == ["contributor", "agent"]

def test_catalogue_default_follows_wiki_dir(repo):
    repo.config(wiki_dir="wiki"); assert config.load(repo.root).catalogue == repo.root / "wiki/catalogue.json"

def test_context_default_uses_existing_files(repo):
    repo.write("README.md", "r"); repo.write("AGENTS.md", "a"); repo.config()
    assert config.load(repo.root).context == [{"file": "README.md"}, {"file": "AGENTS.md"}]

def test_missing_config_refused(repo):
    with pytest.raises(Refused, match="run setup"):
        config.load(repo.root)

def test_bare_string_instruction_rejected(repo):
    repo.config(instructions=["do x"])
    with pytest.raises(Refused, match="/instructions/0"):
        config.load(repo.root)

def test_check_reports_each_code(repo):
    repo.config(context=[{"file": "nope.md"}], post_commands=["prettier"], exclude=["zzz/**"],
                audiences=[{"id": "a", "title": "A", "description": "d", "no_code": False}] * 2)
    codes = {i["code"]: i["severity"] for i in config.check(repo.root)}
    assert codes == {"file-missing": "error", "post-no-files": "error",
                     "exclude-empty": "warning", "audience-duplicate": "error"}

def test_cli_config_check_exit_codes(repo):
    assert run_cli(repo.root, "config", "check")[0] == 2
    repo.config(); assert run_cli(repo.root, "config", "check")[0] == 0
    repo.config(post_commands=["x"]); assert run_cli(repo.root, "config", "check")[0] == 1
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_gitutil.py tests/test_config.py -v`
Expected: FAIL（モジュールが無い）

- [ ] **Step 3: `gitutil.py`、`config.py`、`config.schema.json` を実装し、`config` コマンドを登録する**

schema のパスは `Path(__file__).resolve().parents[2] / "schemas" / "config.schema.json"`。検証は `jsonschema.Draft202012Validator`。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest tests/test_gitutil.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): git の呼び出しと設定ファイルの検査を追加"
```

---

### Task 3: カタログ・ページ状態・`status`

**Files:**
- Create: `skills/wiki/scripts/adoc/catalogue.py`、`state.py`、`workdir.py`、`cmd_status.py`
- Create: `skills/wiki/schemas/catalogue.schema.json`
- Modify: `skills/wiki/scripts/adoc/i18n.py`（状態名と status の文言）、`agentic_doc.py`
- Test: `tests/test_catalogue.py`、`tests/test_state.py`、`tests/test_status.py`

**Interfaces:**
- Consumes: Task 2 の `Config`、`config.load`、`gitutil.*`
- Produces:
  - `catalogue.load(cfg: Config) -> dict`: 無ければ `Refused("catalogue not found: <path> — run outline")`。schema 不一致は `Refused`
  - `catalogue.dump(data: dict) -> str`（Global Constraints の JSON 書式）
  - `catalogue.save(cfg, data) -> None`: 書く前に、読み込んだ元のテキストが `dump(json.loads(元))` と一致することを確かめ、一致しなければ `Refused("catalogue is not in canonical format (2-space JSON); refusing to rewrite")`
  - `catalogue.page_index(data) -> dict[str, dict]`、`catalogue.page_file(cfg, page) -> Path`
  - `state.State`（`StrEnum`）: `MISSING = "missing"`、`UNVERIFIED = "unverified"`、`UNRESOLVED = "unresolved"`、`CHANGED = "changed"`、`FRESH = "fresh"`
  - `state.PageStatus`（dataclass）: `id`、`state: State`、`base: str | None`、`reviewed_at: str | None`、`changed: list[str]`、`pending: int`（保留中の指摘の件数）
  - `state.classify(cfg, page) -> PageStatus`: 判定順は仕様書 7.4 の表（missing → unverified → unresolved → changed → fresh）。changed の判定は `gitutil.changed_since(cfg.root, sha, page["sources"], cfg.exclude)`
  - `state.warnings(cfg, pages) -> dict`: `{"uncommitted": [...], "untracked": [...]}`。全ページの sources に対する `gitutil.dirty` と `gitutil.untracked`
  - `workdir.findings_path(cfg, page_id) -> Path`、`workdir.pending_count(cfg, page_id, page_text: str | None) -> int`（ハッシュ不一致なら 0。読み込み側の詳細は Task 5）
  - CLI `status [ID ...] [--state STATE] [--verbose] [--json]`
    - `--json` の出力: `{"head": str, "wiki_dir": str, "catalogue": str, "pages": [{"id","state","base","reviewed_at","changed","pending"}], "counts": {state: int}, "warnings": {...}, "next": [str]}`
    - テキスト出力は仕様書 7.4 の例の形。状態名・見出し・次の操作は `i18n.t(cfg.language, ...)`。`changed` は先頭 1 件と「ほか N 件」、`--verbose` で全件と sources
    - `next` の規則: missing・unverified・changed が 1 件以上なら sync の案内（件数入り）。unresolved が 1 件以上なら stamp の案内（`stamp --pages <id ...>` まで）。warnings があればコミットの案内。すべて fresh なら「対応不要」
    - 終了コード: 常に 0（未知の ID は 2）

`catalogue.schema.json` は仕様書 6 章どおり。トップレベルは `version`（`const: 1`）、`chapters`、`pages`（すべて必須）と任意の `title`（文字列。目次の H1 に使う。Task 7）。ページは 9 キーすべて必須で、`source_commit` は `^[0-9a-f]{40}$` か null、`reviewed_at` は `^\d{4}-\d{2}-\d{2}$` か null。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_state.py` は 5 状態を 1 ページずつ作る（計画 1 のフィクスチャと同じ構成）:

```python
@pytest.fixture
def five(repo):
    repo.write("src/a.py", "a"); repo.write("src/b.py", "b"); c1 = repo.commit()
    repo.write("src/b.py", "b2"); c2 = repo.commit()
    for p in ["fresh", "changed", "unresolved", "unverified"]:
        repo.write(f"docs/wiki/g/{p}.md", "x")
    repo.config()
    repo.catalogue([
        {"id": "g/fresh", "path": "g/fresh.md", "sources": ["src/a.py"], "source_commit": c2},
        {"id": "g/changed", "path": "g/changed.md", "sources": ["src/b.py"], "source_commit": c1},
        {"id": "g/unresolved", "path": "g/unresolved.md", "sources": ["src/a.py"], "source_commit": "0" * 40},
        {"id": "g/unverified", "path": "g/unverified.md", "sources": ["src/a.py"], "source_commit": None},
        {"id": "g/missing", "path": "g/missing.md", "sources": ["src/a.py"], "source_commit": c2},
    ])
    repo.commit()
    return repo

def test_classify_five_states(five):
    cfg = config.load(five.root); data = catalogue.load(cfg)
    got = {p["id"]: state.classify(cfg, p).state for p in data["pages"]}
    assert got == {"g/fresh": "fresh", "g/changed": "changed", "g/unresolved": "unresolved",
                   "g/unverified": "unverified", "g/missing": "missing"}

def test_changed_lists_files(five):
    cfg = config.load(five.root); p = catalogue.page_index(catalogue.load(cfg))["g/changed"]
    assert state.classify(cfg, p).changed == ["src/b.py"]

def test_excluded_change_does_not_make_page_changed(repo):
    # sources ["src/**"]、exclude ["src/gen/**"]。src/gen/x.py だけ変えても fresh
```

`tests/test_catalogue.py`:

```python
def test_dump_format():
    assert catalogue.dump({"a": "日本"}) == '{\n  "a": "日本"\n}\n'

def test_missing_catalogue_refused(repo):
    repo.config()
    with pytest.raises(Refused, match="run outline"):
        catalogue.load(config.load(repo.root))

def test_save_refuses_non_canonical(repo):
    repo.config(); repo.write("docs/wiki/catalogue.json", '{"version":1,"chapters":[],"pages":[]}')
    cfg = config.load(repo.root); data = catalogue.load(cfg)
    with pytest.raises(Refused, match="canonical"):
        catalogue.save(cfg, data)
```

`tests/test_status.py`（`five` フィクスチャを conftest に移して共有する）:

```python
def test_status_json(five):
    code, out, _ = run_cli(five.root, "status", "--json")
    d = json.loads(out)
    assert code == 0 and d["counts"] == {"fresh": 1, "changed": 1, "unresolved": 1, "unverified": 1, "missing": 1}
    assert any("stamp --pages g/unresolved" in n for n in d["next"])

def test_status_filters(five):
    d = json.loads(run_cli(five.root, "status", "--json", "--state", "changed")[1])
    assert [p["id"] for p in d["pages"]] == ["g/changed"]

def test_status_unknown_id_exits_2(five):
    assert run_cli(five.root, "status", "nope")[0] == 2

def test_status_warns_uncommitted_and_untracked(five):
    set_sources(five, "g/fresh", ["src/**"]); five.commit()   # src/new.py を sources の範囲に入れる
    five.write("src/a.py", "dirty"); five.write("src/new.py", "n")
    w = json.loads(run_cli(five.root, "status", "--json")[1])["warnings"]
    assert w == {"uncommitted": ["src/a.py"], "untracked": ["src/new.py"]}

def test_status_text_in_japanese(five):
    five.config(language="ja"); out = run_cli(five.root, "status")[1]
    assert "変更あり" in out and "解決不能" in out

def test_status_outside_repo_exits_2(tmp_path):
    assert run_cli(tmp_path, "status")[0] == 2
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run pytest tests/test_catalogue.py tests/test_state.py tests/test_status.py -v`
Expected: FAIL

- [ ] **Step 3: 実装する**

`workdir.pending_count` は Task 5 で本実装する。この Task では `findings.json` が無ければ 0 を返すだけでよい。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest -v`
Expected: PASS（Task 1〜3 の全テスト）

- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): カタログの読み書きとページ状態の判定、status を追加"
```

---

### Task 4: `plan`

**Files:**
- Create: `skills/wiki/scripts/adoc/cmd_plan.py`
- Modify: `agentic_doc.py`
- Test: `tests/test_plan.py`

**Interfaces:**
- Consumes: Task 3 の `state.classify`、`state.warnings`、`catalogue.load`、`gitutil.head`
- Produces: CLI `plan [--pages ID ...] [--include-unresolved] [--today YYYY-MM-DD]`。標準出力に JSON:
  `{"head": "<40桁>", "today": "YYYY-MM-DD", "targets": [<カタログのページ全キー> + {"state": str, "reason": str, "pending": int}], "skipped": [{"id": str, "state": str}], "warnings": {...}}`
  - 既定の対象: missing・unverified・changed。`--include-unresolved` で unresolved も足す
  - `--pages` 指定時: 指定したページだけを、状態に関係なく対象にする（fresh も含む）。未知の ID は 2
  - `reason`: missing は「file not found」、unverified は「never verified」（pending > 0 なら件数も）、changed は変更ファイルの先頭 5 件、unresolved は「source_commit not found」、明示指定の fresh は「requested」
  - `--today` の既定は `datetime.date.today().isoformat()`
  - 終了コード: 0

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_plan_default_targets(five):
    d = json.loads(run_cli(five.root, "plan", "--today", "2026-10-09")[1])
    assert sorted(t["id"] for t in d["targets"]) == ["g/changed", "g/missing", "g/unverified"]
    assert {s["id"] for s in d["skipped"]} == {"g/fresh", "g/unresolved"}
    assert len(d["head"]) == 40 and d["today"] == "2026-10-09"

def test_plan_include_unresolved(five):
    d = json.loads(run_cli(five.root, "plan", "--include-unresolved")[1])
    assert "g/unresolved" in {t["id"] for t in d["targets"]}

def test_plan_explicit_pages_ignore_state(five):
    d = json.loads(run_cli(five.root, "plan", "--pages", "g/fresh")[1])
    assert [(t["id"], t["reason"]) for t in d["targets"]] == [("g/fresh", "requested")]

def test_plan_targets_carry_catalogue_fields(five):
    t = json.loads(run_cli(five.root, "plan")[1])["targets"][0]
    assert {"id", "path", "title", "audience", "brief", "sources", "related", "source_commit", "state", "reason"} <= t.keys()
```

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_plan.py -v` / Expected: FAIL
- [ ] **Step 3: 実装する**
- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -v` / Expected: PASS
- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): sync の対象を決める plan を追加"
```

---

### Task 5: 作業ディレクトリと `findings`・`checkpoint`・`stamp`

**Files:**
- Modify: `skills/wiki/scripts/adoc/workdir.py`
- Create: `skills/wiki/scripts/adoc/cmd_findings.py`、`cmd_checkpoint.py`、`cmd_stamp.py`
- Modify: `agentic_doc.py`
- Test: `tests/test_workdir.py`、`tests/test_checkpoint.py`、`tests/test_stamp.py`

**Interfaces:**
- Consumes: Task 3 の `catalogue.save`、`state.classify`、`catalogue.page_file`
- Produces:
  - `workdir.save(cfg, page_id: str, findings: list[dict], page_text: str) -> Path`: `{"page_sha256": <本文の sha256>, "findings": [...]}` を書く。初回は `.gitignore.in` をコピーする
  - `workdir.load(cfg, page_id, page_text: str) -> list[dict] | None`: 無ければ None。ハッシュ不一致ならファイルを削除して None
  - `workdir.clear(cfg, page_id) -> None`
  - CLI `findings save PAGE_ID FILE`（FILE は findings の JSON 配列、`-` で標準入力）、`findings show PAGE_ID`（JSON。無ければ `null`）、`findings clear PAGE_ID`。未知の ID は 2。`show` は本文と照合して破棄判定まで行う
  - CLI `checkpoint --pages ID ... [--sha REV] [--today YYYY-MM-DD]`: 指定ページの `source_commit`（既定 HEAD）と `reviewed_at` を書き、作業ディレクトリの該当ページを削除する。本文ファイルが無いページは `Refused`。終了コード 0
  - CLI `stamp [--sha REV] [--pages ID ...] [--dry-run]`: 仕様書 7.6 の規則
    - 既定の対象は全ページ。unresolved と fresh を打ち直す。missing と unverified は打ち直さずスキップ。changed は `--pages` で明示したときだけ打ち直し、それ以外はスキップ
    - 拒否（2）: `--sha` が解決できない、HEAD の祖先でない、未知の ID、対象ページの sources に未コミットの変更がある、カタログが canonical でない
    - 出力: 打ち直し・スキップ（理由付き）・変更なしの一覧。スキップがあれば 1、なければ 0
    - `reviewed_at` は変えない（内容を見直したわけではないため）

- [ ] **Step 1: 失敗するテストを書く**

```python
# test_workdir.py
def test_save_creates_self_ignoring_dir(five):
    cfg = config.load(five.root); workdir.save(cfg, "g/changed", [{"severity": "major"}], "body")
    assert (five.root / ".agentic-doc/work/.gitignore").read_text() == "*\n"
    assert five.git("status", "--porcelain") == ""

def test_load_discards_on_hash_mismatch(five):
    cfg = config.load(five.root); workdir.save(cfg, "g/changed", [{"x": 1}], "body")
    assert workdir.load(cfg, "g/changed", "edited") is None
    assert not workdir.findings_path(cfg, "g/changed").exists()

def test_existing_gitignore_not_overwritten(five):
    five.write(".agentic-doc/work/.gitignore", "custom\n"); cfg = config.load(five.root)
    workdir.save(cfg, "g/changed", [], "b")
    assert (five.root / ".agentic-doc/work/.gitignore").read_text() == "custom\n"

def test_status_shows_pending_count(five):
    run_cli(five.root, "findings", "save", "g/unverified", "-", input='[{"a":1},{"a":2}]')
    d = json.loads(run_cli(five.root, "status", "--json")[1])
    assert next(p for p in d["pages"] if p["id"] == "g/unverified")["pending"] == 2

# test_checkpoint.py
def test_checkpoint_sets_commit_and_date_and_clears_findings(five):
    run_cli(five.root, "findings", "save", "g/changed", "-", input="[]")
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed", "--today", "2026-10-09")[0] == 0
    p = page(five, "g/changed")
    assert p["source_commit"] == five.git("rev-parse", "HEAD") and p["reviewed_at"] == "2026-10-09"
    assert not (five.root / ".agentic-doc/work/g/changed").exists()

def test_checkpoint_changes_only_target_bytes(five):
    before = (five.root / "docs/wiki/catalogue.json").read_text()
    run_cli(five.root, "checkpoint", "--pages", "g/changed", "--today", "2026-10-09")
    after = (five.root / "docs/wiki/catalogue.json").read_text()
    assert diff_lines(before, after) == 2   # source_commit と reviewed_at の 2 行だけ

def test_checkpoint_refuses_missing_page_file(five):
    assert run_cli(five.root, "checkpoint", "--pages", "g/missing")[0] == 2

# test_stamp.py
def test_stamp_repins_unresolved_and_skips_others(five):
    code, out, _ = run_cli(five.root, "stamp")
    assert code == 1
    assert page(five, "g/unresolved")["source_commit"] == five.git("rev-parse", "HEAD")
    assert page(five, "g/unverified")["source_commit"] is None
    assert page(five, "g/changed")["source_commit"] != five.git("rev-parse", "HEAD")

def test_stamp_changed_only_when_explicit(five):
    assert run_cli(five.root, "stamp", "--pages", "g/changed")[0] == 0
    assert page(five, "g/changed")["source_commit"] == five.git("rev-parse", "HEAD")

def test_stamp_after_squash_merge(repo):
    # ブランチで src を変更しコミット → ページを checkpoint → main に squash merge → ブランチ削除と gc
    # → status は unresolved、stamp 後は fresh

def test_stamp_refusals(five):
    assert run_cli(five.root, "stamp", "--sha", "nope")[0] == 2
    assert run_cli(five.root, "stamp", "--pages", "nope")[0] == 2
    five.write("src/a.py", "dirty"); assert run_cli(five.root, "stamp")[0] == 2

def test_stamp_dry_run_writes_nothing(five):
    before = (five.root / "docs/wiki/catalogue.json").read_text()
    run_cli(five.root, "stamp", "--dry-run")
    assert (five.root / "docs/wiki/catalogue.json").read_text() == before
```

`run_cli` に `input: str | None = None` を足して標準入力を渡せるようにする。`page(repo, id)` と `diff_lines(a, b)` は conftest のヘルパー。squash merge のテストは、`git merge --squash` → `git commit` → `git branch -D` → `git reflog expire --expire=now --all && git gc --prune=now` で元のコミットを消してから判定する。

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_workdir.py tests/test_checkpoint.py tests/test_stamp.py -v` / Expected: FAIL
- [ ] **Step 3: 実装する**

`.gitignore.in` のパスは `Path(__file__).resolve().parents[2] / "assets" / "work" / ".gitignore.in"`。

- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -v` / Expected: PASS
- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): findings・checkpoint・stamp を追加"
```

---

### Task 6: `lint`

**Files:**
- Create: `skills/wiki/scripts/adoc/lint.py`、`mermaid_check.mjs`
- Modify: `skills/wiki/scripts/adoc/i18n.py`（関連ページの見出し）、`agentic_doc.py`
- Test: `tests/test_lint.py`

**Interfaces:**
- Consumes: Task 2〜3 の `Config`、`catalogue.*`、`state.classify`、`gitutil.ls_files`、`gitutil.untracked`、`gitutil.dirty`
- Produces:
  - `lint.lint_page(cfg, page, all_pages, tracked: set[str], check_sources=True) -> list[dict]`: 問題は `{"page", "severity", "code", "detail"}`
  - `lint.extract_citations(body: str, tracked: set[str]) -> list[dict]`（元実装の `extract_citations` と同じ規則。省略形 `:NNN` は同じ行の直前のファイルを引き継ぐ）
  - CLI `lint [ID ...] [--json] [--skip-sources] [--mermaid] [--citations ID]`
    - `--json`: `{"pages_checked", "issue_count", "stale_count", "issues": [...], "stale": [{"page", "reason", "kind"}]}`。`stale` は state が fresh 以外のページで、`kind` は state の値
    - `--citations ID`: 元実装の `show_citations` と同じ出力（引用ごとに `--- path:spec (総行数 N)` と、行番号付きの引用先の行）
    - 終了コード: 問題があれば 1、なければ 0、未知の ID は 2

検査と重大度（元実装 `wiki_lint.py` からの移植。★は新規）:

| code | severity | 条件 |
|---|---|---|
| `missing-page` | blocker | 本文ファイルが無い（以降の検査を省く） |
| `frontmatter` | major | フロントマターが無い・パースできない・マッピングでない・キーが `audience, description, title, updated` の 4 つちょうどでない・`updated` が YYYY-MM-DD でない・`description` が 10 文字未満・`title` か `audience` がカタログと不一致 |
| `mermaid-count` | minor | Mermaid が 2〜4 枚でない |
| `mermaid-style` | major | `style` / `classDef` / `fill:` / `stroke:` / `<br/>` を使っている |
| `related` | major | `related` があるのに関連ページの見出し（`i18n` の `related_heading`。`ja` は `## 関連ページ`、`en` は `## Related pages`）が無い |
| `github-url` | major | GitHub の blob URL がある |
| `source-glob-empty` | major | sources の glob が対象ファイルに 1 件もマッチしない |
| `source-uncommitted` | major | sources に未コミットの変更がある |
| ★`source-untracked` | major | sources にマッチする未追跡ファイルがある |
| `cite-shorthand` | minor | 直前に完全なパスが無い省略形 |
| `cite-missing` | blocker | 引用先が追跡済みファイルに無い（短縮名が一意に決まらない場合も） |
| ★`cite-excluded` | major | 引用先が `exclude` にマッチする |
| `cite-shortpath` | minor | 短縮名での引用 |
| `cite-overflow` | blocker | 行番号が 0 以下・開始 > 終了・総行数超過（0 行のファイルへの `:1` は許す） |
| `cite-variety` | minor | 引用ファイルが 5 種未満（`no_code` の読者層だけのページは対象外） |
| ★`no-code-leak` | major | `no_code` の読者層だけのページに引用がある |
| `link-broken` | blocker | 相対リンク先が存在せず、カタログ上のページでもない |
| `mermaid-syntax` | major | `--mermaid` 指定時のみ。構文エラー |

`--mermaid` は `node` が PATH にあり、`<wiki_dir>/node_modules` から `mermaid` と `jsdom` を解決できるときだけ動く。使えなければ標準エラーに `warning: --mermaid skipped (<理由>)` を 1 行出して省く。`mermaid_check.mjs` は元実装を移植し、解決元のディレクトリを第 1 引数で受け取る形にする（`node mermaid_check.mjs <resolve-dir> FILE...`）。

- [ ] **Step 1: 失敗するテストを書く**

フィクスチャ `wiki(repo)`: 6 ファイルを持つリポジトリと、規約どおりの正常なページ 1 枚（フロントマター 4 キー、Mermaid 2 枚、6 ファイルの引用、関連ページの節）を作る。各テストはそのページを 1 か所だけ壊して、期待するコードだけが出ることを確かめる。

```python
def test_clean_page_has_no_issues(wiki):
    assert run_cli(wiki.root, "lint", "--json")[0] == 0

@pytest.mark.parametrize("mutate, code", [
    (drop_frontmatter_key("updated"), "frontmatter"),
    (set_mermaid_blocks(1), "mermaid-count"),
    (add_to_mermaid("style A fill:#f00"), "mermaid-style"),
    (remove_related_section, "related"),
    (append("https://github.com/o/r/blob/main/x.py#L1"), "github-url"),
    (append("`src/a.py:999`"), "cite-overflow"),
    (append("`src/nope.py:1`"), "cite-missing"),
    (append("`:3`"), "cite-shorthand"),
    (append("[x](../nope.md)"), "link-broken"),
])
def test_each_breakage_reports_its_code(wiki, mutate, code):
    mutate(wiki); codes = issue_codes(wiki)
    assert codes == {code}

def test_non_ascii_citation_resolves(wiki):
    wiki.write("src/日本語 ファイル.py", "1\n2\n"); wiki.commit()
    append("`src/日本語 ファイル.py:2`")(wiki)
    assert issue_codes(wiki) == set()

def test_cite_excluded(wiki):
    wiki.config(exclude=["src/f.py"]); assert "cite-excluded" in issue_codes(wiki)

def test_no_code_page_rules(wiki):
    # audiences に no_code: true の "product" を足し、ページの audience を ["product"] にする
    # → 引用があると no-code-leak、cite-variety は出ない

def test_glob_star_migration_warning(wiki):
    # sources を ["src/*.py"] から、深い階層だけを指す ["lib/*.py"]（実ファイルは lib/x/y.py）に変える
    assert "source-glob-empty" in issue_codes(wiki)

def test_untracked_and_uncommitted_sources(wiki):
    wiki.write("src/new.py", "n"); wiki.write("src/a.py", "dirty")
    assert {"source-untracked", "source-uncommitted"} <= issue_codes(wiki)
    assert "source-untracked" not in issue_codes(wiki, "--skip-sources")

def test_related_heading_follows_language(wiki):
    wiki.config(language="ja")
    assert issue_codes(wiki) == {"related"}   # 本文は "## Related pages" のまま

def test_citations_output(wiki):
    out = run_cli(wiki.root, "lint", "--citations", "g/page")[1]
    assert "--- src/a.py:1-2 (総行数 3)" in out and "    1| " in out

def test_mermaid_skipped_without_node_modules(wiki):
    code, _, err = run_cli(wiki.root, "lint", "--mermaid")
    assert "warning: --mermaid skipped" in err and code == 0
```

`set_sources(repo, page_id, globs)` はカタログの該当ページの sources を書き換える conftest のヘルパー。`issue_codes(repo, *args) -> set[str]` は `lint --json` の issues の `code` の集合を返す conftest のヘルパー。正常ページの本文と変形関数（`drop_frontmatter_key`、`set_mermaid_blocks`、`add_to_mermaid`、`remove_related_section`、`append`）は `tests/lint_fixtures.py` に置く。

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_lint.py -v` / Expected: FAIL
- [ ] **Step 3: 実装する**

フロントマターは PyYAML の `safe_load` で読む。`updated` は YAML が `date` 型にするので `str()` してから照合する（元実装と同じ）。

- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -v` / Expected: PASS
- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): Wiki の機械検査 lint を追加"
```

---

### Task 7: `toc`

**Files:**
- Create: `skills/wiki/scripts/adoc/cmd_toc.py`
- Modify: `skills/wiki/scripts/adoc/i18n.py`、`agentic_doc.py`
- Test: `tests/test_toc.py`

**Interfaces:**
- Consumes: Task 3 の `catalogue.load` / `save` / `page_file`、Task 6 の `related_heading`
- Produces: CLI `toc [--dry-run]`。次の 3 つを行い、変更したファイルの一覧を標準出力に 1 行 1 パスで出す（`--dry-run` では書かずに一覧だけ）。終了コード 0
  1. **目次** `<wiki_dir>/README.md` を生成する:
     - H1 はカタログの `title`（無ければ `i18n` の `toc_default_title`。`ja` は「Wiki」、`en` は「Wiki」）
     - 「読者別の入口」の節（`toc_audience_heading`）: 設定の `audiences` の順に、`### <audience.title>` と、その読者を持つページへの番号付きリンク（カタログの順）
     - 「目次」の節（`toc_contents_heading`）: `chapters` の順に `### <chapter.title>`、`chapter.description`、表 `| <toc_col_page> | <toc_col_summary> |`。概要はページの `brief` の最初の 1 文（`。` か `. ` までを含む）
     - 本文ファイルが無いページは、リンクの後に `toc_not_written`（`ja` は「（未生成）」、`en` は「(not yet written)」）を付ける
  2. **related の双方向化**: A の `related` に B があり、B の `related` に A が無ければ、B の末尾に A を足してカタログを保存する
  3. **既存ページの整形**: 本文ファイルがあるページについて、フロントマターの `title` と `audience` をカタログに合わせ、`updated` を `reviewed_at`（null なら変えない）にする。`description` は変えない。関連ページの節（`related_heading` の行から次の `## ` か末尾まで）を、`related` の順に `- [<title>](<相対パス>)` で置き換える（節が無ければ末尾に足す）
  - フロントマターの書き出し: `title: "<エスケープ済み>"`、`description: "<エスケープ済み>"`、`audience: [a, b]`、`updated: YYYY-MM-DD`（引用符なし）。エスケープは `\` と `"` をバックスラッシュで
  - 冪等: 2 回続けて実行すると、2 回目は変更ファイルが空

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_toc_lists_audiences_and_chapters(wiki2):   # 2 章 3 ページ、うち 1 ページ未生成
    run_cli(wiki2.root, "toc")
    t = (wiki2.root / "docs/wiki/README.md").read_text()
    assert t.index("### Contributors") < t.index("### AI agents")
    assert "(not yet written)" in t and "| Page | Summary |" in t

def test_toc_japanese(wiki2):
    wiki2.config(language="ja"); run_cli(wiki2.root, "toc")
    assert "（未生成）" in (wiki2.root / "docs/wiki/README.md").read_text()

def test_related_made_symmetric(wiki2):
    run_cli(wiki2.root, "toc")
    assert "a/one" in page(wiki2, "b/two")["related"]

def test_page_frontmatter_and_related_section_synced(wiki2):
    # カタログの title を変え、reviewed_at を 2026-10-09 にしてから toc
    fm, body = read_page(wiki2, "a/one")
    assert fm["title"] == "New title" and str(fm["updated"]) == "2026-10-09"
    assert body.rstrip().endswith("- [Two](../b/two.md)")

def test_title_with_quotes_and_hash_roundtrips(wiki2):
    # title を 'He said "x" # y' にして toc → lint の frontmatter が出ないこと

def test_toc_idempotent(wiki2):
    run_cli(wiki2.root, "toc")
    assert run_cli(wiki2.root, "toc")[1].strip() == ""
```

`wiki2` フィクスチャと `read_page(repo, id) -> (dict, str)` は conftest に置く。

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_toc.py -v` / Expected: FAIL
- [ ] **Step 3: 実装する**
- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -v` / Expected: PASS
- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): 目次と相互リンクを整える toc を追加"
```

---

### Task 8: `post`

**Files:**
- Create: `skills/wiki/scripts/adoc/cmd_post.py`
- Modify: `agentic_doc.py`、`skills/wiki/scripts/adoc/config.py`（`post-backslash`）
- Test: `tests/test_post.py`

**Interfaces:**
- Consumes: Task 2 の `Config.post_commands`
- Produces: CLI `post FILE ...`。`post_commands` を順に実行する
  - 各要素を `shlex.split` で分割し、`{files}` と完全に一致する引数を `FILE ...` に展開する（1 ファイル 1 引数）。`{files}` を含むが一致しない引数（例 `--x={files}`）は `Refused`
  - `subprocess.run(argv, cwd=cfg.root)`。シェルを介さない。`argv[0]` は `shutil.which` で解決してから渡す（Windows の `npx.cmd` などを PATHEXT で見つけるため）
  - `shlex.split` は POSIX 規則なので、`post_commands` のパスは Windows でもスラッシュ区切りで書く（`config check` は要素にバックスラッシュがあれば warning `post-backslash` を出す。この Task で `config.check` に足す）
  - 出力: コマンドごとに `$ <コマンド>`、終了コード、標準出力と標準エラー。`--json` で `[{"command", "argv", "code", "stdout", "stderr"}]`
  - 終了コード: すべて 0 なら 0、1 つでも失敗なら 1（失敗しても残りのコマンドは実行する）、コマンドが見つからなければその要素の `code` を 127 として 1。`post_commands` が空なら何もせず 0

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_files_expand_one_arg_each_without_shell(repo):
    py = sys.executable.replace("\\", "/")   # Windows でも shlex で壊れないようにスラッシュにする
    repo.config(post_commands=[f'"{py}" -c "import sys; print(sys.argv[1:])" {{files}}'])
    d = json.loads(run_cli(repo.root, "post", "--json", "a b.md", "日本.md", "$(x).md")[1])
    assert d[0]["stdout"].strip() == "['a b.md', '日本.md', '$(x).md']"

def test_failure_continues_and_exits_1(repo):
    py = sys.executable.replace("\\", "/")
    repo.config(post_commands=[f"\"{py}\" -c 'import sys; sys.exit(3)' {{files}}",
                               f"\"{py}\" -c 'print(1)' {{files}}"])
    code, out, _ = run_cli(repo.root, "post", "--json", "x.md")
    d = json.loads(out)
    assert code == 1 and [r["code"] for r in d] == [3, 0]

def test_missing_command_is_127(repo):
    repo.config(post_commands=["no-such-cmd-zzz {files}"])
    assert json.loads(run_cli(repo.root, "post", "--json", "x.md")[1])[0]["code"] == 127

def test_embedded_placeholder_refused(repo):
    repo.config(post_commands=["fmt --x={files}"])
    assert run_cli(repo.root, "post", "x.md")[0] == 2

def test_config_check_warns_backslash(repo):
    repo.config(post_commands=["C:\\tools\\fmt.exe {files}"])
    assert any(i["code"] == "post-backslash" for i in config.check(repo.root))

def test_no_commands_is_noop(repo):
    repo.config(); assert run_cli(repo.root, "post", "x.md")[0] == 0
```

`config check` の `post-no-files` は「`{files}` を含まない」の判定なので、`--x={files}` は `config check` を通る。`post` 側で拒否することを確かめる。

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_post.py -v` / Expected: FAIL
- [ ] **Step 3: 実装する**
- [ ] **Step 4: 通ることを確かめる** — Run: `uv run pytest -v` / Expected: PASS
- [ ] **Step 5: コミット**

```bash
git add skills/wiki tests
git commit -m "feat(scripts): post_commands を実行する post を追加"
```

---

### Task 9: 整合テストと文書の更新

**Files:**
- Create: `tests/test_integrity.py`
- Modify: `AGENTS.md`（コマンドの節）、`docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`（実装中に新たに決めたことがあれば）
- Modify: `.github/workflows/`（pytest を走らせるワークフローを追加。ファイル名 `tests.yml`）

**Interfaces:**
- Consumes: Task 1〜8 の全コマンド

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_manifests_agree():
    a = json.loads(Path("plugin.json").read_text()); b = json.loads(Path(".claude-plugin/plugin.json").read_text())
    m = json.loads(Path(".claude-plugin/marketplace.json").read_text())["plugins"][0]
    for k in ["name", "version", "description"]:
        assert a[k] == b[k] == m[k]

def test_schemas_are_valid_json_schema():
    for p in Path("skills/wiki/schemas").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(p.read_text()))

def test_gitignore_template_is_star():
    assert Path("skills/wiki/assets/work/.gitignore.in").read_text() == "*\n"

def test_pep723_block_declares_runtime():
    head = Path("skills/wiki/scripts/agentic_doc.py").read_text().split("# ///")[1]
    assert 'requires-python = ">=3.11"' in head and "pyyaml>=6" in head and "jsonschema>=4.23" in head

def test_every_command_has_help():
    for name, c in COMMANDS.items():
        assert c.help and len(c.help) < 100
```

- [ ] **Step 2: 失敗を確かめる** — Run: `uv run pytest tests/test_integrity.py -v` / Expected: すべて PASS してよい。この Task のテストは既存の状態を固定する回帰テストで、失敗させる実装の変更が無いため。FAIL したものは、その不一致を直してから次へ進む

- [ ] **Step 3: 文書とワークフローを更新する**

- `AGENTS.md` のコマンド節に `uv run pytest`、`uv run ruff check .`、`uv run --script skills/wiki/scripts/agentic_doc.py --help` を足し、「テストスイートはまだ無い」の行を削除する
- 計画作成時に決めたこと（`findings` コマンド、カタログの任意の `title`、glob の `:(glob)` 解釈、状態の内部名、`post-backslash`）は仕様書に反映済み。実装中の Ruling で仕様に関わるものがあれば、それを仕様書に反映する
- `.github/workflows/tests.yml`: `pull_request` と `push`（main）で、`astral-sh/setup-uv` → `uv sync` → `uv run pytest` → `uv run ruff check .` を ubuntu-latest・macos-latest・windows-latest の 3 OS で走らせる

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run pytest -v && uv run ruff check . && uv run --script skills/wiki/scripts/agentic_doc.py --help`
Expected: 全テスト PASS、ruff `All checks passed!`、help に 9 コマンド（`config`、`status`、`plan`、`checkpoint`、`stamp`、`findings`、`lint`、`toc`、`post`）

- [ ] **Step 5: コミット**

```bash
git add tests AGENTS.md docs .github/workflows/tests.yml
git commit -m "test(scripts): 整合テストと CI を追加し、仕様と AGENTS.md を更新"
```
