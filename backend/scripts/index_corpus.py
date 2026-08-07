from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.rag.store import CorpusVectorStore

    corpus_root = root_dir / "dataset" / "textos"
    output_dir = root_dir / "backend" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    store = CorpusVectorStore(root_dir=root_dir)
    store.reset()
    summary = store.ingest_corpus(corpus_root)

    output_path = output_dir / "vector_index_summary.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Vector index summary written to: {output_path}")
    print(summary)


if __name__ == "__main__":
    main()
