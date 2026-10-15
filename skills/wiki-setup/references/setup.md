# Setting up `.agentic-doc.config.json`

Write only `.agentic-doc.config.json`, except for the catalogue move in the update procedure, and only after the user agrees to it. Do not commit.

## The keys

| Key | Default | Meaning |
| --- | --- | --- |
| `version` | (required) | Always `1` |
| `wiki_dir` | `docs/wiki` | Where the wiki is written |
| `catalogue` | `<wiki_dir>/catalogue.json` | The catalogue path |
| `language` | `en` | The language of the wiki prose (a BCP 47 tag such as `en`, `ja` or `de`) |
| `audiences` | `contributor` and `agent` | The reader groups `{id, title, description, no_code}`. `no_code: true` means pages for only that group show no code. |
| `exclude` | `[]` | Globs to remove from the target files (git pathspec glob rules: `*` does not cross `/`, `**` does) |
| `context` | README.md, AGENTS.md and CLAUDE.md, if they exist | `[{"file": ...}]` or `[{"text": ...}]`. Premises that writers verify against the code. |
| `instructions` | `[]` | Same shape as `context`. Rules that writers must follow. |
| `post_commands` | `[]` | Commands run on the generated files. `{files}` must be an argument of its own, and it expands to one argument per file. Use `/` in paths, also on Windows. |
| `max_pages` | `24` | The largest number of pages in the catalogue |

Write only the keys whose value differs from the default, and always write `version`. Start the file with:

```json
{
  "$schema": "https://raw.githubusercontent.com/AJpon/agentic-doc/main/skills/wiki/schemas/config.schema.json",
  "version": 1
}
```

## First time (no configuration file)

1. Read the following:
   - README, AGENTS.md, CLAUDE.md and CONTRIBUTING.
   - The build and package files.
   - `.gitignore`.
   - The formatter and hook configuration.
   - The CI configuration.
   - The top-level directories (`git ls-files` shows only tracked files).
2. Infer a value for each key, and note the file that supports it:

   | Key | How to infer it |
   | --- | --- |
   | `language` | The language of the README and docs, and of the last commit messages (`git log -n 50 --format=%s`) |
   | `post_commands` | `.pre-commit-config.yaml`: `pre-commit run --files {files}`, or `uv run pre-commit run --files {files}` in a uv project. Prettier or markdownlint configuration: that tool's CLI with `{files}`. |
   | `exclude` | Vendored code (`vendor/`, `third_party/`), generated code, large fixtures, and anything that the wiki must not depend on |
   | `audiences` | The default two groups. If the project needs explanations for non-programmers (product, management), suggest a third group with `no_code: true`. |
   | `context` | The default, unless the main overview document has another name |

3. Show the draft to the user, with the supporting file for each inferred value. Ask only about the keys you could not infer, or that need a judgement (usually `audiences`, `exclude` and `post_commands`).
   - Do not infer `instructions`. Ask whether the user has rules for the writers, for example "Do not cite docs/history/ as current behaviour".
   - If the harness has a question tool, use it. Otherwise ask in a short list, and wait for the answer.
4. Write `.agentic-doc.config.json` (JSON with 2-space indentation and a final newline).
5. Check it. If errors are reported, fix them and check again. Show any warnings to the user.

   ```bash
   uv run --script "<SKILL_DIR>/../wiki/scripts/agentic_doc.py" config check
   ```

6. Tell the user that the next step is `/agentic-doc:wiki outline`.

## Update (the configuration file exists)

1. Do steps 1 and 2 of the first-time procedure again. Compare the result with the current file, and propose only the differences, each with its reason. Examples:
   - A new generated directory is missing from `exclude`.
   - A `file` in `context` no longer exists.
   - The formatter changed.
2. Change only the keys that the user approves. Then run `config check` as in step 5 of the first-time procedure.
3. If `exclude` changed, show which pages are affected:

   ```bash
   uv run --script "<SKILL_DIR>/../wiki/scripts/agentic_doc.py" lint --json
   ```

   Pages with `source-glob-empty` (a sources glob now matches nothing) or `cite-excluded` (a citation points into an excluded file) need attention. Suggest `sync --pages <ids>`, or `outline --force` if many pages are affected.
4. If no file exists at the `catalogue` path, look for one at the default path or at the old name `<wiki_dir>/_catalogue.json`.
   - A file in the current format (it has `chapters`): offer the user two choices, move the file or point `catalogue` at it. Do what the user chooses.
   - A file in the old format (no `chapters`, for example the `_catalogue.json` of the original wiki workflow): offer to convert it. On approval, run the command below. It writes the catalogue to the `catalogue` path, keeps every `source_commit`, and removes the old file. If it exits with 1, show the issues and stop.

     ```bash
     uv run --script "<SKILL_DIR>/../wiki/scripts/agentic_doc.py" catalogue migrate "<path of the old file>"
     ```

     The converted chapters use their IDs as titles and have empty descriptions. Propose a `title` and a `description` for each chapter, taken from the chapter headings of the existing `<wiki_dir>/README.md` where possible, and write them into the catalogue after the user approves. Then run `catalogue check`, and `toc` to regenerate the table of contents.
