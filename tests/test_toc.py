from conftest import dump, issue_codes, load_catalogue, page, read_page, run_cli


def readme(r) -> str:
    return (r.root / "docs/wiki/README.md").read_text(encoding="utf-8")


def test_toc_lists_audiences_and_chapters(wiki2):
    assert run_cli(wiki2.root, "toc")[0] == 0
    t = readme(wiki2)
    assert t.startswith("# Wiki\n")
    assert t.index("### Contributors") < t.index("### AI agents")
    assert t.index("### Chapter A") < t.index("### Chapter B")
    assert "(not yet written)" in t and "| Page | Summary |" in t
    assert "| [One](a/one.md) | First page. |" in t
    assert "Third \\| page" in t
    contributors = t[t.index("### Contributors"):t.index("### AI agents")]
    assert "1. [One](a/one.md)" in contributors and "2. [Three](b/three.md)" in contributors


def test_toc_uses_catalogue_title(wiki2):
    data = load_catalogue(wiki2)
    data = {"version": 1, "title": "My Wiki", **{k: v for k, v in data.items() if k != "version"}}
    wiki2.write("docs/wiki/catalogue.json", dump(data))
    run_cli(wiki2.root, "toc")
    assert readme(wiki2).startswith("# My Wiki\n")


def test_toc_japanese(wiki2):
    wiki2.config(language="ja")
    run_cli(wiki2.root, "toc")
    t = readme(wiki2)
    assert "（未生成）" in t and "| 二つ目。 |" in t


def test_related_made_symmetric(wiki2):
    run_cli(wiki2.root, "toc")
    assert "a/one" in page(wiki2, "b/two")["related"]


def test_page_frontmatter_and_related_section_synced(wiki2):
    data = load_catalogue(wiki2)
    data["pages"][0]["title"] = "New title"
    data["pages"][0]["reviewed_at"] = "2026-10-09"
    wiki2.write("docs/wiki/catalogue.json", dump(data))
    run_cli(wiki2.root, "toc")
    fm, body = read_page(wiki2, "a/one")
    assert fm["title"] == "New title" and str(fm["updated"]) == "2026-10-09"
    assert fm["audience"] == ["contributor"] and fm["description"] == "Describes the first page."
    assert body.rstrip().endswith("## Related pages\n\n- [Two](../b/two.md)")
    assert "- stale" not in body


def test_related_section_added_when_missing(wiki2):
    run_cli(wiki2.root, "toc")
    fm, body = read_page(wiki2, "b/two")
    assert body.rstrip().endswith("## Related pages\n\n- [New title](../a/one.md)".replace("New title", "One"))
    assert str(fm["updated"]) == "2026-01-01"


def test_title_with_quotes_and_hash_roundtrips(wiki2):
    data = load_catalogue(wiki2)
    data["pages"][0]["title"] = 'He said "x" # y \\ z'
    wiki2.write("docs/wiki/catalogue.json", dump(data))
    run_cli(wiki2.root, "toc")
    assert read_page(wiki2, "a/one")[0]["title"] == 'He said "x" # y \\ z'
    assert "frontmatter" not in issue_codes(wiki2, "a/one")


def test_toc_reports_changed_files_and_is_idempotent(wiki2):
    out = run_cli(wiki2.root, "toc")[1].split()
    assert set(out) == {"docs/wiki/README.md", "docs/wiki/catalogue.json", "docs/wiki/a/one.md",
                        "docs/wiki/b/two.md"}
    assert run_cli(wiki2.root, "toc")[1].strip() == ""


def test_toc_dry_run_writes_nothing(wiki2):
    out = run_cli(wiki2.root, "toc", "--dry-run")[1]
    assert "docs/wiki/README.md" in out
    assert not (wiki2.root / "docs/wiki/README.md").exists()
    assert wiki2.git("status", "--porcelain") == ""
