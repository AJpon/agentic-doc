# agentic-doc: コードベース Wiki 生成・保守プラグイン 設計

- 作成日: 2026-10-08
- 状態: 設計確定（実行方式とハーネスの検証記録: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`）
- 移植元: `AJpon/fbx-view` PR #21（`.claude/workflows/wiki.js` と `.claude/workflows/scripts/`）

## 1. 背景と目的

このリポジトリ（旧 DocAgent PoC）が目指していた「コードベースから Markdown Wiki を生成し、コードの変化に追随させ続ける」仕組みは、fbx-view で Claude Code の Workflow として実用水準に達した。ただし、その実装は fbx-view の事情（日本語固定、FBX/Qt の前提、uv と pre-commit と cspell の運用、`docs/superpowers` の扱い）を全体に埋め込んでおり、Claude Code 以外では動かない。

本プロジェクトは、その仕組みを任意のリポジトリと複数のエージェントハーネスで再利用できるプラグイン `agentic-doc` として作り直す。既存の PoC 実装は置き換える。

**成功の条件**

- 任意の git リポジトリに導入し、setup → outline → sync で Wiki を作り、以後 status / sync / audit / stamp で保守できる。
- Claude Code では Workflow で並列実行と独立した検証まで完全に動く。
- GitHub Copilot（VS Code）と Codex CLI では、同じスキルを 1 体のエージェントが直列に実行する縮退動作で、同じ成果物を作れる。
- 受入検証（12 章）の 4 リポジトリで動作を確認できる。

## 2. 範囲

**含む**

- 素の Markdown Wiki の生成・更新・監査・状態表示
- 導入先ごとの設定ファイルと、それを作る setup
- 陳腐化検出（git 差分）と、そのための決定的なスクリプト群
- ページ単位の中断・再開と、未解決の指摘の引き継ぎ
- help と「次にやるべき操作」の案内
- Agent Plugins 1.0 形式と Claude Code 形式の両方のマニフェスト

**含まない（別のサブプロジェクトにする）**

- VitePress などの閲覧層（サイドバー生成、引用のパーマリンク化、検索、llms.txt）。フロントマターは VitePress と互換にしておく。
- 1 つのリポジトリに複数の Wiki を置くこと（モノレポ対応）
- 人間向けの引き継ぎ文書の生成

## 3. 用語

| 用語 | 意味 |
|---|---|
| 導入先 | プラグインを使って Wiki を作るリポジトリ |
| 設定ファイル | 導入先に置く `.agentic-doc.config.json` |
| カタログ | Wiki のページ構成と各ページの状態を持つ JSON（既定 `<wiki_dir>/catalogue.json`） |
| sources | ページの内容が依存するファイルの glob。陳腐化判定の範囲 |
| source_commit | そのページが最後に検証を通ったときの HEAD の SHA |
| 縮退動作 | Workflow を持たないハーネスで、入口スキルを 1 体のエージェントが直列に実行すること |
| 対象ファイル | `git ls-files` で得られる追跡済みファイルから `exclude` を除いたもの |
| glob | `sources` と `exclude` の書き方。git の pathspec の `:(glob)` 規則で解釈する。`*` は `/` を越えず、`**` は越える。`git ls-files` と `git diff` に同じ pathspec を渡す |

## 4. 全体構成

方針は「スキルが唯一の正」である。各フェーズの手順・プロンプト・執筆規約・出力スキーマはスキルの中にだけ置き、Claude Code の Workflow は並列実行・検証ループ・チェックポイントの制御だけを持つ。

```
agentic-doc/                          # リポジトリ = プラグインのルート
├── plugin.json                       # Agent Plugins 1.0（$schema 付き）。Copilot / Codex が読む
├── .claude-plugin/
│   ├── plugin.json                   # Claude Code 用。workflows の場所を指す
│   └── marketplace.json
├── skills/
│   ├── wiki/                         # 入口スキル。全ハーネス共通
│   │   ├── SKILL.md                  #   モードの振り分け、help、次の操作の案内、縮退動作の手順
│   │   ├── references/               #   overview（全体フロー）、各フェーズの手順、執筆規約
│   │   ├── schemas/                  #   設定・カタログ・各フェーズ出力の JSON Schema
│   │   ├── scripts/                  #   決定的な処理（8 章）。入口は agentic_doc.py
│   │   └── assets/work/.gitignore.in #   作業ディレクトリの雛形（中身は `*` の 1 行）
│   └── wiki-setup/                   # 設定ファイルの作成・更新
│       ├── SKILL.md
│       └── references/
└── com.anthropic.claude-code/
    └── workflows/wiki-run.js         # Claude Code 専用のオーケストレーション（meta.name は wiki-run）
