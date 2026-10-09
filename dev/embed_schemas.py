"""skills/wiki/schemas のフェーズ出力スキーマを wiki-run.js の生成ブロックに埋め込む（開発用）.

Workflow はファイルを読めないため、スキーマの正は schemas/ に置き、Workflow にはその写しを埋め込む。
埋め込むときは $schema / title を外し、#/$defs への $ref を展開する（構造化出力に渡す形にするため）。

使い方（リポジトリのルートで）:
    uv run python dev/embed_schemas.py           生成ブロックを書き換える
    uv run python dev/embed_schemas.py --check   書き換えずに一致を確かめる（不一致なら 1）
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "skills" / "wiki" / "schemas"
WORKFLOW = ROOT / "com.anthropic.claude-code" / "workflows" / "wiki-run.js"
SKIP = {"config", "catalogue", "findings"}
BEGIN = "// BEGIN GENERATED SCHEMAS (dev/embed_schemas.py)"
END = "// END GENERATED SCHEMAS"


def _inline(node, defs: dict):
    """#/$defs/<name> への $ref を展開し、$schema・title・$defs を外す."""
    if isinstance(node, list):
        return [_inline(n, defs) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _inline(defs[node["$ref"].removeprefix("#/$defs/")], defs)
    return {k: _inline(v, defs) for k, v in node.items() if k not in {"$schema", "title", "$defs"}}


def block() -> str:
    data = {}
    for p in sorted(SCHEMAS.glob("*.schema.json")):
        name = p.name.removesuffix(".schema.json")
        if name in SKIP:
            continue
        schema = json.loads(p.read_text(encoding="utf-8"))
        data[name] = _inline(schema, schema.get("$defs", {}))
    return f"{BEGIN}\nconst SCHEMAS = {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n{END}"


def main(argv: list[str]) -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END) + len(END)
    new = text[:start] + block() + text[end:]
    if "--check" in argv:
        if new != text:
            print("wiki-run.js: embedded schemas are out of date; run `uv run python dev/embed_schemas.py`")
            return 1
        return 0
    WORKFLOW.write_bytes(new.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
