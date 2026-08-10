from __future__ import annotations

import hashlib
import math
import os
import re
import warnings
from functools import lru_cache

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

TOKEN_PATTERN = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", re.UNICODE)


def _read_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _read_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    backend_name = "hash"

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions
        self.model_name = "hash"

    @property
    def embedding_dimensions(self) -> int:
        return self.dimensions

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


class SentenceTransformerEmbeddingFunction(EmbeddingFunction[Documents]):
    backend_name = "sentence-transformers"

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
        normalize_embeddings: bool | None = None,
        trust_remote_code: bool | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.device = device or os.getenv("EMBEDDING_DEVICE") or None
        self.batch_size = batch_size or _read_env_int("EMBEDDING_BATCH_SIZE", 16)
        self.normalize_embeddings = (
            normalize_embeddings if normalize_embeddings is not None else _read_env_bool("EMBEDDING_NORMALIZE", True)
        )
        self.trust_remote_code = (
            trust_remote_code if trust_remote_code is not None else _read_env_bool("EMBEDDING_TRUST_REMOTE_CODE", True)
        )

    @property
    def embedding_dimensions(self) -> int:
        return int(self._load_model().get_sentence_embedding_dimension())

    @lru_cache(maxsize=4)
    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised by runtime environment
            raise RuntimeError(
                "sentence-transformers no está instalado. Ejecuta `pip install -r backend/requirements.txt` o usa EMBEDDING_BACKEND=hash."
            ) from exc

        kwargs: dict[str, object] = {"trust_remote_code": self.trust_remote_code}
        if self.device:
            kwargs["device"] = self.device

        return SentenceTransformer(self.model_name, **kwargs)

    def __call__(self, input: Documents) -> Embeddings:
        documents = [document.strip() for document in input]
        if not documents:
            return []

        model = self._load_model()
        vectors = model.encode(
            documents,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [[float(value) for value in row] for row in vectors.tolist()]


def create_embedding_function() -> EmbeddingFunction[Documents]:
    # Antes el default era "auto", que caía en silencio al hash (256 dim) si
    # sentence-transformers fallaba por cualquier motivo transitorio (carrera con
    # --reload, lock de archivo en Windows, etc). Como el índice ya quedó construido
    # con sentence-transformers (384 dim), un fallback silencioso siempre termina en
    # InvalidDimensionException más adelante, solo que de forma más difícil de
    # diagnosticar. Ahora el default exige sentence-transformers explícitamente: si
    # falla, falla ruidoso con el traceback real en vez de degradar en silencio.
    backend = os.getenv("EMBEDDING_BACKEND", "sentence-transformers").strip().lower()

    if backend == "hash":
        return HashEmbeddingFunction(dimensions=_read_env_int("HASH_EMBEDDING_DIMENSIONS", 256))

    if backend in {"auto", "sentence-transformers", "bge-m3"}:
        embedding_function = SentenceTransformerEmbeddingFunction()
        try:
            _ = embedding_function.embedding_dimensions
            return embedding_function
        except Exception as exc:
            if backend != "auto":
                raise

            warnings.warn(
                f"No se pudo cargar el backend de sentence-transformers ({exc}). Se usará el embedding hash como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )
            return HashEmbeddingFunction(dimensions=_read_env_int("HASH_EMBEDDING_DIMENSIONS", 256))

    raise ValueError(
        "EMBEDDING_BACKEND debe ser auto, sentence-transformers, bge-m3 o hash."
    )
