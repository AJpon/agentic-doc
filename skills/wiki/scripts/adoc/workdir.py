"""中断・再開用の作業ディレクトリ <root>/.agentic-doc/work/（仕様書 10.2）."""

import hashlib
import json
import shutil
from pathlib import Path

from adoc.config import Config

GITIGNORE_TEMPLATE = Path(__file__).resolve().parents[2] / "assets" / "work" / ".gitignore.in"


def work_dir(cfg: Config) -> Path:
    return cfg.root / ".agentic-doc" / "work"


def findings_path(cfg: Config, page_id: str) -> Path:
    """ページの未解決の指摘を置くファイル."""
    return work_dir(cfg) / page_id / "findings.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(cfg: Config, page_id: str, page_text: str) -> tuple[list[dict] | None, bool]:
    """(指摘, ハッシュが一致したか)。ファイルが無ければ (None, True)."""
    path = findings_path(cfg, page_id)
    if not path.is_file():
        return None, True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ok = data["page_sha256"] == _sha256(page_text)
        return (data["findings"] if ok else None), ok
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, False


def save(cfg: Config, page_id: str, findings: list[dict], page_text: str) -> Path:
    """指摘とページ本文のハッシュを保存する。初回は .gitignore を置く."""
    ignore = work_dir(cfg) / ".gitignore"
    if not ignore.exists():
        ignore.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(GITIGNORE_TEMPLATE, ignore)
    path = findings_path(cfg, page_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"page_sha256": _sha256(page_text), "findings": findings}
    path.write_bytes((json.dumps(body, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def load(cfg: Config, page_id: str, page_text: str) -> list[dict] | None:
    """保存された指摘。無ければ None。本文が変わっていれば破棄して None."""
    findings, ok = _read(cfg, page_id, page_text)
    if not ok:
        clear(cfg, page_id)
    return findings


def clear(cfg: Config, page_id: str) -> None:
    """ページの作業ディレクトリを削除する."""
    shutil.rmtree(work_dir(cfg) / page_id, ignore_errors=True)


def pending_count(cfg: Config, page_id: str, page_text: str | None) -> int:
    """保留中の指摘の件数。ファイルを書き換えない（本文と一致しなければ 0）."""
    if page_text is None:
        return 0
    findings, _ = _read(cfg, page_id, page_text)
    return len(findings or [])
