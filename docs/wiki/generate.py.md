# generate.py

## function: `generate_docs`

**File:** /Users/taka/works/dev/agentic-wiki/tools/docagent/generate.py :25

**Signature:** `generate_docs(module, out_dir)`

Generate simple Markdown pages from the local index files.

This PoC groups entries by source file and renders a Markdown page per file.

```python
def generate_docs(module=None, out_dir='docs/wiki'):
    """Generate simple Markdown pages from the local index files.

    This PoC groups entries by source file and renders a Markdown page per file.
    """
    idx1 = 'tools/docagent/data/index_with_embeddings.json'
    idx2 = 'tools/docagent/data/index.json'
    if os.path.exists(idx1):
        with open(idx1, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    elif os.path.exists(idx2):
        with open(idx2, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    else:
        print('No index found. Run index command first.')
        return

    grouped = {}
    for d in docs:
        meta = d.get('meta') or d.get('meta', {})
        file = meta.get('file') if isinstance(meta, dict) else d.get('file', 'unknown')
        if module and module not in file:
            continue
        grouped.setdefault(file, []).append(d)

    os.makedirs(out_dir, exist_ok=True)
    tpl = Template('# {{ title }}\n\n{% for item in items %}- **{{ item.get("meta",{}).get("type","item") }}** `{{ item.get("meta",{}).get("name","") }}`\n\n  {{ item.get("text")[:400] }}\n\n{% endfor %}')

    for file, items in grouped.items():
        title = os.path.basename(file)
        md = tpl.render(title=title, items=items)
        out_path = os.path.join(out_dir, title + '.md')
        with open(out_path, 'w', encoding='utf-8') as fo:
            fo.write(md)

    print('Generated', len(grouped), 'pages to', out_dir)
```

