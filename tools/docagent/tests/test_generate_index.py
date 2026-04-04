import os
import subprocess
import sys
from pathlib import Path


def test_generate_creates_index(tmp_path):
    # minimal repo
    repo = tmp_path / 'repo'
    repo.mkdir()
    f = repo / 'sample.py'
    f.write_text('"""module doc"""\n\ndef f():\n    """fn doc"""\n    return 1\n')

    # run agent_runner against this temporary repo
    py = sys.executable
    subprocess.check_call([py, '-m', 'tools.docagent.agent_runner', '--repo', str(repo)])

    # Expect docs/wiki/index.md exists in workspace
    assert Path('docs/wiki/index.md').exists()
