import os
import json
from pathlib import Path


def index_jsonl(input_file='tools/docagent/data/extracted.jsonl', persist_dir='tools/docagent/data'):
    """Create embeddings and save a local index. Uses sentence-transformers if available.

    Fallback: write a JSON index without embeddings.
    """
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    docs = []
    if not os.path.exists(input_file):
        print('Input not found:', input_file)
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            text = obj.get('doc') or obj.get('source') or ''
            if not text.strip():
                continue
            docs.append({'id': f"{obj.get('file')}:{obj.get('line')}", 'text': text, 'meta': obj})

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        texts = [d['text'] for d in docs]
        embeddings = model.encode(texts, show_progress_bar=False)
        # Try to save embeddings locally (simple JSON)
        for i, d in enumerate(docs):
            d['embedding'] = embeddings[i].tolist()
        with open(os.path.join(persist_dir, 'index_with_embeddings.json'), 'w', encoding='utf-8') as fo:
            json.dump(docs, fo, ensure_ascii=False, indent=2)
        print('Indexed', len(docs), 'items to', persist_dir)
    except Exception as e:
        # Fallback
        with open(os.path.join(persist_dir, 'index.json'), 'w', encoding='utf-8') as fo:
            json.dump(docs, fo, ensure_ascii=False, indent=2)
        print('Saved JSON index (no embeddings) to', persist_dir)
