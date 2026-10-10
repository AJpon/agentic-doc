# Step: merge the proposals and install the catalogue

You are a documentation architect. Several structures were proposed independently from the same surveys. Evaluate them, write the final catalogue, and install it.

## Inputs

- `surveys`: the survey results.
- `proposals`: the proposals (`<SKILL_DIR>/schemas/proposal.schema.json`), one per angle.
- `force`: `true` if the user allowed replacing an existing catalogue.

## Procedure

1. Evaluate each proposal on three points:
   - Can a first-time reader reach the page they need?
   - Is it easy to tell which pages are stale after a change?
   - Are the chapters similar in size?
2. Pick the best proposal as the base. Add the good pages and good `sources` splits that only the other proposals have. Merge duplicate pages, and add pages for anything that every proposal missed.
3. Make sure that the result follows the constraints in `<SKILL_DIR>/references/outline-propose.md`. Fix any violations in the base proposal.
4. Write the catalogue to `.agentic-doc/work/outline/catalogue.json`:
   - Format: JSON with 2-space indentation and a final newline.
   - Shape:
     ```json
     {
       "version": 1,
       "title": "Optional title for the table of contents",
       "chapters": [{ "id": "...", "title": "...", "description": "..." }],
       "pages": [
         {
           "id": "chapter/page", "path": "chapter/page.md", "title": "...",
           "audience": ["..."], "brief": "...", "sources": ["..."], "related": ["..."],
           "source_commit": null, "reviewed_at": null
         }
       ]
     }
     ```
   - Order the `pages` array in reading order, grouped by chapter.
5. Check the file, and fix every `error` until the check exits with 0. Try at most 3 times:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" catalogue check .agentic-doc/work/outline/catalogue.json
   ```

6. Install the file. Add `--force` only if `force` is `true`:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" catalogue install .agentic-doc/work/outline/catalogue.json
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" catalogue install .agentic-doc/work/outline/catalogue.json --force
   ```

   If the install exits with 2 (a catalogue already exists) or 1 (the check failed), stop. Report the message in `issues`.
7. After a successful install, generate the table of contents:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" toc
   ```

You may write `.agentic-doc/work/outline/catalogue.json`. You may change other files only through `catalogue install` and `toc`.

## Output

Return `<SKILL_DIR>/schemas/outline-result.schema.json`:

| Field | Content |
| --- | --- |
| `installed` | `true` only if `catalogue install` exited with 0 |
| `catalogue` | The path that `catalogue install` printed, or the work file if the install did not happen |
| `page_count` | The number of pages in the final catalogue |
| `rationale` | Why you chose this structure |
| `issues` | The remaining check errors, or the refusal message. Empty on success. |
