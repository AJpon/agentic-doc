# これはサブエージェントが生成しました
# 簡易pytest: index_jsonl が index.json を生成することを確認する

import json
from pathlib import Path
from tools.docagent.index import index_jsonl

def test_indexer_creates_index(tmp_path: Path):
    input_file = tmp_path / "input.jsonl"
    data = {"file": "sample.py", "line": 1, "doc": "hello world"}
    input_file.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding='utf-8')
    persist_dir = tmp_path / "persist"
    persist_dir.mkdir()
    index_jsonl(input_file=str(input_file), persist_dir=str(persist_dir))
    out_file = persist_dir / "index.json"
    assert out_file.exists()
    with open(out_file, 'r', encoding='utf-8') as f:
        arr = json.load(f)
    assert isinstance(arr, list)

# 実行:
# pytest -q tools/docagent/tests/test_indexer.py
