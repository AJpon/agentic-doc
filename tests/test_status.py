import json

from conftest import run_cli, set_sources


def test_status_json(five):
    code, out, _ = run_cli(five.root, "status", "--json")
    d = json.loads(out)
    assert code == 0 and d["counts"] == {"fresh": 1, "changed": 1, "unresolved": 1, "unverified": 1, "missing": 1}
    assert any("stamp --pages g/unresolved" in n for n in d["next"])
    assert len(d["head"]) == 40


def test_status_filters(five):
    d = json.loads(run_cli(five.root, "status", "--json", "--state", "changed")[1])
    assert [p["id"] for p in d["pages"]] == ["g/changed"]
    d = json.loads(run_cli(five.root, "status", "--json", "g/fresh", "g/missing")[1])
    assert [p["id"] for p in d["pages"]] == ["g/fresh", "g/missing"]


def test_status_unknown_id_exits_2(five):
    assert run_cli(five.root, "status", "nope")[0] == 2


def test_status_warns_uncommitted_and_untracked(five):
    set_sources(five, "g/fresh", ["src/**"])
    five.commit()
    five.write("src/a.py", "dirty")
    five.write("src/new.py", "n")
    w = json.loads(run_cli(five.root, "status", "--json")[1])["warnings"]
    assert w == {"uncommitted": ["src/a.py"], "untracked": ["src/new.py"]}


def test_status_text_in_japanese(five):
    five.config(language="ja")
    out = run_cli(five.root, "status")[1]
    assert "変更あり" in out and "解決不能" in out and "次の操作" in out


def test_status_text_in_english(five):
    out = run_cli(five.root, "status")[1]
    assert "changed" in out and "src/b.py" in out and "Next" in out


def test_status_outside_repo_exits_2(tmp_path):
    assert run_cli(tmp_path, "status")[0] == 2


def test_all_fresh_says_nothing_to_do(repo):
    repo.write("src/a.py", "a")
    base = repo.commit()
    repo.write("docs/wiki/g/p.md", "x")
    repo.config()
    repo.catalogue([{"id": "g/p", "sources": ["src/a.py"], "source_commit": base}])
    repo.commit()
    d = json.loads(run_cli(repo.root, "status", "--json")[1])
    assert d["counts"]["fresh"] == 1 and d["next"] == ["nothing to do"]
