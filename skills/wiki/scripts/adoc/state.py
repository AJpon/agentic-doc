"""ページ状態の判定（仕様書 7.4）."""

from dataclasses import dataclass, field
from enum import StrEnum

from adoc import catalogue, gitutil, workdir
from adoc.config import Config


class State(StrEnum):
    """判定順に並べたページ状態."""

    MISSING = "missing"
    UNVERIFIED = "unverified"
    UNRESOLVED = "unresolved"
    CHANGED = "changed"
    FRESH = "fresh"


@dataclass
class PageStatus:
    id: str
    state: State
    base: str | None
    reviewed_at: str | None
    changed: list[str] = field(default_factory=list)
    pending: int = 0


def classify(cfg: Config, page: dict) -> PageStatus:
    """ページの状態を missing → unverified → unresolved → changed → fresh の順に判定する."""
    path = catalogue.page_file(cfg, page)
    sha = page["source_commit"]
    st = PageStatus(page["id"], State.FRESH, sha, page["reviewed_at"])
    if not path.is_file():
        st.state = State.MISSING
        return st
    st.pending = workdir.pending_count(cfg, page["id"], path.read_text(encoding="utf-8"))
    if sha is None:
        st.state = State.UNVERIFIED
        return st
    changed = gitutil.changed_since(cfg.root, sha, page["sources"], cfg.exclude)
    if changed is None:
        st.state = State.UNRESOLVED
    elif changed:
        st.state = State.CHANGED
        st.changed = changed
    return st


def warnings(cfg: Config, pages: list[dict]) -> dict:
    """全ページの sources に対する未コミットの変更と未追跡ファイル."""
    globs = sorted({g for p in pages for g in p["sources"]})
    if not globs:
        return {"uncommitted": [], "untracked": []}
    return {
        "uncommitted": sorted(gitutil.dirty(cfg.root, globs, cfg.exclude)),
        "untracked": sorted(gitutil.untracked(cfg.root, globs, cfg.exclude)),
    }
