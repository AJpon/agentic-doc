"""lint: Wiki の機械検査（仕様書 7.5 の 1）。LLM を使わず、ファイルを書き換えない."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from adoc import catalogue, config, gitutil, state
from adoc.cli import Command
from adoc.config import Config
from adoc.i18n import t
from adoc.state import State

MERMAID_CHECK = Path(__file__).resolve().parent / "mermaid_check.mjs"
# 引用: `path:12`、`path:12-30`、`path:12,40-50`、直前の完全な引用に続く省略形 `:1035`。
_RANGE = r"\d+(?:-\d+)?"
_PATH = r"[^`:\n]*\.[\w\-]+"
CITE = re.compile(r"`(?P<path>" + _PATH + r")?:(?P<spec>" + _RANGE + r"(?:,\s*" + _RANGE + r")*)`")
CODE_SPAN = re.compile(r"`[^`\n]*`")
PATH_ONLY = re.compile(_PATH)
GITHUB_BLOB = re.compile(r"https?://github\.com/[^\s)]*/blob/")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
MERMAID_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
FORBIDDEN_MERMAID = re.compile(r"^\s*(style|classDef)\b|fill:|stroke:|<br/>", re.MULTILINE)
FRONTMATTER = re.compile(r"---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
FM_KEYS = ["audience", "description", "title", "updated"]


def parse_spec(spec: str) -> list[tuple[int, int]]:
    """`12,40-50` を [(12, 12), (40, 50)] にする."""
    ranges = []
    for part in spec.split(","):
        a, _, b = part.strip().partition("-")
        ranges.append((int(a), int(b or a)))
    return ranges


def extract_citations(body: str, tracked: set[str]) -> list[dict]:
    """本文から引用を抜き出す。省略形 `:NNN` は同じ行の直前のファイルを引き継ぐ.

    「直前のファイル」は、同じ行で最も近い完全な引用のパス、または追跡済みファイルを指す
    行番号なしの `path` 表記。戻り値の各要素は ref（省略形で先行が無ければ None）、spec、
    ranges、shorthand を持つ。
    """
    cites = []
    for line in body.split("\n"):
        last = None
        for span in CODE_SPAN.findall(line):
            m = CITE.fullmatch(span)
            if m is None:
                inner = span.strip("`")
                if PATH_ONLY.fullmatch(inner) and inner in tracked:
                    last = inner
                continue
            ref = m.group("path")
            shorthand = ref is None
            if shorthand:
                ref = last
            else:
                last = ref
            cites.append({"ref": ref, "spec": m.group("spec"), "ranges": parse_spec(m.group("spec")),
                          "shorthand": shorthand})
    return cites


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """(フロントマター, 本体)。先頭の BOM は除く。フロントマターが無ければ (None, text)."""
    text = text.removeprefix("\ufeff")
    m = FRONTMATTER.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


_FENCE = re.compile(r"^[ \t]*(```|~~~)")


def find_heading(body: str, heading: str) -> tuple[int, int] | None:
    """コードフェンスの外で heading と一致する行の (開始, 終了) を返す。節の終わりは次の `## ` の手前か末尾."""
    pos, fence, start = 0, None, None
    for line in body.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        m = _FENCE.match(stripped)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
        elif fence is None:
            if start is None and stripped.rstrip(" \t") == heading:
                start = pos
            elif start is not None and stripped.startswith("## "):
                return start, pos
        pos += len(line)
    return (start, len(body)) if start is not None else None


def resolve(ref: str, tracked: set[str]) -> tuple[str | None, bool]:
    """引用パスを追跡済みファイルへ解決する。短縮名は一意に決まるときだけ許す. (path, 短縮名か)"""
    if ref in tracked:
        return ref, False
    if "/" in ref:
        return None, False
    hits = [f for f in tracked if f.rsplit("/", 1)[-1] == ref]
    return (hits[0], True) if len(hits) == 1 else (None, False)


def _lines(cfg: Config, rel: str) -> list[str]:
    """改行（LF）だけで区切った行。\f などでは区切らない."""
    text = (cfg.root / rel).read_bytes().decode("utf-8", errors="replace")
    lines = [ln.removesuffix("\r") for ln in text.split("\n")]
    return lines[:-1] if lines and lines[-1] == "" else lines


def is_no_code(cfg: Config, page: dict) -> bool:
    """no_code の読者層だけを持つページか."""
    no_code = {a["id"] for a in cfg.audiences if a["no_code"]}
    return bool(page["audience"]) and set(page["audience"]) <= no_code


class _Ctx:
    """1 回の lint 実行で共有する、追跡済み・対象ファイルの集合."""

    def __init__(self, cfg: Config):
        self.tracked = set(gitutil.ls_files(cfg.root, [], []))
        self.included = set(gitutil.ls_files(cfg.root, [], cfg.exclude))


def _check_frontmatter(raw: str | None, page: dict, add) -> None:
    if raw is None:
        add("major", "frontmatter", "no front matter, or it is not closed")
        return
    try:
        fm = yaml.safe_load(raw) or {}
    except yaml.YAMLError as e:
        add("major", "frontmatter", f"cannot parse: {e}")
        return
    if not isinstance(fm, dict):
        add("major", "frontmatter", f"not a mapping: {type(fm).__name__}")
        return
    if sorted(fm) != FM_KEYS:
        add("major", "frontmatter", f"keys must be exactly {FM_KEYS}: {sorted(fm)}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fm.get("updated", ""))):
        add("major", "frontmatter", f"updated is not YYYY-MM-DD: {fm.get('updated')!r}")
    desc = fm.get("description")
    if not isinstance(desc, str) or len(desc) < 10:
        add("major", "frontmatter", f"description is empty or too short: {desc!r}")
    if fm.get("title") != page["title"]:
        add("major", "frontmatter", "title does not match the catalogue")
    audience = fm.get("audience")
    if not isinstance(audience, list) or sorted(map(str, audience)) != sorted(page["audience"]):
        add("major", "frontmatter", "audience does not match the catalogue")


def _check_sources(cfg: Config, page: dict, add) -> None:
    sources = page["sources"]
    for glob in sources:
        if not gitutil.ls_files(cfg.root, [glob], cfg.exclude):
            add("major", "source-glob-empty", f"sources glob matches no target file: {glob} "
                "(* does not cross /; use ** for deeper paths)")
    if not sources:
        return
    dirty = gitutil.dirty(cfg.root, sources, cfg.exclude)
    if dirty:
        add("major", "source-uncommitted", "uncommitted changes in sources; commit first: " + ", ".join(dirty[:5]))
    new = gitutil.untracked(cfg.root, sources, cfg.exclude)
    if new:
        add("major", "source-untracked", "untracked files match sources; commit or ignore them: "
            + ", ".join(new[:5]))


def _check_citations(cfg: Config, ctx: _Ctx, body: str, add) -> set[str]:
    cited = set()
    for c in extract_citations(body, ctx.tracked):
        ref, spec = c["ref"], c["spec"]
        if ref is None:
            add("minor", "cite-shorthand", f":{spec} — shorthand without a preceding full path on the line")
            continue
        label = f"{ref}:{spec}"
        real, short = resolve(ref, ctx.tracked)
        if real is None:
            add("blocker", "cite-missing", f"{label} — not a tracked file, or the short name is ambiguous")
            continue
        if not (cfg.root / real).is_file():
            add("blocker", "cite-missing", f"{label} — the file is deleted in the working tree")
            continue
        if short:
            add("minor", "cite-shortpath", f"{label} — write the full path {real}")
        if real not in ctx.included:
            add("major", "cite-excluded", f"{label} — the file is excluded by the config")
        cited.add(real)
        n = len(_lines(cfg, real))
        for a, b in c["ranges"]:
            if n == 0 and a == 1 and b == 1:
                continue  # 0 行のファイルの存在を示す :1 は許す
            if a < 1 or a > b:
                add("blocker", "cite-overflow", f"{real}:{a}-{b} — invalid line numbers")
            elif b > n:
                add("blocker", "cite-overflow", f"{real}:{a}-{b} — the file has {n} lines")
    return cited


def lint_page(cfg: Config, page: dict, all_pages: list[dict], tracked: set[str] | None = None,
              check_sources: bool = True, ctx: _Ctx | None = None) -> list[dict]:
    """1 ページ分の機械検査。問題は {page, severity, code, detail}."""
    ctx = ctx or _Ctx(cfg)
    if tracked is not None:
        ctx.tracked = tracked
    issues: list[dict] = []

    def add(severity: str, code: str, detail: str) -> None:
        issues.append({"page": page["id"], "severity": severity, "code": code, "detail": detail})

    path = catalogue.page_file(cfg, page)
    if not path.is_file():
        add("blocker", "missing-page", path.relative_to(cfg.root).as_posix())
        return issues
    raw, body = split_frontmatter(path.read_text(encoding="utf-8"))
    _check_frontmatter(raw, page, add)

    diagrams = MERMAID_BLOCK.findall(body)
    if not 2 <= len(diagrams) <= 4:
        add("minor", "mermaid-count", f"{len(diagrams)} Mermaid diagrams (2-4 expected)")
    if any(FORBIDDEN_MERMAID.search(d) for d in diagrams):
        add("major", "mermaid-style", "uses style/classDef/fill:/stroke:/<br/>")
    heading = t(cfg.language, "related_heading")
    if page["related"] and find_heading(body, heading) is None:
        add("major", "related", f"related is set but the page has no `{heading}` section")
    if GITHUB_BLOB.search(body):
        add("major", "github-url", "cites with a GitHub blob URL")

    if check_sources:
        _check_sources(cfg, page, add)
    cited = _check_citations(cfg, ctx, body, add)
    if is_no_code(cfg, page):
        if cited:
            add("major", "no-code-leak", f"a no_code page cites {len(cited)} files")
    elif len(cited) < 5:
        add("minor", "cite-variety", f"cites {len(cited)} files (5 or more expected)")

    planned = {catalogue.page_file(cfg, q).resolve() for q in all_pages}
    for target in LINK.findall(body):
        if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
            continue
        dest = (path.parent / target.split("#")[0]).resolve()
        if not dest.exists() and dest not in planned:
            add("blocker", "link-broken", f"relative link target does not exist: {target}")
    return issues


def mermaid_issues(cfg: Config, pages: list[dict]) -> list[dict] | None:
    """mermaid_check.mjs で構文検査する。使えなければ警告を 1 行出して None."""
    node = shutil.which("node")
    modules = cfg.wiki_dir / "node_modules"
    if node is None:
        reason = "node not found on PATH"
    elif not (modules / "mermaid").is_dir() or not (modules / "jsdom").is_dir():
        reason = f"mermaid/jsdom not installed in {modules.relative_to(cfg.root).as_posix()}"
    else:
        reason = None
    if reason:
        print(f"warning: --mermaid skipped ({reason})", file=sys.stderr)
        return None
    by_file = {str(catalogue.page_file(cfg, p).resolve()): p["id"] for p in pages
               if catalogue.page_file(cfg, p).is_file()}
    if not by_file:
        return []
    r = subprocess.run([node, str(MERMAID_CHECK), str(cfg.wiki_dir), *by_file], capture_output=True, text=True,
                       encoding="utf-8", check=False)
    if r.returncode != 0:
        first = (r.stderr.strip().splitlines() or ["unknown error"])[0]
        print(f"warning: --mermaid skipped (mermaid_check.mjs failed: {first})", file=sys.stderr)
        return None
    return [{"page": by_file[e["file"]], "severity": "major", "code": "mermaid-syntax",
             "detail": f"Mermaid block {e['block_index']} (line {e['line']}) has a syntax error: {e['message']}"}
            for e in json.loads(r.stdout)]


def show_citations(cfg: Config, page: dict) -> None:
    """ページ内の全引用と、引用先の実際の行を表示する."""
    tracked = set(gitutil.ls_files(cfg.root, [], []))
    path = catalogue.page_file(cfg, page)
    if not path.is_file():
        print(f"--- page file not found: {page['path']}")
        return
    body = split_frontmatter(path.read_text(encoding="utf-8"))[1]
    for c in extract_citations(body, tracked):
        spec = c["spec"]
        if c["ref"] is None:
            print(f"--- :{spec} — shorthand without a preceding full path")
            continue
        real, _ = resolve(c["ref"], tracked)
        if real is None or not (cfg.root / real).is_file():
            print(f"--- {c['ref']}:{spec} — not a tracked file")
            continue
        lines = _lines(cfg, real)
        tag = " (shorthand)" if c["shorthand"] else ""
        print(f"--- {real}:{spec}{tag} ({len(lines)} lines)")
        for a, b in c["ranges"]:
            for i in range(max(a, 1), min(b, len(lines)) + 1):
                print(f"{i:>5}| {lines[i - 1]}")


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("ids", nargs="*", metavar="ID", help="page ids (default: all)")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--skip-sources", action="store_true", help="skip checks on the sources globs")
    p.add_argument("--mermaid", action="store_true", help="parse Mermaid blocks (needs node and mermaid/jsdom "
                   "in <wiki_dir>/node_modules)")
    p.add_argument("--citations", metavar="ID", help="print every citation of a page with the cited lines")


def run(args: argparse.Namespace) -> int:
    root = Path.cwd()
    gitutil.ensure_repo(root)
    cfg = config.load(root)
    data = catalogue.load(cfg)
    if args.citations:
        show_citations(cfg, catalogue.select(data, [args.citations])[0])
        return 0
    targets = catalogue.select(data, args.ids)
    ctx = _Ctx(cfg)
    issues = [i for p in targets for i in lint_page(cfg, p, data["pages"], check_sources=not args.skip_sources,
                                                    ctx=ctx)]
    if args.mermaid:
        issues += mermaid_issues(cfg, targets) or []
    stale = []
    for p in targets:
        st = state.classify(cfg, p)
        if st.state != State.FRESH:
            why = ", ".join(st.changed[:5]) if st.state == State.CHANGED else st.state.value
            stale.append({"page": p["id"], "reason": why, "kind": st.state.value})
    if args.json:
        print(json.dumps({"pages_checked": len(targets), "issue_count": len(issues), "stale_count": len(stale),
                          "issues": issues, "stale": stale}, indent=2, ensure_ascii=False))
    else:
        for i in issues:
            print(f"{i['page']}  [{i['severity']}] {i['code']}: {i['detail']}")
        for s in stale:
            print(f"{s['page']}  [stale:{s['kind']}] {s['reason']}")
        print(f"{len(issues)} issues / {len(stale)} stale pages")
    return 1 if issues else 0


COMMAND = Command(help="mechanical checks of wiki pages (citations, front matter, links, Mermaid)",
                  add_args=add_args, run=run)
