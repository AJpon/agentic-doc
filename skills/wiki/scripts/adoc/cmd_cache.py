"""cache: 中断後の再開用に、research の結果と書き込み済みの本文を記録・照会する（仕様書 10.2）."""

import argparse
import json
from pathlib import Path

from adoc import cache, catalogue, config
from adoc.cli import Command


def add_args(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)
    s = sub.add_parser("save", help="record that research.json or the page body is current")
    s.add_argument("kind", choices=["research", "written"], help="research: validate research.json; written: the page body")
    s.add_argument("page_id", metavar="PAGE_ID")
    s.add_argument("file", nargs="?", metavar="FILE",
                   help="research only: the research result as JSON (default: the page's research.json)")
    sh = sub.add_parser("show", help="print, as JSON, whether the cached research and page body are still valid")
    sh.add_argument("page_id", metavar="PAGE_ID")


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    page = catalogue.select(catalogue.load(cfg), [args.page_id])[0]
    if args.action == "save":
        if args.kind == "research":
            cache.save_research(cfg, page, Path(args.file) if args.file else None)
        else:
            cache.save_written(cfg, page)
        print(f"{page['id']}  {args.kind}  saved")
        return 0
    print(json.dumps(cache.show(cfg, page), indent=2, ensure_ascii=False))
    return 0


COMMAND = Command(help="record and check cached research and written pages for resuming sync", add_args=add_args,
                  run=run)
