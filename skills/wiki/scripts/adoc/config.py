"""設定ファイル .agentic-doc.config.json の読み込みと検査."""

import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from adoc import gitutil
from adoc.errors import Refused

CONFIG_NAME = ".agentic-doc.config.json"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "config.schema.json"
DEFAULT_AUDIENCES = [
    {"id": "contributor", "title": "Contributors", "description": "People changing the code", "no_code": False},
    {"id": "agent", "title": "AI agents", "description": "Coding agents changing the code", "no_code": False},
]
DEFAULT_CONTEXT_FILES = ["README.md", "AGENTS.md", "CLAUDE.md"]


@dataclass(frozen=True)
class Config:
    """既定値を補った設定。パスは絶対パス."""

    root: Path
    wiki_dir: Path
    catalogue: Path
    language: str
    audiences: list[dict]
    exclude: list[str]
    context: list[dict]
    instructions: list[dict]
    post_commands: list[str]
    max_pages: int


def _read(root: Path) -> dict:
    path = Path(root) / CONFIG_NAME
    if not path.is_file():
        raise Refused(f"config not found: {CONFIG_NAME} — run setup")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Refused(f"{CONFIG_NAME} is not valid JSON: line {e.lineno} column {e.colno}: {e.msg}") from e


def _schema_errors(raw: dict) -> list[str]:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    return [f"/{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors]


def load(root: Path) -> Config:
    """設定を読み、検証し、既定値を補う."""
    root = Path(root).resolve()
    raw = _read(root)
    errors = _schema_errors(raw)
    if errors:
        raise Refused(f"{CONFIG_NAME} does not match the schema: {errors[0]}")
    wiki_dir = root / raw.get("wiki_dir", "docs/wiki")
    catalogue = root / raw["catalogue"] if "catalogue" in raw else wiki_dir / "catalogue.json"
    context = raw.get("context")
    if context is None:
        context = [{"file": f} for f in DEFAULT_CONTEXT_FILES if (root / f).is_file()]
    return Config(
        root=root,
        wiki_dir=wiki_dir,
        catalogue=catalogue,
        language=raw.get("language", "en"),
        audiences=raw.get("audiences", DEFAULT_AUDIENCES),
        exclude=raw.get("exclude", []),
        context=context,
        instructions=raw.get("instructions", []),
        post_commands=raw.get("post_commands", []),
        max_pages=raw.get("max_pages", 24),
    )


def _issue(severity: str, code: str, detail: str) -> dict:
    return {"severity": severity, "code": code, "detail": detail}


def check(root: Path) -> list[dict]:
    """設定を検査して問題の一覧を返す。設定ファイルが無い・JSON でなければ Refused."""
    root = Path(root).resolve()
    raw = _read(root)
    errors = _schema_errors(raw)
    if errors:
        return [_issue("error", "schema", e) for e in errors]
    cfg = load(root)
    issues = []
    for key in ("context", "instructions"):
        for i, item in enumerate(getattr(cfg, key)):
            if "file" in item and not (cfg.root / item["file"]).is_file():
                issues.append(_issue("error", "file-missing", f"/{key}/{i}: {item['file']}"))
    for i, cmd in enumerate(cfg.post_commands):
        if "{files}" not in cmd:
            issues.append(_issue("error", "post-no-files", f"/post_commands/{i}: {cmd}"))
    ids = [a["id"] for a in cfg.audiences]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        issues.append(_issue("error", "audience-duplicate", f"audiences id: {dup}"))
    if cfg.exclude:
        gitutil.ensure_repo(cfg.root)
        for i, glob in enumerate(cfg.exclude):
            if not gitutil.ls_files(cfg.root, [glob], []):
                issues.append(_issue("warning", "exclude-empty", f"/exclude/{i}: {glob} matches no tracked file"))
    return issues
