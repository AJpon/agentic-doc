"""post: post_commands をシェルを介さずに実行する（仕様書 8 章）."""

import argparse
import json
import shlex
import shutil
import subprocess
from pathlib import Path

from adoc import config
from adoc.cli import Command
from adoc.errors import Refused

PLACEHOLDER = "{files}"


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("files", nargs="*", metavar="FILE", help="files to pass as {files}")
    p.add_argument("--json", action="store_true", help="print results as JSON")


def build_argv(command: str, files: list[str]) -> list[str]:
    """shlex で分割し、{files} と完全に一致する引数を 1 ファイル 1 引数に展開する."""
    argv = []
    for arg in shlex.split(command):
        if arg == PLACEHOLDER:
            argv.extend(files)
        elif PLACEHOLDER in arg:
            raise Refused(f"{PLACEHOLDER} must be a separate argument: {command}")
        else:
            argv.append(arg)
    if not argv:
        raise Refused(f"empty post command: {command!r}")
    return argv


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    if not cfg.post_commands or not args.files:
        if args.json:
            print("[]")
        return 0
    plans = [(c, build_argv(c, args.files)) for c in cfg.post_commands]
    results = []
    for command, argv in plans:
        exe = shutil.which(argv[0])
        if exe is None:
            results.append({"command": command, "argv": argv, "code": 127, "stdout": "",
                            "stderr": f"command not found: {argv[0]}"})
            continue
        r = subprocess.run([exe, *argv[1:]], cwd=cfg.root, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", check=False)
        results.append({"command": command, "argv": argv, "code": r.returncode, "stdout": r.stdout,
                        "stderr": r.stderr})
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"$ {shlex.join(r['argv'])}")
            print(f"exit {r['code']}")
            for stream in ("stdout", "stderr"):
                if r[stream].strip():
                    print(r[stream].rstrip("\n"))
    return 1 if any(r["code"] != 0 for r in results) else 0


COMMAND = Command(help="run post_commands on the given files (no shell)", add_args=add_args, run=run)
