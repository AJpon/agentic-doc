# Step: fix the findings on one page

The verifiers reported problems on one page. Fix the places that they name, and leave the rest of the page alone.

## Inputs

- `page`: the catalogue entry of the page.
- `findings`: the issues to fix (`blocker` and `major`). Each issue has `severity`, `location`, `problem` and `fix`, and may have `lens`.
- `round`: `1` or `2`.
- `note_path` (optional): the research notes. If it is missing, this run resumed from findings saved in an earlier run. Read the sources again when you need facts.

## Procedure

1. Read `<SKILL_DIR>/references/writing-rules.md`. The fixed page must still follow it.
2. Check each finding against the sources yourself:
   - If the finding is right, fix it on the page.
   - If the finding is wrong, leave the text as it is, and add the finding with your reason to `disputed`.
3. If a finding is about a Mermaid diagram, change the diagram itself: add, remove or rename nodes and arrows as needed. Readers trust the diagram over the text. Do not adjust the text alone to hide the disagreement.
4. Fix every finding in this round. Do not leave any for later.
5. In round 2, the same findings were not resolved in round 1. Repeating the round-1 change will not work. Do exactly what each `fix` asks, and read the sources again if you lack information.

You may write only `<wiki_dir>/<page.path>`.

## Output

Return `<SKILL_DIR>/schemas/fix.schema.json`:

| Field | Content |
| --- | --- |
| `changed` | One short entry for each place that you changed |
| `disputed` | One entry for each finding that you rejected, with the reason |
