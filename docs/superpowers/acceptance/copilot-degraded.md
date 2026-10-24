# 受入検証の手順書: VS Code の Copilot での縮退動作

計画 4 の Task 9。所有者が VS Code で実施し、最後の「記録」の表を埋めて返す。macOS と Windows のどちらで行ってもよい（Windows で行う場合は `windows-powershell.md` の 3 節と兼ねられる）。

## 準備

1. agentic-doc を clone し、検証するブランチ（`docs/plan4-acceptance`、マージ後は `main`）を checkout する。
2. VS Code の設定 `chat.pluginLocations` に、clone したディレクトリを追加する。
3. サンプルリポジトリを用意する。Claude が `scratchpad/sample-todo` に作ったものを使う場合は、そのディレクトリを `git clone` して別の場所に置く（元のディレクトリはセッションの終了で消える）。自分で用意する場合は、Python の小さなプロジェクト（5〜8 ファイル、README あり、非 ASCII と空白を含むファイル名を 1 つ）を作って commit する。
4. サンプルリポジトリを VS Code で開き、Copilot Chat をエージェントモードにする。
5. uv と git が PATH にあることを、ターミナルで `uv --version` と `git --version` で確かめる。

## 手順

チャットに次を順に入力する。各段階が終わってから次へ進む。スクリプトの実行の承認を求められたら許可する。

| # | 入力 | 確かめること |
| --- | --- | --- |
| 1 | `/agentic-doc:wiki help`（スラッシュコマンドとして出ない場合は「agentic-doc の wiki スキルで help を実行して」） | 設定ファイルが無いことを示し、`setup` を案内する |
| 2 | `/agentic-doc:wiki setup` | 推定値と根拠を示し、`audiences` などを尋ねる。承認すると `.agentic-doc.config.json` ができ、`config check` が `ok` |
| 3 | `/agentic-doc:wiki outline` | Workflow ではなく、`references/run-outline.md` の手順を 1 つずつ実行する。`docs/wiki/catalogue.json` ができる |
| 4 | `/agentic-doc:wiki sync` | ページごとに research → write → 2 観点の verify → 記録を順に行う。最後に目次（`docs/wiki/README.md`）ができる |
| 5 | `/agentic-doc:wiki status` | 全ページ「最新」 |
| 6 | `/agentic-doc:wiki audit` | `report` の出力が表示される。指摘があれば内容を控える |
| 7 | `/agentic-doc:wiki stamp --dry-run` | 何も書き換えずに、対象のページを示す |

ターミナルで次も実行する（`<clone>` は agentic-doc の clone のパス）:

```bash
uv run --script "<clone>/skills/wiki/scripts/agentic_doc.py" lint
```

## 記録

| 項目 | 結果 |
| --- | --- |
| OS と VS Code・Copilot Chat の版 | |
| 使ったモデル | |
| スラッシュコマンドとして出た名前（例: `/agentic-doc:wiki`、`/wiki`） | |
| 両方のマニフェスト（`plugin.json` と `.claude-plugin/plugin.json`）があるとき、VS Code が表示したプラグイン名 | |
| 1〜7 の各段階の成否（失敗したら、その出力） | |
| sync で書かれたページ数、失敗したページ | |
| `lint` の指摘の件数 | |
| Workflow を呼ぼうとした、手順を飛ばした、などの逸脱 | |
| 所要時間（概算） | |
