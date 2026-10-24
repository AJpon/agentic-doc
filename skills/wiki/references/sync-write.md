# Step: write one page

Write one wiki page from the research results.

## Inputs

- `page`: the catalogue entry of the page, plus `state` and `reason`.
- `research_path`: the file that holds the research result (`<SKILL_DIR>/schemas/research.schema.json`), for example `.agentic-doc/work/<page-id>/research.json`. Read it first.
- `note_path`: the research notes.
- `today`: the date for `updated` (`YYYY-MM-DD`).

## Procedure

1. Read `<SKILL_DIR>/references/writing-rules.md`. Follow every rule in it.
2. Read the research result at `research_path`, then the research notes at `note_path`.
3. If you want to make a claim that the notes do not contain, read the source and confirm it before you write it.
4. Write the page to `<wiki_dir>/<page.path>`. Create directories if needed. If the file exists, rewrite it completely.
   - The H1 is `page.title`.
   - The page answers `page.brief` for the readers in `page.audience`.
   - Draw the diagrams in the research result's `diagrams` where they help, staying within the 2 to 4 diagram limit.
   - Do not state the items in the research result's `open_questions` as fact. Where the page needs them, mark them with `strings.unverified_marker`.
5. Links to related pages:
   1. Read the catalogue file (`catalogue` from `config show`).
   2. For each ID in `page.related`, find its `path`.
   3. Link with a path relative to this page's file. For example, from `a/one.md` to `b/two.md` the link is `../b/two.md`.
6. If this is a no-code page (see `writing-rules.md`), follow the no-code rules, and do not show code even if the research notes contain it.

You may write only `<wiki_dir>/<page.path>`.

## Output

Return `<SKILL_DIR>/schemas/write.schema.json`:

| Field | Content |
| --- | --- |
| `page_id` | `page.id` |
| `path` | The file you wrote, relative to the repository root |
| `written` | `true` only if you actually wrote the file |
| `headings` | The H2 headings |
| `cited_files` | The files that you cited |
| `diagram_count` | The number of Mermaid diagrams |
| `notes` | Optional remarks |
