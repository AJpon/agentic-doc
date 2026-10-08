from conftest import diff_lines, page, run_cli


def test_checkpoint_sets_commit_and_date_and_clears_findings(five):
    run_cli(five.root, "findings", "save", "g/changed", "-", input="[]")
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed", "--today", "2026-10-09")[0] == 0
    p = page(five, "g/changed")
    assert p["source_commit"] == five.git("rev-parse", "HEAD") and p["reviewed_at"] == "2026-10-09"
    assert not (five.root / ".agentic-doc/work/g/changed").exists()


def test_checkpoint_changes_only_target_bytes(five):
    before = (five.root / "docs/wiki/catalogue.json").read_text()
    run_cli(five.root, "checkpoint", "--pages", "g/changed", "--today", "2026-10-09")
    after = (five.root / "docs/wiki/catalogue.json").read_text()
    assert diff_lines(before, after) == 2


def test_checkpoint_refuses_missing_page_file(five):
    assert run_cli(five.root, "checkpoint", "--pages", "g/missing")[0] == 2


def test_checkpoint_refusals(five):
    assert run_cli(five.root, "checkpoint", "--pages", "nope")[0] == 2
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed", "--sha", "nope")[0] == 2
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed", "--today", "9 Oct")[0] == 2


def test_checkpoint_refuses_non_canonical_catalogue(five):
    p = five.root / "docs/wiki/catalogue.json"
    p.write_text(p.read_text().replace("  ", "    "))
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed")[0] == 2


def test_concurrent_checkpoints_keep_both_updates(five):
    import subprocess
    import sys

    from conftest import SCRIPT

    for _ in range(3):
        five.git("checkout", "--", "docs/wiki/catalogue.json")
        procs = [subprocess.Popen([sys.executable, str(SCRIPT), "checkpoint", "--pages", pid, "--today", "2026-10-09"],
                                  cwd=five.root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                 for pid in ("g/changed", "g/unverified")]
        assert [p.wait() for p in procs] == [0, 0]
        assert page(five, "g/changed")["reviewed_at"] == "2026-10-09"
        assert page(five, "g/unverified")["reviewed_at"] == "2026-10-09"
    assert not (five.root / "docs/wiki/catalogue.json.lock").exists()


def test_checkpoint_refuses_crlf_catalogue(five):
    p = five.root / "docs/wiki/catalogue.json"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    before = p.read_bytes()
    assert run_cli(five.root, "checkpoint", "--pages", "g/changed")[0] == 2
    assert p.read_bytes() == before
