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


def load_catalogue(r: Repo, path: str = "docs/wiki/catalogue.json") -> dict:
    return json.loads((r.root / path).read_text(encoding="utf-8"))


def page(r: Repo, page_id: str) -> dict:
    """カタログ上のページを返す."""
    return next(p for p in load_catalogue(r)["pages"] if p["id"] == page_id)


def set_sources(r: Repo, page_id: str, globs: list[str]) -> None:
    """カタログの該当ページの sources を書き換える."""
    data = load_catalogue(r)
    for p in data["pages"]:
        if p["id"] == page_id:
            p["sources"] = globs
    r.write("docs/wiki/catalogue.json", dump(data))


@pytest.fixture
def five(repo) -> Repo:
    """5 状態（fresh / changed / unresolved / unverified / missing）を 1 ページずつ持つリポジトリ."""
    repo.write("src/a.py", "a")
    repo.write("src/b.py", "b")
    c1 = repo.commit()
    repo.write("src/b.py", "b2")
    c2 = repo.commit()
    for p in ["fresh", "changed", "unresolved", "unverified"]:
        repo.write(f"docs/wiki/g/{p}.md", "x")
    repo.config()
    repo.catalogue([
        {"id": "g/fresh", "path": "g/fresh.md", "sources": ["src/a.py"], "source_commit": c2},
        {"id": "g/changed", "path": "g/changed.md", "sources": ["src/b.py"], "source_commit": c1},
        {"id": "g/unresolved", "path": "g/unresolved.md", "sources": ["src/a.py"], "source_commit": "0" * 40},
        {"id": "g/unverified", "path": "g/unverified.md", "sources": ["src/a.py"], "source_commit": None},
        {"id": "g/missing", "path": "g/missing.md", "sources": ["src/a.py"], "source_commit": c2},
    ])
    repo.commit()
    return repo


def diff_lines(a: str, b: str) -> int:
    """a と b で異なる行の数（置き換えは 1 行と数える）."""
    import difflib

    return sum(1 for line in difflib.ndiff(a.splitlines(), b.splitlines()) if line.startswith("+ "))


def issue_codes(r: Repo, *args: str) -> set[str]:
    """lint --json の issues の code の集合."""
    code, out, err = run_cli(r.root, "lint", "--json", *args)
    assert code in (0, 1), err
    return {i["code"] for i in json.loads(out)["issues"]}


@pytest.fixture
def wiki(repo) -> Repo:
    """6 ファイルのソースと、規約どおりの正常なページ 2 枚を持つリポジトリ."""
    from lint_fixtures import clean_page

    repo.write("src/a.py", "1\n2\n3\n")
    for n in "bcdef":
        repo.write(f"src/{n}.py", "x\n")
    base = repo.commit()
    repo.write("docs/wiki/g/page.md", clean_page("Page", "Other", "other.md"))
    repo.write("docs/wiki/g/other.md", clean_page("Other", "Page", "page.md"))
    repo.config()
    repo.catalogue([
        {"id": "g/page", "title": "Page", "sources": ["src/*.py"], "related": ["g/other"], "source_commit": base},
        {"id": "g/other", "title": "Other", "sources": ["src/*.py"], "related": ["g/page"], "source_commit": base},
    ])
    repo.commit()
    return repo