```

- Workflow の各エージェントには、「`<スキルのパス>/references/<フェーズ>.md` を読んで従え。対象ページは〜」という短い指示とスキーマだけを渡す。プロンプトの本文は Workflow に書かない。
- スキーマの正は `skills/wiki/schemas/` に置く。Workflow はファイルを読めないため、`dev/embed_schemas.py` が `wiki-run.js` の生成ブロックに写しを埋め込み、整合テストで一致を固定する。
- 参照文書とスキル本文は英語で書く。Wiki 本文は設定の `language` で書き、言語ごとの固定の文字列は `config show` の `strings` から取る。
- 外部プラグイン（元実装の `deep-wiki:wiki-researcher`）には依存しない。
- Copilot 用の名前空間ディレクトリは最初は作らない。スキルだけで呼び出せるため。

**マニフェスト**

- ルートの `plugin.json` は Agent Plugins 1.0 形式で、`$schema` に `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json` を書く。Copilot（VS Code）と Codex がこれを読む。
- `.claude-plugin/plugin.json` は Claude Code 用で、`workflows` に `["./com.anthropic.claude-code/workflows/"]` を書く。
- 両方の `name` は `agentic-doc` にそろえる。

**パスの受け渡し**

- スキル本文からスクリプトや参照文書を指すときは、「この SKILL.md と同じディレクトリからの相対パス」で書く。Claude Code、VS Code（Copilot）、Codex の 3 つで動くことを確認した。`${PLUGIN_ROOT}` はスキル本文では展開されないので使わない。
- 表記は `<SKILL_DIR>/...` に統一する。`<SKILL_DIR>` は wiki スキルの SKILL.md のあるディレクトリで、SKILL.md の冒頭で定義する。Workflow はその絶対パスをプロンプトの `SKILL_DIR = ...` 行で渡す。wiki-setup からは `<SKILL_DIR>/../wiki/` で wiki スキルを指す。
- Claude Code の Workflow はファイルシステムに触れず、日付も取得できない。入口スキルが Workflow を呼ぶときに、`args.plugin_root` に `${CLAUDE_PLUGIN_ROOT}`（スキル本文で展開される）を入れて渡す。Workflow はこれをもとに参照文書とスクリプトの絶対パスを組み立て、エージェントに渡す。日付は `plan` が出す `today` を使う（`args.today` は上書きしたいときだけ渡す任意の値）。
- Workflow の `args` は `{mode: "outline"|"sync"|"audit", plugin_root, pages?, force?, include_unresolved?, lint_only?, today?}`。
- Workflow の `meta.name` は入口スキルと別の名前（`wiki-run`）にする。同じ名前だと、コマンドがスキルを経由せずに Workflow を直接起動し、`args` が渡らない。
- Codex はプラグインをキャッシュ（`~/.codex/plugins/cache/...`）にコピーしてから読み込む。スクリプトはプラグイン内の相対位置だけを前提にし、プラグインのリポジトリ内の位置を前提にしない。

## 5. 設定ファイル

### 5.1 場所とパスの基準

- 初版は導入先のリポジトリ直下の `.agentic-doc.config.json` だけを読む。
- 設定ファイル内の相対パスはすべて**設定ファイルのあるディレクトリ**を基準に解決する。初版では設定ファイルが直下にあるので、リポジトリルート基準と一致する。
- 実装は最初から内部の `root` という 1 つの値を通してパスを解決する。初版の `root` は設定ファイルのディレクトリに固定し、キーとしては公開しない。
- 形式は JSON だけ。

### 5.2 項目

| 項目 | 必須 | 既定値 | 内容 |
|---|---|---|---|
| `version` | 必須 | — | 設定スキーマのバージョン。初版は `1` |
| `wiki_dir` | 任意 | `docs/wiki` | Wiki の出力先 |
| `catalogue` | 任意 | `<wiki_dir>/catalogue.json` | カタログのパス。`wiki_dir` を変えると既定値も付いてくる |
| `language` | 任意 | `en` | 執筆言語（BCP 47 の言語タグ。例 `ja`、`en`） |
| `audiences` | 任意 | 下記 | 読者層の定義 |
| `exclude` | 任意 | `[]` | 対象ファイルからさらに除外する glob（`**` 対応、`root` 基準）。vendor、生成コード、大きなフィクスチャなど |
| `context` | 任意 | README / AGENTS.md / CLAUDE.md のうち存在するもの | リポジトリの概要。**検証すべき前提**として扱う |
| `instructions` | 任意 | `[]` | 生成のルール。**従うべきルール**として扱う |
| `post_commands` | 任意 | `[]` | 生成・更新したファイルに最後に実行するコマンドの配列。`{files}` が対象ファイルに置き換わる |
| `max_pages` | 任意 | `24` | カタログのページ数の上限 |

`audiences` の各要素は `id`、`title`（目次に出す名前）、`description`、`no_code`（真のとき、その層だけを読者に持つページはコード・識別子・ファイルパス・引用を本文に出さない）を持つ。既定値は次の 2 つ。

```json
[
  { "id": "contributor", "title": "Contributors", "description": "People changing the code", "no_code": false },
  { "id": "agent", "title": "AI agents", "description": "Coding agents changing the code", "no_code": false }
]
```

`context` と `instructions` はどちらも、`text`（文字列そのもの）か `file`（パス）のどちらか 1 つだけを持つオブジェクトの配列である。素の文字列は受け付けない。`file` は実行のたびに読み、配列の順に連結して全フェーズのエージェントに渡す。両者は次のように扱いを分ける。

| | `context` | `instructions` |
|---|---|---|
| エージェントの扱い | 検証すべき前提。Wiki に書く前にコードで確かめ、そのまま引き写さない | 従うべきルール。検証の対象ではない |
| 陳腐化判定 | 対象にしない | 対象にしない |

`post_commands` の `{files}` は、対象ファイルのパスに展開される。実行の規則は 8 章の `post` を参照。

### 5.3 設定例

```json
{
  "version": 1,
  "wiki_dir": "docs/wiki",
  "language": "ja",
  "audiences": [
    { "id": "contributor", "title": "コントリビューター", "description": "コードを変更する人", "no_code": false },
    { "id": "agent", "title": "AIエージェント", "description": "コード変更を担当するエージェント", "no_code": false },
    { "id": "product", "title": "プロダクト", "description": "できること・できないことを知りたい人", "no_code": true }
  ],
  "exclude": ["resources/**", "typings/**"],
  "context": [{ "file": "AGENTS.md" }],
  "instructions": [{ "text": "docs/superpowers/ の文書は履歴であり、現在の振る舞いの根拠として引用しない" }],
  "post_commands": ["uv run pre-commit run --files {files}"]
}
```

### 5.4 検査（`config check`）

次のどれかに当たれば検査は失敗する。

- JSON Schema に合わない
- `context` / `instructions` の `file` が存在しない
- `post_commands` の要素が `{files}` を含まない

次の場合は警告にとどめる。

- `exclude` の glob が 1 件もファイルにマッチしない（打ち間違いの可能性）
- `post_commands` の要素にバックスラッシュが含まれる（`post-backslash`）。`shlex.split` は POSIX の規則で分割するため、パスは Windows でもスラッシュ区切りで書く

## 6. カタログ

元実装の `_catalogue.json` から `language` と `citation_style` を除き、章の情報を足したもの。

```json
{
  "version": 1,
  "chapters": [
    { "id": "overview", "title": "全体像", "description": "最初に読む章" }
  ],
  "pages": [
    {
      "id": "overview/data-flow",
      "path": "overview/data-flow.md",
      "title": "アーキテクチャ全体像",
      "audience": ["contributor", "agent"],
      "brief": "このページが答えるべき問い（1〜3 文）",
      "sources": ["src/**/*.py", "AGENTS.md"],
      "related": ["overview/repository-map"],
      "source_commit": null,
      "reviewed_at": null
    }
  ]
}
```

- `id` は `章/ページ` 形式。章の部分は `chapters[].id` のどれかと一致する。章 ID とページ ID の各部分は小文字の英字・数字・ハイフンで、英字か数字で始まる。`chapters[].id` は重複させない。
- `path` は `<id>.md` と完全に一致させる。連番の接頭辞は付けない。
- `pages` 配列の並び順が読む順序の正である。
- 章は最大 6、1 章あたりのページは最大 8、全ページ数は `max_pages` 以下。
- `audience` の値は設定ファイルの `audiences[].id` のどれか。
- `sources` は 1 件以上の glob を持ち、各 glob は対象ファイルに 1 件以上マッチする。glob の解釈は 3 章のとおりで、`*` は 1 階層しかマッチしない。元実装から移したカタログで `*` が深い階層を指していた場合は `**` に直す（0 件マッチは `lint` が報告する）。
- トップレベルに任意の `title`（文字列）を置ける。`toc` が目次の H1 に使い、無ければ言語ごとの既定の見出しを使う。
- JSON は 2 スペースインデント、非 ASCII 文字はエスケープしない、末尾に改行 1 つ。スクリプトはこの書式で読み書きし、`source_commit` と `reviewed_at` 以外のバイトを変えない。
- カタログが Wiki ディレクトリの中にあっても、ページとしては扱わない。

## 7. モードとコマンド

ユーザーから見た操作は `/agentic-doc:wiki <モード> [引数]` に統一する（ハーネスによって呼び出し方の表記は異なる）。

| モード | 種類 | 内容 |
|---|---|---|
| （引数なし）/ `help` | 読み取り | `status` を実行し、全体フローのどこにいるかと次にやる操作を説明する。モードの説明や質問にも答える |
| `setup` | 書き込み | 設定ファイルを作成・更新する（wiki-setup スキル） |
| `outline` | 書き込み | Wiki の構成（章、ページ割り、各ページの sources）を設計し、カタログを書く |
| `sync` | 書き込み | 未生成・未検証・陳腐化したページを書く／書き直す。初回も日常も同じ |
| `status` | 読み取り | 各ページの状態を表で出す。LLM を使わない |
| `audit` | 読み取り | Wiki の中身の正しさを監査する |
| `stamp` | 書き込み | 本文を変えずに、指定のコミットで確認済みという印を押す |

全体のフロー:

```
導入時:   setup ──▶ outline ──▶ (人がカタログを確認・修正) ──▶ sync ──▶ コミット
日常:     status / audit (任意) ──▶ sync ──▶ コミット
構成変更: outline --force ──▶ sync
履歴変更: status で「解決不能」を確認 ──▶ stamp
```

### 7.1 setup

**初回（設定ファイルが無いとき）**

1. README / AGENTS.md / CLAUDE.md / CONTRIBUTING、ビルド設定、`.gitignore`、フォーマッタやフック、CI の設定、トップレベルのディレクトリ構成を読む。
2. 各項目の推定値と、その根拠になったファイルを並べた下書きを作る。`language` は既存のドキュメントとコミットメッセージから、`post_commands` は導入済みのフォーマッタやフックから推定する。
3. 推定できない項目か判断が分かれる項目（主に `audiences`、`exclude`、`post_commands`）だけを、根拠を添えて人間に尋ねる。`instructions` は推定せず、書きたいルールがあるかだけを尋ねる。
4. 設定ファイルを書き、`config check` を通す。
5. 次は `outline` を実行するよう案内する。

**更新（設定ファイルがあるとき）**

1. 初回の 1〜2 をやり直し、現状との差分だけを提案する（例: 新しい生成物ディレクトリが `exclude` に無い、`file` の指す先が消えた、フォーマッタが変わった）。
2. 承認された項目だけを書き換え、`config check` を通す。
3. `exclude` が変わった場合は、除外したファイルを `sources` に持つページを示し、そのページの再生成か `outline` の見直しを勧める。
4. 設定の `catalogue` が指す先にファイルが無く、既定の場所や旧名（`_catalogue.json`）に見つかった場合は、設定の書き換えかファイルの移動を提案する。見つかったのが旧形式（`chapters` が無い。元実装のカタログ）なら、`catalogue migrate` での変換を提案し、変換後に章の `title` と `description` を既存の目次から埋める案を示す。

### 7.2 outline

1. 調査領域の決定: 1 体のエージェントがリポジトリの構成を見て 3〜5 の調査領域に分ける。
2. 領域ごとの調査（Claude Code では並列）。
3. 3 つの切り口（アーキテクチャの層 / データの流れ / 読者層）で構成案を作る（Claude Code では並列）。
4. 構成案を評価・統合し、`.agentic-doc/work/outline/catalogue.json` に書く。`catalogue check` が通るまで直し、`catalogue install`（`--force` は outline の `--force` のときだけ）で設定の場所に置く。
5. `toc` で目次を生成する。

既存のカタログがある場合、`--force` が無ければ上書きしない。上書きすると全ページの `source_commit` が null に戻る。

### 7.3 sync

1. `plan` で対象ページを決める。既定の対象は「未生成」「未検証」「変更あり」の状態のページ。`--pages <id>...` で明示したページは状態に関係なく対象になる。「解決不能」のページは既定では対象にせず、`stamp` か `--pages` での再生成を案内する（`--include-unresolved` で対象に含める）。
2. 対象のうち `source_commit` を持つページ（`--pages` の明示や変更あり）は、`unverify` で未検証に戻してから処理する。ページごとに research → write → verify（引用レンズと主張レンズ。両方が終わらなければ未検証のまま）→ fix（最大 2 ラウンド）。作業ディレクトリに未解決の指摘が残っているページは、research と write を飛ばして fix から始める（10 章）。
3. 検証を通ったページは、その時点で `checkpoint` が `source_commit` と `reviewed_at` を書く。
4. 全ページの処理後、`toc` で目次・相互リンク・フロントマターを整え、`post_commands` を実行する。`toc` で直しきれなかった壊れたリンクはエージェントが直す。

### 7.4 status

```
$ agentic-doc status
Wiki: docs/wiki  (catalogue.json, 24 pages)  HEAD 3f2a1c9

