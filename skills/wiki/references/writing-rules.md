# Writing rules

These rules apply to every wiki page. `lint` checks most of them, and they cannot be changed in the configuration. Strings that depend on the language come from `strings` in the output of `config show`.

## Front matter

Start every page with YAML front matter that has exactly these four keys:

```yaml
---
title: "The page title from the catalogue, unchanged"
description: "One sentence for the reader about this page. Do not copy the brief."
audience: [contributor, agent]
updated: 2026-10-09
---
```

- Always put `title` and `description` in double quotes. Without the quotes, YAML can break in two ways:
  - A colon followed by a space in the value (`Overview: ...`), or a value that starts with `[`, `-`, `>` or `*`, makes parsing fail.
  - A value that starts with `#`, or that contains a space followed by `#`, still parses, but the value silently becomes null or is cut off. No check catches this, so always quote.
- Inside a quoted value, escape a double quote with a backslash.
- `audience` lists the catalogue values in one pair of square brackets. `[[contributor]]` is wrong.
- `updated` is the `today` value from your inputs, without quotes. Do not run `date`.
- Do not add other keys. Do not put `sources` in the front matter: the catalogue owns staleness detection, and a second copy would drift.

## Structure

- Start with why the subject exists, then describe what it does.
- Put structured information in tables, not in prose.
- End the page with a section whose heading is exactly `strings.related_heading` (for example `## Related pages`). Under it, link to every page in the catalogue entry's `related` with a relative link, such as `[Title](../chapter/page.md)`. Every page needs this section, including no-code pages.

## Citations

- Cite code in backquotes with the local form `path/to/file.py:42`. For a range, write `path/to/file.py:42-58`. Use the full path from the repository root.
- Never cite with a GitHub blob URL. Line links in URLs go stale.
- Cite at least 5 different files on each page.
- Every citation must support the sentence that it is attached to.

## Diagrams

- Draw 2 to 4 Mermaid diagrams on each page, and do not repeat a diagram type on the same page. Choose by subject:
  - Structure: `graph` or `flowchart`.
  - Behaviour: `sequenceDiagram` or `stateDiagram-v2`.
  - Data: `erDiagram` or `classDiagram`.
- Do not use `style`, `classDef`, `fill:` or `stroke:`. Readers use both light and dark themes, so a fixed colour is unreadable in one of them.
- Do not use `<br/>`. Use `<br>` or a line break.

## No-code pages

A page is a no-code page when every audience in its `audience` list has `no_code: true` in the configuration. On a no-code page:

- Do not write citations, file paths, code, function names or type names.
- Explain what the product can and cannot do, and where the risks are, in plain language.
- Relative links to other wiki pages are allowed. The related-pages section is required.

## Facts only

- Do not guess. Read the code first, even when a guess seems obvious.
- If you cannot confirm a point, mark it in the text with `strings.unverified_marker`, with `{what}` replaced by what is unconfirmed. For example: `(unverified: how retries are scheduled)`.
