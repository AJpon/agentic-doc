"""lint のテスト用: 規約どおりの正常なページと、1 か所だけ壊す変形関数."""

import re

FENCE = "```"


def clean_page(title: str, other_title: str, other_file: str, heading: str = "## Related pages") -> str:
    return f'''---
title: "{title}"
description: "A page that explains how things fit together."
audience: [contributor]
updated: 2026-10-09
---

# {title}

Why it exists. `src/a.py:1-2` `src/b.py:1` `src/c.py:1` `src/d.py:1` `src/e.py:1` `src/f.py:1`

{FENCE}mermaid
flowchart LR
  A --> B
{FENCE}

{FENCE}mermaid
sequenceDiagram
  A->>B: hi
{FENCE}

{heading}

- [{other_title}]({other_file})
'''


PAGE = "docs/wiki/g/page.md"


def _edit(repo, fn) -> None:
    p = repo.root / PAGE
    p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")


def drop_frontmatter_key(key: str):
    return lambda repo: _edit(repo, lambda t: re.sub(rf"^{key}:.*\n", "", t, count=1, flags=re.MULTILINE))


def set_mermaid_blocks(n: int):
    def fn(t: str) -> str:
        t = re.sub(rf"{FENCE}mermaid\n.*?{FENCE}\n\n", "", t, flags=re.DOTALL)
        blocks = "".join(f"{FENCE}mermaid\nflowchart LR\n  A{i} --> B{i}\n{FENCE}\n\n" for i in range(n))
        return t.replace("## Related pages", blocks + "## Related pages")
    return lambda repo: _edit(repo, fn)


def add_to_mermaid(line: str):
    return lambda repo: _edit(repo, lambda t: t.replace("  A --> B\n", f"  A --> B\n  {line}\n", 1))


def remove_related_section(repo) -> None:
    _edit(repo, lambda t: t[: t.index("## Related pages")])


def append(text: str):
    return lambda repo: _edit(repo, lambda t: t + "\n" + text + "\n")
