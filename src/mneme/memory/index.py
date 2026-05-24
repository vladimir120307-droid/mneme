"""Vector index over memory embeddings.

Three backends, picked in this order when ``backend="auto"``:

1. ``NativeIndex`` — C++ core (``mneme._native``). SIMD-friendly brute force
   parallelised with OpenMP. Selected when the extension is compiled.
2. ``HNSWIndex`` — ``hnswlib`` for sub-linear search on very large stores.
3. ``NumpyIndex`` — pure-numpy brute force. Always available.

All three expose the same API: ``add``, ``search``, ``remove``,
``save``, ``load`` and ``__len__``.
"""

from __future__ import annotations

import contextlib
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
        if backend == "native" or (backend == "auto" and _native_available()):
            try:
                return NativeIndex.load(path, dim=dim)
            except Exception:
                pass  # fall through to next backend
        if backend == "hnsw" or (backend == "auto" and _hnsw_available()):
            try:
                return HNSWIndex.load(path, dim=dim)
            except Exception:
                pass
        return NumpyIndex.load(path, dim=dim)


# ── numpy backend ───────────────────────────────────────────────────────

class NumpyIndex(VectorIndex):
    """Pure-numpy brute-force cosine index.

    Uses an amortised-growth backing buffer (like ``std::vector``) so that
    ``add`` is O(1) amortised instead of O(N) per insert. Search is a single
    dense matrix-vector product followed by partial top-K.
    """

    _INITIAL_CAPACITY = 256

    def __init__(self, dim: int):
        self.dim = dim
        self._ids: list[str] = []
        self._id_to_pos: dict[str, int] = {}
        self._capacity = self._INITIAL_CAPACITY
        self._size = 0
        self._buffer = np.zeros((self._capacity, dim), dtype=np.float32)

    @property
    def _vectors(self) -> np.ndarray:
        """View of the live portion of the buffer (no copy)."""
        return self._buffer[: self._size]

    def _ensure_capacity(self, needed: int) -> None:
        if needed <= self._capacity:
            return
        new_cap = self._capacity
        while new_cap < needed:
            new_cap *= 2
        new_buf = np.zeros((new_cap, self.dim), dtype=np.float32)
        new_buf[: self._size] = self._buffer[: self._size]
        self._buffer = new_buf
        self._capacity = new_cap

    def add(self, memory_id: str, vector: np.ndarray) -> None:
        v = np.asarray(vector, dtype=np.float32).reshape(self.dim)
        existing = self._id_to_pos.get(memory_id)
        if existing is not None:
            self._buffer[existing] = v
            return
        self._ensure_capacity(self._size + 1)
        pos = self._size
        self._buffer[pos] = v
        self._ids.append(memory_id)
        self._id_to_pos[memory_id] = pos
        self._size += 1

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        if self._size == 0:
            return []
        q = np.asarray(query, dtype=np.float32).reshape(self.dim)
        # vectors are assumed already L2-normalised by the embedder
        sims = self._vectors @ q
        k = min(k, self._size)
        if k <= 0:
            return []
        top = np.argpartition(-sims, kth=k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        return [(self._ids[i], float(sims[i])) for i in top]

    def remove(self, memory_id: str) -> None:
        pos = self._id_to_pos.pop(memory_id, None)
        if pos is None:
            return
        last = self._size - 1
        if pos != last:
            # swap-remove: move the last live row into the freed slot
            last_id = self._ids[last]
            self._buffer[pos] = self._buffer[last]
            self._ids[pos] = last_id
            self._id_to_pos[last_id] = pos
        self._ids.pop()
        self._buffer[last] = 0.0
        self._size -= 1

    def __len__(self) -> int:
        return self._size

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path.with_suffix(".npz"),
            vectors=self._vectors,
            ids=np.array(self._ids, dtype=object),
        )

    @classmethod
    def load(cls, path: Path, dim: int, **_: object) -> NumpyIndex:
        inst = cls(dim)
        npz_path = path.with_suffix(".npz")
        if not npz_path.exists():
            return inst
        data = np.load(npz_path, allow_pickle=True)
        vectors = data["vectors"].astype(np.float32)
        ids = list(data["ids"])
        inst._ensure_capacity(max(len(ids), cls._INITIAL_CAPACITY))
        inst._buffer[: len(ids)] = vectors
        inst._ids = ids
        inst._id_to_pos = {mid: i for i, mid in enumerate(ids)}
        inst._size = len(ids)
        return inst


# ── Native backend (optional) ───────────────────────────────────────────

def _native_available() -> bool:
    try:
        from mneme import _native  # noqa: F401
        return True
    except ImportError:
        return False


class NativeIndex(VectorIndex):
    """Thin wrapper around the C++ ``mneme._native.VectorIndex``."""

    def __init__(self, dim: int):
        from mneme import _native

        self.dim = dim
        self._inner = _native.VectorIndex(dim)

    def add(self, memory_id: str, vector: np.ndarray) -> None:
        v = np.ascontiguousarray(vector, dtype=np.float32).reshape(self.dim)
        self._inner.add(memory_id, v)

    def search(self, query: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        q = np.ascontiguousarray(query, dtype=np.float32).reshape(self.dim)
        return list(self._inner.search(q, k))

    def remove(self, memory_id: str) -> None:
        self._inner.remove(memory_id)

    def __len__(self) -> int:
        return len(self._inner)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._inner.save(path.with_suffix(".bin"))

    @classmethod
    def load(cls, path: Path, dim: int, **_: object) -> NativeIndex:
        from mneme import _native

        bin_path = path.with_suffix(".bin")
        inst = cls.__new__(cls)
        inst.dim = dim
        if bin_path.exists():
            inst._inner = _native.VectorIndex.load(bin_path)
        else:
            inst._inner = _native.VectorIndex(dim)
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
        for label, dist in zip(labels[0], dists[0], strict=True):
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
        with contextlib.suppress(RuntimeError):
            self._index.mark_deleted(label)

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
    if backend == "native" or (backend == "auto" and _native_available()):
        try:
            return NativeIndex(dim=dim)
        except Exception:
            pass
    if backend == "hnsw" or (backend == "auto" and _hnsw_available()):
        try:
            return HNSWIndex(dim=dim, max_elements=max_elements)
        except Exception:
            pass
    return NumpyIndex(dim=dim)


def active_backend() -> str:
    """Name of the backend ``backend='auto'`` would pick right now."""
    if _native_available():
        return "native"
    if _hnsw_available():
        return "hnsw"
    return "numpy"
