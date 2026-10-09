---
name: wiki
description: Use when generating, updating, auditing, or checking the status of a codebase Markdown wiki (setup, outline, sync, status, audit, stamp), or when asked what to do next with the wiki or how agentic-doc works.
---

# agentic-doc wiki

This skill generates a Markdown wiki from a codebase and keeps it in step with the code. The user runs it as `/agentic-doc:wiki <mode> [arguments]`. The modes are `help`, `setup`, `outline`, `sync`, `status`, `audit` and `stamp`.

## Paths

`<SKILL_DIR>` is the directory that contains this `SKILL.md`. In the commands below, replace it with that absolute path. Run every command from the repository root:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" status
```

Keep the double quotes around the script path. Exit codes: 0 means OK, 1 means findings were reported, 2 means the input was refused or the command failed. Read `<SKILL_DIR>/references/overview.md` for the modes, the flow and the page states.

## Checks before each mode

Skip these checks for `help` and `setup`.

1. Run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" config check`.
   - If it exits with 1 or 2, show its output, explain that the configuration must be fixed or created first, point to `setup`, and stop.
2. Run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" config show`.
   - Except in `outline`: if `catalogue_exists` is false, point to `outline` and stop.
   - In `outline`: if `catalogue_exists` is true and the user did not pass `--force`, stop. Explain that `outline` would replace the catalogue, and that every page would become unverified (`source_commit` is reset). Point to `outline --force` if the user really wants that.

## Modes

| Mode | What to do |
| --- | --- |
| No mode, `help`, or a question | 1. Run `config check`. If it passes and a catalogue exists, run `status`.<br>2. Read `<SKILL_DIR>/references/overview.md`.<br>3. Tell the user where the project is in the flow, and the next command to run, with its arguments.<br>4. For questions about the scripts, run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" --help`. |
| `setup` | Use the `wiki-setup` skill. If you cannot invoke skills, read `<SKILL_DIR>/../wiki-setup/SKILL.md` and follow it. |
| `status [<id>...] [--state <state>] [--verbose]` | Run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" status` with the user's arguments, and show its output. |
| `stamp [--sha <rev>] [--pages <id>...] [--dry-run]` | Run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" stamp` with the user's arguments, and show its output. Exit code 1 means some pages were skipped. Explain why, using the output. |
| `outline [--force]`, `sync [--pages <id>...] [--include-unresolved]`, `audit [--lint-only]` | See the next section. |

## Running outline, sync and audit

### When the Workflow tool is available (Claude Code)

Run the workflow `agentic-doc:wiki-run` with these args:

```json
{"mode": "<outline|sync|audit>", "plugin_root": "${CLAUDE_PLUGIN_ROOT}"}
```

Add the user's options to the args:

| Option | Arg |
| --- | --- |
| `--pages a b` | `"pages": ["a", "b"]` |
| `--include-unresolved` | `"include_unresolved": true` |
| `--force` | `"force": true` |
| `--lint-only` | `"lint_only": true` |

When the workflow returns, report the result:

- **sync**:
  1. Show a table with one row per page: `id`, `result` and `findings`.
  2. List `failed`, and anything in `integrate.notes` or `integrate.broken_links_remaining`.
  3. Run `status`, and give the next step from its `Next:` line.
- **audit**: Pass `{"results": <drift>, "failed": <drift_failed>}` as JSON on standard input to the command below, and show its output. With `--lint-only`, run `report` without `--drift`.

  ```bash
  uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" report --drift -
  ```

- **outline**:
  - If `installed` is true, give the catalogue path and the page count. Ask the user to review and edit the catalogue (chapters, pages, `sources`, `brief`) before the first `sync`.
  - Otherwise, show `issues`.

If the workflow fails with an error, show the error. Do not run the steps by hand instead.

### When there is no Workflow tool (GitHub Copilot, Codex and others)

Run the same steps yourself, one at a time. Read the procedure for the mode and follow it:

- `outline`: `<SKILL_DIR>/references/run-outline.md`
- `sync`: `<SKILL_DIR>/references/run-sync.md`
- `audit`: `<SKILL_DIR>/references/run-audit.md`

## What you may change

- Write only:
  - The wiki directory.
  - The catalogue.
  - `.agentic-doc/`.
  - `.agentic-doc.config.json` (in `setup`).
  - Files that a `post_commands` hook changed and that the integrate step restores.
- Do not commit. Leave the commit to the user, and remind them that a wiki page should be committed together with the sources it describes.
