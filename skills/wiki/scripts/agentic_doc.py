# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "jsonschema>=4.23"]
# ///
"""agentic-doc の決定的なスクリプトの入口.

呼び出し（カレントディレクトリは導入先のルート）:
    uv run --script "<スキルのディレクトリ>/scripts/agentic_doc.py" <コマンド> [引数]

終了コード: 0 = 問題なし、1 = 指摘あり、2 = 拒否・入力エラー。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adoc import cmd_config
from adoc.cli import Command
from adoc.errors import Refused

COMMANDS: dict[str, Command] = {
    "config": cmd_config.COMMAND,
}


class _Parser(argparse.ArgumentParser):
    """使い方エラーを終了コード 2 で返すパーサ（argparse の既定と同じ値）."""


def build_parser() -> argparse.ArgumentParser:
    """COMMANDS からパーサを組み立てる."""
    parser = _Parser(prog="agentic_doc.py", description="agentic-doc deterministic scripts")
    sub = parser.add_subparsers(dest="command", metavar="<command>", required=True)
    for name, cmd in COMMANDS.items():
        p = sub.add_parser(name, help=cmd.help, description=cmd.help)
        cmd.add_args(p)
        p.set_defaults(_run=cmd.run)
    return parser


def main(argv: list[str] | None = None) -> int:
    """コマンドライン入口."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    try:
        return args._run(args)
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
