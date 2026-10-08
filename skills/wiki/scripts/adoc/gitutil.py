"""git の呼び出し。パスを出力させる呼び出しは常に core.quotepath=false か -z で行う."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from adoc.errors import Refused


@dataclass(frozen=True)
class GitResult:
    """git の終了コードと標準出力."""

    code: int
    out: str


def git(root: Path, *args: str) -> GitResult:
    """root で git を実行する。git が PATH に無ければ Refused."""
    exe = shutil.which("git")
    if exe is None:
        raise Refused("git not found on PATH")
    r = subprocess.run(
        [exe, "-c", "core.quotepath=false", *args],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    return GitResult(r.returncode, r.stdout)


def ensure_repo(root: Path) -> None:
    """root が git の作業ツリーでなければ Refused."""
    if not Path(root).is_dir() or git(root, "rev-parse", "--is-inside-work-tree").out.strip() != "true":
        raise Refused(f"not a git repository: {root}")


def resolve_commit(root: Path, rev: str) -> str | None:
    """rev を 40 桁のコミット SHA に解決する。解決できなければ None."""
    r = git(root, "rev-parse", "--verify", "--quiet", "--end-of-options", f"{rev}^{{commit}}")
    sha = r.out.strip()
    return sha if r.code == 0 and sha else None


def head(root: Path) -> str:
    """HEAD の SHA。コミットが無ければ Refused."""
    sha = resolve_commit(root, "HEAD")
    if sha is None:
        raise Refused("HEAD does not point to a commit")
    return sha


def is_ancestor(root: Path, sha: str, head_sha: str) -> bool:
    """sha が head_sha の祖先（または同一）か."""
    return git(root, "merge-base", "--is-ancestor", sha, head_sha).code == 0


def pathspecs(globs: list[str], exclude: list[str]) -> list[str]:
    """glob を :(glob) の pathspec に変換する。globs が空なら全体を対象にする."""
    specs = [f":(glob){g}" for g in globs] or [":(glob)**"]
    return specs + [f":(exclude,glob){e}" for e in exclude]


def _split_z(out: str) -> list[str]:
    return [p for p in out.split("\0") if p]


def ls_files(root: Path, globs: list[str], exclude: list[str]) -> list[str]:
    """追跡済みファイルのうち globs にマッチし exclude にマッチしないもの."""
    return _split_z(git(root, "ls-files", "-z", "--", *pathspecs(globs, exclude)).out)


def changed_since(root: Path, sha: str, globs: list[str], exclude: list[str]) -> list[str] | None:
    """sha から HEAD までに変わったファイル。sha が解決できなければ None."""
    if resolve_commit(root, sha) is None:
        return None
    r = git(root, "diff", "--name-only", "-z", f"{sha}..HEAD", "--", *pathspecs(globs, exclude))
    return _split_z(r.out) if r.code == 0 else None


def dirty(root: Path, globs: list[str], exclude: list[str]) -> list[str]:
    """未コミットの変更・追加・削除があるパス（未追跡は含まない）."""
    entries = _split_z(git(root, "status", "--porcelain", "-z", "--", *pathspecs(globs, exclude)).out)
    paths, skip = [], False
    for e in entries:
        if skip:
            skip = False
            continue
        status, path = e[:2], e[3:]
        if status == "??" or status == "!!":
            continue
        if "R" in status or "C" in status:
            skip = True
        paths.append(path)
    return paths


def untracked(root: Path, globs: list[str], exclude: list[str]) -> list[str]:
    """未追跡で ignore もされていないファイル."""
    return _split_z(git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", *pathspecs(globs, exclude)).out)
