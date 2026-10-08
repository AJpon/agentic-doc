"""カタログ（既定 <wiki_dir>/catalogue.json）の読み書き."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from adoc.config import Config
from adoc.errors import Refused

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "catalogue.schema.json"


def dump(data: dict) -> str:
    """2 スペースインデント・非 ASCII はそのまま・末尾改行 1 つ."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _rel(cfg: Config, path: Path) -> str:
    try:
        return path.relative_to(cfg.root).as_posix()
    except ValueError:
        return str(path)


def load(cfg: Config) -> dict:
    """カタログを読み、schema で検証する."""
    if not cfg.catalogue.is_file():
        raise Refused(f"catalogue not found: {_rel(cfg, cfg.catalogue)} — run outline")
    try:
        data = json.loads(cfg.catalogue.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Refused(f"catalogue is not valid JSON: line {e.lineno} column {e.colno}: {e.msg}") from e
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        e = errors[0]
        pointer = "/" + "/".join(str(p) for p in e.absolute_path)
        raise Refused(f"catalogue does not match the schema: {pointer}: {e.message}")
    return data


def save(cfg: Config, data: dict) -> None:
    """カタログを書く。ディスク上の元テキストが正規の書式でなければ Refused."""
    original = cfg.catalogue.read_text(encoding="utf-8")
    if dump(json.loads(original)) != original:
        raise Refused("catalogue is not in canonical format (2-space JSON); refusing to rewrite")
    cfg.catalogue.write_bytes(dump(data).encode("utf-8"))


def page_index(data: dict) -> dict[str, dict]:
    """ページ ID からページへの辞書."""
    return {p["id"]: p for p in data["pages"]}


def page_file(cfg: Config, page: dict) -> Path:
    """ページの本文ファイルの絶対パス."""
    return cfg.wiki_dir / page["path"]


def select(data: dict, ids: list[str] | None) -> list[dict]:
    """ids の順にページを返す。ids が空なら全ページ。未知の ID は Refused."""
    if not ids:
        return list(data["pages"])
    index = page_index(data)
    unknown = [i for i in ids if i not in index]
    if unknown:
        raise Refused(f"unknown page id: {', '.join(unknown)}")
    return [index[i] for i in ids]
