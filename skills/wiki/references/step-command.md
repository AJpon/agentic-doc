# Step: run one command

This is a mechanical step. Do not interpret the result, fix anything, or retry.

## Inputs

- `command`: the command line to run, exactly as given.
- `stdin` (optional): text to pass to the command as standard input.

## Procedure

1. Run `command` once, from the repository root, exactly as given.
2. If `stdin` is given, pass it as standard input, unchanged:
   1. Write `stdin` to `.agentic-doc/work/stdin-<any unique suffix>.json`.
   2. Redirect the file into the command. POSIX shells: `command < file`. PowerShell: `Get-Content -Raw file | command`.
   3. Delete the file after the command finishes.
3. A non-zero exit code is a valid result. Report it. Do not run the command again.

## Output

Return `<SKILL_DIR>/schemas/command-result.schema.json`. Copy `stdout` and `stderr` character for character, without shortening, summarising or reformatting them.
