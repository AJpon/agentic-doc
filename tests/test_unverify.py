import json

from conftest import diff_lines, page, run_cli


def test_unverify_nulls_source_commit_and_keeps_reviewed_at(five):
    before = (five.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8")
    code, out, _ = run_cli(five.root, "unverify", "--pages", "g/fresh")
    assert code == 0 and out.strip() == "g/fresh"
    assert page(five, "g/fresh")["source_commit"] is None
    after = (five.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8")
    assert diff_lines(before, after) == 1
    st = json.loads(run_cli(five.root, "status", "--json", "g/fresh")[1])["pages"][0]
    assert st["state"] == "unverified"


def test_unverify_unknown_page_is_2(five):
    assert run_cli(five.root, "unverify", "--pages", "nope")[0] == 2
