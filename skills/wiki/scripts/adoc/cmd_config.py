"""config: 設定ファイルの検査（check）と、既定値を補った設定の表示（show）."""

import argparse
import json
from pathlib import Path

from adoc import config
from adoc.cli import Command
from adoc.config import Config
from adoc.errors import Refused
from adoc.i18n import t

STRING_KEYS = ["related_heading", "unverified_marker"]


def add_args(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)
    c = sub.add_parser("check", help="validate .agentic-doc.config.json")
    c.add_argument("--json", action="store_true", help="print issues as JSON")
    sub.add_parser("show", help="print the resolved config, context and instructions as JSON")


def _rel(cfg: Config, path: Path) -> str:
    return path.relative_to(cfg.root).as_posix()


def _entries(cfg: Config, entries: list[dict]) -> list[dict]:
    """context / instructions の各要素を {source, text} にする。file は毎回読む."""
    out = []
    for e in entries:
        if "text" in e:
            out.append({"source": "text", "text": e["text"]})
            continue
        path = cfg.root / e["file"]
        if not path.is_file():
            raise Refused(f"context file not found: {e['file']} — run setup")
        out.append({"source": e["file"], "text": path.read_text(encoding="utf-8")})
    return out


def show(cfg: Config) -> dict:
    return {
        "wiki_dir": _rel(cfg, cfg.wiki_dir),
        "catalogue": _rel(cfg, cfg.catalogue),
        "catalogue_exists": cfg.catalogue.is_file(),
        "language": cfg.language,
        "audiences": cfg.audiences,
        "exclude": cfg.exclude,
        "context": _entries(cfg, cfg.context),
        "instructions": _entries(cfg, cfg.instructions),
        "post_commands": cfg.post_commands,
        "max_pages": cfg.max_pages,
        "strings": {k: t(cfg.language, k) for k in STRING_KEYS},
    }


def run(args: argparse.Namespace) -> int:
    if args.action == "show":
        print(json.dumps(show(config.load(Path.cwd())), indent=2, ensure_ascii=False))
        return 0
    issues = config.check(Path.cwd())
    if args.json:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        for i in issues:
            print(f"{i['severity']}: {i['code']}: {i['detail']}")
        if not issues:
            print("ok")
    return 1 if any(i["severity"] == "error" for i in issues) else 0


COMMAND = Command(help="check or show the config file (.agentic-doc.config.json)", add_args=add_args, run=run)
