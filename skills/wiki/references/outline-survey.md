# Step: survey one area

Investigate one area of the repository and report only what you confirmed by reading files.

## Inputs

- `area`: `{key, title, scope, questions}` from the area split.

## Procedure

1. Expand `area.scope` with `git ls-files` and read the files. Answer each question in `area.questions` from what the code and configuration actually do.
2. Also look for the following:
   - Which parts of the code deserve a page of their own, and which parts can be covered together.
   - Large or complex files that could be split into several topics.
   - Empty placeholders and dead code that a reader might trip over.
3. For documentation in the area:
   - Record who each document is written for.
   - Compare its statements with the current code. Report each disagreement as a finding, with evidence. Writers must not copy these statements into the wiki.
   - Extract the design intent, trade-offs and rejected options that the code alone does not show. Writers use them to explain why something exists.
4. Add behaviour that matters but has no documentation to `doc_gaps`.

Do not write any file.

## Output

Return `<SKILL_DIR>/schemas/survey.schema.json`:

| Field | Content |
| --- | --- |
| `area` | `area.key` |
| `summary` | A short summary of the area |
| `findings` | One entry per finding. `topic` is the subject, `detail` is what you found by reading, and `evidence` has at least one `path:line`. |
| `doc_gaps` | Important behaviour that has no documentation |
