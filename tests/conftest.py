"""テスト共通のフィクスチャとヘルパー."""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "wiki" / "scripts" / "agentic_doc.py"


def dump(data) -> str:
    """カタログと同じ書式の JSON 文字列を返す."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


@dataclass
class Repo:
    """テスト用の一時 git リポジトリ."""

    root: Path

    def git(self, *args: str) -> str:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return out.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def commit(self, msg: str = "c") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.git("rev-parse", "HEAD")

    def config(self, **overrides) -> None:
        self.write(".agentic-doc.config.json", dump({"version": 1, **overrides}))

    def catalogue(self, pages: list[dict], chapters: list[dict] | None = None,
                  path: str = "docs/wiki/catalogue.json") -> None:
        full = []
        for p in pages:
            q = {"id": p["id"], "path": p.get("path", p["id"] + ".md"), "title": p["id"],
                 "audience": ["contributor"], "brief": "b", "sources": [], "related": [],
                 "source_commit": None, "reviewed_at": None}
            q.update(p)
            full.append(q)
        if chapters is None:
            seen = []
            for p in full:
                ch = p["id"].split("/")[0]
                if ch not in seen:
                    seen.append(ch)
            chapters = [{"id": c, "title": c, "description": "d"} for c in seen]
        self.write(path, dump({"version": 1, "chapters": chapters, "pages": full}))


@pytest.fixture
def repo(tmp_path) -> Repo:
    r = Repo(tmp_path / "repo")
    r.root.mkdir()
    r.git("init", "-q", "-b", "main")
    r.git("config", "user.email", "t@example.com")
    r.git("config", "user.name", "t")
    r.git("config", "commit.gpgsign", "false")
    r.git("config", "core.autocrlf", "false")
    return r


def run_cli(cwd: Path, *args: str, input: str | None = None) -> tuple[int, str, str]:
    """入口スクリプトをサブプロセスで実行する（uv を介さない）."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True,
        input=input, text=True, encoding="utf-8", check=False,
    )
    return r.returncode, r.stdout, r.stderr