ID                       状態        基準       確認日       理由
overview/reading-guide   最新        74c473a    2026-10-06
overview/data-flow       変更あり    1aefb3b    2026-10-06   src/camera.py ほか 2 件
render/pipeline          解決不能    bd25bfa    2026-10-04   コミットが見つからない
app/settings             未生成      -          -
dev/testing              未検証      -          2026-10-07   保留中の指摘 3 件

最新 20 / 変更あり 1 / 解決不能 1 / 未生成 1 / 未検証 1
未コミット: src/new_widget.py（sources に該当）
次の操作: sync で 3 ページを書き直す / 解決不能の 1 ページは内容を確認して stamp
```

| 状態 | 内部名 | 条件（上から順に判定） |
|---|---|---|
| 未生成 | `missing` | `path` のファイルが無い |
| 未検証 | `unverified` | `source_commit` が null |
| 解決不能 | `unresolved` | `source_commit` が現在のリポジトリでコミットとして解決できない |
| 変更あり | `changed` | `git diff --name-only <source_commit>..HEAD -- <sources>` が空でない |
| 最新 | `fresh` | 上のどれにも当たらない |

内部名は `--state` の値と `--json` の出力に使う。表示は設定の `language` に合わせて訳す。

引数: `status [<id>...]`、`--state <状態>`、`--verbose`（変わったファイルの全件と sources を出す）、`--json`（`plan` と `stamp` の候補表示が使う）。sources に該当する未コミットの変更と、未追跡で ignore もされていないファイルがあれば警告し、先にコミットするよう案内する。

### 7.5 audit

1. `lint`（LLM を使わない）: 引用先の実在と行範囲、フロントマター、相対リンク、Mermaid の禁止構文、`## 関連ページ` 節、未追跡ファイルを引用・sources に含むページ。
2. drift（LLM を使う）: 「変更あり」のページだけについて、`source_commit` 以降の差分が本文の記述に影響するかを判定する。
3. 報告はスクリプト（`report`）が組み立てる。ページごとの最悪の重大度、件数、次の操作（`sync --pages`、`stamp --pages` など）を出す。drift の結果は `report --drift -` に標準入力で渡す。

