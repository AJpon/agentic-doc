# 実行方式とハーネスの検証記録

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
