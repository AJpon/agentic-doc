import pytest
from adoc import config
from adoc.errors import Refused
from conftest import run_cli


def test_load_applies_defaults(repo):
    repo.config()
    c = config.load(repo.root)
    assert c.wiki_dir == repo.root / "docs/wiki"
    assert c.catalogue == repo.root / "docs/wiki/catalogue.json"
    assert c.language == "en" and c.max_pages == 24
    assert [a["id"] for a in c.audiences] == ["contributor", "agent"]


def test_catalogue_default_follows_wiki_dir(repo):
    repo.config(wiki_dir="wiki")
    assert config.load(repo.root).catalogue == repo.root / "wiki/catalogue.json"


def test_context_default_uses_existing_files(repo):
    repo.write("README.md", "r")
    repo.write("AGENTS.md", "a")
    repo.config()
    assert config.load(repo.root).context == [{"file": "README.md"}, {"file": "AGENTS.md"}]


def test_missing_config_refused(repo):
    with pytest.raises(Refused, match="run setup"):
        config.load(repo.root)


def test_bare_string_instruction_rejected(repo):
    repo.config(instructions=["do x"])
    with pytest.raises(Refused, match="/instructions/0"):
        config.load(repo.root)


def test_invalid_json_refused(repo):
    repo.write(".agentic-doc.config.json", "{")
    with pytest.raises(Refused, match="JSON"):
        config.load(repo.root)


def test_check_reports_each_code(repo):
    repo.config(context=[{"file": "nope.md"}], post_commands=["prettier"], exclude=["zzz/**"],
                audiences=[{"id": "a", "title": "A", "description": "d", "no_code": False}] * 2)
    codes = {i["code"]: i["severity"] for i in config.check(repo.root)}
    assert codes == {"file-missing": "error", "post-no-files": "error",
                     "exclude-empty": "warning", "audience-duplicate": "error"}


def test_cli_config_check_exit_codes(repo):
    assert run_cli(repo.root, "config", "check")[0] == 2
    repo.config()
    assert run_cli(repo.root, "config", "check")[0] == 0
    repo.config(post_commands=["x"])
    assert run_cli(repo.root, "config", "check")[0] == 1
