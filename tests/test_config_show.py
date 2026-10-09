import json

from conftest import run_cli


def test_show_resolves_context_and_strings(repo):
    repo.write("AGENTS.md", "agent notes\n")
    repo.config(language="ja", instructions=[{"text": "rule"}])
    code, out, _ = run_cli(repo.root, "config", "show")
    d = json.loads(out)
    assert code == 0
    assert d["wiki_dir"] == "docs/wiki" and d["catalogue"] == "docs/wiki/catalogue.json"
    assert d["catalogue_exists"] is False
    assert d["context"] == [{"source": "AGENTS.md", "text": "agent notes\n"}]
    assert d["instructions"] == [{"source": "text", "text": "rule"}]
    assert d["strings"] == {"related_heading": "## 関連ページ", "unverified_marker": "(未確認: {what})"}
    assert d["language"] == "ja" and d["max_pages"] == 24 and d["post_commands"] == []
    assert [a["id"] for a in d["audiences"]] == ["contributor", "agent"]


def test_show_refuses_missing_context_file(repo):
    repo.config(context=[{"file": "nope.md"}])
    code, _, err = run_cli(repo.root, "config", "show")
    assert code == 2 and "nope.md" in err


def test_show_without_config_is_2(repo):
    assert run_cli(repo.root, "config", "show")[0] == 2
