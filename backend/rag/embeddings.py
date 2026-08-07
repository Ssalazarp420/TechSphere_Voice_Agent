from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

TOKEN_PATTERN = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", re.UNICODE)


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_document(document) for document in input]

    def _embed_document(self, document: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(document.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            weight = 1.0 + math.log1p(len(token))
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
