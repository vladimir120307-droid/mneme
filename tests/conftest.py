from __future__ import annotations

import hashlib

import numpy as np
import pytest

from mneme.memory.embeddings import Embedder
from mneme.memory.store import MemoryStore


class FakeEmbedder(Embedder):
    """Deterministic 32-dim hash embedder — fast, no model download."""

    def __init__(self, dim: int = 32):
        self._fake_dim = dim
        self.model_name = "fake"

    @property
    def dim(self) -> int:
        return self._fake_dim

    def embed(self, text: str) -> np.ndarray:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> np.ndarray:
        vecs = np.zeros((len(texts), self._fake_dim), dtype=np.float32)
        for i, t in enumerate(texts):
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            buf = (digest * ((self._fake_dim * 4) // len(digest) + 1))[: self._fake_dim * 4]
            arr = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)[: self._fake_dim]
            arr = arr - 127.5
            norm = np.linalg.norm(arr)
            vecs[i] = arr / norm if norm else arr
        return vecs


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(path=tmp_path / "mneme", embedder=FakeEmbedder())
    yield s
    s.close()
