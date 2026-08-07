from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.rag.catalog import build_corpus_catalog, catalog_to_dicts

    corpus_root = root_dir / "dataset" / "textos"
    output_dir = root_dir / "backend" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    documents = build_corpus_catalog(corpus_root)
    output_path = output_dir / "corpus_catalog.json"

    payload = {
        "corpus_root": str(corpus_root),
        "total_documents": len(documents),
        "text_documents": sum(1 for document in documents if document.has_text),
        "scanned_documents": sum(1 for document in documents if not document.has_text),
        "documents": catalog_to_dicts(documents),
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Corpus catalog written to: {output_path}")
    print(f"Total documents: {payload['total_documents']}")
    print(f"Text documents: {payload['text_documents']}")
    print(f"Scanned documents: {payload['scanned_documents']}")


if __name__ == "__main__":
    main()
