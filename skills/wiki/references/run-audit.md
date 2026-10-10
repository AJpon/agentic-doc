# Running audit without a workflow

Use this procedure when the harness has no Workflow tool. Audit is read-only: do not change any file.

Read `<SKILL_DIR>/references/common.md` once first.

1. If the user passed `--lint-only`, run the following command, show its output, and stop:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" report
   ```

2. Run `plan`. From its `targets`, take the pages with `"state": "changed"`:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" plan
   ```

3. For each of those pages in turn, read `<SKILL_DIR>/references/audit-drift.md` again and follow it with `page` set to the target. Keep each result. If you cannot finish a page, add its ID to a `failed` list.
4. Combine the results into `{"results": [<drift results>], "failed": [<ids>]}`. Write the JSON to `.agentic-doc/work/drift.json` with your file-writing tool. Then run the following command, and show its output to the user:

   ```bash
   uv run --script "<SKILL_DIR>/scripts/agentic_doc.py" report --drift .agentic-doc/work/drift.json
   ```
