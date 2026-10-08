"""checkpoint と stamp が共有する、打ち込み先コミットの検証."""

from adoc import gitutil
from adoc.config import Config
from adoc.errors import Refused


def target_commit(cfg: Config, rev: str) -> str:
    """rev を解決し、HEAD の祖先であることを確かめる."""
    sha = gitutil.resolve_commit(cfg.root, rev)
    if sha is None:
        raise Refused(f"--sha {rev} does not resolve to a commit")
    if not gitutil.is_ancestor(cfg.root, sha, gitutil.head(cfg.root)):
        raise Refused(f"{sha[:12]} is not an ancestor of HEAD")
    return sha
