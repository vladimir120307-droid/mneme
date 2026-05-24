"""Embedding model wrapper.

Lazy-loads sentence-transformers so importing mneme stays fast.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIM = 384


@lru_cache(maxsize=4)
def _load_model(name: str) -> SentenceTransformer:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


class Embedder:
    """Turns text into a normalised float32 vector."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._dim: int | None = None

    @property
    def dim(self) -> int:
        if self._dim is None:
            model = _load_model(self.model_name)
            self._dim = int(model.get_sentence_embedding_dimension())
        return self._dim

    def embed(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        model = _load_model(self.model_name)
        vecs = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vecs.astype(np.float32)
