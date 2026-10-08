"""status: ページの状態の表示（仕様書 7.4）."""

import argparse
import json
from pathlib import Path

from adoc import catalogue, config, gitutil, state
from adoc.cli import Command
from adoc.i18n import t
from adoc.state import State
from adoc.textutil import table


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("ids", nargs="*", metavar="ID", help="page ids (default: all)")
    p.add_argument("--state", choices=[s.value for s in State], help="show only pages in this state")
    p.add_argument("--verbose", action="store_true", help="list every changed file and the sources")
    p.add_argument("--json", action="store_true", help="print JSON")


def next_steps(lang: str, statuses: list[state.PageStatus], warns: dict) -> list[str]:
    """次の操作の案内."""
    steps = []
    todo = [s for s in statuses if s.state in (State.MISSING, State.UNVERIFIED, State.CHANGED)]
    if todo:
        steps.append(t(lang, "next_sync", n=len(todo)))
    unresolved = [s.id for s in statuses if s.state == State.UNRESOLVED]
    if unresolved:
        steps.append(t(lang, "next_stamp", n=len(unresolved), ids=" ".join(unresolved)))
    if warns["uncommitted"] or warns["untracked"]:
        steps.append(t(lang, "next_commit"))
    return steps or [t(lang, "next_none")]


def reason(lang: str, s: state.PageStatus, verbose: bool) -> str:
    if s.state == State.CHANGED:
        if verbose or len(s.changed) == 1:
            return ", ".join(s.changed)
        return t(lang, "reason_more", first=s.changed[0], n=len(s.changed) - 1)
    if s.state == State.UNRESOLVED:
        return t(lang, "reason_unresolved")
    if s.pending:
        return t(lang, "reason_pending", n=s.pending)
    return ""


def collect(cfg: config.Config, data: dict) -> list[state.PageStatus]:
    return [state.classify(cfg, p) for p in data["pages"]]


def run(args: argparse.Namespace) -> int:
    root = Path.cwd()
    gitutil.ensure_repo(root)
    cfg = config.load(root)
    data = catalogue.load(cfg)
    shown_pages = catalogue.select(data, args.ids)
    head = gitutil.head(cfg.root)
    statuses = collect(cfg, data)
    by_id = {s.id: s for s in statuses}
    shown = [by_id[p["id"]] for p in shown_pages]
    if args.state:
        shown = [s for s in shown if s.state == args.state]
    warns = state.warnings(cfg, data["pages"])
    counts = {s.value: sum(1 for x in statuses if x.state == s) for s in reversed(State)}
    steps = next_steps(cfg.language, statuses, warns)
    wiki_dir = cfg.wiki_dir.relative_to(cfg.root).as_posix()
    cat = cfg.catalogue.relative_to(cfg.root).as_posix() if cfg.catalogue.is_relative_to(cfg.root) else str(cfg.catalogue)
    if args.json:
        out = {
            "head": head, "wiki_dir": wiki_dir, "catalogue": cat,
            "pages": [{"id": s.id, "state": s.state.value, "base": s.base, "reviewed_at": s.reviewed_at,
                       "changed": s.changed, "pending": s.pending} for s in shown],
            "counts": counts, "warnings": warns, "next": steps,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    lang = cfg.language
    print(t(lang, "status_header", wiki_dir=wiki_dir, catalogue=Path(cat).name, count=len(data["pages"]),
            head=head[:7]))
    print()
    rows = [[t(lang, k) for k in ("status_col_id", "status_col_state", "status_col_base",
                                   "status_col_reviewed", "status_col_reason")]]
    pages_by_id = catalogue.page_index(data)
    for s in shown:
        rows.append([s.id, t(lang, f"state_{s.state.value}"), (s.base or "-")[:7], s.reviewed_at or "-",
                     reason(lang, s, args.verbose)])
        if args.verbose:
            rows.append(["", "", "", "", f"{t(lang, 'verbose_sources')}: {' '.join(pages_by_id[s.id]['sources'])}"])
    for line in table(rows):
        print(line)
    print()
    print(" / ".join(f"{t(lang, f'state_{k}')} {v}" for k, v in counts.items()))
    if warns["uncommitted"]:
        print(t(lang, "status_uncommitted", files=", ".join(warns["uncommitted"])))
    if warns["untracked"]:
        print(t(lang, "status_untracked", files=", ".join(warns["untracked"])))
    print(t(lang, "status_next", steps=" / ".join(steps)))
    return 0


COMMAND = Command(help="show the state of each wiki page", add_args=add_args, run=run)
