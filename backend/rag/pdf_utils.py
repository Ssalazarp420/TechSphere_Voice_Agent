from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class PdfIngestionResult:
    path: Path
    pages: int
    text_length: int
    has_text: bool
    extractable_pages: int


def extract_pdf_text(path: Path, max_pages: int | None = None) -> str:
    reader = PdfReader(str(path))
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    parts: list[str] = []
    for page in pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text)
    return "\n".join(parts).strip()


def inspect_pdf(path: Path) -> PdfIngestionResult:
    reader = PdfReader(str(path))
    text = extract_pdf_text(path, max_pages=min(len(reader.pages), 3))
    return PdfIngestionResult(
        path=path,
        pages=len(reader.pages),
        text_length=len(text),
        has_text=bool(text.strip()),
        extractable_pages=sum(1 for page in reader.pages if (page.extract_text() or "").strip()),
    )
