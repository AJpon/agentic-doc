# ts_extractor.py

## function: `extract_file`

**File:** /Users/taka/works/dev/agentic-wiki/tools/docagent/extractors/ts_extractor.py :1

**Signature:** `extract_file(path)`

Lightweight TypeScript extractor: returns file-level content and TODO stub.

For PoC we read file and emit a single module entry. A full implementation
should use `ts-morph` or the TypeScript compiler API to extract symbols.

```python
def extract_file(path):
    """Lightweight TypeScript extractor: returns file-level content and TODO stub.

    For PoC we read file and emit a single module entry. A full implementation
    should use `ts-morph` or the TypeScript compiler API to extract symbols.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception:
        return []

    return [{'lang': 'typescript', 'type': 'module', 'name': path.split('/')[-1], 'doc': '', 'file': path, 'line': 1, 'source': src[:2000]}]
```

