# ingest.py

## function: `ingest_repo`

**File:** /Users/taka/works/dev/agentic-wiki/tools/docagent/ingest.py :6

**Signature:** `ingest_repo(repo_path, out_file)`

Walk repository and extract symbols using language-specific extractors.

Output is JSONL with items like {lang,type,name,signature,doc,file,line,source}.

```python
def ingest_repo(repo_path='.', out_file='tools/docagent/data/extracted.jsonl'):
    """Walk repository and extract symbols using language-specific extractors.

    Output is JSONL with items like {lang,type,name,signature,doc,file,line,source}.
    """
    repo_path = os.path.abspath(repo_path)
    Path(os.path.dirname(out_file)).mkdir(parents=True, exist_ok=True)

    with open(out_file, 'w', encoding='utf-8') as fout:
        for root, dirs, files in os.walk(repo_path):
            # skip VCS and large folders
            if '.git' in root.split(os.sep):
                continue
            if 'node_modules' in root.split(os.sep):
                continue
            for fn in files:
                if fn.endswith('.py') or fn.endswith('.ts') or fn.endswith('.cs'):
                    path = os.path.join(root, fn)
                    try:
                        if fn.endswith('.py'):
                            from .extractors.py_extractor import extract_file
                            items = extract_file(path)
                        elif fn.endswith('.ts'):
                            from .extractors.ts_extractor import extract_file
                            items = extract_file(path)
                        else:
                            from .extractors.cs_extractor import extract_file
                            items = extract_file(path)

                        for it in items:
                            fout.write(json.dumps(it, ensure_ascii=False) + '\n')
                    except Exception as e:
                        print('ingest error', path, e)
```

