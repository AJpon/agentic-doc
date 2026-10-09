# Running outline without a workflow

Use this procedure when the harness has no Workflow tool. You run the same steps as the Claude Code workflow, in order.

Read `<SKILL_DIR>/references/common.md` once first. Before each step, read that step's document again, and keep each result in the shape its schema gives.

1. **Areas.** Follow `<SKILL_DIR>/references/outline-areas.md`. The result is 3 to 5 areas.
2. **Survey.** For each area in turn, follow `<SKILL_DIR>/references/outline-survey.md` with that `area`. Keep every survey result. If no survey succeeds, stop and report the failure.
3. **Propose.** Follow `<SKILL_DIR>/references/outline-propose.md` three times, with `angle` set to `layer`, then `flow`, then `audience`, and `surveys` set to all survey results. Write each proposal independently: do not let an earlier proposal shape a later one.
4. **Merge.** Follow `<SKILL_DIR>/references/outline-merge.md` with `surveys`, `proposals`, and `force` (`true` only if the user passed `--force`).
5. **Report.**
   - If `installed` is true, tell the user where the catalogue is and how many pages it has. Ask them to review and edit the catalogue (chapters, pages, `sources`, `brief`), then run `sync`.
   - Otherwise, show the `issues`.
