# Common rules for every agentic-doc step

Read this before the document for your step. It applies to every step of every mode.

## Paths and scripts

`<SKILL_DIR>` is the directory of the wiki skill. It contains `SKILL.md`, `references/`, `schemas/` and `scripts/`. When a workflow started you, the prompt gives its absolute path. Otherwise it is the directory of the `SKILL.md` you are following.

Run every command from the repository root, the directory that contains `.agentic-doc.config.json`. Call the scripts like this:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" <command> [arguments]
```

Keep the double quotes around the script path, because the install path can contain spaces. All scripts use the same exit codes:

| Code | Meaning |
| --- | --- |
| 0 | OK |
| 1 | Findings were reported. This is not a failure of the script. |
| 2 | The input was refused, or the script failed. Read the message on standard error. |

## Load the configuration first

At the start of the step, run this command once and read its JSON output:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" config show
```

| Key | How to use it |
| --- | --- |
| `language` | The language of all wiki prose (a BCP 47 tag). Write headings, body text, tables and diagram labels in this language. Code identifiers, file paths and commands stay as they are. |
| `audiences` | The reader groups. If every audience of a page has `no_code: true`, the page is a no-code page. See `writing-rules.md`. |
| `context` | Premises about the repository. Treat each entry as a claim to verify: check it against the code before you rely on it, and never copy it into the wiki as fact. If it disagrees with the code, the code is right. Report the disagreement where your step allows (`open_questions`, `notes` or `doc_gaps`). |
| `instructions` | Rules that you must follow. Do not verify them. |
| `strings` | Fixed strings for the configured language. The checks expect them exactly as given (for example `related_heading` and `unverified_marker`). |
| `wiki_dir`, `catalogue` | Where the pages and the catalogue are, relative to the repository root. |

## Ground rules

- Do not ask the user questions. Decide from the code and these documents. If you cannot confirm something, say so in your output.
- Read the code instead of guessing. Do not make claims from file names, naming conventions or what projects "usually" do.
- Design documents, specs and plans in the repository are history. You may use them to explain why something exists. Current behaviour must come from the code or the tests. If they disagree, the code is right.
- Write only the files that your step document allows. Every other file is read-only.
- Do not commit. Do not run `git checkout`, `git reset` or `git stash` unless your step document tells you to.
- Put working notes under `.agentic-doc/work/<page-id>/`. Git ignores this directory.
- Return the structure that the `Output` section of your step document names, and nothing else.
