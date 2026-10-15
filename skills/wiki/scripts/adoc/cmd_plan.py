"""plan: sync の対象・HEAD・日付・警告を JSON で出す."""

import argparse
import json
from pathlib import Path

from adoc import catalogue, config, dates, gitutil, state, workdir
from adoc.cli import Command
from adoc.state import State

DEFAULT_TARGETS = {State.MISSING, State.UNVERIFIED, State.CHANGED}


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pages", nargs="+", metavar="ID", help="target exactly these pages, whatever their state")
    p.add_argument("--include-unresolved", action="store_true", help="also target pages whose source_commit is gone")
    p.add_argument("--today", type=dates.iso_date, default=None, help="date to record (YYYY-MM-DD, default: today)")


def reason(st: state.PageStatus, explicit: bool) -> str:
    if st.state == State.MISSING:
        return "file not found"
    if st.state == State.UNVERIFIED:
        return f"never verified ({st.pending} pending findings)" if st.pending else "never verified"
    if st.state == State.CHANGED:
        return ", ".join(st.changed[:5])
    if st.state == State.UNRESOLVED:
        return "source_commit not found"
    return "requested" if explicit else ""


def run(args: argparse.Namespace) -> int:
    root = Path.cwd()
    gitutil.ensure_repo(root)
    cfg = config.load(root)
    data = catalogue.load(cfg)
    explicit = bool(args.pages)
    pages = catalogue.select(data, args.pages)
    wanted = DEFAULT_TARGETS | ({State.UNRESOLVED} if args.include_unresolved else set())
    targets, skipped = [], []
    for p in pages:
        st = state.classify(cfg, p)
        if explicit or st.state in wanted:
            targets.append({**p, "state": st.state.value, "reason": reason(st, explicit), "pending": st.pending})
        else:
            skipped.append({"id": p["id"], "state": st.state.value})
    work = workdir.ensure_root(cfg)
    out = {
        "head": gitutil.head(cfg.root),
        "wiki_dir": cfg.wiki_dir.relative_to(cfg.root).as_posix(),
        "work_dir": work.relative_to(cfg.root).as_posix(),
        "today": args.today or dates.today(),
        "targets": targets,
        "target_count": len(targets),
        "skipped": skipped,
        "warnings": state.warnings(cfg, data["pages"]),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


COMMAND = Command(help="list the pages sync should (re)write, as JSON", add_args=add_args, run=run)
