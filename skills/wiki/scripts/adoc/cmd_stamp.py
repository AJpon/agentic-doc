"""stamp: source_commit を打ち直す（仕様書 7.6）."""

import argparse
from pathlib import Path

from adoc import catalogue, commits, config, gitutil, state
from adoc.cli import Command
from adoc.errors import Refused
from adoc.state import State


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sha", default="HEAD", help="commit to stamp (default: HEAD)")
    p.add_argument("--pages", nargs="+", metavar="ID", help="pages to stamp (default: all)")
    p.add_argument("--dry-run", action="store_true", help="show the result without writing")


def decide(cfg: config.Config, pages: list[dict], target: str, explicit: bool):
    """(打ち直す ID, 変更なしの ID, (ID, 理由) のスキップ) を返す."""
    repin, unchanged, skipped = [], [], []
    for p in pages:
        st = state.classify(cfg, p)
        if st.state == State.MISSING:
            skipped.append((p["id"], "page file not found"))
            continue
        if st.state == State.UNVERIFIED:
            skipped.append((p["id"], "never verified (source_commit is null)"))
            continue
        if st.state == State.CHANGED and not explicit:
            skipped.append((p["id"], "changed: " + ", ".join(st.changed[:5])))
            continue
        later = gitutil.changed_since(cfg.root, target, p["sources"], cfg.exclude) or []
        if later and not explicit:
            skipped.append((p["id"], "changed after target: " + ", ".join(later[:5])))
        elif p["source_commit"] == target:
            unchanged.append(p["id"])
        else:
            repin.append(p["id"])
    return repin, unchanged, skipped


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    with catalogue.locked(cfg):
        return _run(args, cfg)


def _run(args: argparse.Namespace, cfg: config.Config) -> int:
    gitutil.ensure_repo(cfg.root)
    data = catalogue.load(cfg)
    catalogue.ensure_canonical(cfg)
    target = commits.target_commit(cfg, args.sha)
    pages = catalogue.select(data, args.pages)
    sources = sorted({g for p in pages for g in p["sources"]})
    dirty = gitutil.dirty(cfg.root, sources, cfg.exclude) if sources else []
    if dirty:
        raise Refused(f"uncommitted changes in sources: {', '.join(dirty[:5])}")
    repin, unchanged, skipped = decide(cfg, pages, target, bool(args.pages))
    index = catalogue.page_index(data)
    for pid in repin:
        index[pid]["source_commit"] = target
    if repin and not args.dry_run:
        catalogue.save(cfg, data)
    print(f"target: {target[:12]}" + (" (dry-run: nothing written)" if args.dry_run else ""))
    print(f"stamped: {len(repin)}")
    for pid in repin:
        print(f"  {pid}")
    print(f"skipped: {len(skipped)}")
    for pid, why in skipped:
        print(f"  {pid}  {why}")
    print(f"unchanged: {len(unchanged)}")
    for pid in unchanged:
        print(f"  {pid}")
    return 1 if skipped else 0


COMMAND = Command(help="re-pin source_commit after squash merge/rebase or a no-impact review",
                  add_args=add_args, run=run)
