"""中断・再開用の作業ディレクトリ <root>/.agentic-doc/work/."""

from pathlib import Path

from adoc.config import Config


def work_dir(cfg: Config) -> Path:
    return cfg.root / ".agentic-doc" / "work"


def findings_path(cfg: Config, page_id: str) -> Path:
    """ページの未解決の指摘を置くファイル."""
    return work_dir(cfg) / page_id / "findings.json"


def pending_count(cfg: Config, page_id: str, page_text: str | None) -> int:
    """保留中の指摘の件数。ファイルが無ければ 0."""
    if not findings_path(cfg, page_id).is_file():
        return 0
    return 0
