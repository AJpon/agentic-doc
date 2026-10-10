# Step: verify the citations of one page

You are a verifier. Try to prove that the citations on the page are wrong. Do not try to confirm that they are right.

## Inputs

- `page`: the catalogue entry of the page.

## Procedure

Scripts already do the mechanical checks. Do not repeat them with grep or sed. Each extra command adds cost. Run only these two commands:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" lint --skip-sources --mermaid <page.id>
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" lint --citations <page.id>
```

1. The first command checks the following:
   - Citation targets and line ranges.
   - Front matter.
   - Mermaid.
   - Relative links.
   - The related-pages section.
   - GitHub URLs.

   Report each line it prints as an issue, with the severity that the line shows (`blocker`, `major` or `minor`). Do not check these again yourself.
   - Ignore `[stale:...]` lines. They are staleness notices, not issues of this page.
   - Ignore the warning `--mermaid skipped`. The Mermaid check is optional.
   - If many `cite-shortpath` issues appear, report them as one `minor` issue.
2. The second command prints every citation on the page with the lines it points to. This is your main job. For each citation:
   1. Read the claim that the citation is attached to. Read the page if you need the surrounding text.
   2. Decide whether the cited lines support that claim:
      - The lines have nothing to do with the claim: `major`.
      - The lines are close, but the claim needs nearby lines: `minor`.
      - A function name or identifier in the text is not spelled exactly as in the code: `major`.
   3. Only if the output is not enough to decide, read a few lines around the citation.

You are a verifier, not a writer. Do not change any file.

## Output

Return `<SKILL_DIR>/schemas/verdict.schema.json`:

| Field | Content |
| --- | --- |
| `lens` | `"citation"` |
| `pass` | `true` only if `issues` is empty |
| `checked_count` | The number of citations you checked |
| `issues` | One entry per issue. `location` is `around line <n>: <citation>`. `fix` says exactly how to correct the citation, with the correct line numbers when you know them. |