`--lint-only` で 1 だけを実行する。どのファイルも書き換えない。

### 7.6 stamp

元実装の `wiki_repin.py` を正式なモードにしたもの。squash merge や rebase で `source_commit` が消えたページや、audit が「本文への影響なし」と判定したページに使う。

- 引数: `--sha <rev>`（既定 HEAD）、`--pages <id>...`、`--dry-run`
- 既定の対象は全ページ。「解決不能」と「最新」のページの `source_commit` を打ち直す。
- 「未生成」「未検証」のページは打ち直さない（未検証の印を消さないため）。
- 「変更あり」のページは、`--pages` で明示したときだけ打ち直す。
- 拒否する条件: `--sha` が解決できない、HEAD の祖先でない、未知のページ ID、対象ページの sources に未コミットの変更がある、カタログが想定の書式で再現できない。

## 8. 決定的なスクリプト

LLM を使わず、全ハーネスで同じ結果になる処理をスクリプトにまとめる。コマンドと引数の定義（説明文を含む）は 1 か所に置き、CLI の `--help` と入口スキルの help の両方がそれを使う。

**実行方式**: uv + PEP 723 の Python スクリプトとする。導入先に要求する前提は uv と git だけで、Python 本体は uv が用意する。

- 入口は `skills/wiki/scripts/agentic_doc.py` の 1 本で、先頭の PEP 723 ブロックに `requires-python` と依存（YAML が必要なら PyYAML）を宣言する。呼び出しは `uv run --script <スキルのディレクトリ>/scripts/agentic_doc.py <コマンド> [引数]`。
- 各コマンドの実装は同じ `scripts/` ディレクトリのモジュールに分け、入口から import する。
- 導入先のリポジトリでは、カレントディレクトリを導入先のルートにして実行する。導入先の `pyproject.toml` の影響を受けない呼び出し方にする（`--script` はプロジェクトを同期しない）。
- スキルの本文に呼び出し例を書くときは、スクリプトのパスを必ずダブルクォートで囲む（インストール先のパスに空白が入りうるため）。
- 入口で標準出力と標準エラーを UTF-8 に設定する（Windows ではパイプ先の既定がシステムのコードページになるため）。
- git はファイルパスを出力させるすべての呼び出しで `-c core.quotepath=false` を付けるか `-z` で区切る。既定では非 ASCII のパスが 8 進エスケープされ、sources との照合が壊れる。
- `post` は `post_commands` の各要素を `shlex.split` で引数に分割し、シェルを介さずに実行する。`{files}` を単独の引数として書いた箇所は、対象ファイルを 1 つずつ別の引数に展開する（引用符の規則を OS ごとに持たないため）。5.2 の `{files}` の説明はこの規則に置き換える。

