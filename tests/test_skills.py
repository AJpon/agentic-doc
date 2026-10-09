"""スキル本文・参照文書・スキーマの整合テスト."""

import argparse
import json
import re
from pathlib import Path

from agentic_doc import build_parser

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "skills/wiki"
REFS = WIKI / "references"
SCHEMAS = WIKI / "schemas"
NOT_PHASE_SCHEMAS = {"config", "catalogue", "findings"}

# スクリプトの呼び出し。wiki は "<SKILL_DIR>/scripts/..."、wiki-setup は "<SKILL_DIR>/../wiki/scripts/..."
CALL = re.compile(r'"<SKILL_DIR>/(?:\.\./wiki/)?scripts/agentic_doc\.py"(?P<rest>[^`\n]*)')
ANY_CALL = re.compile(r"agentic_doc\.py")
REF_LINK = re.compile(r"<SKILL_DIR>/((?:\.\./wiki/)?(?:references|schemas)/[\w.-]+)")


def skill_docs() -> list[Path]:
    return sorted((ROOT / "skills").rglob("*.md"))


def parser_options() -> dict[str, tuple[set[str], set[str]]]:
    """'cmd' / 'cmd sub' → (オプション文字列, サブコマンド名)."""
    out: dict[str, tuple[set[str], set[str]]] = {}

    def walk(name: str, p: argparse.ArgumentParser) -> None:
        opts = {s for a in p._actions for s in a.option_strings}
        subs = {}
        for a in p._actions:
            if isinstance(a, argparse._SubParsersAction):
                subs = a.choices
        out[name] = (opts, set(subs))
        for sub, sp in subs.items():
            walk(f"{name} {sub}".strip(), sp)

    walk("", build_parser())
    return out


def test_reference_script_calls_are_quoted_and_exist():
    table = parser_options()
    commands = table[""][1]
    for doc in skill_docs():
        text = doc.read_text(encoding="utf-8")
        assert len(ANY_CALL.findall(text)) == len(CALL.findall(text)), f"{doc}: unquoted or misplaced script path"
        for m in CALL.finditer(text):
            words = m.group("rest").split()
            if words and words[0] == "<command>":  # 呼び出し方の書式の説明
                continue
            if words and words[0].startswith("--"):  # トップレベルのオプション（--help）
                assert words[0] in table[""][0], f"{doc}: unknown option {words[0]}"
                continue
            assert words and words[0] in commands, f"{doc}: unknown command in {m.group(0)!r}"
            name = words[0]
            if len(words) > 1 and words[1] in table[name][1]:
                name = f"{name} {words[1]}"
            for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", m.group("rest")):
                assert flag in table[name][0], f"{doc}: {name} has no option {flag}"


def test_reference_links_resolve():
    for doc in skill_docs():
        skill_dir = ROOT / "skills" / doc.relative_to(ROOT / "skills").parts[0]
        for rel in REF_LINK.findall(doc.read_text(encoding="utf-8")):
            assert (skill_dir / rel).resolve().is_file(), f"{doc}: {rel} does not exist"


def test_each_reference_has_inputs_and_output_sections():
    for p in REFS.glob("*.md"):
        if p.name in {"overview.md", "common.md", "writing-rules.md"} or p.name.startswith("run-"):
            continue
        text = p.read_text(encoding="utf-8")
        assert "## Inputs" in text and "## Output" in text, p.name


def test_output_sections_name_existing_schemas():
    for p in REFS.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if "## Output" not in text:
            continue
        out = text.split("## Output", 1)[1]
        assert re.search(r"schemas/[\w-]+\.schema\.json", out), f"{p.name}: Output names no schema"


def test_phase_schemas_are_workflow_compatible():
    for p in SCHEMAS.glob("*.schema.json"):
        if p.name.removesuffix(".schema.json") in NOT_PHASE_SCHEMAS:
            continue
        s = json.loads(p.read_text(encoding="utf-8"))
        assert s["type"] == "object" and set(s.get("required", [])) <= set(s["properties"]), p.name


def test_phase_schemas_share_issue_definition():
    issue = json.loads((SCHEMAS / "findings.schema.json").read_text(encoding="utf-8"))["items"]
    for name in ["verdict", "drift"]:
        s = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
        assert s["$defs"]["issue"] == issue, name


def test_writing_rules_cover_spec_chapter_9():
    text = (REFS / "writing-rules.md").read_text(encoding="utf-8")
    for needle in ["title", "description", "audience", "updated", "style", "classDef", "fill:", "stroke:",
                   "<br/>", "5", "related_heading", "unverified_marker", "no_code"]:
        assert needle in text, needle


def test_run_docs_reference_every_phase_doc():
    expected = {
        "run-sync.md": ["sync-research.md", "sync-write.md", "verify-citation.md", "verify-claim.md", "sync-fix.md",
                        "sync-integrate.md"],
        "run-outline.md": ["outline-areas.md", "outline-survey.md", "outline-propose.md", "outline-merge.md"],
        "run-audit.md": ["audit-drift.md", "agentic_doc.py\" report"],
    }
    for doc, needles in expected.items():
        text = (REFS / doc).read_text(encoding="utf-8")
        for n in needles:
            assert n in text, f"{doc}: {n}"


def test_overview_lists_all_modes():
    text = (REFS / "overview.md").read_text(encoding="utf-8")
    for needle in ["help", "setup", "outline", "sync", "status", "audit", "stamp",
                   "missing", "unverified", "unresolved", "changed", "fresh"]:
        assert f"`{needle}`" in text, needle


def test_skill_frontmatter():
    import yaml

    for name in ["wiki", "wiki-setup"]:
        fm = yaml.safe_load((ROOT / f"skills/{name}/SKILL.md").read_text(encoding="utf-8").split("---")[1])
        assert fm["name"] == name and 20 < len(fm["description"]) < 1024


def test_wiki_skill_routes_every_mode_and_both_harnesses():
    text = (WIKI / "SKILL.md").read_text(encoding="utf-8")
    for needle in ["agentic-doc:wiki-run", "${CLAUDE_PLUGIN_ROOT}", "run-outline.md", "run-sync.md", "run-audit.md",
                   "overview.md", 'report --drift -', "config check", "wiki-setup"]:
        assert needle in text, needle
    assert text.count("${CLAUDE_PLUGIN_ROOT}") == 1


def test_setup_skill_points_to_wiki_scripts():
    text = (ROOT / "skills/wiki-setup/SKILL.md").read_text(encoding="utf-8")
    assert "references/setup.md" in text
    setup = (ROOT / "skills/wiki-setup/references/setup.md").read_text(encoding="utf-8")
    for needle in ['"<SKILL_DIR>/../wiki/scripts/agentic_doc.py" config check', "$schema", "_catalogue.json",
                   "source-glob-empty", "cite-excluded"]:
        assert needle in setup, needle


def test_plugin_root_token_not_used():
    for p in (ROOT / "skills").rglob("*.md"):
        assert "${PLUGIN_ROOT}" not in p.read_text(encoding="utf-8"), p
