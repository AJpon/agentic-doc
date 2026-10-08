"""checkpoint: 検証を通ったページの source_commit と reviewed_at を書く."""

import argparse
from pathlib import Path

from adoc import catalogue, commits, config, dates, gitutil, workdir
from adoc.cli import Command
from adoc.errors import Refused


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pages", nargs="+", metavar="ID", required=True, help="pages that passed review")
    p.add_argument("--sha", default="HEAD", help="commit to record (default: HEAD)")
    p.add_argument("--today", type=dates.iso_date, default=None, help="review date (YYYY-MM-DD, default: today)")


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    with catalogue.locked(cfg):
        return _run(args, cfg)


def _run(args: argparse.Namespace, cfg: config.Config) -> int:
    gitutil.ensure_repo(cfg.root)
    data = catalogue.load(cfg)
    catalogue.ensure_canonical(cfg)
    pages = catalogue.select(data, args.pages)
    missing = [p["id"] for p in pages if not catalogue.page_file(cfg, p).is_file()]
    if missing:
        raise Refused(f"page file not found: {', '.join(missing)}")
    sha = commits.target_commit(cfg, args.sha)
    today = args.today or dates.today()
    for p in pages:
        p["source_commit"] = sha
        p["reviewed_at"] = today
    catalogue.save(cfg, data)
    for p in pages:
        workdir.clear(cfg, p["id"])
        print(f"{p['id']}  {sha[:7]}  {today}")
    return 0


COMMAND = Command(help="record source_commit and reviewed_at for pages that passed review",
                  add_args=add_args, run=run)
