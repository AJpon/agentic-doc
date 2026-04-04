# これはサブエージェントが生成しました
# 簡易pytest: ingest_repo が extracted.jsonl を生成することを確認する

import json
from pathlib import Path
from tools.docagent.ingest import ingest_repo

def test_ingest_generates_jsonl(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    sample = repo_dir / "sample.py"
    sample.write_text(
        '''"""モジュールドキュメント"""

def foo():
    """関数doc"""
    return 42
''', encoding='utf-8'
    )
    out_file = tmp_path / "extracted.jsonl"
    ingest_repo(repo_path=str(repo_dir), out_file=str(out_file))
    assert out_file.exists(), "extracted.jsonl が作成されていません"
    with open(out_file, 'r', encoding='utf-8') as f:
        lines = [l for l in f if l.strip()]
    assert len(lines) > 0
    obj = json.loads(lines[0])
    assert 'file' in obj

# 実行:
# pytest -q tools/docagent/tests/test_ingest.py
