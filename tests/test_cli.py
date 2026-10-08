import subprocess

import agentic_doc
from adoc.errors import Refused
from agentic_doc import COMMANDS, Command
from conftest import SCRIPT, run_cli


def test_help_lists_every_command(tmp_path):
    code, out, _ = run_cli(tmp_path, "--help")
    assert code == 0
    for name in COMMANDS:
        assert name in out


def test_unknown_command_exits_2(tmp_path):
    code, _, _ = run_cli(tmp_path, "nope")
    assert code == 2


def test_refused_exits_2_with_message(monkeypatch, capsys):
    def boom(args):
        raise Refused("boom")

    monkeypatch.setitem(COMMANDS, "_boom", Command(help="boom", add_args=lambda p: None, run=boom))
    assert agentic_doc.main(["_boom"]) == 2
    assert "refused: boom" in capsys.readouterr().err


def test_runs_under_uv_script_ignoring_target_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\nversion="0"\ndependencies=["nonexistent-pkg-zzz"]\n')
    (tmp_path / "uv.toml").write_text('index-url = "http://127.0.0.1:9/"\n')
    r = subprocess.run(["uv", "run", "--script", str(SCRIPT), "--help"], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
