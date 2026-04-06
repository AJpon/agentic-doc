---
description: "Use when: wiki ドキュメントの作成・解析・保守。キーワード: wiki, docs, index, template, extract, ingest, generate, docagent"
applyTo: "docs/**, wiki/**, tools/**, agents/**, skills/**, README.md"
---

# 概要
このリポジトリは Claude Code や GitHub Copilot 向けのエージェントプラグインを開発するものです。エージェントはウィキベースのソフトウェアドキュメントの自動生成・解析・保守を行います。

## 使用条件 (Use when)
- docs/ または wiki/ に関する作業を行うとき。
- テンプレートを用いてページを生成・更新するとき。
- インデックスやクロスリンクを更新するとき。
- 抽出器（extractors）で API 情報やコードスニペットを取り込むとき。

（発見用キーワード: wiki, documentation, index, template, extract, ingest, generate, docagent）

## 優先ルール
- 新規ドキュメントの既定言語は既存ページに合わせる。ページがまだ存在しない場合は `#askQuestions` を使用して、どの言語を使用するかユーザーに尋ねる。
- 変更は原則 PR 作成で行う。直接 `main` にコミットしない。
- ドキュメントは Markdown で作成し、`tools/templates/basic_page.tpl.md` を優先テンプレートとして利用する。
- 各ページは YAML frontmatter を必ず含める（例: `title`, `summary`, `tags`, `source`）。

## 書式とテンプレート
- 見出しは H1 をページ先頭に1つだけ置く。
- コードブロックは必ず言語指定する（例: ```python）。
- メタ情報は frontmatter（YAML）で管理する。

例:
```
---
title: ページタイトル
summary: ページ概要の一行要約
tags: [index, api]
---

# ページタイトル

本文...
```

## インデックスとリンク
- `docs/index.md` や `wiki/index.md` を更新し、索引を最新に保つ。
- クロスリンクは原則相対パスを使用し、アンカーは一意にする。

## 自動処理とフック
- 抽出や検証、差分生成は `hooks/` に定義されたフックを利用する（例: `docagent-preindex.json`, `post-generate-diff.json`）。
- 生成後は差分を確認し、必要ならレビュー用の PR を作成する。

## 禁止事項
- 明示的な依頼がない限り、ソースコードのロジック修正は行わない。
- 機密情報やトークンを生成・公開しない。

## 例示プロンプト
- "docs/index.md を最新のモジュール一覧で更新し、変更を PR にしてください。"
- "tools/templates/basic_page.tpl.md を元に新しい API ページを wiki/ に作成してください（参照: tools/docagent/ingest.py）。"
- "wiki/cli.py.md を解析して欠落している使用例を追加してください。"


## 運用メモ
- `description` に上記キーワードを含め、検出性を高めること。
- `applyTo` グロブは必要に応じて追加・調整してください。

-- エンド
