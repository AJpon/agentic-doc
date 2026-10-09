"""report: lint と drift の結果から audit の報告を組み立てる（仕様書 7.5 の 3）."""

import argparse
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from adoc import catalogue, config, gitutil, lint, state
from adoc.cli import Command
from adoc.errors import Refused
from adoc.i18n import t
from adoc.state import State
from adoc.textutil import table

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "drift.schema.json"
RANK = {"blocker": 3, "major": 2, "minor": 1}
HEADLINE_MAX = 120
SENTENCE_END = re.compile(r"。|\.\s")


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--drift", metavar="FILE", help='drift results {"results": [...], "failed": [...]}, - for stdin')
    p.add_argument("--mermaid", action="store_true", help="also parse Mermaid blocks (see lint --mermaid)")
    p.add_argument("--json", action="store_true", help="print JSON")


def _read_drift(src: str | None) -> dict:
    if src is None:
        return {"results": [], "failed": []}
    text = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise Refused(f"drift results are not valid JSON: {e.msg}") from e
    if not isinstance(data, dict) or not isinstance(data.get("results"), list) or not isinstance(
            data.get("failed"), list):
        raise Refused('drift results must be {"results": [...], "failed": [...]}')
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    for n, r in enumerate(data["results"]):
        errors = sorted(validator.iter_errors(r), key=lambda e: list(e.absolute_path))
        if errors:
            e = errors[0]
            raise Refused(f"drift result {n} does not match the schema: "
                          f"/{'/'.join(str(p) for p in e.absolute_path)}: {e.message}")
    return data


def _headline(text: str) -> str:
    first = SENTENCE_END.split(text, maxsplit=1)[0].strip()
    return first[:HEADLINE_MAX] + "…" if len(first) > HEADLINE_MAX else first


def build(cfg, data: dict, drift: dict, mermaid: bool = False) -> dict:
    """報告を組み立てる."""
    pages = data["pages"]
    issues = lint.collect(cfg, data, pages, mermaid=mermaid)
    rows: dict[str, dict] = {}

    def add(page_id: str, severity: str, text: str) -> None:
        r = rows.setdefault(page_id, {"page_id": page_id, "issue_count": 0, "rank": 0, "headline": ""})
        r["issue_count"] += 1
        if RANK[severity] > r["rank"]:
            r["rank"] = RANK[severity]
            r["headline"] = _headline(text)

    for i in issues:
        add(i["page"], i["severity"], f"[{i['code']}] {i['detail']}")
    for d in drift["results"]:
        for i in d["issues"]:
            add(d["page_id"], i["severity"], i["problem"])
    ordered = sorted(rows.values(), key=lambda r: (-r["rank"], -r["issue_count"]))
    by_page = [{"page_id": r["page_id"], "issue_count": r["issue_count"],
                "worst_severity": next(k for k, v in RANK.items() if v == r["rank"]), "headline": r["headline"]}
               for r in ordered]
    statuses = [state.classify(cfg, p) for p in pages]
    needs_update = [{"page_id": s.id, "state": s.state.value} for s in statuses
                    if s.state in (State.MISSING, State.UNVERIFIED, State.UNRESOLVED)]
    lang = cfg.language
    nxt = []

    def ids(items) -> str:
        return " ".join(items)

    if any(i["code"] == "source-uncommitted" for i in issues):
        nxt.append(t(lang, "next_commit"))
    todo = [n["page_id"] for n in needs_update if n["state"] != State.UNRESOLVED]
    if todo:
        nxt.append(t(lang, "report_sync", ids=ids(todo)))
    gone = [n["page_id"] for n in needs_update if n["state"] == State.UNRESOLVED]
    if gone:
        nxt.append(t(lang, "report_stamp_or_sync", ids=ids(gone)))
    if drift["failed"]:
        nxt.append(t(lang, "report_rerun_audit", ids=ids(drift["failed"])))
    drift_major = [d["page_id"] for d in drift["results"] if any(RANK[i["severity"]] >= 2 for i in d["issues"])]
    if drift_major:
        nxt.append(t(lang, "report_drift_sync", ids=ids(drift_major)))
    lint_pages = list(dict.fromkeys(i["page"] for i in issues))
    if lint_pages:
        nxt.append(t(lang, "report_fix_lint", ids=ids(lint_pages)))
    changed = {s.id for s in statuses if s.state == State.CHANGED}
    quiet = [d["page_id"] for d in drift["results"] if not d["issues"] and d["page_id"] in changed]
    if quiet:
        nxt.append(t(lang, "report_stamp_quiet", ids=ids(quiet)))
    return {
        "pages_checked": len(pages),
        "total_issues": sum(r["issue_count"] for r in by_page),
        "by_page": by_page,
        "needs_update": needs_update,
        "drift_failed": drift["failed"],
        "next": nxt or [t(lang, "next_none")],
    }


def run(args: argparse.Namespace) -> int:
    root = Path.cwd()
    gitutil.ensure_repo(root)
    cfg = config.load(root)
    data = catalogue.load(cfg)
    drift = _read_drift(args.drift)
    rep = build(cfg, data, drift, mermaid=args.mermaid)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        lang = cfg.language
        print(t(lang, "report_header", pages=rep["pages_checked"], issues=rep["total_issues"]))
        if rep["by_page"]:
            print()
            rows = [[t(lang, k) for k in ("status_col_id", "report_col_count", "report_col_worst",
                                           "report_col_headline")]]
            rows += [[r["page_id"], str(r["issue_count"]), r["worst_severity"], r["headline"]] for r in rep["by_page"]]
            for line in table(rows):
                print(line)
        if rep["needs_update"]:
            items = ", ".join(f"{n['page_id']} ({t(lang, 'state_' + n['state'])})" for n in rep["needs_update"])
            print()
            print(t(lang, "report_needs_update", items=items))
        print()
        print(t(lang, "status_next", steps=" / ".join(rep["next"])))
    return 1 if rep["total_issues"] else 0


COMMAND = Command(help="build the audit report from lint and drift results", add_args=add_args, run=run)
