import ast
from pathlib import Path


def extract_file(path):
    """Extract top-level module/class/function docstrings and signatures from a Python file."""
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()

    results = []
    try:
        tree = ast.parse(src)
    except Exception:
        return results

    # module docstring
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        results.append({'lang': 'python', 'type': 'module', 'name': Path(path).stem, 'doc': mod_doc, 'file': path, 'line': 1, 'source': mod_doc})

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ''
            results.append({'lang': 'python', 'type': 'class', 'name': node.name, 'doc': doc, 'file': path, 'line': node.lineno, 'source': ast.get_source_segment(src, node) or ''})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ''
            args = [a.arg for a in node.args.args]
            sig = f"{node.name}({', '.join(args)})"
            results.append({'lang': 'python', 'type': 'function', 'name': node.name, 'signature': sig, 'doc': doc, 'file': path, 'line': node.lineno, 'source': ast.get_source_segment(src, node) or ''})

    return results
