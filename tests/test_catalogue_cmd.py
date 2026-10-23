import json

import pytest
from conftest import dump, run_cli

WORK = ".agentic-doc/work/outline/catalogue.json"


def _page(pid: str, **kw) -> dict:
    p = {"id": pid, "path": pid + ".md", "title": pid, "audience": ["contributor"], "brief": "b",
         "sources": ["src/*.py"], "related": [], "source_commit": None, "reviewed_at": None}
    p.update(kw)
    return p


GOOD = {
    "version": 1,
    "chapters": [{"id": "a", "title": "A", "description": "d"}, {"id": "b", "title": "B", "description": "d"}],
    "pages": [_page("a/one", related=["a/two"]), _page("a/two"), _page("b/three")],
}


@pytest.fixture
def good(repo):
    repo.write("src/a.py", "a\n")
    repo.commit()
    repo.config()
    repo.write(WORK, dump(GOOD))
    return repo


def mutate(r, fn) -> None:
    data = json.loads((r.root / WORK).read_text(encoding="utf-8"))
    fn(data)
    r.write(WORK, dump(data))


def codes(out: str) -> set[str]:
    return {i["code"] for i in json.loads(out)}


def check(r, *extra) -> tuple[int, set[str]]:
    code, out, _ = run_cli(r.root, "catalogue", "check", WORK, "--json", *extra)
    return code, codes(out)


def assert_error(r, code_name: str) -> None:
    code, found = check(r)
    assert code_name in found and code == 1


def test_good_catalogue_passes(good):
    assert run_cli(good.root, "catalogue", "check", WORK)[0] == 0


def test_schema(good):
    mutate(good, lambda d: d["pages"][0].pop("brief"))
    assert_error(good, "schema")


def test_duplicate_id(good):
    mutate(good, lambda d: d["pages"].append(_page("a/one")))
    assert_error(good, "duplicate-id")


def test_id_form(good):
    mutate(good, lambda d: d["pages"][2].update(id="b/x/y", path="b/x/y.md"))
    assert_error(good, "id-form")


def test_id_chapter(good):
    mutate(good, lambda d: d["pages"][2].update(id="c/three", path="c/three.md"))
    assert_error(good, "id-chapter")


def test_id_path(good):
    mutate(good, lambda d: d["pages"][0].update(path="a/01-one.md"))
    assert_error(good, "id-path")


def test_chapter_count(good):
    def f(d):
        d["chapters"] = [{"id": f"c{i}", "title": "C", "description": "d"} for i in range(7)]
        d["pages"] = [_page(f"c{i}/p") for i in range(7)]
    mutate(good, f)
    assert_error(good, "chapter-count")


def test_chapter_size(good):
    mutate(good, lambda d: d["pages"].extend(_page(f"a/x{i}") for i in range(7)))
    assert_error(good, "chapter-size")


def test_page_count(good):
    good.config(max_pages=2)
    assert_error(good, "page-count")


def test_audience_unknown(good):
    mutate(good, lambda d: d["pages"][0].update(audience=["product"]))
    assert_error(good, "audience-unknown")


def test_related_unknown(good):
    mutate(good, lambda d: d["pages"][0].update(related=["z/none"]))
    assert_error(good, "related-unknown")


def test_related_self(good):
    mutate(good, lambda d: d["pages"][0].update(related=["a/one"]))
    code, found = check(good)
    assert "related-self" in found and code == 0


def test_source_glob_empty(good):
    mutate(good, lambda d: d["pages"][0].update(sources=["src/**/*.rs"]))
    assert_error(good, "source-glob-empty")


def test_single_nested_source_with_exclude(good):
    good.write("a/b/c.py", "m\n")
    good.commit()
    good.config(exclude=["zzz/**"])
    mutate(good, lambda d: d["pages"][0].update(sources=["a/b/c.py"]))
    code, found = check(good)
    assert "source-glob-empty" not in found and code == 0


def test_chapter_empty(good):
    mutate(good, lambda d: d["chapters"].append({"id": "c", "title": "C", "description": "d"}))
    code, found = check(good)
    assert "chapter-empty" in found and code == 0


def test_chapter_order(good):
    mutate(good, lambda d: d["pages"].insert(1, d["pages"].pop(2)))
    code, found = check(good)
    assert "chapter-order" in found and code == 0