| コマンド | 役割 |
|---|---|
| `config check` | 設定ファイルの検査（5.4） |
| `config show` | 既定値を補った設定、`context` / `instructions` の本文（`file` は毎回読む）、言語ごとの固定の文字列（`strings`）を JSON で出す。全フェーズのエージェントが最初に読む |
| `catalogue check [FILE]` | カタログを 6 章の制約（ID と path、章とページの上限、audience、related、sources の 0 件マッチなど）で検査する。FILE を省くと設定のカタログを検査し、書式も確かめる |
| `catalogue install FILE [--force]` | 検査を通ったカタログを設定の場所に置く。既存のカタログは `--force` が無ければ拒否する。全ページの `source_commit` と `reviewed_at` を null にする |
| `catalogue migrate FILE [--force] [--json]` | 旧形式のカタログ（`chapters` が無い）を変換して設定の場所に置く。章はページ ID の前半から作り（`title` は ID、`description` は空）、カタログの `title` は `<wiki_dir>/README.md` の最初の H1 から採る。`source_commit` と `reviewed_at` は保つ。余分なトップレベルのキー（`language`、`citation_style`）は捨て、`language` が設定と違えば警告する。既存のカタログは `--force` が無ければ拒否する。成功したら元のファイルを消す |
| `report [--drift FILE]` | lint と drift の結果から audit の報告（ページごとの最悪の重大度、件数、次の操作）を組み立てる |
| `status` | ページの状態の表示（7.4）。`--json` は他のコマンドの入力になる |
| `plan` | sync の対象とその件数（`target_count`。Workflow が転記の欠落を検知する）、HEAD、日付、警告、`wiki_dir`、`work_dir` を JSON で出す。判定は `status` と共通。作業ディレクトリと `.gitignore` を用意する |
| `lint` | 機械的な検査（7.5 の 1）。`--citations <id>` で、ページ内の全引用と引用先の実際の行を並べて出す（引用レンズが使う） |
| `checkpoint` | 指定ページの `source_commit` と `reviewed_at` を書く。作業ディレクトリの該当ページを削除する。本文ファイルが無いページ、HEAD の祖先でないコミット、正規の書式でないカタログは拒否する |
| `stamp` | 7.6 |
| `unverify --pages <id>...` | 書き直す前のページの `source_commit` を null に戻す。書き直しが検証を通らずに終わったページが「最新」に見えないようにするため、sync が対象のうち `source_commit` を持つページに対して最初に実行する |
| `findings` | 未解決の指摘（10.2）を保存・表示・削除する。`findings save <id> <file>`（`-` で標準入力。`schemas/findings.schema.json` で検証する）、`findings show <id>`（本文のハッシュが一致しなければ破棄して `null`）、`findings clear <id>`。Workflow はファイルを書けないため、エージェントがこのコマンドで保存する |
| `cache` | 中断後の再開用に、research の結果と書き込み済みの本文を記録・照会する（10.2）。`cache save research <id>`（作業ディレクトリの `research.json` を `schemas/research.schema.json` で検証し、`research.md` の存在を確かめ、入力のキーを記録する）、`cache save written <id>`（今の本文のキーを記録する）、`cache show <id>`（どちらが今も有効かを JSON で出す。`plan` の各対象の `cache` も同じ形） |
| `toc` | カタログから目次（`<wiki_dir>/README.md`）を生成し、`related` の相互リンクを双方向にし、各ページのフロントマターの `title` / `audience` / `updated` をカタログに揃える |
| `post` | `post_commands` を実行する。ファイルの指定が無ければ何も実行しない。`{files}` を他の文字と連結した引数があれば、どのコマンドも実行せずに拒否する |

