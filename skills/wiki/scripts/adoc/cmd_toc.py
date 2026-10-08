"""toc: 目次の生成、related の双方向化、各ページのフロントマターと関連ページ節の整形."""

import argparse
import os
import re
from pathlib import Path

import yaml

from adoc import catalogue, config
from adoc.cli import Command
from adoc.config import Config
from adoc.i18n import t
from adoc.lint import split_frontmatter


def add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--dry-run", action="store_true", help="list the files that would change without writing")


def first_sentence(text: str) -> str:
    """brief の最初の 1 文（。か '. ' までを含む）."""
    m = re.search(r"。|\.(\s|$)", text)
    return text[: m.start() + 1].strip() if m else text.strip()


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _link_suffix(cfg: Config, page: dict) -> str:
    return "" if catalogue.page_file(cfg, page).is_file() else " " + t(cfg.language, "toc_not_written")


def render_readme(cfg: Config, data: dict) -> str:
    lang = cfg.language
    lines = [f"# {data.get('title') or t(lang, 'toc_default_title')}", "", t(lang, "toc_audience_heading"), ""]
    for aud in cfg.audiences:
        pages = [p for p in data["pages"] if aud["id"] in p["audience"]]
        if not pages:
            continue
        lines += [f"### {aud['title']}", ""]
        lines += [f"{i}. [{p['title']}]({p['path']}){_link_suffix(cfg, p)}" for i, p in enumerate(pages, 1)]
        lines.append("")
    lines += [t(lang, "toc_contents_heading"), ""]
    for ch in data["chapters"]:
        pages = [p for p in data["pages"] if p["id"].split("/")[0] == ch["id"]]
        lines += [f"### {ch['title']}", ""]
        if ch["description"]:
            lines += [ch["description"], ""]
        lines += [f"| {t(lang, 'toc_col_page')} | {t(lang, 'toc_col_summary')} |", "|---|---|"]
        lines += [f"| [{_cell(p['title'])}]({p['path']}){_link_suffix(cfg, p)} | {_cell(first_sentence(p['brief']))} |"
                  for p in pages]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def make_related_symmetric(data: dict) -> bool:
    """A→B があって B→A が無ければ B の末尾に A を足す。変えたら True."""
    index = catalogue.page_index(data)
    changed = False
    for p in data["pages"]:
        for other in p["related"]:
            q = index.get(other)
            if q is not None and q["id"] != p["id"] and p["id"] not in q["related"]:
                q["related"].append(p["id"])
                changed = True
    return changed


def _quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_frontmatter(title: str, description: str, audience: list[str], updated: str | None) -> str:
    lines = [f"title: {_quote(title)}", f"description: {_quote(description)}",
             f"audience: [{', '.join(audience)}]"]
    if updated:
        lines.append(f"updated: {updated}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def sync_page(cfg: Config, page: dict, index: dict[str, dict], text: str) -> str:
    """フロントマターと関連ページ節をカタログに合わせた本文を返す."""
    raw, body = split_frontmatter(text)
    try:
        fm = yaml.safe_load(raw) if raw is not None else {}
    except yaml.YAMLError:
        fm = {}
    fm = fm if isinstance(fm, dict) else {}
    description = fm.get("description")
    if not isinstance(description, str) or not description:
        description = page["brief"]
    updated = page["reviewed_at"] or (str(fm["updated"]) if fm.get("updated") is not None else None)
    head = render_frontmatter(page["title"], description, page["audience"], updated)

    heading = t(cfg.language, "related_heading")
    here = catalogue.page_file(cfg, page).parent
    items = []
    for rid in page["related"]:
        q = index.get(rid)
        if q is None:
            continue
        rel = Path(os.path.relpath(catalogue.page_file(cfg, q), here)).as_posix()
        items.append(f"- [{q['title']}]({rel})")
    m = re.search(r"^" + re.escape(heading) + r"[ \t]*$", body, re.MULTILINE)
    if m:
        nxt = re.search(r"^## ", body[m.end():], re.MULTILINE)
        before = body[: m.start()]
        after = body[m.end() + nxt.start():] if nxt else ""
    elif items:
        before, after = body.rstrip("\n") + "\n\n", ""
    else:
        return head + body
    section = heading + "\n\n" + "\n".join(items) + "\n" if items else ""
    new_body = before + section + ("\n" + after if after else "")
    return head + new_body.rstrip("\n") + "\n"


def run(args: argparse.Namespace) -> int:
    cfg = config.load(Path.cwd())
    data = catalogue.load(cfg)
    changed: list[Path] = []
    writes: list[tuple[Path, str]] = []

    if make_related_symmetric(data):
        catalogue.ensure_canonical(cfg)
        changed.append(cfg.catalogue)
    readme = cfg.wiki_dir / "README.md"
    text = render_readme(cfg, data)
    if not readme.is_file() or readme.read_text(encoding="utf-8") != text:
        writes.append((readme, text))
    index = catalogue.page_index(data)
    for p in data["pages"]:
        path = catalogue.page_file(cfg, p)
        if not path.is_file():
            continue
        old = path.read_text(encoding="utf-8")
        new = sync_page(cfg, p, index, old)
        if new != old:
            writes.append((path, new))

    if not args.dry_run:
        if cfg.catalogue in changed:
            catalogue.save(cfg, data)
        for path, text in writes:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
    for path in changed + [w[0] for w in writes]:
        print(path.relative_to(cfg.root).as_posix())
    return 0


COMMAND = Command(help="rebuild the wiki README, make related links symmetric, sync page front matter",
                  add_args=add_args, run=run)
