from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    text: str
    chunk_index: int


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[TextChunk]:
    normalized = TOKEN_PATTERN.sub(" ", text).strip()
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    start = 0
    chunk_index = 0
    length = len(normalized)

    while start < length:
        end = min(length, start + chunk_size)
        if end < length:
            boundary = normalized.rfind(". ", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(TextChunk(chunk_id=f"chunk_{chunk_index}", text=chunk, chunk_index=chunk_index))
            chunk_index += 1

        if end >= length:
            break

        start = max(0, end - overlap)

    return chunks
