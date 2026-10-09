# Step: check whether a changed page still matches the code

You are an auditor. The sources of this page changed after the page was last verified. Decide whether those changes make the text wrong. Read only. Do not change any file.

## Inputs

- `page`: an entry from `plan` with `state: "changed"`. It has `id`, `path`, `sources`, `source_commit`, and `reason` (the files that changed).

## Procedure

`lint` already checks the mechanical points: citation targets, line ranges, front matter, Mermaid and links. Do not check them again.

1. See how big the change is, then read the diff. If the diff is very large, read the parts that matter to the page:

   ```bash
   git diff --stat <source_commit>..HEAD -- ':(glob)<source 1>' ':(glob)<source 2>' ...
   git diff <source_commit>..HEAD -- ':(glob)<source 1>' ':(glob)<source 2>' ...
   ```

   Write each glob in `sources` as its own `:(glob)` pathspec.
2. Read the page at `<wiki_dir>/<page.path>`. Decide whether the change affects what the page says: described behaviour, values, tables or diagrams.
3. For each citation `path:line` that points into a changed file, check that the cited lines still support the claim.

Severity:

| Situation | Severity |
| --- | --- |
| The text now contradicts the code | `major` |
| A citation's lines have shifted, or the wording is outdated but still true | `minor` |
| The change does not affect the text | Report no issue |

## Output

Return `<SKILL_DIR>/schemas/drift.schema.json`:
- `page_id` is `page.id`.
- `issues` is empty when the change does not affect the page.
- The `fix` of each issue says what to change and how.
