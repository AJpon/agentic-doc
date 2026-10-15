# 受入検証の手順書: Windows（PowerShell）

計画 4 の Task 10。所有者が Windows の PowerShell で実施し、最後の「記録」の表を埋めて返す。Git Bash ではなく PowerShell で行う。

## 準備

1. uv と git を入れる（`winget install astral-sh.uv`、`winget install Git.Git`）。`uv --version` と `git --version` で確かめる。
2. agentic-doc を clone し、検証するブランチ（`docs/plan4-acceptance`、マージ後は `main`）を checkout する。以下、その場所を `$plugin` とする。
3. サンプルリポジトリを clone する。macOS で Claude が作ったものを使う場合は、所有者が別途受け取って置く。以下、その場所を `$sample` とする。

```powershell
$plugin = "C:\path\to\agentic-doc"
$sample = "C:\path\to\sample-todo"
$cli = Join-Path $plugin "skills\wiki\scripts\agentic_doc.py"
Set-Location $sample
```

## 1. スクリプトだけで確かめること（LLM を使わない）

サンプルリポジトリには、macOS で setup・outline・sync を済ませた状態（`.agentic-doc.config.json` と `docs/wiki/` が commit 済み）を使う。

```powershell
uv run --script $cli --help
uv run --script $cli config check
uv run --script $cli status
uv run --script $cli status --json | Out-File status-win.json -Encoding utf8
uv run --script $cli lint
uv run --script $cli plan
uv run --script $cli catalogue check
```

確かめること:

- どのコマンドも、文字化けや Python の例外を出さない。
- `status` と `lint` の出力が、macOS の出力（Claude が研究記録の 5 節に貼ったもの）と同じ。
- 非 ASCII と空白を含むファイル名（`src/todo/表示 format.py`）が、`status --verbose` や `lint` の出力で正しく表示される。

## 2. カタログの書き換えと改行

```powershell
uv run --script $cli stamp --dry-run
git config core.autocrlf
git status --short
```

確かめること: `stamp --dry-run` が何も書き換えない。`core.autocrlf` が `true` の場合も、`git status` に改行だけの差分が出ない。

## 3. エージェント経由で 1 ページを書き直す（計画 3 の修正の実機確認）

VS Code の Copilot（`copilot-degraded.md` の準備）か Claude Code で、次を実行する。

```text
/agentic-doc:wiki sync --pages <任意の 1 ページの ID>
```

確かめること:

- 指摘が保存された場合、`.agentic-doc/work/<ID>/findings.json` を開いて、日本語が化けていない（PowerShell のパイプを通さず、ファイルで渡す修正の確認）。
- 終わった後の `status` で、そのページが「最新」か「未検証」のどちらかで、「最新」なのに検証が終わっていない状態になっていない。

## 記録

| 項目 | 結果 |
| --- | --- |
| Windows と PowerShell の版、uv と git の版 | |
| 1 の各コマンドの成否と、macOS との差 | |
| 非 ASCII のファイル名の表示 | |
| 2 の結果（`core.autocrlf` の値、改行の差分の有無） | |
| 3 で使ったハーネスとページ、結果、`findings.json` の文字化けの有無 | |
| その他、気付いたこと | |
