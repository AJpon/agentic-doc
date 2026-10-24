# Running sync without a workflow

Use this procedure when the harness has no Workflow tool, for example GitHub Copilot or Codex. You run every step yourself, one page at a time. The step documents and scripts are the same ones the Claude Code workflow uses. The only difference is that everything runs in order instead of in parallel.

Read `<SKILL_DIR>/references/common.md` once first. Before each step, read that step's document again: each step has its own role and rules, and you must not carry assumptions over from the previous step. Keep the result of each step in your working memory, in the shape its schema gives.

## 1. Plan

Run `plan`, with the user's arguments mapped as `<SKILL_DIR>/references/overview.md` describes:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" plan
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" plan --pages <id> <id>
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" plan --include-unresolved
```

The JSON output contains `head`, `today`, `wiki_dir`, `work_dir`, `targets`, `target_count`, `skipped` and `warnings`.
- If `warnings` lists uncommitted or untracked files, tell the user that the wiki will describe the committed state, and suggest committing first. Then continue.
- If `targets` is empty, report that nothing needs to be done, and stop.

Some targets may still have a `source_commit` (for example, pages named with `--pages`, or changed pages). Reset it before you rewrite them, so that a page whose rewrite fails stays unverified instead of looking fresh. If this command fails, stop:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" unverify --pages <ids of the targets whose source_commit is not null>
```

## 2. Process each target in order

For each page in `targets`, do the following steps. If one page fails, record the failure and continue with the next page.

1. **Resume from saved findings.** If `pending` is greater than 0, run the command below.
   - If it prints an array, skip steps 2–5 and start at step 6, using the array as the round-1 findings. The page counts as written: add its file to `written_files`.
   - If it prints `null`, continue with step 2.

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" findings show <id>
   ```

2. **Use the cache.** Each target has `cache` in the plan output. It is valid only while the page's `brief` and the contents of its source files are unchanged.
   - If `cache.written.hit` is true, the page body from the interrupted run is still valid. Skip steps 3–4 and start at step 5 (verify). Add the page file to `written_files`.
   - If `cache.research.hit` is true, skip step 3. Use `cache.research.path` as `research_path` and `cache.research.note_path` as `note_path` in step 4.
3. **Research.** Follow `<SKILL_DIR>/references/sync-research.md`. Inputs: `page` (the target) and `note_path` = `<work_dir>/<id>/research.md`. When you finish, write your research result as JSON to `<work_dir>/<id>/research-input.json`, using your file-writing tool, then record it. If this command refuses, the research result is not usable: record the failure and continue with the next page.

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" cache save research <id> <work_dir>/<id>/research-input.json
   ```

4. **Write.** Follow `<SKILL_DIR>/references/sync-write.md`. Inputs: `page`, `research_path` (`<work_dir>/<id>/research.json`), `note_path`, and `today` from the plan. When you finish, and after every fix round in step 6, record the page body. If this command fails, continue anyway.

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" cache save written <id>
   ```
5. **Verify.**
   1. Follow `<SKILL_DIR>/references/verify-citation.md`.
   2. Read `<SKILL_DIR>/references/verify-claim.md` again, and follow it.

   While verifying, you are a verifier, not the author: try to prove the page wrong. Do not edit the page in this step.
6. **Fix.**
   - If the verdicts contain `blocker` or `major` issues, follow `<SKILL_DIR>/references/sync-fix.md`, with `round` 1, then verify again as in step 5.
   - If such issues remain, fix with `round` 2, then verify once more. Do not do more than 2 rounds.
7. **Record.**
   - If no `blocker` or `major` issue remains:

     ```bash
     uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" checkpoint --pages <id> --sha <head> --today <today>
     ```

   - Otherwise, write the remaining `blocker` and `major` issues as a JSON array to `<work_dir>/<id>/findings-input.json`, using your file-writing tool, then save them. The next sync resumes from them.

     ```bash
     uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" findings save <id> <work_dir>/<id>/findings-input.json
     ```

   - If either verification lens could not be completed, record nothing. The page stays unverified.

## 3. Integrate

If at least one page was processed (its result is `verified`, `unresolved` or `unverified`), follow `<SKILL_DIR>/references/sync-integrate.md`. Inputs:
- `pages`: every processed page, with its result (`verified`, `unresolved` or `unverified`).
- `written_files`: the page files you wrote or fixed, relative to the repository root (`<wiki_dir>/<path>`).

Integrate can change a page body (links, `post_commands`), which invalidates the findings and the written-page cache you saved earlier. For every page whose result is `unresolved` or `unverified`, save them again, using the same findings as before:

```bash
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" findings save <id> <work_dir>/<id>/findings-input.json
uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" cache save written <id>
```

Run the first command only for `unresolved` pages. Skip this step if integrate failed.

## 4. Report

Show the user a table with one row per page: `id`, the result, and the number of remaining findings. List the pages that failed. Then run `status`, and give the next step from its `Next` line.
