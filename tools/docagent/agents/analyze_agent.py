#!/usr/bin/env python3
"""analyze_agent.py

簡易 Analyze エージェント
入力: index.json (tools/docagent/data/index.json) と docs/wiki ディレクトリ
出力: JSON レポート（missing pages / duplicate symbols / content overlap）

Usage:
  python tools/docagent/agents/analyze_agent.py --index tools/docagent/data/index.json --docs docs/wiki --out outputs/agents/analyze_report.json
"""
import argparse
import json
import os
import re
import time
from pathlib import Path
from collections import defaultdict


def load_index(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_wiki_pages(docs_dir):
    pages = {}
    p = Path(docs_dir)
    if not p.exists():
        return pages
    for fp in p.glob('*.md'):
        pages[fp.name] = str(fp)
    return pages


def tokenize(text):
    if not text:
        return set()
    s = text.lower()
    # remove common punctuation
    s = re.sub(r"[\t\n\r]+", " ", s)
    s = re.sub(r'[!"#$%&\'()\*+,\-\./:;<=>?@\[\\\]^_`{|}~]+', ' ', s)
    # extract ascii words (2+ chars)
    words = re.findall(r"\w{2,}", s, flags=re.UNICODE)
    # extract CJK/Japanese runs
    cjk = re.findall(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]+", s)
    allw = [w.strip() for w in words + cjk if w.strip()]
    return set(allw)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', default='tools/docagent/data/index.json')
    parser.add_argument('--docs', default='docs/wiki')
    parser.add_argument('--out', default='outputs/agents/analyze_report.json')
    args = parser.parse_args()

    idx_path = Path(args.index)
    if not idx_path.exists():
        print('Index file not found:', idx_path)
        return 1

    docs_dir = args.docs
    out_path = Path(args.out)

    data = load_index(str(idx_path))

    # Normalize items: support both shapes saved by index_jsonl and raw extract items
    items = []
    for d in data:
        if isinstance(d, dict) and 'meta' in d:
            meta = d.get('meta') or {}
            text = d.get('text') or meta.get('doc') or meta.get('source') or ''
        else:
            meta = d if isinstance(d, dict) else {}
            text = d.get('doc') if isinstance(d, dict) else ''
        items.append({'meta': meta, 'text': text})

    # Group by source file
    by_file = defaultdict(list)
    for it in items:
        m = it.get('meta') or {}
        file = m.get('file') or m.get('file_path') or m.get('path') or ''
        by_file[file].append(it)

    wiki_pages = get_wiki_pages(docs_dir)

    # Missing pages: index mentions a source file that has no corresponding wiki page
    missing = []
    for file, its in by_file.items():
        if not file:
            continue
        base = Path(file).name
        expected = base if base.endswith('.md') else base + '.md'
        if expected not in wiki_pages:
            missing.append({'file': file, 'suggested_page': expected, 'count': len(its)})

    # Duplicate symbols: same API name appears in multiple files
    name_map = defaultdict(set)
    for it in items:
        m = it.get('meta') or {}
        name = m.get('name') or m.get('module') or m.get('title') or ''
        file = m.get('file') or m.get('file_path') or ''
        if name:
            name_map[name].add(file)
    duplicates = []
    for name, files in name_map.items():
        files = [f for f in files if f]
        if len(files) > 1:
            duplicates.append({'name': name, 'files': files})

    # Content overlap: naive Jaccard on token sets, report pairs with high similarity
    token_sets = []
    for it in items:
        token_sets.append(tokenize(it.get('text') or ''))

    overlaps = []
    n = len(token_sets)
    for i in range(n):
        for j in range(i + 1, n):
            score = jaccard(token_sets[i], token_sets[j])
            if score >= 0.5:
                overlaps.append({'i': i, 'j': j, 'score': round(score, 3), 'shared': list((token_sets[i] & token_sets[j]))[:10]})

    report = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'index_items': len(items),
        'wiki_pages': len(wiki_pages),
        'missing_pages': missing,
        'duplicate_symbols': duplicates,
        'content_overlaps': overlaps,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fo:
        json.dump(report, fo, ensure_ascii=False, indent=2)

    print('Wrote analyze report to', str(out_path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
