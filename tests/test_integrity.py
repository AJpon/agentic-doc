"""リポジトリの構成どうしの整合を固定する回帰テスト."""

import json
from pathlib import Path

from agentic_doc import COMMANDS
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_manifests_agree():
    a = read_json("plugin.json")
    b = read_json(".claude-plugin/plugin.json")
    m = read_json(".claude-plugin/marketplace.json")["plugins"][0]
    for k in ["name", "version", "description"]:
        assert a[k] == b[k] == m[k]


def test_schemas_are_valid_json_schema():
    paths = list((ROOT / "skills/wiki/schemas").glob("*.json"))
    assert len(paths) >= 2
    for p in paths:
        Draft202012Validator.check_schema(json.loads(p.read_text(encoding="utf-8")))


def test_gitignore_template_is_star():
    assert (ROOT / "skills/wiki/assets/work/.gitignore.in").read_text(encoding="utf-8") == "*\n"


def test_pep723_block_declares_runtime():
    head = (ROOT / "skills/wiki/scripts/agentic_doc.py").read_text(encoding="utf-8").split("# ///")[1]
    assert 'requires-python = ">=3.11"' in head and "pyyaml>=6" in head and "jsonschema>=4.23" in head


def test_every_command_has_help():
    assert set(COMMANDS) == {"config", "status", "plan", "checkpoint", "stamp", "findings", "cache", "lint", "toc", "post", "catalogue",
                             "report", "unverify"}
    for c in COMMANDS.values():
        assert c.help and len(c.help) < 100


def test_i18n_tables_have_same_keys():
    from adoc.i18n import STRINGS

    assert set(STRINGS["ja"]) == set(STRINGS["en"])
