# agentic-doc 開発の指示

このリポジトリは、コードベースから Markdown Wiki を生成・保守するエージェントプラグイン `agentic-doc` を開発している。旧 DocAgent PoC（`tools/docagent` など）は削除済みで、その構成やコマンドを前提にしないこと。

- 設計の正: `docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md`
- 実行方式とハーネスの検証記録: `docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md`
- 実装計画: `docs/superpowers/plans/`
- 受入検証の手順書（Copilot と Windows の実機用）: `docs/superpowers/acceptance/`
- 旧形式のカタログは `catalogue` コマンドの `migrate` で変換する。中断後の再開用のキャッシュは `cache` コマンドが扱う。
- コミットは Conventional Commits。description は日本語か英語。
