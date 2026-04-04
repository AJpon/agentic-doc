"""Simple orchestration script to run the DocAgent PoC pipeline.

Usage:
    python -m tools.docagent.agent_runner --repo /path/to/repo
"""
import argparse
import subprocess
import sys


def run_pipeline(repo='.'):
    py = sys.executable
    subprocess.check_call([py, '-m', 'tools.docagent.cli', 'ingest', '--repo', repo, '--out', 'tools/docagent/data/extracted.jsonl'])
    subprocess.check_call([py, '-m', 'tools.docagent.cli', 'index', '--input', 'tools/docagent/data/extracted.jsonl', '--persist', 'tools/docagent/data'])
    subprocess.check_call([py, '-m', 'tools.docagent.cli', 'generate', '--out', 'docs/wiki'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', default='.', help='Path to target repository')
    args = parser.parse_args()
    run_pipeline(args.repo)


if __name__ == '__main__':
    main()
