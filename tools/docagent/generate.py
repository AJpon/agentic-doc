import os
import json
try:
    from jinja2 import Template
    has_jinja = True
except Exception:
    Template = None
    has_jinja = False


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
    # Prefer Jinja2 template if available, otherwise use fallback renderer
    jinja_tpl = '''# {{ title }}

{% for item in items %}
## {{ item.meta.type | default('item') }}: `{{ item.meta.name | default('') }}`

**File:** {{ item.meta.file }} :{{ item.meta.line }}

{% if item.meta.signature %}**Signature:** `{{ item.meta.signature }}`

{% endif %}
{{ item.text }}

```{{ item.meta.lang | default('') }}
{{ item.meta.source | default('') }}
```

{% endfor %}
'''

    def render_fallback(title, items):
        out = f"# {title}\n\n"
        for it in items:
            meta = it.get('meta', {})
            typ = meta.get('type', 'item')
            name = meta.get('name', '')
            file = meta.get('file', '')
            line = meta.get('line', '')
            sig = meta.get('signature', '')
            lang = meta.get('lang', '')
            text = it.get('text', '')
            src = meta.get('source', '')

            out += f"## {typ}: `{name}`\n\n"
            out += f"**File:** {file} :{line}\n\n"
            if sig:
                out += f"**Signature:** `{sig}`\n\n"
            if text:
                out += text + "\n\n"
            if src:
                out += f"```{lang}\n{src}\n```\n\n"
        return out

    for file, items in grouped.items():
        title = os.path.basename(file)
        if has_jinja and Template is not None:
            try:
                md = Template(jinja_tpl).render(title=title, items=[{'meta': it.get('meta', {}), 'text': it.get('text','')} for it in items])
            except Exception:
                md = render_fallback(title, items)
        else:
            md = render_fallback(title, items)

        out_path = os.path.join(out_dir, title + '.md')
        with open(out_path, 'w', encoding='utf-8') as fo:
            fo.write(md)
    # write an index page linking to generated module pages
    index_lines = ['# Generated Wiki', '']
    for file in sorted(grouped.keys()):
        name = os.path.basename(file)
        index_lines.append(f"- [{name}]({name}.md)")

    with open(os.path.join(out_dir, 'index.md'), 'w', encoding='utf-8') as fi:
        fi.write('\n'.join(index_lines) + '\n')

    print('Generated', len(grouped), 'pages to', out_dir)
