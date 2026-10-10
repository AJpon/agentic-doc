import json

from conftest import run_cli


def plan(r, *args):
    code, out, err = run_cli(r.root, "plan", *args)
    assert code == 0, err
    return json.loads(out)


def test_plan_default_targets(five):
    d = plan(five, "--today", "2026-10-09")
    assert sorted(t["id"] for t in d["targets"]) == ["g/changed", "g/missing", "g/unverified"]
    assert {s["id"] for s in d["skipped"]} == {"g/fresh", "g/unresolved"}
    assert len(d["head"]) == 40 and d["today"] == "2026-10-09"


def test_plan_include_unresolved(five):
    d = plan(five, "--include-unresolved")
    assert "g/unresolved" in {t["id"] for t in d["targets"]}


def test_plan_explicit_pages_ignore_state(five):
    d = plan(five, "--pages", "g/fresh")
    assert [(t["id"], t["reason"]) for t in d["targets"]] == [("g/fresh", "requested")]


def test_plan_unknown_page_exits_2(five):
    assert run_cli(five.root, "plan", "--pages", "nope")[0] == 2


def test_plan_reasons(five):
    r = {t["id"]: t["reason"] for t in plan(five, "--include-unresolved")["targets"]}
    assert r == {"g/changed": "src/b.py", "g/missing": "file not found",
                 "g/unverified": "never verified", "g/unresolved": "source_commit not found"}


def test_plan_targets_carry_catalogue_fields(five):
    t = plan(five)["targets"][0]
    assert {"id", "path", "title", "audience", "brief", "sources", "related", "source_commit",
            "state", "reason", "pending"} <= t.keys()


def test_plan_default_today_is_iso_date(five):
    assert len(plan(five)["today"]) == 10


def test_plan_reports_dirs_and_ignores_workdir(five):
    d = plan(five)
    assert d["wiki_dir"] == "docs/wiki" and d["work_dir"] == ".agentic-doc/work"
    assert (five.root / ".agentic-doc/work/.gitignore").read_text(encoding="utf-8") == "*\n"


def test_plan_reports_target_count(five):
    code, out, _ = run_cli(five.root, "plan")
    data = json.loads(out)
    assert code == 0 and data["target_count"] == len(data["targets"]) == 3
