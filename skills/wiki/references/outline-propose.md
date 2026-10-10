# Step: propose a wiki structure from one angle

You are a documentation architect. From the survey results, propose one structure for the wiki: chapters, pages, and the sources of each page.

## Inputs

- `angle`: the axis to organise chapters by. It is one of:

  | Angle | Chapters follow | Benefit |
  | --- | --- | --- |
  | `layer` | The architectural layers or module boundaries | Someone changing the code reaches the right page fastest |
  | `flow` | The flow of data or control, from input to output | A newcomer can follow one request, file or event from start to end |
  | `audience` | The reader groups in `audiences` | Each reader can read only their own chapter |

- `surveys`: the survey results (`<SKILL_DIR>/schemas/survey.schema.json`, one per area).

## Constraints

- At most `max_pages` pages (from `config show`), at most 6 chapters, and at most 8 pages per chapter.
- The `audience` values must be `audiences[].id` values from `config show`. Design pages whose readers are all `no_code` so that they do not need code, identifiers or file paths.
- Do not create end-user manuals. The README covers those.
- `id` is `<chapter>/<page>`, a stable identifier made of lowercase words and hyphens. The chapter part must be one of the chapter IDs.
- `path` is exactly `<id>.md`. Never add number prefixes such as `01-` to file or directory names. With numbers, inserting a page renames every later file and breaks every link to them. The order of the `pages` array is the reading order.
- `sources` are the globs that the page depends on, and they define staleness detection:
  - They use git pathspec glob rules: `*` does not cross `/`, and `**` does.
  - Too wide, and unrelated changes force rewrites. Too narrow, and stale pages go unnoticed.
  - Each glob must match at least one tracked file. Check with `git ls-files -- ':(glob)<glob>'`.
- `brief` is the question that the page must answer, in 1 to 3 sentences. The writer receives it as the instruction.
- `related` lists the IDs of the pages to link to.

Do not write any file.

## Output

Return `<SKILL_DIR>/schemas/proposal.schema.json`. In `rationale`, explain why you chose this split, and which pages you deliberately left out.
