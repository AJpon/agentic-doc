import json
import os
import shutil

import pytest
from conftest import dump, issue_codes, load_catalogue, run_cli, set_sources
from lint_fixtures import add_to_mermaid, append, drop_frontmatter_key, remove_related_section, set_mermaid_blocks


def test_clean_page_has_no_issues(wiki):
    code, out, _ = run_cli(wiki.root, "lint", "--json")
    assert code == 0, out
    d = json.loads(out)
    assert d["pages_checked"] == 2 and d["issue_count"] == 0 and d["stale_count"] == 0


@pytest.mark.parametrize("mutate, code", [
    (drop_frontmatter_key("updated"), "frontmatter"),
    (set_mermaid_blocks(1), "mermaid-count"),
    (add_to_mermaid("style A fill:#f00"), "mermaid-style"),
    (remove_related_section, "related"),
    (append("https://github.com/o/r/blob/main/x.py#L1"), "github-url"),
    (append("`src/a.py:999`"), "cite-overflow"),
    (append("`src/a.py:0`"), "cite-overflow"),
    (append("`src/nope.py:1`"), "cite-missing"),
    (append("`:3`"), "cite-shorthand"),
    (append("`a.py:1`"), "cite-shortpath"),
    (append("[x](../nope.md)"), "link-broken"),
])
def test_each_breakage_reports_its_code(wiki, mutate, code):
    mutate(wiki)
    assert issue_codes(wiki, "g/page") == {code}


def test_missing_page(wiki):
    (wiki.root / "docs/wiki/g/page.md").unlink()
    assert issue_codes(wiki, "g/page") == {"missing-page"}


def test_shorthand_inherits_previous_path(wiki):
    append("`src/a.py:1` and `:3`")(wiki)
    assert issue_codes(wiki) == set()


def test_link_to_planned_page_is_not_broken(wiki):
    data = load_catalogue(wiki)
    data["pages"].append({**data["pages"][1], "id": "g/later", "path": "g/later.md", "title": "Later"})
    wiki.write("docs/wiki/catalogue.json", dump(data))
    append("[later](later.md)")(wiki)
    assert issue_codes(wiki, "g/page") == set()


def test_non_ascii_citation_resolves(wiki):
    wiki.write("src/日本語 ファイル.py", "1\n2\n")
    wiki.commit()
    append("`src/日本語 ファイル.py:2`")(wiki)
    assert issue_codes(wiki, "g/page", "--skip-sources") == set()


def test_cite_excluded(wiki):
    wiki.config(exclude=["src/f.py"])
    assert "cite-excluded" in issue_codes(wiki)


def test_cite_variety(wiki):
    p = wiki.root / "docs/wiki/g/page.md"
    p.write_text(p.read_text().replace(" `src/e.py:1` `src/f.py:1`", ""))
    assert issue_codes(wiki, "g/page") == {"cite-variety"}


def test_no_code_page_rules(wiki):
    wiki.config(audiences=[{"id": "contributor", "title": "C", "description": "d", "no_code": False},
                           {"id": "product", "title": "P", "description": "d", "no_code": True}])
    data = load_catalogue(wiki)
    data["pages"][0]["audience"] = ["product"]
    wiki.write("docs/wiki/catalogue.json", dump(data))
    p = wiki.root / "docs/wiki/g/page.md"
    p.write_text(p.read_text().replace("audience: [contributor]", "audience: [product]"))
    codes = issue_codes(wiki, "g/page")
    assert "no-code-leak" in codes and "cite-variety" not in codes


def test_glob_star_migration_warning(wiki):
    wiki.write("lib/x/y.py", "y\n")
    wiki.commit()
    set_sources(wiki, "g/page", ["lib/*.py"])
    wiki.commit()
    assert "source-glob-empty" in issue_codes(wiki, "g/page")


def test_untracked_and_uncommitted_sources(wiki):
    wiki.write("src/new.py", "n")
    wiki.write("src/a.py", "1\n2\n3\n4\n")
    assert {"source-untracked", "source-uncommitted"} <= issue_codes(wiki)
    assert not {"source-untracked", "source-uncommitted"} & issue_codes(wiki, "--skip-sources")


def test_related_heading_follows_language(wiki):
    wiki.config(language="ja")
    assert issue_codes(wiki, "g/page") == {"related"}


def test_stale_reported_but_not_an_issue(wiki):
    wiki.write("src/b.py", "y\n")
    wiki.commit()
    code, out, _ = run_cli(wiki.root, "lint", "--json")
    d = json.loads(out)
    assert code == 0 and d["stale_count"] == 2 and d["stale"][0]["kind"] == "changed"


def test_unknown_id_exits_2(wiki):
    assert run_cli(wiki.root, "lint", "nope")[0] == 2
    assert run_cli(wiki.root, "lint", "--citations", "nope")[0] == 2


def test_citations_output(wiki):
    out = run_cli(wiki.root, "lint", "--citations", "g/page")[1]
    assert "--- src/a.py:1-2 (3 lines)" in out and "    1| 1" in out


def test_text_output_and_exit_1(wiki):
    append("`src/nope.py:1`")(wiki)
    code, out, _ = run_cli(wiki.root, "lint")
    assert code == 1 and "g/page  [blocker] cite-missing" in out


def test_mermaid_skipped_without_node_modules(wiki):
    code, _, err = run_cli(wiki.root, "lint", "--mermaid")
    assert "warning: --mermaid skipped" in err and code == 0


@pytest.mark.skipif(not os.environ.get("AGENTIC_DOC_MERMAID_MODULES") or not shutil.which("node"),
                    reason="set AGENTIC_DOC_MERMAID_MODULES to a node_modules dir with mermaid and jsdom")
def test_mermaid_syntax_error_reported(wiki):
    (wiki.root / "docs/wiki/node_modules").symlink_to(os.environ["AGENTIC_DOC_MERMAID_MODULES"])
    assert run_cli(wiki.root, "lint", "--json", "--mermaid", "g/page")[0] == 0
    add_to_mermaid("A -->")(wiki)
    assert "mermaid-syntax" in issue_codes(wiki, "--mermaid", "g/page")
