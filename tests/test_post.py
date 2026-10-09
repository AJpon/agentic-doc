import json
import sys

from adoc import config
from conftest import run_cli

PY = sys.executable.replace("\\", "/")  # Windows でも shlex で壊れないようにスラッシュにする


def test_files_expand_one_arg_each_without_shell(repo):
    code = "import sys; sys.stdout.reconfigure(encoding='utf-8'); print(sys.argv[1:])"
    repo.config(post_commands=[f'"{PY}" -c "{code}" {{files}}'])
    d = json.loads(run_cli(repo.root, "post", "--json", "a b.md", "日本.md", "$(x).md")[1])
    assert d[0]["stdout"].strip() == "['a b.md', '日本.md', '$(x).md']"
    assert d[0]["code"] == 0


def test_runs_in_repo_root(repo):
    repo.config(post_commands=[f'"{PY}" -c "import os; print(os.getcwd())" {{files}}'])
    sub = repo.root / "sub"
    sub.mkdir()
    d = json.loads(run_cli(repo.root, "post", "--json", "x.md")[1])
    assert d[0]["stdout"].strip() == str(repo.root.resolve())


def test_failure_continues_and_exits_1(repo):
    repo.config(post_commands=[f"\"{PY}\" -c 'import sys; sys.exit(3)' {{files}}",
                               f"\"{PY}\" -c 'print(1)' {{files}}"])
    code, out, _ = run_cli(repo.root, "post", "--json", "x.md")
    d = json.loads(out)
    assert code == 1 and [r["code"] for r in d] == [3, 0]


def test_text_output(repo):
    repo.config(post_commands=[f"\"{PY}\" -c 'print(42)' {{files}}"])
    code, out, _ = run_cli(repo.root, "post", "x.md")
    assert code == 0 and out.startswith("$ ") and "42" in out


def test_missing_command_is_127(repo):
    repo.config(post_commands=["no-such-cmd-zzz {files}"])
    code, out, _ = run_cli(repo.root, "post", "--json", "x.md")
    assert code == 1 and json.loads(out)[0]["code"] == 127


def test_embedded_placeholder_refused(repo):
    repo.config(post_commands=["fmt --x={files}"])
    assert run_cli(repo.root, "post", "x.md")[0] == 2


def test_config_check_warns_backslash(repo):
    repo.config(post_commands=["C:\\tools\\fmt.exe {files}"])
    issues = config.check(repo.root)
    assert any(i["code"] == "post-backslash" and i["severity"] == "warning" for i in issues)


def test_no_commands_is_noop(repo):
    repo.config()
    assert run_cli(repo.root, "post", "x.md")[0] == 0
