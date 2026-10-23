"""Workflow wiki-run.js の制御を、node のスタブのハーネスで検査する."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "com.anthropic.claude-code/workflows/wiki-run.js"
HARNESS = ROOT / "tests/workflow_harness.mjs"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

ROOT_SP = "/tmp/plug in/root"  # 空白入り
SCRIPT = f'uv run --script "{ROOT_SP}/skills/wiki/scripts/agentic_doc.py"'
HEAD = "a" * 40
TODAY = "2026-10-09"
SYNC = {"mode": "sync", "plugin_root": ROOT_SP}
BLOCKER = {"severity": "blocker", "location": "l", "problem": "p", "fix": "f"}
INTEGRATE = {"toc_files": [], "links_fixed": 0, "broken_links_remaining": [], "post_ran": False, "post_passed": True,
             "reverted": []}


def run_wf(args, responses, tmp_path_factory=None) -> dict:
    scenario = ROOT / ".pytest_cache" / "workflow-scenario.json"
    scenario.parent.mkdir(exist_ok=True)
    scenario.write_text(json.dumps({"args": args, "responses": responses}), encoding="utf-8")
    r = subprocess.run([NODE, str(HARNESS), str(WORKFLOW), str(scenario)], capture_output=True, text=True,
                       encoding="utf-8", check=False)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def labels(r) -> list[str]:
    return [c["label"] for c in r["calls"]]


def call(r, label: str) -> dict:
    return next(c for c in r["calls"] if c["label"] == label)


def inputs(c: dict) -> dict:
    return json.loads(c["prompt"].split("Inputs (JSON):\n", 1)[1])


def lab(label: str) -> str:
    return "^" + re.escape(label) + "$"


def cmdres(stdout: str, code: int = 0) -> dict:
    return {"exit_code": code, "stdout": stdout, "stderr": ""}


def target(pid: str, pending: int = 0, state: str = "missing") -> dict:
    return {"id": pid, "path": pid + ".md", "title": pid, "audience": ["agent"], "brief": "b", "sources": ["src/**"],
            "related": [], "source_commit": None, "reviewed_at": None, "state": state, "reason": "r",
            "pending": pending}


def cached(t: dict, research: bool = True, written: bool = False) -> dict:
    pid = t["id"]
    hit = {"hit": True, "path": f".agentic-doc/work/{pid}/research.json", "note_path": f".agentic-doc/work/{pid}/research.md"}
    return {**t, "cache": {"research": hit if research else {"hit": False}, "written": {"hit": written}}}


def ok_plan(targets: list[dict]) -> str:
    return json.dumps({"head": HEAD, "today": TODAY, "wiki_dir": "docs/wiki", "work_dir": ".agentic-doc/work",
                       "targets": targets, "target_count": len(targets), "skipped": [],
                       "warnings": {"uncommitted": [], "untracked": []}})


def research(pid: str) -> dict:
    return {"page_id": pid, "note_path": f".agentic-doc/work/{pid}/research.md", "key_claims": []}


def written(pid: str) -> dict:
    return {"page_id": pid, "path": f"docs/wiki/{pid}.md", "written": True}


def verdict(lens: str, issues=()) -> dict:
    return {"lens": lens, "pass": not issues, "issues": list(issues)}


def page_responses(pid: str, dead=frozenset(), claim=None, research_ok=True) -> list:
    out = [
        (lab(f"verify:citation:{pid}"), None if "verify" in dead else verdict("citation")),
        (lab(f"verify:claim:{pid}"), None if "verify" in dead else (claim or verdict("claim"))),
        (lab(f"record:{pid}"), cmdres("")),
        (f"^fix[12]:{re.escape(pid)}$", {"changed": ["x"], "disputed": []}),
        (f"^cache:(research|written):{re.escape(pid)}", cmdres("")),
    ]
    if research_ok:
        out += [(lab(f"research:{pid}"), None if f"research:{pid}" in dead else research(pid)),
                (lab(f"write:{pid}"), written(pid))]
    return out


def clean_responses(ids, dead=frozenset()) -> list:
    out = [("^plan$", cmdres(ok_plan([target(i) for i in ids]))), ("^integrate$", INTEGRATE)]
    for i in ids:
        out += page_responses(i, dead=dead)
    return out


def test_requires_plugin_root():
    assert "plugin_root" in run_wf({"mode": "sync"}, [])["error"]


def test_unknown_mode_throws():
    assert "mode" in run_wf({"mode": "nope", "plugin_root": ROOT_SP}, [])["error"]


def test_no_targets_skips_integrate():
    r = run_wf(SYNC, [("^plan$", cmdres(ok_plan([])))])
    assert r["error"] is None and r["result"]["pages"] == [] and "integrate" not in labels(r)


def test_plan_command_carries_arguments():
    r = run_wf({**SYNC, "pages": ["a/x", "b/y"], "include_unresolved": True, "today": TODAY},
               [("^plan$", cmdres(ok_plan([])))])
    assert inputs(call(r, "plan"))["command"] == (f"{SCRIPT} plan --pages a/x b/y --include-unresolved "
                                                  f"--today {TODAY}")
    assert call(r, "plan")["model"] == "haiku" and call(r, "plan")["effort"] == "low"


def test_clean_page_is_checkpointed_with_quoted_script():
    r = run_wf(SYNC, clean_responses(["a/x"]))
    rec = call(r, "record:a/x")
    assert inputs(rec)["command"] == f"{SCRIPT} checkpoint --pages a/x --sha {HEAD} --today {TODAY}"
    assert r["result"]["pages"][0]["result"] == "verified" and "integrate" in labels(r)
    integ = inputs(call(r, "integrate"))
    assert integ["written_files"] == ["docs/wiki/a/x.md"] and integ["pages"][0]["id"] == "a/x"


def test_research_gets_note_path_in_work_dir():
    r = run_wf(SYNC, clean_responses(["a/x"]))
    assert inputs(call(r, "research:a/x"))["note_path"] == ".agentic-doc/work/a/x/research.md"
    assert inputs(call(r, "write:a/x"))["today"] == TODAY


def test_persistent_blocker_runs_two_fix_rounds_then_saves_findings():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", claim=verdict("claim", [BLOCKER]))
    r = run_wf(SYNC, responses)
    assert labels(r).count("fix1:a/x") == 1 and labels(r).count("fix2:a/x") == 1
    rec = inputs(call(r, "record:a/x"))
    assert rec["command"] == f"{SCRIPT} findings save a/x <FILE>"
    assert json.loads(rec["file"]) == [{**BLOCKER, "lens": "claim"}]
    assert r["result"]["pages"][0]["result"] == "unresolved" and r["result"]["pages"][0]["findings"] == 1


def test_fix_then_clean_is_verified():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", claim={"__seq": [verdict("claim", [BLOCKER]), verdict("claim")]})
    r = run_wf(SYNC, responses)
    assert "fix1:a/x" in labels(r) and "fix2:a/x" not in labels(r)
    assert "checkpoint" in inputs(call(r, "record:a/x"))["command"]


def test_minor_issues_do_not_trigger_fix():
    minor = {**BLOCKER, "severity": "minor"}
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", claim=verdict("claim", [minor]))
    r = run_wf(SYNC, responses)
    assert not any(label.startswith("fix") for label in labels(r))
    assert r["result"]["pages"][0]["result"] == "verified"


def test_all_verifiers_dead_leaves_page_unverified_without_fix():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", dead={"verify"})
    r = run_wf(SYNC, responses)
    assert not any(label.startswith(("fix", "record")) for label in labels(r))
    assert r["result"]["pages"][0]["result"] == "unverified"


def test_failed_checkpoint_leaves_page_unverified():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE),
                 (lab("record:a/x"), cmdres("", 2))]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert r["result"]["pages"][0]["result"] == "unverified"


def test_pending_findings_skip_research_and_write():
    responses = [("^plan$", cmdres(ok_plan([target("a/x", pending=1, state="unverified")]))),
                 ("^integrate$", INTEGRATE), (lab("findings:a/x"), cmdres(json.dumps([BLOCKER])))]
    responses += page_responses("a/x", research_ok=False)
    r = run_wf(SYNC, responses)
    assert "research:a/x" not in labels(r) and "write:a/x" not in labels(r)
    assert inputs(call(r, "findings:a/x"))["command"] == f"{SCRIPT} findings show a/x"
    fix = inputs(call(r, "fix1:a/x"))
    assert fix["findings"] == [BLOCKER] and "note_path" not in fix
    assert r["result"]["pages"][0]["result"] == "verified"


def test_resumed_page_reaches_post_commands():
    responses = [("^plan$", cmdres(ok_plan([target("a/x", pending=1, state="unverified")]))),
                 ("^integrate$", INTEGRATE), (lab("findings:a/x"), cmdres(json.dumps([BLOCKER])))]
    responses += page_responses("a/x", research_ok=False)
    r = run_wf(SYNC, responses)
    assert inputs(call(r, "integrate"))["written_files"] == ["docs/wiki/a/x.md"]


def test_stale_pending_findings_fall_back_to_research():
    responses = [("^plan$", cmdres(ok_plan([target("a/x", pending=1, state="unverified")]))),
                 ("^integrate$", INTEGRATE), (lab("findings:a/x"), cmdres("null"))]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert "research:a/x" in labels(r)


def test_failed_research_marks_failed_and_others_continue():
    r = run_wf(SYNC, clean_responses(["a/x", "a/y"], dead={"research:a/x"}))
    assert r["result"]["failed"] == ["a/x"] and [p["id"] for p in r["result"]["pages"]] == ["a/y"]


def test_at_most_two_pages_in_flight():
    r = run_wf(SYNC, clean_responses(["a/1", "a/2", "a/3", "a/4", "a/5"]))
    assert r["error"] is None and len(r["result"]["pages"]) == 5
    assert r["max_in_flight"] <= 4


def test_bad_head_throws():
    bad = json.dumps({**json.loads(ok_plan([])), "head": "HEAD"})
    assert "head" in run_wf(SYNC, [("^plan$", cmdres(bad))])["error"]


def test_truncated_plan_transcription_throws():
    short = json.dumps({**json.loads(ok_plan([target("a/x")])), "target_count": 2})
    r = run_wf(SYNC, [("^plan$", cmdres(short))])
    assert "target_count" in r["error"]


def test_failed_plan_throws_with_stderr():
    r = run_wf(SYNC, [("^plan$", {"exit_code": 2, "stdout": "", "stderr": "refused: catalogue not found"})])
    assert "catalogue not found" in r["error"]


OUTLINE_RESPONSES = [
    ("^areas$", {"areas": [{"key": k, "title": k, "scope": ["**"], "questions": ["q"]}
                           for k in ["src", "tests", "build"]]}),
    ("^survey:", {"area": "x", "summary": "s", "findings": []}),
    ("^propose:", {"rationale": "r", "chapters": [], "pages": []}),
    ("^merge$", {"installed": True, "catalogue": "docs/wiki/catalogue.json", "page_count": 3, "rationale": "r",
                 "issues": []}),
]


def test_outline_force_flag_reaches_merge():
    r = run_wf({"mode": "outline", "plugin_root": ROOT_SP, "force": True}, OUTLINE_RESPONSES)
    assert inputs(call(r, "merge"))["force"] is True
    assert sum(label.startswith("survey:") for label in labels(r)) == 3
    assert sorted(label for label in labels(r) if label.startswith("propose:")) == [
        "propose:audience", "propose:flow", "propose:layer"]
    assert r["result"]["installed"] is True


def test_outline_without_surveys_throws():
    dead = [OUTLINE_RESPONSES[0], ("^survey:", None)] + OUTLINE_RESPONSES[2:]
    assert run_wf({"mode": "outline", "plugin_root": ROOT_SP}, dead)["error"]


def test_audit_lint_only_calls_no_agent():
    r = run_wf({"mode": "audit", "plugin_root": ROOT_SP, "lint_only": True}, [])
    assert r["calls"] == [] and r["result"]["lint_only"] is True


def test_audit_collects_drift_and_failures():
    targets = [target("a/x", state="changed"), target("a/y", state="changed"), target("a/z")]
    r = run_wf({"mode": "audit", "plugin_root": ROOT_SP}, [
        ("^plan$", cmdres(ok_plan(targets))),
        (lab("drift:a/x"), {"page_id": "a/x", "issues": []}),
        (lab("drift:a/y"), None),
    ])
    assert "drift:a/z" not in labels(r)
    assert [d["page_id"] for d in r["result"]["drift"]] == ["a/x"] and r["result"]["drift_failed"] == ["a/y"]


def test_prompts_carry_no_procedure_text():
    r = run_wf(SYNC, clean_responses(["a/x"]))
    r2 = run_wf({"mode": "outline", "plugin_root": ROOT_SP}, OUTLINE_RESPONSES)
    for c in r["calls"] + r2["calls"]:
        lines = c["prompt"].split("\n")
        assert len(lines) == 5, c["label"]
        assert lines[0].startswith("You are one step of the agentic-doc wiki workflow.")
        assert lines[1] == f"SKILL_DIR = {ROOT_SP}/skills/wiki"
        assert lines[2].startswith(f'Read "{ROOT_SP}/skills/wiki/references/')
        assert lines[2].endswith(("and follow them exactly.", "and follow it exactly."))
        assert lines[3] == "Inputs (JSON):"
        json.loads(lines[4])


def test_embedded_schemas_match_files():
    r = subprocess.run([sys.executable, "dev/embed_schemas.py", "--check"], cwd=ROOT, capture_output=True,
                       text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr


def test_one_lens_missing_leaves_page_unverified():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE),
                 (lab("verify:citation:a/x"), None)]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert not any(label.startswith(("fix", "record")) for label in labels(r))
    assert r["result"]["pages"][0]["result"] == "unverified"


def test_verified_pages_are_unverified_before_rewrite():
    t = target("a/x", state="fresh")
    t["source_commit"] = "b" * 40
    responses = [("^plan$", cmdres(ok_plan([t, target("a/y")]))), ("^integrate$", INTEGRATE),
                 ("^unverify$", cmdres("a/x\n"))]
    responses += page_responses("a/x") + page_responses("a/y")
    r = run_wf({**SYNC, "pages": ["a/x", "a/y"]}, responses)
    assert inputs(call(r, "unverify"))["command"] == f"{SCRIPT} unverify --pages a/x"
    assert labels(r).index("unverify") < labels(r).index("research:a/x")


def test_no_unverify_when_every_target_is_already_unverified():
    r = run_wf(SYNC, clean_responses(["a/x"]))
    assert "unverify" not in labels(r)


def test_failed_unverify_throws():
    t = target("a/x", state="changed")
    t["source_commit"] = "b" * 40
    r = run_wf(SYNC, [("^plan$", cmdres(ok_plan([t]))),
                      ("^unverify$", {"exit_code": 2, "stdout": "", "stderr": "refused: locked"})])
    assert "locked" in r["error"]


def test_fresh_research_is_saved_before_write():
    r = run_wf(SYNC, clean_responses(["a/x"]))
    save = inputs(call(r, "cache:research:a/x"))
    assert save["command"] == f"{SCRIPT} cache save research a/x <FILE>"
    assert json.loads(save["file"]) == research("a/x")
    assert labels(r).index("research:a/x") < labels(r).index("cache:research:a/x") < labels(r).index("write:a/x")
    w = inputs(call(r, "write:a/x"))
    assert w["research_path"] == ".agentic-doc/work/a/x/research.json"
    assert w["note_path"] == ".agentic-doc/work/a/x/research.md" and "research" not in w


def test_research_cache_save_is_retried_once():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE),
                 (lab("cache:research:a/x"), {"__seq": [cmdres("", 2), cmdres("")]})]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert labels(r).count("cache:research:a/x") == 2
    assert r["result"]["pages"][0]["result"] == "verified"


def test_failed_research_cache_save_fails_the_page():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE),
                 (lab("cache:research:a/x"), cmdres("", 2))]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert r["result"]["failed"] == ["a/x"] and "write:a/x" not in labels(r)


def test_cached_research_skips_the_research_agent():
    responses = [("^plan$", cmdres(ok_plan([cached(target("a/x"))]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", research_ok=False) + [(lab("write:a/x"), written("a/x"))]
    r = run_wf(SYNC, responses)
    assert "research:a/x" not in labels(r) and "cache:research:a/x" not in labels(r)
    w = inputs(call(r, "write:a/x"))
    assert w["research_path"] == ".agentic-doc/work/a/x/research.json"
    assert w["note_path"] == ".agentic-doc/work/a/x/research.md"
    assert r["result"]["pages"][0]["result"] == "verified"


def test_written_page_goes_straight_to_verify():
    t = cached(target("a/x", state="unverified"), written=True)
    responses = [("^plan$", cmdres(ok_plan([t]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", research_ok=False)
    r = run_wf(SYNC, responses)
    assert not any(label in labels(r) for label in ("research:a/x", "write:a/x"))
    assert "verify:citation:a/x" in labels(r) and r["result"]["pages"][0]["result"] == "verified"
    assert inputs(call(r, "integrate"))["written_files"] == ["docs/wiki/a/x.md"]


def test_written_page_fix_gets_the_cached_note():
    t = cached(target("a/x", state="unverified"), written=True)
    responses = [("^plan$", cmdres(ok_plan([t]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", research_ok=False, claim=verdict("claim", [BLOCKER]))
    r = run_wf(SYNC, responses)
    assert inputs(call(r, "fix1:a/x"))["note_path"] == ".agentic-doc/work/a/x/research.md"


def test_written_cache_is_saved_after_write_and_after_each_fix():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE)]
    responses += page_responses("a/x", claim=verdict("claim", [BLOCKER]))
    r = run_wf(SYNC, responses)
    seq = [label for label in labels(r) if label.startswith(("write:", "fix", "cache:written"))]
    assert seq == ["write:a/x", "cache:written:a/x", "fix1:a/x", "cache:written:a/x", "fix2:a/x",
                   "cache:written:a/x"]
    assert inputs(call(r, "cache:written:a/x"))["command"] == f"{SCRIPT} cache save written a/x"


def test_failed_written_cache_save_is_not_fatal():
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", INTEGRATE),
                 (lab("cache:written:a/x"), cmdres("", 2))]
    responses += page_responses("a/x")
    r = run_wf(SYNC, responses)
    assert r["result"]["pages"][0]["result"] == "verified"


def _resave_run(claim=None, dead=frozenset(), integrate=INTEGRATE):
    responses = [("^plan$", cmdres(ok_plan([target("a/x")]))), ("^integrate$", integrate),
                 (r"^resave:", cmdres(""))]
    responses += page_responses("a/x", claim=claim, dead=dead)
    return run_wf(SYNC, responses)


def test_unresolved_page_findings_and_cache_are_saved_again_after_integrate():
    r = _resave_run(claim=verdict("claim", [BLOCKER]))
    seq = [label for label in labels(r) if label in ("integrate", "resave:findings:a/x", "resave:cache:a/x")]
    assert seq[0] == "integrate" and sorted(seq[1:]) == ["resave:cache:a/x", "resave:findings:a/x"]
    f = inputs(call(r, "resave:findings:a/x"))
    assert f["command"] == f"{SCRIPT} findings save a/x <FILE>"
    assert json.loads(f["file"]) == [{**BLOCKER, "lens": "claim"}]
    assert inputs(call(r, "resave:cache:a/x"))["command"] == f"{SCRIPT} cache save written a/x"


def test_unverified_page_cache_is_saved_again_after_integrate():
    r = _resave_run(dead={"verify"})
    assert "resave:cache:a/x" in labels(r) and "resave:findings:a/x" not in labels(r)


def test_verified_page_needs_no_resave():
    r = _resave_run()
    assert not any(label.startswith("resave:") for label in labels(r))


def test_no_resave_when_integrate_failed():
    r = _resave_run(claim=verdict("claim", [BLOCKER]), integrate=None)
    assert not any(label.startswith("resave:") for label in labels(r))
