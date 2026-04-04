<!-- これはサブエージェントが生成しました -->
## Files I Need
### Must See
- `tools/docagent/ingest.py` — 実装エントリ。リポジトリ走査ロジックと出力フォーマットを確認するため。
- `tools.docagent/extractors/py_extractor.py` — Python 抽出の出力形式を理解するため。
### Should See
- `tools.docagent/extractors/ts_extractor.py` — 他言語抽出の挙動確認。
- `tools.docagent/templates/basic_page.tpl.md` — 出力テンプレートの参照。
### Already Have
- `README.md` — プロジェクト概要。
### Uncertainties
- 抽出対象に含めるファイルの除外ルール（大きなバイナリやnode_modulesなど）。
