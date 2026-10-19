"""中断後の再開用キャッシュ: research の結果と、書き込み済みの本文（作業ディレクトリ内）.

有効かどうかは、入力のハッシュで決める。無関係なコミットでは無効にならない。
- research: ページの brief・title と、sources に展開されるファイルの内容（作業ツリー）
- written: 本文のハッシュと research のキー
"""

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from adoc import catalogue, gitutil, workdir
from adoc.config import Config
from adoc.errors import Refused

RESEARCH_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "research.schema.json"
MISSING = b"<missing>"


def _dir(cfg: Config, page: dict) -> Path:
    return workdir.work_dir(cfg) / page["id"]


def research_file(cfg: Config, page: dict) -> Path:
    return _dir(cfg, page) / "research.json"


def note_file(cfg: Config, page: dict) -> Path:
    return _dir(cfg, page) / "research.md"


def _keys_file(cfg: Config, page: dict) -> Path:
    return _dir(cfg, page) / "cache.json"


def research_key(cfg: Config, page: dict) -> str:
    """brief・title・sources のファイル内容から決まるキー."""
    h = hashlib.sha256()
    for part in (page["title"], page["brief"]):
        h.update(part.encode("utf-8") + b"\0")
    for rel in sorted(gitutil.ls_files(cfg.root, page["sources"], cfg.exclude)):
        path = cfg.root / rel
        body = path.read_bytes() if path.is_file() else MISSING
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(body).digest())
    return h.hexdigest()


def written_key(cfg: Config, page: dict) -> str | None:
    """本文と research のキーから決まるキー。本文が無ければ None."""
    path = catalogue.page_file(cfg, page)
    if not path.is_file():
        return None
    body = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(f"{body}\0{research_key(cfg, page)}".encode()).hexdigest()


def _load_keys(cfg: Config, page: dict) -> dict:
    try:
        data = json.loads(_keys_file(cfg, page).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _store_key(cfg: Config, page: dict, kind: str, key: str) -> None:
    keys = _load_keys(cfg, page)
    keys[kind] = key
    path = _keys_file(cfg, page)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(keys, indent=2) + "\n").encode("utf-8"))


def save_research(cfg: Config, page: dict) -> None:
    """research.json を検証し、今の入力のキーを記録する."""
    path, note = research_file(cfg, page), note_file(cfg, page)
    rel = path.relative_to(cfg.root).as_posix()
    if not path.is_file():
        raise Refused(f"research result not found: {rel}")
    if not note.is_file():
        raise Refused(f"research notes not found: {note.relative_to(cfg.root).as_posix()}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Refused(f"{rel} is not valid JSON: {e.msg}") from e
    validator = Draft202012Validator(json.loads(RESEARCH_SCHEMA.read_text(encoding="utf-8")))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        e = errors[0]
        raise Refused(f"{rel} does not match the research schema: /{'/'.join(str(p) for p in e.absolute_path)}: "
                      f"{e.message}")
    _store_key(cfg, page, "research", research_key(cfg, page))


def save_written(cfg: Config, page: dict) -> None:
    """今の本文と入力のキーを記録する."""
    key = written_key(cfg, page)
    if key is None:
        raise Refused(f"page file not found: {page['path']}")
    _store_key(cfg, page, "written", key)


def show(cfg: Config, page: dict) -> dict:
    """research と written のキャッシュが今も有効か."""
    keys = _load_keys(cfg, page)
    root = cfg.root
    out: dict = {"research": {"hit": False}, "written": {"hit": False}}
    path, note = research_file(cfg, page), note_file(cfg, page)
    if path.is_file() and note.is_file() and keys.get("research") == research_key(cfg, page):
        out["research"] = {"hit": True, "path": path.relative_to(root).as_posix(),
                           "note_path": note.relative_to(root).as_posix()}
        if keys.get("written") == written_key(cfg, page):
            out["written"] = {"hit": True}
    return out
