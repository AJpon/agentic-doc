# agentic-doc

コードベースから Markdown の Wiki を生成し、コードの変化に追随させ続けるためのエージェントプラグインです。各ページが依存するファイルとコミットを記録し、git の差分で古くなったページを見つけて書き直します。Claude Code、GitHub Copilot（VS Code）、Codex CLI での利用を想定しています。

## 状態

開発中です。まだ利用できる機能はありません。

## 設計

- [設計仕様](docs/superpowers/specs/2026-10-08-agentic-doc-wiki-plugin-design.md)
- [実行方式とハーネスの検証記録](docs/superpowers/research/2026-10-08-runtime-and-harness-probes.md)
