from __future__ import annotations

import json
import shutil
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

    # Borrado físico completo del directorio persistido en vez de confiar solo en
    # store.reset()/delete_collection(): en Windows, archivos bloqueados por un
    # proceso anterior (p.ej. un intento de indexado que crasheó a medio camino)
    # pueden impedir que delete_collection() limpie del todo, dejando una
    # dimensión de embeddings vieja "pegada" en chroma.sqlite3 aunque el código
    # ya use un modelo distinto. Empezar de cero en disco evita ese desfase.
    persist_dir = root_dir / "backend" / "data" / "chroma"
    if persist_dir.exists():
        print(f"Eliminando índice previo en: {persist_dir}")
        shutil.rmtree(persist_dir, ignore_errors=True)

    store = CorpusVectorStore(root_dir=root_dir)
    summary = store.ingest_corpus(corpus_root)

    output_path = output_dir / "vector_index_summary.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Vector index summary written to: {output_path}")
    print(summary)


if __name__ == "__main__":
    main()
