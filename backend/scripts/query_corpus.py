from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the corpus vector store")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[2]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))

    from backend.rag.store import CorpusVectorStore

    store = CorpusVectorStore(root_dir=root_dir)
    results = store.search(args.query, limit=args.limit)

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]
        print(f"\n### Result {index} ###")
        print(f"id: {result['id']}")
        print(f"distance: {result['distance']}")
        print(f"document: {metadata['filename']}")
        print(f"category: {metadata['category']}")
        print(result["text"][:700])


if __name__ == "__main__":
    main()
