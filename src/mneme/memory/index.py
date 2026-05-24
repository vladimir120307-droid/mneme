"""Vector index over memory embeddings.

Two backends:

* ``NumpyIndex`` — pure-numpy brute force. Always available, fast enough up
  to ~100k vectors. Default.
* ``HNSWIndex`` — wraps ``hnswlib`` for sub-linear search on larger stores.
  Activated automatically if hnswlib is importable, or explicitly via
  ``backend="hnsw"``.

Both expose the same minimal API: ``add``, ``search``, ``remove``,
``save``, ``load`` and ``__len__``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class VectorIndex(ABC):
    dim: int

    @abstractmethod
    def add(self, memory_id: str, vector: np.ndarray) -> None: ...

    @abstractmethod
    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]: ...

    @abstractmethod
    def remove(self, memory_id: str) -> None: ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path, dim: int, **kwargs: object) -> VectorIndex:
        backend = kwargs.get("backend", "auto")
        if backend == "hnsw" or (backend == "auto" and _hnsw_available()):
            try:
                return HNSWIndex.load(path, dim=dim)
            except Exception:
                return NumpyIndex.load(path, dim=dim)
        return NumpyIndex.load(path, dim=dim)


# ── numpy backend ───────────────────────────────────────────────────────

class NumpyIndex(VectorIndex):
    def __init__(self, dim: int):
        self.dim = dim
        self._ids: list[str] = []
        self._id_to_pos: dict[str, int] = {}
        self._vectors = np.zeros((0, dim), dtype=np.float32)

    def add(self, memory_id: str, vector: np.ndarray) -> None:
        v = np.asarray(vector, dtype=np.float32).reshape(self.dim)
        if memory_id in self._id_to_pos:
            self._vectors[self._id_to_pos[memory_id]] = v
            return
        self._id_to_pos[memory_id] = len(self._ids)
        self._ids.append(memory_id)
        self._vectors = np.vstack([self._vectors, v[None, :]])

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        if not self._ids:
            return []
        q = np.asarray(query, dtype=np.float32).reshape(self.dim)
        # vectors are assumed already L2-normalised by the embedder
        sims = self._vectors @ q
        k = min(k, len(self._ids))
        if k <= 0:
            return []
        top = np.argpartition(-sims, kth=k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        return [(self._ids[i], float(sims[i])) for i in top]

    def remove(self, memory_id: str) -> None:
        pos = self._id_to_pos.pop(memory_id, None)
        if pos is None:
            return
        self._ids.pop(pos)
        self._vectors = np.delete(self._vectors, pos, axis=0)
        # rebuild positions
        self._id_to_pos = {mid: i for i, mid in enumerate(self._ids)}

    def __len__(self) -> int:
        return len(self._ids)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path.with_suffix(".npz"), vectors=self._vectors, ids=np.array(self._ids, dtype=object))

    @classmethod
    def load(cls, path: Path, dim: int, **_: object) -> NumpyIndex:
        inst = cls(dim)
        npz_path = path.with_suffix(".npz")
        if not npz_path.exists():
            return inst
        data = np.load(npz_path, allow_pickle=True)
        inst._vectors = data["vectors"].astype(np.float32)
        inst._ids = list(data["ids"])
        inst._id_to_pos = {mid: i for i, mid in enumerate(inst._ids)}
        return inst


# ── HNSW backend (optional) ─────────────────────────────────────────────

def _hnsw_available() -> bool:
    try:
        import hnswlib  # noqa: F401
        return True
    except ImportError:
        return False


class HNSWIndex(VectorIndex):
    def __init__(self, dim: int, max_elements: int = 100_000):
        import hnswlib

        self.dim = dim
        self.max_elements = max_elements
        self._index = hnswlib.Index(space="cosine", dim=dim)
        self._index.init_index(max_elements=max_elements, ef_construction=200, M=16)
        self._index.set_ef(50)
        self._id_to_label: dict[str, int] = {}
        self._label_to_id: dict[int, str] = {}
        self._next_label = 0

    def add(self, memory_id: str, vector: np.ndarray) -> None:
        if memory_id in self._id_to_label:
            label = self._id_to_label[memory_id]
        else:
            if self._next_label >= self.max_elements:
                self.max_elements *= 2
                self._index.resize_index(self.max_elements)
            label = self._next_label
            self._next_label += 1
            self._id_to_label[memory_id] = label
            self._label_to_id[label] = memory_id
        self._index.add_items(vector.reshape(1, -1), [label])

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        if self._next_label == 0:
            return []
        k = min(k, self._next_label)
        labels, dists = self._index.knn_query(query.reshape(1, -1), k=k)
        out: list[tuple[str, float]] = []
        for label, dist in zip(labels[0], dists[0]):
            mid = self._label_to_id.get(int(label))
            if mid is None:
                continue
            out.append((mid, 1.0 - float(dist)))  # cosine sim
        return out

    def remove(self, memory_id: str) -> None:
        label = self._id_to_label.pop(memory_id, None)
        if label is None:
            return
        self._label_to_id.pop(label, None)
        try:
            self._index.mark_deleted(label)
        except RuntimeError:
            pass

    def __len__(self) -> int:
        return len(self._id_to_label)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._index.save_index(str(path))
        with path.with_suffix(".map").open("w", encoding="utf-8") as f:
            for mid, label in self._id_to_label.items():
                f.write(f"{label}\t{mid}\n")

    @classmethod
    def load(cls, path: Path, dim: int, **_: object) -> HNSWIndex:
        import hnswlib

        inst = cls(dim=dim)
        if not path.exists():
            return inst
        inst._index = hnswlib.Index(space="cosine", dim=dim)
        inst._index.load_index(str(path), max_elements=inst.max_elements)
        inst._index.set_ef(50)
        mapping = path.with_suffix(".map")
        if mapping.exists():
            with mapping.open("r", encoding="utf-8") as f:
                for line in f:
                    label_s, mid = line.rstrip("\n").split("\t", 1)
                    label = int(label_s)
                    inst._id_to_label[mid] = label
                    inst._label_to_id[label] = mid
                    inst._next_label = max(inst._next_label, label + 1)
        return inst


def make_index(dim: int, backend: str = "auto", max_elements: int = 100_000) -> VectorIndex:
    """Create a fresh empty index. Used when no persisted state exists yet."""
    if backend == "hnsw" or (backend == "auto" and _hnsw_available()):
        try:
            return HNSWIndex(dim=dim, max_elements=max_elements)
        except Exception:
            return NumpyIndex(dim=dim)
    return NumpyIndex(dim=dim)
