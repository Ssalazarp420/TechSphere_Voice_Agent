from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

import chromadb

from .chunking import chunk_text
from .embeddings import create_embedding_function
from .pdf_utils import extract_pdf_text, inspect_pdf


class CorpusVectorStore:
    def __init__(self, root_dir: Path, collection_name: str = "techsphere_corpus") -> None:
        self.root_dir = root_dir
        self.persist_dir = root_dir / "backend" / "data" / "chroma"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_function = create_embedding_function()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_backend = getattr(self.embedding_function, "backend_name", type(self.embedding_function).__name__)
        self.embedding_model = getattr(self.embedding_function, "model_name", None)
        self.embedding_dimensions = getattr(self.embedding_function, "embedding_dimensions", None)

    def reset(self) -> None:
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()

    def status(self, corpus_root: Path) -> dict[str, Any]:
        catalog_path = self.root_dir / "backend" / "data" / "corpus_catalog.json"
        corpus_documents = 0
        text_documents = 0
        scanned_documents = 0

        if catalog_path.exists():
            import json

            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            corpus_documents = int(catalog.get("total_documents", 0))
            text_documents = int(catalog.get("text_documents", 0))
            scanned_documents = int(catalog.get("scanned_documents", 0))

        return {
            "corpus_root": str(corpus_root),
            "catalog_path": str(catalog_path),
            "catalog_exists": catalog_path.exists(),
            "corpus_documents": corpus_documents,
            "text_documents": text_documents,
            "scanned_documents": scanned_documents,
            "indexed_chunks": self.count(),
            "embedding_backend": self.embedding_backend,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
        }

    def ingest_corpus(self, corpus_root: Path) -> dict[str, int]:
        indexed_chunks = 0
        skipped_documents = 0
        scanned_documents = 0

        for pdf_path in sorted(corpus_root.rglob("*.pdf")):
            inspection = inspect_pdf(pdf_path)
            if not inspection.has_text:
                scanned_documents += 1
                continue

            text = extract_pdf_text(pdf_path)
            if not text.strip():
                skipped_documents += 1
                continue

            for chunk in chunk_text(text):
                chunk_id = f"{pdf_path.stem}::chunk::{chunk.chunk_index}"
                metadata = {
                    "document_path": str(pdf_path),
                    "category": pdf_path.parent.name,
                    "filename": pdf_path.name,
                    "chunk_index": chunk.chunk_index,
                    "pages": inspection.pages,
                    "has_text": inspection.has_text,
                }
                self.collection.upsert(
                    ids=[chunk_id],
                    documents=[chunk.text],
                    metadatas=[metadata],
                )
                indexed_chunks += 1

        return {
            "indexed_chunks": indexed_chunks,
            "skipped_documents": skipped_documents,
            "scanned_documents": scanned_documents,
        }

    def search(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        candidate_count = max(limit * 4, 12)
        result = self.collection.query(query_texts=[query], n_results=candidate_count)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]

        matches: list[dict[str, object]] = []
        query_tokens = set(re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", query.lower()))

        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            metadata = metadata or {}
            searchable_text = " ".join(
                [
                    document or "",
                    str(metadata.get("filename", "")),
                    str(metadata.get("category", "")),
                ]
            ).lower()
            overlap = sum(1 for token in query_tokens if token and token in searchable_text)
            score = overlap * 2 - float(distance)
            matches.append(
                {
                    "id": chunk_id,
                    "text": document,
                    "metadata": metadata,
                    "distance": distance,
                    "score": score,
                }
            )

        matches.sort(key=lambda item: (item.get("score", 0.0), -float(item.get("distance", 0.0))), reverse=True)
        return matches[:limit]

