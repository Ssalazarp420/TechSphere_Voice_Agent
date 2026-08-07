from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.rag.chunking import chunk_text
from backend.rag.pdf_utils import extract_pdf_text, inspect_pdf
from backend.rag.store import CorpusVectorStore


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


@dataclass(frozen=True)
class ManagedDocument:
    document_id: str
    filename: str
    stored_path: str
    original_name: str
    status: str
    created_at: str
    updated_at: str
    pages: int
    chunk_count: int
    has_text: bool
    category: str


class AdminDocumentService:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.data_dir = root_dir / "backend" / "data"
        self.upload_dir = self.data_dir / "admin_uploads"
        self.registry_path = self.data_dir / "admin_registry.json"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store = CorpusVectorStore(root_dir=root_dir)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_registry(self) -> list[dict[str, object]]:
        if not self.registry_path.exists():
            return []
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save_registry(self, records: list[dict[str, object]]) -> None:
        self.registry_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_documents(self) -> list[dict[str, object]]:
        return self._load_registry()

    def upload_document(self, upload: UploadFile) -> dict[str, object]:
        original_name = upload.filename or "documento"
        extension = Path(original_name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValueError("Solo se permiten archivos PDF o TXT")

        document_id = uuid4().hex
        stored_filename = f"{document_id}{extension}"
        stored_path = self.upload_dir / stored_filename

        with stored_path.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        if extension == ".pdf":
            inspection = inspect_pdf(stored_path)
            if not inspection.has_text:
                stored_path.unlink(missing_ok=True)
                raise ValueError("El PDF no contiene texto extraíble; usa OCR antes de subirlo")
            text = extract_pdf_text(stored_path)
            pages = inspection.pages
            has_text = inspection.has_text
        else:
            text = stored_path.read_text(encoding="utf-8")
            pages = 1
            has_text = bool(text.strip())

        chunks = chunk_text(text)
        if not chunks:
            stored_path.unlink(missing_ok=True)
            raise ValueError("El documento no contiene texto útil para indexar")

        chunk_ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, object]] = []

        for chunk in chunks:
            chunk_id = f"admin::{document_id}::{chunk.chunk_index}"
            chunk_ids.append(chunk_id)
            documents.append(chunk.text)
            metadatas.append(
                {
                    "document_id": document_id,
                    "document_kind": "admin",
                    "document_path": str(stored_path),
                    "filename": original_name,
                    "stored_filename": stored_filename,
                    "chunk_index": chunk.chunk_index,
                    "category": "admin_upload",
                    "pages": pages,
                    "has_text": has_text,
                    "status": "available",
                }
            )

        self.vector_store.collection.upsert(ids=chunk_ids, documents=documents, metadatas=metadatas)

        registry = self._load_registry()
        now = self._now()
        record = ManagedDocument(
            document_id=document_id,
            filename=original_name,
            stored_path=str(stored_path),
            original_name=original_name,
            status="available",
            created_at=now,
            updated_at=now,
            pages=pages,
            chunk_count=len(chunk_ids),
            has_text=has_text,
            category="admin_upload",
        )
        registry.append({**asdict(record), "chunk_ids": chunk_ids})
        self._save_registry(registry)

        return {
            **asdict(record),
            "chunk_ids": chunk_ids,
        }

    def delete_document(self, document_id: str) -> dict[str, object]:
        registry = self._load_registry()
        remaining: list[dict[str, object]] = []
        deleted: dict[str, object] | None = None

        for record in registry:
            if record.get("document_id") == document_id:
                deleted = record
                continue
            remaining.append(record)

        if deleted is None:
            raise ValueError("No existe el documento solicitado")

        chunk_ids = list(deleted.get("chunk_ids", []))
        if chunk_ids:
            self.vector_store.collection.delete(ids=chunk_ids)

        stored_path = Path(str(deleted.get("stored_path", "")))
        if stored_path.exists():
            stored_path.unlink(missing_ok=True)

        self._save_registry(remaining)

        return {
            "deleted": True,
            "document_id": document_id,
            "filename": deleted.get("filename"),
            "chunk_count": len(chunk_ids),
        }
