import json

from conftest import run_cli

PID = "g/page"


def ISSUE(severity: str, problem: str) -> dict:
    return {"severity": severity, "location": "l", "problem": problem, "fix": "f"}


def break_link(r, page_id: str) -> None:
    p = r.root / "docs/wiki" / (page_id + ".md")
    p.write_text(p.read_text(encoding="utf-8").replace("(other.md)", "(gone.md)"), encoding="utf-8")


def report(r, *args, drift=None):
    extra = ("--drift", "-") if drift is not None else ()
    code, out, err = run_cli(r.root, "report", "--json", *extra, *args,
                             input=json.dumps(drift) if drift is not None else None)
    assert code in (0, 1), err
    return code, json.loads(out)


def test_clean_wiki_reports_nothing(wiki):
    code, d = report(wiki)
    assert code == 0 and d["total_issues"] == 0 and d["next"] == ["nothing to do"]
    assert d["pages_checked"] == 2 and d["by_page"] == [] and d["needs_update"] == []


def test_lint_and_drift_merge_by_page(wiki):
    break_link(wiki, PID)
    code, d = report(wiki, drift={"results": [{"page_id": PID, "issues": [ISSUE("major", "Wrong. More.")]}],
                                  "failed": []})
    row = d["by_page"][0]
    assert code == 1
    assert row == {"page_id": PID, "issue_count": 2, "worst_severity": "blocker", "headline": row["headline"]}
    assert row["headline"].startswith("[link-broken]")


def test_drift_headline_is_first_sentence(wiki):
    _, d = report(wiki, drift={"results": [{"page_id": PID, "issues": [ISSUE("minor", "First. Second.")]}],
                               "failed": []})
    assert d["by_page"][0]["headline"] == "First"


def test_headline_is_truncated(wiki):
    _, d = report(wiki, drift={"results": [{"page_id": PID, "issues": [ISSUE("minor", "x" * 300)]}], "failed": []})
    assert len(d["by_page"][0]["headline"]) == 121 and d["by_page"][0]["headline"].endswith("…")


def test_needs_update_and_next_steps(five):
    _, d = report(five)
    assert {(n["page_id"], n["state"]) for n in d["needs_update"]} >= {("g/missing", "missing"),
                                                                       ("g/unresolved", "unresolved")}
    assert any(s.startswith("sync --pages") for s in d["next"])
    assert any("stamp --pages g/unresolved" in s for s in d["next"])


def test_quiet_drift_suggests_stamp(five):
    _, d = report(five, drift={"results": [{"page_id": "g/changed", "issues": []}], "failed": ["g/fresh"]})
    assert any("stamp --pages g/changed" in s for s in d["next"])
    assert d["drift_failed"] == ["g/fresh"]
    assert any("audit" in s for s in d["next"])


def test_drift_major_suggests_sync(wiki):
    _, d = report(wiki, drift={"results": [{"page_id": PID, "issues": [ISSUE("major", "p")]}], "failed": []})
    assert any(f"sync --pages {PID}" in s for s in d["next"])


def test_drift_off_schema_is_2(wiki):
    bad = json.dumps({"results": [{"page_id": PID}], "failed": []})
    assert run_cli(wiki.root, "report", "--drift", "-", input=bad)[0] == 2


def test_text_output_is_localized(five):
    five.config(language="ja")
    assert "次の操作" in run_cli(five.root, "report")[1]


def test_minor_only_drift_on_changed_page_suggests_check(five):
    _, d = report(five, drift={"results": [{"page_id": "g/changed", "issues": [ISSUE("minor", "p")]}],
                               "failed": []})
    assert any("stamp --pages g/changed" in s and "sync --pages g/changed" in s for s in d["next"])


def test_lint_only_changed_page_suggests_audit(five):
    _, d = report(five)
    assert any("g/changed" in s and "audit" in s for s in d["next"])
