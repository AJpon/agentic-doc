import argparse
from . import ingest, index, generate


def main():
    parser = argparse.ArgumentParser(prog='docagent', description='DocAgent PoC CLI')
    sub = parser.add_subparsers(dest='cmd')

    p_ing = sub.add_parser('ingest', help='Extract symbols and docstrings from a repo')
    p_ing.add_argument('--repo', default='.', help='Path to target repository')
    p_ing.add_argument('--out', default='tools/docagent/data/extracted.jsonl', help='Output JSONL')

    p_idx = sub.add_parser('index', help='Index extracted JSONL into local vector store')
    p_idx.add_argument('--input', default='tools/docagent/data/extracted.jsonl', help='Input JSONL')
    p_idx.add_argument('--persist', default='tools/docagent/data', help='Persist directory')

    p_gen = sub.add_parser('generate', help='Generate Markdown pages from index')
    p_gen.add_argument('--module', default=None, help='Optional module/file filter')
    p_gen.add_argument('--out', default='docs/wiki', help='Output directory for markdown')

    args = parser.parse_args()
    if args.cmd == 'ingest':
        ingest.ingest_repo(args.repo, args.out)
    elif args.cmd == 'index':
        index.index_jsonl(args.input, args.persist)
    elif args.cmd == 'generate':
        generate.generate_docs(args.module, args.out)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