終了コードは全コマンド共通で、0 = 問題なし、1 = 指摘あり（lint の指摘、stamp でスキップしたページなど）、2 = 拒否・入力エラー。想定外の失敗も 2 にし、1（指摘あり）と区別する。

カタログを書き換えるコマンド（`checkpoint`、`stamp`、`toc`）は、`<catalogue>.lock` で他のプロセスと排他し、一時ファイルからの置き換えで書く（Claude Code では複数ページの checkpoint が並行するため）。

Mermaid の構文検査は、実行環境があるときだけ動く任意の検査とする。

## 9. 執筆規約（全導入先で共通）

lint がこれらを前提に検査するため、設定では変えられない。言語に依存する文字列（見出し名など）は言語ごとの固定の表で決め、表に無い言語は英語にする。

- 先頭に YAML フロントマターを置き、`title`、`description`、`audience`、`updated` の 4 キーだけを書く。`title` と `description` は必ずダブルクォートで囲む。`audience` はカタログの値をそのまま角括弧で並べる。`updated` は `YYYY-MM-DD` で引用符を付けない。`sources` はフロントマターに書かない。
- 引用はバッククォートで囲んだローカル形式 `path/to/file.py:42`、範囲は `:42-58`。GitHub の blob URL は使わない。1 ページあたり 5 ファイル以上を引用する。
- `no_code` の読者層だけを持つページは、引用・ファイルパス・識別子を本文に書かない。
- Mermaid 図は 1 ページあたり 2〜4 枚。同じ図の種類を繰り返さない。`style` / `classDef` / `fill:` / `stroke:` / `<br/>` を使わない。
- 構造化できる情報は表にする。
- 推測を書かない。確認できない点は言語ごとの固定の表記（日本語なら `(未確認: ...)`）で明示する。
- 冒頭は「なぜこれが存在するのか」から始める。
- 末尾に関連ページの節を置き、`related` の各ページへ相対リンクを張る。

