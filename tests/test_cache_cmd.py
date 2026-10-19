import json

from conftest import dump, load_catalogue, run_cli

PAGE = "g/unverified"
WORK = f".agentic-doc/work/{PAGE}"
RESEARCH = {"page_id": PAGE, "note_path": f"{WORK}/research.md",
            "key_claims": [{"claim": "a は 1 を返す", "evidence": ["src/a.py:1"]}]}


def show(r, page_id: str = PAGE) -> dict:
    code, out, err = run_cli(r.root, "cache", "show", page_id)
    assert code == 0, err
    return json.loads(out)


def save_research(r, data=RESEARCH, note: bool = True):
    r.write(f"{WORK}/research.json", data if isinstance(data, str) else dump(data))
    if note:
        r.write(f"{WORK}/research.md", "notes\n")
    return run_cli(r.root, "cache", "save", "research", PAGE)


def edit_page(r, **fields) -> None:
    data = load_catalogue(r)
    for p in data["pages"]:
        if p["id"] == PAGE:
            p.update(fields)
    r.write("docs/wiki/catalogue.json", dump(data))


def test_show_reports_miss_when_nothing_saved(five):
    assert show(five) == {"research": {"hit": False}, "written": {"hit": False}}


def test_save_research_needs_a_valid_research_json(five):
    assert run_cli(five.root, "cache", "save", "research", PAGE)[0] == 2
    assert save_research(five, "{not json")[0] == 2
    assert save_research(five, {"page_id": PAGE})[0] == 2


def test_save_research_needs_the_note(five):
    code, _, err = save_research(five, note=False)
    assert code == 2 and "research.md" in err


def test_research_hit_after_save(five):
    assert save_research(five)[0] == 0
    hit = show(five)["research"]
    assert hit["hit"] is True and hit["path"] == f"{WORK}/research.json"
    assert hit["note_path"] == f"{WORK}/research.md"


def test_research_survives_unrelated_changes(five):
    save_research(five)
    five.write("src/b.py", "unrelated change")
    five.write("docs/other.md", "x")
    five.commit()
    assert show(five)["research"]["hit"] is True


def test_research_invalidated_by_source_content(five):
    save_research(five)
    five.write("src/a.py", "a changed, not committed")
    assert show(five)["research"]["hit"] is False


def test_research_invalidated_by_new_matching_source(five):
    edit_page(five, sources=["src/*.py"])
    five.commit()
    save_research(five)
    five.write("src/c.py", "c")
    five.commit()
    assert show(five)["research"]["hit"] is False


def test_research_invalidated_by_brief(five):
    save_research(five)
    edit_page(five, brief="a different brief")
    assert show(five)["research"]["hit"] is False


def test_save_written_needs_the_page_file(five):
    five.write(f"{WORK}/research.md", "notes\n")
    (five.root / "docs/wiki/g/unverified.md").unlink()
    assert run_cli(five.root, "cache", "save", "written", PAGE)[0] == 2


def test_written_hit_after_save_and_miss_after_edit(five):
    save_research(five)
    assert run_cli(five.root, "cache", "save", "written", PAGE)[0] == 0
    assert show(five)["written"]["hit"] is True
    five.write("docs/wiki/g/unverified.md", "x edited")
    assert show(five)["written"]["hit"] is False


def test_written_invalidated_by_source_change(five):
    save_research(five)
    run_cli(five.root, "cache", "save", "written", PAGE)
    five.write("src/a.py", "a changed")
    assert show(five)["written"]["hit"] is False


def test_checkpoint_clears_the_cache(five):
    save_research(five)
    run_cli(five.root, "cache", "save", "written", PAGE)
    assert run_cli(five.root, "checkpoint", "--pages", PAGE)[0] == 0
    assert show(five) == {"research": {"hit": False}, "written": {"hit": False}}


def test_stale_findings_do_not_wipe_the_cache(five):
    save_research(five)
    run_cli(five.root, "findings", "save", PAGE, "-", input=dump(
        [{"severity": "major", "location": "l", "problem": "p", "fix": "f"}]))
    five.write("docs/wiki/g/unverified.md", "edited after the findings")
    code, out, _ = run_cli(five.root, "findings", "show", PAGE)
    assert code == 0 and json.loads(out) is None
    assert show(five)["research"]["hit"] is True


def test_unknown_page_is_refused(five):
    assert run_cli(five.root, "cache", "show", "g/nope")[0] == 2
