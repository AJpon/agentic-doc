# Step: integrate the wiki after sync

Rebuild the table of contents, repair links, and run the project's `post_commands`.

## Inputs

- `pages`: the pages that were processed in this sync. Each has `{id, path, result}`, where `result` is `verified`, `unresolved` or `unverified`.
- `written_files`: the page files written in this sync, relative to the repository root.

## Procedure

1. Rebuild the table of contents, the reciprocal related links and the page front matter:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" toc
   ```

   `toc` prints each file that it changed. Save that list as `toc_files`.
2. Find broken links:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" lint --json --skip-sources
   ```

   For each issue with code `link-broken`, correct the link in the wiki file:
   - Use the catalogue `path` values to find the right target.
   - If no target exists, add the link to `broken_links_remaining`.
   - Count the links that you fixed in `links_fixed`.
3. If `post_commands` (from `config show`) is empty, skip steps 4 to 6 and set `post_ran: false` and `post_passed: true`.
4. Record `git status --porcelain` before you run anything.
5. Run the post commands on the wiki files:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" post <written_files and toc_files, deduplicated>
   ```

6. If `post` exits with 1, read its output and handle each failure:
   - **The failure is caused by a wiki file.** Fix the wiki file, then run step 5 again. Repeat at most 3 times.
   - **The failure is caused by a file that is not part of the wiki.** Do not fix it. Describe it in `notes`.
   - **A hook changed a file outside the wiki directory and the catalogue** that was clean in step 4. Restore it with `git checkout -- <path>`, and add the path to `reverted`. Do not touch files that already had changes in step 4.

You may write the files in `wiki_dir`, the catalogue (through `toc`), and the files restored in step 6.

## Output

Return `<SKILL_DIR>/schemas/integrate.schema.json`:

| Field | Content |
| --- | --- |
| `toc_files` | The files that `toc` changed |
| `links_fixed` | The number of links that you fixed |
| `broken_links_remaining` | The links that you could not fix |
| `post_ran` | Whether you ran `post` |
| `post_passed` | Whether the last run of `post` exited with 0 |
| `reverted` | The files that you restored |
| `notes` | Failures you did not fix, and anything else the user should know |
