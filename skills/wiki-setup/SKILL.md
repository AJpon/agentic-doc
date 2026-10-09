---
name: wiki-setup
description: Use when creating or updating the .agentic-doc.config.json for the codebase wiki, for example on first use of agentic-doc, or after the repository layout, formatters or documentation language changed.
---

# agentic-doc setup

This skill creates or updates `.agentic-doc.config.json` at the repository root. The `wiki` skill reads this file in every mode.

`<SKILL_DIR>` is the directory that contains this `SKILL.md`. The scripts belong to the wiki skill next to it. Call them like this:

```bash
uv run --script "<SKILL_DIR>/../wiki/scripts/agentic_doc.py" config check
```

Read `<SKILL_DIR>/references/setup.md` and follow it:

- If `.agentic-doc.config.json` does not exist, follow the first-time procedure.
- If the file exists, follow the update procedure.

The schema of the configuration file is `<SKILL_DIR>/../wiki/schemas/config.schema.json`.
