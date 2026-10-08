"""config check: 設定ファイルの検査."""

import argparse
import json
from pathlib import Path

from adoc import config
from adoc.cli import Command


def add_args(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", metavar="<action>", required=True)
    c = sub.add_parser("check", help="validate .agentic-doc.config.json")
    c.add_argument("--json", action="store_true", help="print issues as JSON")


def run(args: argparse.Namespace) -> int:
    issues = config.check(Path.cwd())
    if args.json:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        for i in issues:
            print(f"{i['severity']}: {i['code']}: {i['detail']}")
        if not issues:
            print("ok")
    return 1 if any(i["severity"] == "error" for i in issues) else 0


COMMAND = Command(help="check the config file (.agentic-doc.config.json)", add_args=add_args, run=run)
