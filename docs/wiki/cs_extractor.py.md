# cs_extractor.py

## function: `extract_file`

**File:** /Users/taka/works/dev/agentic-wiki/tools/docagent/extractors/cs_extractor.py :1

**Signature:** `extract_file(path)`

Minimal C# extractor stub.

Full-featured extraction should use Roslyn (dotnet) to produce structured JSON.
For PoC this function emits a single module entry with a snippet.

```python
def extract_file(path):
    """Minimal C# extractor stub.

    Full-featured extraction should use Roslyn (dotnet) to produce structured JSON.
    For PoC this function emits a single module entry with a snippet.
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            src = f.read()
    except Exception:
        return []

    return [{'lang': 'csharp', 'type': 'module', 'name': path.split('/')[-1], 'doc': '', 'file': path, 'line': 1, 'source': src[:2000]}]
```