## 10. ハーネスごとの実行と、中断・再開

### 10.1 Claude Code と縮退動作の差

スクリプトの呼び出し順と参照文書は両者で同じ。差はオーケストレーションだけ。

| | Claude Code（Workflow） | 縮退動作（入口スキル） |
|---|---|---|
| ページの処理 | 2 ページずつ並列 | 1 ページずつ直列 |
| outline の調査と構成案 | 並列 | 直列 |
| verify | 2 レンズを別々のエージェントが並列で実行 | 同じエージェントが 2 レンズを順に実行し、レンズごとに参照文書を読み直す |
| 中断からの再開 | 10.2 | 10.2（同じ） |

### 10.2 中断・再開

- **ページ単位**: 状態はカタログの `source_commit` と Wiki のファイルの有無にある。検証を通ったページはそのつど `checkpoint` が記録するので、止まったあとに `sync` を実行し直せば残りのページだけを処理する。`toc` は何度実行しても同じ結果になる。
- **未解決の指摘の引き継ぎ**: 最大ラウンドの fix のあとも指摘が残ったページは、`.agentic-doc/work/<page-id>/findings.json` に指摘とページ本文のハッシュを保存する。次の `sync` でこれが見つかり、本文のハッシュが一致すれば、research と write を飛ばして指摘を fix に渡す。一致しなければ人が手で直したとみなして破棄し、通常の処理に戻す。`checkpoint` を書いたときに削除する。
- **research と書き込み済みの本文のキャッシュ**: research は最も重い工程なので、中断後は有効な結果を再利用する。research のエージェントは、メモ（`research.md`）と結果（`research.json`）を作業ディレクトリに書き、`cache save research` がスキーマ検証とキーの記録（`cache.json`）を行う。キーは、ページの `title`・`brief` と、`sources` に展開されるファイルの内容（作業ツリー）のハッシュで、無関係なコミットでは無効にならない。write のあと、および fix の各ラウンドのあとに `cache save written` を行い、本文と research のキーから決まるキーを記録する。次の `sync` で `plan` が各対象の `cache` を示し、research が有効なら research を、本文も有効なら research と write を飛ばして、write への入力（`research_path`・`note_path`）か検証から再開する。`checkpoint` が作業ディレクトリごと削除する。
- **作業ディレクトリの ignore**: スクリプトが作業ディレクトリを最初に作るとき、`skills/wiki/assets/work/.gitignore.in` を `.agentic-doc/work/.gitignore` としてコピーする（既にあれば上書きしない）。中身は `*` だけで、ディレクトリ全体が git から見えなくなる。導入先の `.gitignore` は変更しない。
- Claude Code の `resumeFromRunId` は同じセッション内でしか使えないので、主な仕組みにしない。

### 10.3 help と次の操作の案内

- 入口スキルを引数なしか `help` で呼ぶと、`status` の結果と `references/overview.md` をもとに、全体フローの現在地と次に実行すべきコマンド（引数まで）を示す。
- ユーザーに次に何をすべきか聞かれたときも、エージェントは同じ情報で答える。
- CLI の `--help` は静的な説明（コマンド、引数、終了コード）を出す。

## 11. エラー処理

| 場面 | 挙動 |
|---|---|
| 設定ファイルが無い、または検査に通らない | 理由を示し、`setup` を案内して止まる |
| カタログが無い（`sync` / `status` / `audit` / `stamp`） | `outline` を案内して止まる |
| sources に未コミットの変更がある、または未追跡のファイルがある | 警告して続行する。`stamp` は拒否する |
| ページ単位の失敗（エージェントの失敗、検証の全滅） | そのページを未検証のまま残し、他のページを続ける。最後に失敗したページの一覧を出す |
| 検証エージェントが全滅した、または一方のレンズしか終わらなかったページ | 「検証済み・指摘なし」と区別して未検証のまま残す。fix も、指摘の保存もしない（合成の指摘を保存すると、次の sync が無意味な fix から始まるため） |
| `post_commands` の失敗 | Wiki のファイルが原因ならエージェントが直す（最大 3 回）。既存ファイルが原因なら直さずに報告する。Wiki 以外のファイルがフックの自動修正で変わった場合は元に戻す |

## 12. テストと受入検証

