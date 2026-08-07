from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .pdf_utils import inspect_pdf


@dataclass(frozen=True)
class CorpusDocument:
    path: str
    category: str
    filename: str
    pages: int
    has_text: bool
    text_length: int
    extractable_pages: int


def build_corpus_catalog(corpus_root: Path) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    for pdf_path in sorted(corpus_root.rglob("*.pdf")):
        inspection = inspect_pdf(pdf_path)
        documents.append(
            CorpusDocument(
                path=str(pdf_path),
                category=pdf_path.parent.name,
                filename=pdf_path.name,
                pages=inspection.pages,
                has_text=inspection.has_text,
                text_length=inspection.text_length,
                extractable_pages=inspection.extractable_pages,
            )
        )
    return documents


def catalog_to_dicts(documents: list[CorpusDocument]) -> list[dict[str, object]]:
    return [asdict(document) for document in documents]
