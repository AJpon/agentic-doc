"""catalogue: カタログの検査（check）・設置（install）・旧形式からの変換（migrate）（仕様書 6 章、7.1、7.2）."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from adoc import catalogue, config, gitutil, workdir
from adoc.cli import Command
from adoc.config import Config
from adoc.errors import Refused

MAX_CHAPTERS = 6
MAX_PAGES_PER_CHAPTER = 8
ID_PART = re.compile(r"[a-z0-9][a-z0-9-]*")


def add_args(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)
    c = sub.add_parser("check", help="check a catalogue against the spec (default: the configured one)")
    c.add_argument("file", metavar="FILE", nargs="?", help="catalogue to check")
    c.add_argument("--json", action="store_true", help="print issues as JSON")
    i = sub.add_parser("install", help="check FILE and install it as the catalogue (source_commit reset)")
    i.add_argument("file", metavar="FILE", help="catalogue to install")
    i.add_argument("--force", action="store_true", help="overwrite an existing catalogue")
    m = sub.add_parser("migrate", help="convert an old-format catalogue (no chapters, e.g. _catalogue.json) and "
                       "install it as the catalogue, keeping source_commit")
    m.add_argument("file", metavar="FILE", help="old-format catalogue to convert (removed on success)")
    m.add_argument("--force", action="store_true", help="overwrite an existing catalogue")
    m.add_argument("--json", action="store_true", help="print the result as JSON")


def _issue(severity: str, code: str, detail: str) -> dict:
    return {"severity": severity, "code": code, "detail": detail}


def _read(path: Path) -> tuple[str, dict]:
    if not path.is_file():
        raise Refused(f"catalogue not found: {path}")
    text = path.read_bytes().decode("utf-8")
    try:
        return text, json.loads(text)
    except json.JSONDecodeError as e:
        raise Refused(f"catalogue is not valid JSON: line {e.lineno} column {e.colno}: {e.msg}") from e


def check_data(cfg: Config, data: dict) -> list[dict]:
    """カタログの内容を仕様書 6 章の制約で検査する."""
    validator = Draft202012Validator(json.loads(catalogue.SCHEMA_PATH.read_text(encoding="utf-8")))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        return [_issue("error", "schema", f"/{'/'.join(str(p) for p in e.absolute_path)}: {e.message}")
                for e in errors]
    issues: list[dict] = []
    pages, chapters = data["pages"], data["chapters"]
    ids = [p["id"] for p in pages]
    chapter_ids = [c["id"] for c in chapters]
    audiences = {a["id"] for a in cfg.audiences}
    for pid, n in Counter(ids).items():
        if n > 1:
            issues.append(_issue("error", "duplicate-id", f"{pid} appears {n} times"))
    for ch, n in Counter(chapter_ids).items():
        if n > 1:
            issues.append(_issue("error", "duplicate-chapter", f"chapter {ch} appears {n} times"))
    for ch in dict.fromkeys(chapter_ids):
        if not ID_PART.fullmatch(ch):
            issues.append(_issue("error", "id-chars", f"chapter {ch}: use lowercase letters, digits and hyphens"))
    if len(chapters) > MAX_CHAPTERS:
        issues.append(_issue("error", "chapter-count", f"{len(chapters)} chapters (at most {MAX_CHAPTERS})"))
    if len(pages) > cfg.max_pages:
        issues.append(_issue("error", "page-count", f"{len(pages)} pages (max_pages is {cfg.max_pages})"))
    per_chapter = Counter(p["id"].split("/")[0] for p in pages)
    for ch, n in per_chapter.items():
        if n > MAX_PAGES_PER_CHAPTER:
            issues.append(_issue("error", "chapter-size", f"chapter {ch} has {n} pages (at most "
                                 f"{MAX_PAGES_PER_CHAPTER})"))
    for ch in chapter_ids:
        if per_chapter[ch] == 0:
            issues.append(_issue("warning", "chapter-empty", f"chapter {ch} has no pages"))
    for p in pages:
        pid = p["id"]
        parts = pid.split("/")
        if len(parts) != 2 or not all(parts):
            issues.append(_issue("error", "id-form", f"{pid} is not <chapter>/<page>"))
        elif not all(ID_PART.fullmatch(x) for x in parts):
            issues.append(_issue("error", "id-chars", f"{pid}: use lowercase letters, digits and hyphens"))
        elif parts[0] not in chapter_ids:
            issues.append(_issue("error", "id-chapter", f"{pid}: chapter {parts[0]} is not in chapters"))
        if p["path"] != pid + ".md":
            issues.append(_issue("error", "id-path", f"{pid}: path must be {pid}.md, not {p['path']}"))
        unknown = [a for a in p["audience"] if a not in audiences]
        if unknown:
            issues.append(_issue("error", "audience-unknown", f"{pid}: unknown audience {', '.join(unknown)}"))
        for r in p["related"]:
            if r == pid:
                issues.append(_issue("warning", "related-self", f"{pid} lists itself in related"))
            elif r not in ids:
                issues.append(_issue("error", "related-unknown", f"{pid}: related page {r} does not exist"))
        for glob in p["sources"]:
            if not gitutil.ls_files(cfg.root, [glob], cfg.exclude):
                issues.append(_issue("error", "source-glob-empty", f"{pid}: sources glob matches no target file: "
                                     f"{glob}"))
    seen: list[str] = []
    for p in pages:
        ch = p["id"].split("/")[0]
        if seen and seen[-1] == ch:
            continue
        if ch in seen:
            issues.append(_issue("warning", "chapter-order", f"pages of chapter {ch} are not contiguous"))
            break
        seen.append(ch)
    return issues


def _print(issues: list[dict], as_json: bool) -> None:
    if as_json:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
        return
    for i in issues:
        print(f"{i['severity']}: {i['code']}: {i['detail']}")
    if not issues:
        print("ok")


def _readme_title(cfg: Config) -> str | None:
    readme = cfg.wiki_dir / "README.md"
    if not readme.is_file():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return None


def convert(cfg: Config, old: dict) -> tuple[dict, list[str]]:
    """旧形式のカタログ（chapters 無し）を現行の形式に変換する。ページはそのまま保つ."""
    if not isinstance(old, dict) or not isinstance(old.get("pages"), list):
        raise Refused("not an old-format catalogue: no pages array")
    warnings = []
    lang = old.get("language")
    if lang is not None and lang != cfg.language:
        warnings.append(f"old catalogue language {lang} differs from the configured language {cfg.language}")
    order: list[str] = []
    for p in old["pages"]:
        ch = str(p.get("id", "")).split("/")[0] if isinstance(p, dict) else ""
        if ch and ch not in order:
            order.append(ch)
    data: dict = {"version": 1}
    title = old.get("title") if isinstance(old.get("title"), str) else _readme_title(cfg)
    if title:
        data["title"] = title
    data["chapters"] = [{"id": c, "title": c, "description": ""} for c in order]
    data["pages"] = old["pages"]
    return data, warnings


def _migrate(cfg: Config, args: argparse.Namespace) -> int:
    src = Path(args.file).resolve()
    _, old = _read(src)
    data, warnings = convert(cfg, old)
    issues = check_data(cfg, data)
    # 旧カタログの sources は、今の exclude で全部除外されていることがある。変換は内容を変えないので、警告に留める
    soft = [i for i in issues if i["severity"] != "error" or i["code"] == "source-glob-empty"]
    warnings += [f"{i['code']}: {i['detail']}" for i in soft]
    errors = [i for i in issues if i not in soft]
    if errors:
        _print(errors, args.json)
        return 1
    with catalogue.locked(cfg):
        if cfg.catalogue.exists() and not args.force:
            raise Refused(f"catalogue already exists: {cfg.catalogue.relative_to(cfg.root).as_posix()} — pass --force "
                          "to overwrite")
        catalogue.replace(cfg, data)
    if src != cfg.catalogue.resolve():
        src.unlink()
    out = {
        "catalogue": cfg.catalogue.relative_to(cfg.root).as_posix(),
        "chapters": len(data["chapters"]),
        "pages": len(data["pages"]),
        "warnings": warnings,
        "next": "fill in each chapter's title and description in the catalogue",
    }
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    print(f"{out['catalogue']}: {out['chapters']} chapters, {out['pages']} pages")
    for w in warnings:
        print(f"warning: {w}")
    print(f"next: {out['next']}")
    return 0


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    gitutil.ensure_repo(cfg.root)
    if args.action == "migrate":
        return _migrate(cfg, args)
    if args.action == "check":
        path = Path(args.file) if args.file else cfg.catalogue
        text, data = _read(path)
        issues = check_data(cfg, data)
        if not args.file and catalogue.dump(data) != text:
            issues.insert(0, _issue("error", "format", "not in canonical format (2-space JSON, LF)"))
        _print(issues, args.json)
        return 1 if any(i["severity"] == "error" for i in issues) else 0
    _, data = _read(Path(args.file))
    issues = check_data(cfg, data)
    if any(i["severity"] == "error" for i in issues):
        _print(issues, False)
        return 1
    cfg.catalogue.parent.mkdir(parents=True, exist_ok=True)
    workdir.ensure_root(cfg)
    with catalogue.locked(cfg):
        if cfg.catalogue.exists() and not args.force:
            raise Refused(f"catalogue already exists: {cfg.catalogue.relative_to(cfg.root).as_posix()} — pass --force "
                          "to overwrite (every source_commit is reset to null)")
        for p in data["pages"]:
            p["source_commit"] = None
            p["reviewed_at"] = None
        catalogue.replace(cfg, data)
    print(cfg.catalogue.relative_to(cfg.root).as_posix())
    return 0


COMMAND = Command(help="check a catalogue against the spec, install one written by outline, or migrate an old one",
                  add_args=add_args, run=run)
