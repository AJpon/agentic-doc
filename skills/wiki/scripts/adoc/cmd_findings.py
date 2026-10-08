"""findings: 未解決の指摘の保存・表示・削除（仕様書 10.2）."""

import argparse
import json
import sys
from pathlib import Path

from adoc import catalogue, config, workdir
from adoc.cli import Command
from adoc.errors import Refused


def add_args(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)
    s = sub.add_parser("save", help="save findings (JSON array) for a page")
    s.add_argument("page_id", metavar="PAGE_ID")
    s.add_argument("file", metavar="FILE", help="JSON array of findings, or - for stdin")
    sh = sub.add_parser("show", help="print saved findings as JSON (null if none or stale)")
    sh.add_argument("page_id", metavar="PAGE_ID")
    c = sub.add_parser("clear", help="delete saved findings")
    c.add_argument("page_id", metavar="PAGE_ID")


def _read_findings(src: str) -> list:
    text = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise Refused(f"findings are not valid JSON: {e.msg}") from e
    if not isinstance(data, list):
        raise Refused("findings must be a JSON array")
    return data


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    data = catalogue.load(cfg)
    page = catalogue.select(data, [args.page_id])[0]
    path = catalogue.page_file(cfg, page)
    if args.action == "clear":
        workdir.clear(cfg, page["id"])
        return 0
    if args.action == "save":
        findings = _read_findings(args.file)
        if not path.is_file():
            raise Refused(f"page file not found: {page['path']}")
        workdir.save(cfg, page["id"], findings, path.read_text(encoding="utf-8"))
        return 0
    found = workdir.load(cfg, page["id"], path.read_text(encoding="utf-8")) if path.is_file() else None
    print(json.dumps(found, indent=2, ensure_ascii=False))
    return 0


COMMAND = Command(help="save, show or clear unresolved review findings of a page", add_args=add_args, run=run)
