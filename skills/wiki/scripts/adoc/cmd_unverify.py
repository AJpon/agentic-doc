"""unverify: 書き直す前のページの source_commit を null に戻す（検証を通るまで未検証として扱う）."""

import argparse
from pathlib import Path

from adoc import catalogue, config, gitutil
from adoc.cli import Command


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pages", nargs="+", metavar="ID", required=True, help="pages about to be rewritten")


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    gitutil.ensure_repo(cfg.root)
    with catalogue.locked(cfg):
        data = catalogue.load(cfg)
        catalogue.ensure_canonical(cfg)
        pages = catalogue.select(data, args.pages)
        for p in pages:
            p["source_commit"] = None
        catalogue.save(cfg, data)
    for p in pages:
        print(p["id"])
    return 0


COMMAND = Command(help="reset source_commit to null for pages about to be rewritten", add_args=add_args, run=run)
