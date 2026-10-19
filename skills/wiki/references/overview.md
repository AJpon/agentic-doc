# agentic-doc overview

agentic-doc generates a Markdown wiki from a codebase and keeps it in step with the code. Two files hold the state:

- **Catalogue** (`catalogue.json`): the chapters and pages. For each page, it records the files the page depends on (`sources`) and the commit at which the page last passed review (`source_commit`).
- **Configuration file** (`.agentic-doc.config.json`).

When the git diff from `source_commit` touches a page's sources, the page is stale and `sync` rewrites it.

## Modes

Run each mode as `/agentic-doc:wiki <mode> [arguments]`. The exact syntax depends on the harness.

| Mode | Writes | What it does | Arguments |
| --- | --- | --- | --- |
| `help` (or no mode) | No | Shows where the project is in the flow and the next command to run | None |
| `setup` | Yes | Creates or updates `.agentic-doc.config.json` | None |
| `outline` | Yes | Designs the chapters, pages and sources, then installs the catalogue | `--force` replaces an existing catalogue. Every page becomes unverified. |
| `sync` | Yes | Writes or rewrites the pages that are missing, unverified or changed | `--pages <id>...` targets exactly these pages, whatever their state. `--include-unresolved` also targets unresolved pages. |
| `status` | No | Shows the state of each page. No LLM is involved. | `[<id>...]`, `--state <state>`, `--verbose` |
| `audit` | No | Checks the wiki for mechanical problems and for drift between the text and the code | `--lint-only` skips the LLM drift check |
| `stamp` | Yes | Marks pages as reviewed at a commit without changing their text | `--sha <rev>`, `--pages <id>...`, `--dry-run` |

Each mode maps to these scripts. `sync` passes `--pages` and `--include-unresolved` to `plan`. `status` and `stamp` pass their arguments to the script of the same name.

## Flow

```text
First time:          setup ─▶ outline ─▶ (a person reviews the catalogue) ─▶ sync ─▶ commit
Day to day:          status / audit (optional) ─▶ sync ─▶ commit
Restructure:         outline --force ─▶ sync
History rewritten:   status shows "unresolved" ─▶ check the pages ─▶ stamp
```

## Page states

`status` checks these states in order. The first one that applies wins.

| State | Condition | What to do |
| --- | --- | --- |
| `missing` | The page file does not exist | `sync` |
| `unverified` | `source_commit` is null: the page was never verified, a rewrite has not passed review yet, or findings remain | `sync`. It resumes from the saved findings, or reuses the cached research and the written page when they are still valid. |
| `unresolved` | `source_commit` no longer exists, for example after a squash merge or rebase | Check the page, then run `stamp --pages <id>`, or `sync --pages <id>` |
| `changed` | The sources changed after `source_commit` | `sync`. Run `audit` first if you want to know whether the text is still right. |
| `fresh` | None of the above | Nothing |

## Choosing the next step

Answer "what should I do next?" from these checks, in this order:

1. If `config check` fails, or there is no configuration file, run `setup`.
2. If `config show` reports `catalogue_exists: false`, run `outline`.
3. Otherwise, run `status`. Its `Next:` line, or the `next` array of `status --json`, gives the steps with their arguments. Common cases:

   | Situation | Next step |
   | --- | --- |
   | Pages are missing, unverified or changed | `sync` |
   | Pages are unresolved | Check them, then `stamp --pages <ids>` |
   | Sources have uncommitted changes | Commit first |
   | Every page is fresh | Nothing. Optionally run `audit`. |

4. After `outline`, the catalogue needs a human review before the first `sync`.

## Errors

| Situation | What happens |
| --- | --- |
| No configuration file, or it fails `config check` | Explain why, point to `setup`, and stop |
| No catalogue (`sync`, `status`, `audit`, `stamp`) | Point to `outline`, and stop |
| Sources have uncommitted changes or untracked files | Warn and continue. `stamp` refuses. |
| One page fails (an agent fails, or verification fails) | The page stays unverified and the other pages continue. The failed pages are listed at the end. |
| The verification agents of a page all fail | The page stays unverified, and no findings are saved |
| `post_commands` fail | A wiki file causing the failure is fixed (up to 3 times). Other failures are reported. Files outside the wiki that a hook changed are restored. |

Run `uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" --help` for the commands, arguments and exit codes of the scripts.
