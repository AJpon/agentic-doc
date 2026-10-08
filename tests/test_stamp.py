import json

from conftest import page, run_cli


def test_stamp_repins_unresolved_and_skips_others(five):
    code, out, _ = run_cli(five.root, "stamp")
    assert code == 1
    head = five.git("rev-parse", "HEAD")
    assert page(five, "g/unresolved")["source_commit"] == head
    assert page(five, "g/fresh")["source_commit"] == head
    assert page(five, "g/unverified")["source_commit"] is None
    assert page(five, "g/changed")["source_commit"] != head
    assert "g/changed" in out and "src/b.py" in out


def test_stamp_keeps_reviewed_at(five):
    run_cli(five.root, "stamp")
    assert page(five, "g/unresolved")["reviewed_at"] is None


def test_stamp_changed_only_when_explicit(five):
    assert run_cli(five.root, "stamp", "--pages", "g/changed")[0] == 0
    assert page(five, "g/changed")["source_commit"] == five.git("rev-parse", "HEAD")


def test_stamp_after_squash_merge(repo):
    repo.write("src/a.py", "a")
    repo.config()
    repo.commit()
    repo.git("switch", "-q", "-c", "feat")
    repo.write("src/a.py", "a2")
    repo.write("docs/wiki/g/p.md", "x")
    repo.catalogue([{"id": "g/p", "sources": ["src/a.py"]}])
    repo.commit()
    assert run_cli(repo.root, "checkpoint", "--pages", "g/p", "--today", "2026-10-09")[0] == 0
    repo.commit()
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "--squash", "feat")
    repo.commit("squash")
    repo.git("branch", "-D", "feat")
    repo.git("reflog", "expire", "--expire=now", "--all")
    repo.git("gc", "-q", "--prune=now")
    status = lambda: json.loads(run_cli(repo.root, "status", "--json")[1])["pages"][0]["state"]
    assert status() == "unresolved"
    assert run_cli(repo.root, "stamp")[0] == 0
    assert status() == "fresh"


def test_stamp_refusals(five):
    assert run_cli(five.root, "stamp", "--sha", "nope")[0] == 2
    assert run_cli(five.root, "stamp", "--pages", "nope")[0] == 2
    five.write("src/a.py", "dirty")
    assert run_cli(five.root, "stamp")[0] == 2


def test_stamp_refuses_non_ancestor(five):
    five.git("switch", "-q", "-c", "side")
    five.write("x", "1")
    side = five.commit()
    five.git("switch", "-q", "main")
    assert run_cli(five.root, "stamp", "--sha", side)[0] == 2


def test_stamp_refuses_non_canonical_catalogue(five):
    p = five.root / "docs/wiki/catalogue.json"
    p.write_text(p.read_text().replace("  ", "    "))
    assert run_cli(five.root, "stamp", "--dry-run")[0] == 2


def test_stamp_dry_run_writes_nothing(five):
    before = (five.root / "docs/wiki/catalogue.json").read_text()
    code, out, _ = run_cli(five.root, "stamp", "--dry-run")
    assert code == 1 and "g/unresolved" in out
    assert (five.root / "docs/wiki/catalogue.json").read_text() == before