**スクリプトの単体テスト**: 一時ディレクトリに git リポジトリを作り、コミット・変更・履歴の書き換え（squash 相当）を再現して、8 章の全コマンドを検査する。7.4 の 5 状態はそれぞれ専用のテストケースで固定する。リポジトリ内に非 ASCII のファイル名と空白を含むファイル名があるケースも含める。

**整合テスト**: スキーマのファイル、参照文書、Workflow とスキルが参照するパスが実在することを検査する。

単体テストと整合テストは pytest で書き、このリポジトリの開発用の `pyproject.toml`（パッケージは作らず、pytest と ruff を dev 依存に置くだけ）で実行する。

**受入検証**

| リポジトリ | 確かめること |
|---|---|
| fbx-view | 既存の Wiki を移行し、`status` / `audit` / `sync` が通る。品質が元実装から落ちていない |
| agentic-doc 自身 | `setup` から `sync` まで一通り動く |
| 小さなサンプルリポジトリ | Copilot（VS Code）と Codex CLI で縮退動作の一連の流れが動く |
| AJpon/better-experience | 構成の異なるリポジトリで、`setup` の推定と `outline` が妥当に動く |
| （OS） | Windows（PowerShell）と Linux で、スクリプトが macOS と同じ結果を返す。計画 1 の検証では macOS だけで確かめた |
| （初回実行） | Python 本体も uv のキャッシュも無い環境で、初回の実行が通る |
| （配布経路） | Codex で、このリポジトリの `marketplace.json`（`source: "./"`）からインストールして動く。Claude Code で、git のマーケットプレイスからインストールしてキャッシュに置かれた状態で動く |

**fbx-view の移行**: 設定ファイルを作り、`_catalogue.json`（`chapters` が無く、`language` と `citation_style` を持つ旧形式）を `catalogue migrate` で `catalogue.json` に変換する。setup の更新フロー（7.1 の 4）で扱える。

## 13. 既存資産の扱い

旧 PoC の追跡済みファイルは削除する（git の履歴には残る）。対象は `tools/`、`agents/`、`skills/`（旧スキル）、`hooks/`、`outputs/`、`tests/`、`mkdocs.yml`、`docs/poctodo.md`、`docs/superpowers/context/`、`docs/superpowers/plans/2026-04-04-agentic-doc-agent-plan.md`、`pyproject.toml`、`uv.lock`、`.python-version`。開発用の `pyproject.toml` は 12 章の形で作り直す。

引き継ぐものはプラグイン名 `agentic-doc` とリポジトリ。`.claude-plugin/` の 2 ファイルは書き直す。`README.md`、`.github/copilot-instructions.md`、`.github/instructions/doc-spec.instructions.md`、`AGENTS.md` は新しい構成に合わせて書き直す。`.editorconfig` と `.config/cspell*` はこのリポジトリの開発用として残す。

未追跡の `.agents/`、`.opencode/`、`docs/codebase/` はリポジトリ所有者の判断に任せ、この作業では触らない。

## 14. 将来の拡張

- 設定ファイル探索の拡張: cspell と同じ組み立て規則 `[.config/][.]agentic-doc[.config].{json,yaml,yml}` で受け入れる。候補が複数見つかったら列挙してエラーにする。同時に `root` キーを公開する（`root` 自体は設定ファイル基準で解決する）。YAML の設定ファイルは PyYAML で読めるので、探索の拡張と同時に対応する。
- モノレポ対応（1 リポジトリに複数の Wiki）
- `instructions` の適用範囲の指定（各要素に任意の `phases` を足す）
- `pin`: 人が手で書いたページを sync の自動更新から外す機能。名前を空けておく
- 閲覧層（VitePress）
- Copilot 専用のエージェント・コマンドの名前空間

## 付録: 元実装との対応

| 元実装（fbx-view） | 本設計 |
|---|---|
| `wiki.js` の `REPO_CONTEXT` | 設定の `context` / `instructions` |
| `SURVEY_AREAS` | outline の最初のエージェントがリポジトリから決める |
| `CATALOGUE_ANGLES` | 固定（層 / データの流れ / 読者層） |
| `WRITING_RULES` | `references/` の執筆規約（9 章） |
| mode `catalogue` | `outline` |
| mode `init` / `update` | `sync`（統合） |
| mode `audit` | `audit` |
| `wiki_repin.py` | `stamp` |
| LLM の Plan フェーズ | `plan` スクリプト |
| haiku の checkpoint エージェント | `checkpoint` スクリプト |
| LLM の Integrate フェーズ | `toc` と `post` スクリプト（壊れたリンクの修復だけエージェント） |
| `wiki_lint.py` | `lint` |
| `_catalogue.json` | `catalogue.json`（パスは設定で変更可） |
| VitePress のサイドバー生成 | 範囲外（別サブプロジェクト） |
| cspell 辞書への未知語の追加 | 削除（必要なら `post_commands` で） |
| `deep-wiki:wiki-researcher` | 依存しない |
