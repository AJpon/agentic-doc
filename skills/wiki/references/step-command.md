# Step: run one command

This is a mechanical step. Do not interpret the result, fix anything, or retry.

## Inputs

- `command`: the command line to run, exactly as given.
- `file` (optional): text that the command reads from a file. The command contains the placeholder `<FILE>` where the file path goes.

## Procedure

1. If `file` is given:
   1. Write `file` unchanged to `.agentic-doc/work/input-<any unique suffix>.json`. Use your file-writing tool, which writes UTF-8. Do not pipe the text through a shell: Windows PowerShell can corrupt non-ASCII text in pipes.
   2. Replace `<FILE>` in `command` with that path.
2. Run `command` once, from the repository root, exactly as given. Do not change it in any other way.
3. If you wrote a file in step 1, delete it.
4. A non-zero exit code is a valid result. Report it. Do not run the command again.

## Output

Return `<SKILL_DIR>/schemas/command-result.schema.json`. Copy `stdout` and `stderr` character for character, without shortening, summarising or reformatting them.