def test_install_writes_canonical_and_nulls_commits(good):
    mutate(good, lambda d: d["pages"][0].update(source_commit="a" * 40, reviewed_at="2026-01-01"))
    code, out, _ = run_cli(good.root, "catalogue", "install", WORK)
    assert code == 0 and out.strip() == "docs/wiki/catalogue.json"
    text = (good.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8")
    assert text == dump(json.loads(text))
    assert all(p["source_commit"] is None and p["reviewed_at"] is None for p in json.loads(text)["pages"])


def test_install_refuses_existing_without_force(good):
    run_cli(good.root, "catalogue", "install", WORK)
    code, _, err = run_cli(good.root, "catalogue", "install", WORK)
    assert code == 2 and "--force" in err
    assert run_cli(good.root, "catalogue", "install", WORK, "--force")[0] == 0


def test_install_does_not_write_invalid(good):
    mutate(good, lambda d: d["pages"][0].update(path="wrong.md"))
    assert run_cli(good.root, "catalogue", "install", WORK)[0] == 1
    assert not (good.root / "docs/wiki/catalogue.json").exists()


def test_check_default_catalogue_reports_format(good):
    run_cli(good.root, "catalogue", "install", WORK)
    p = good.root / "docs/wiki/catalogue.json"
    p.write_text(p.read_text(encoding="utf-8").replace("  ", "    "), encoding="utf-8")
    assert "format" in codes(run_cli(good.root, "catalogue", "check", "--json")[1])


def test_check_missing_or_broken_file_is_2(good):
    assert run_cli(good.root, "catalogue", "check", "nope.json")[0] == 2
    good.write(WORK, "{not json")
    assert run_cli(good.root, "catalogue", "check", WORK)[0] == 2


OLD = "docs/wiki/_catalogue.json"


@pytest.fixture
def legacy(wiki):
    """wiki フィクスチャのカタログを、fbx-view の旧形式（chapters 無し、余分なキー付き）に置き換える."""
    data = json.loads((wiki.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8"))
    wiki.write(OLD, dump({"version": 1, "language": "en", "citation_style": "local", "pages": data["pages"]}))
    (wiki.root / "docs/wiki/catalogue.json").unlink()
    wiki.commit()
    return wiki


def migrate(r, *extra) -> tuple[int, str, str]:
    return run_cli(r.root, "catalogue", "migrate", OLD, *extra)


def test_migrate_builds_chapters_from_ids(legacy):
    code, _, err = migrate(legacy)
    assert code == 0, err
    data = json.loads((legacy.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8"))
    assert data["chapters"] == [{"id": "g", "title": "g", "description": ""}]
    assert "language" not in data and "citation_style" not in data
    assert run_cli(legacy.root, "catalogue", "check")[0] == 0


def test_migrate_keeps_source_commit(wiki):
    _, before, _ = run_cli(wiki.root, "status", "--json")
    data = json.loads((wiki.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8"))
    wiki.write(OLD, dump({"version": 1, "language": "en", "pages": data["pages"]}))
    (wiki.root / "docs/wiki/catalogue.json").unlink()
    wiki.commit()
    assert migrate(wiki)[0] == 0
    wiki.commit()
    _, after, _ = run_cli(wiki.root, "status", "--json")
    state = lambda s: [(p["id"], p["state"]) for p in json.loads(s)["pages"]]
    assert state(after) == state(before)
    assert [p["source_commit"] for p in json.loads((wiki.root / "docs/wiki/catalogue.json").read_text(
        encoding="utf-8"))["pages"]] == [p["source_commit"] for p in data["pages"]]


def test_migrate_takes_title_from_readme(legacy):
    legacy.write("docs/wiki/README.md", "intro\n\n# My Wiki\n\n## Chapter\n")
    assert migrate(legacy)[0] == 0
    assert json.loads((legacy.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8"))["title"] == "My Wiki"


def test_migrate_refuses_existing_without_force(legacy):
    legacy.write("docs/wiki/catalogue.json", "keep\n")
    code, _, err = migrate(legacy)
    assert code == 2 and "already exists" in err
    assert (legacy.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8") == "keep\n"
    assert (legacy.root / OLD).exists()
    assert migrate(legacy, "--force")[0] == 0


def test_migrate_reports_errors_without_writing(legacy):
    data = json.loads((legacy.root / OLD).read_text(encoding="utf-8"))
    data["pages"][0]["related"] = ["g/nowhere"]
    legacy.write(OLD, dump(data))
    code, out, _ = migrate(legacy)
    assert code == 1 and "related-unknown" in out
    assert not (legacy.root / "docs/wiki/catalogue.json").exists()
    assert (legacy.root / OLD).exists()


def test_migrate_removes_old_file(legacy):
    code, out, _ = migrate(legacy)
    assert code == 0 and "docs/wiki/catalogue.json" in out
    assert not (legacy.root / OLD).exists()


def test_migrate_refuses_a_current_format_catalogue(wiki):
    data = json.loads((wiki.root / "docs/wiki/catalogue.json").read_text(encoding="utf-8"))
    data["chapters"][0]["title"] = "Real Title"
    wiki.write(OLD, dump(data))
    (wiki.root / "docs/wiki/catalogue.json").unlink()
    wiki.commit()
    code, _, err = migrate(wiki)
    assert code == 2 and "chapters" in err
    assert (wiki.root / OLD).exists() and not (wiki.root / "docs/wiki/catalogue.json").exists()


def test_migrate_warns_when_sources_hit_only_excluded_files(legacy):
    legacy.write("vendor/x.py", "x\n")
    data = json.loads((legacy.root / OLD).read_text(encoding="utf-8"))
    data["pages"][0]["sources"] = ["vendor/*.py"]
    legacy.write(OLD, dump(data))
    legacy.config(exclude=["vendor/**"])
    legacy.commit()
    code, out, _ = migrate(legacy, "--json")
    assert code == 0, out
    assert any("source-glob-empty" in w for w in json.loads(out)["warnings"])
    assert (legacy.root / "docs/wiki/catalogue.json").exists()


def test_migrate_warns_language_mismatch(legacy):
    legacy.config(language="ja")
    code, out, _ = migrate(legacy, "--json")
    result = json.loads(out)
    assert code == 0
    assert any("language" in w for w in result["warnings"])
    assert result["chapters"] == 1 and result["pages"] == 2


def test_duplicate_chapter(good):
    mutate(good, lambda d: d["chapters"].append({"id": "a", "title": "A2", "description": "d"}))
    assert_error(good, "duplicate-chapter")


@pytest.mark.parametrize("bad", ["A/one", "a/One", "a/on e", "a/_x", "a/-x"])
def test_id_chars(good, bad):
    mutate(good, lambda d: d["pages"].append(_page(bad, path=bad + ".md")))
    assert_error(good, "id-chars")


def test_install_creates_work_gitignore(good):
    good.write("other/catalogue.json", dump(GOOD))
    assert run_cli(good.root, "catalogue", "install", "other/catalogue.json")[0] == 0
    assert (good.root / ".agentic-doc/work/.gitignore").is_file()
