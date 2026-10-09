import json

from adoc import config, workdir
from conftest import run_cli

F1 = '{"severity": "major", "location": "l", "problem": "p", "fix": "f"}'


def test_save_creates_self_ignoring_dir(five):
    cfg = config.load(five.root)
    workdir.save(cfg, "g/changed", [{"severity": "major"}], "body")
    assert (five.root / ".agentic-doc/work/.gitignore").read_text() == "*\n"
    assert five.git("status", "--porcelain") == ""


def test_load_returns_saved_findings(five):
    cfg = config.load(five.root)
    workdir.save(cfg, "g/changed", [{"x": 1}], "body")
    assert workdir.load(cfg, "g/changed", "body") == [{"x": 1}]


def test_load_discards_on_hash_mismatch(five):
    cfg = config.load(five.root)
    workdir.save(cfg, "g/changed", [{"x": 1}], "body")
    assert workdir.load(cfg, "g/changed", "edited") is None
    assert not workdir.findings_path(cfg, "g/changed").exists()


def test_existing_gitignore_not_overwritten(five):
    five.write(".agentic-doc/work/.gitignore", "custom\n")
    cfg = config.load(five.root)
    workdir.save(cfg, "g/changed", [], "b")
    assert (five.root / ".agentic-doc/work/.gitignore").read_text() == "custom\n"


def test_status_shows_pending_count(five):
    run_cli(five.root, "findings", "save", "g/unverified", "-", input=f'[{F1},{F1}]')
    d = json.loads(run_cli(five.root, "status", "--json")[1])
    assert next(p for p in d["pages"] if p["id"] == "g/unverified")["pending"] == 2


def test_status_does_not_delete_stale_findings(five):
    run_cli(five.root, "findings", "save", "g/unverified", "-", input=f'[{F1}]')
    five.write("docs/wiki/g/unverified.md", "edited by hand")
    d = json.loads(run_cli(five.root, "status", "--json")[1])
    assert next(p for p in d["pages"] if p["id"] == "g/unverified")["pending"] == 0
    assert (five.root / ".agentic-doc/work/g/unverified/findings.json").exists()


def test_findings_show_and_clear(five):
    run_cli(five.root, "findings", "save", "g/changed", "-", input=f'[{F1}]')
    assert json.loads(run_cli(five.root, "findings", "show", "g/changed")[1]) == [json.loads(F1)]
    assert run_cli(five.root, "findings", "clear", "g/changed")[0] == 0
    assert json.loads(run_cli(five.root, "findings", "show", "g/changed")[1]) is None


def test_findings_show_discards_after_hand_edit(five):
    run_cli(five.root, "findings", "save", "g/changed", "-", input=f'[{F1}]')
    five.write("docs/wiki/g/changed.md", "edited")
    assert json.loads(run_cli(five.root, "findings", "show", "g/changed")[1]) is None
    assert not (five.root / ".agentic-doc/work/g/changed/findings.json").exists()


def test_findings_save_from_file(five):
    five.write("f.json", f'[{F1}]')
    assert run_cli(five.root, "findings", "save", "g/changed", "f.json")[0] == 0
    assert json.loads(run_cli(five.root, "findings", "show", "g/changed")[1]) == [json.loads(F1)]


def test_findings_errors(five):
    assert run_cli(five.root, "findings", "show", "nope")[0] == 2
    assert run_cli(five.root, "findings", "save", "g/changed", "-", input="{}")[0] == 2
    assert run_cli(five.root, "findings", "save", "g/changed", "-", input="not json")[0] == 2
    assert run_cli(five.root, "findings", "save", "g/missing", "-", input="[]")[0] == 2


def test_findings_save_reads_stdin_as_utf8(five):
    import os
    import subprocess
    import sys

    from conftest import SCRIPT

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    r = subprocess.run([sys.executable, str(SCRIPT), "findings", "save", "g/changed", "-"], cwd=five.root,
                       input='[{"severity": "minor", "location": "l", "problem": "日本語", "fix": "f"}]'.encode(), capture_output=True, env=env, check=False)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert json.loads(run_cli(five.root, "findings", "show", "g/changed")[1])[0]["problem"] == "日本語"


def test_findings_save_missing_file_exits_2(five):
    assert run_cli(five.root, "findings", "save", "g/changed", "nope.json")[0] == 2


def test_save_rejects_findings_off_schema(five):
    bad = json.dumps([{"severity": "fatal", "location": "x", "problem": "p", "fix": "f"}])
    code, _, err = run_cli(five.root, "findings", "save", "g/changed", "-", input=bad)
    assert code == 2 and "/0/severity" in err
