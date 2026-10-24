# Step: research one page

Gather the facts that the writer needs to answer the page's question. Do not write the page.

## Inputs

- `page`: the catalogue entry of the page (`id`, `path`, `title`, `audience`, `brief`, `sources`, `related`, `source_commit`), plus `state` and `reason` from `plan`.
- `note_path`: the file to write your research notes to, for example `.agentic-doc/work/<page-id>/research.md`.

## Procedure

1. Expand the source globs into the real files:
   - `sources` uses git pathspec glob rules: `*` does not match `/`, and `**` does.
   - Pass each glob as a pathspec, for example `git ls-files -- ':(glob)src/**/*.py'`.
   - Read only tracked files.
2. Read those files. Answer `page.brief` from what the code actually does. You may read other files when the sources call into them.
3. Use only facts that you confirmed in the code. Do not reason from file names or naming conventions, and do not add general knowledge about "how this is usually done".
4. If `context` (from `config show`) or a document in the repository describes this subject, do not take it as true:
   - Compare it with the code.
   - If they disagree, add an item to `open_questions`, such as "The document says X, but the code does Y".
5. Design documents may explain why something exists. Confirm any behaviour they describe in the code before you add it to `key_claims`. If you cannot confirm it, add it to `open_questions`.
6. Write the notes to `note_path`. Create the directory if needed. The writer must be able to write the page from the notes without reading the sources again. Include:
   - The signatures of the main functions and classes.
   - The data flow.
   - The branch conditions.
   - The values of the constants.
   - The relationships that are worth a diagram.


You may write only `note_path`. The result you return is saved by the caller (`cache save research`), which checks it against the schema. After an interruption, the next sync reuses the notes and that result instead of researching again.

## Output

Return `<SKILL_DIR>/schemas/research.schema.json`:

| Field | Content |
| --- | --- |
| `page_id` | `page.id` |
| `note_path` | The `note_path` input |
| `key_claims` | 8 to 20 claims that form the backbone of the page. Each claim has at least one `evidence` entry in the form `path:line` or `path:start-end`. |
| `diagrams` | The diagrams to draw. `kind` is one of `graph`, `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`, `classDiagram`. `subject` is what the diagram shows. |
| `terms` | Terms that the page must introduce. |
| `open_questions` | Points you could not confirm, and disagreements between the documents and the code. |
