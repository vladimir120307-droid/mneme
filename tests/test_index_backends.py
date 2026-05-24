"""Parity tests: all available backends agree on results.

Skips gracefully when an optional backend isn't installed.
"""

from __future__ import annotations

import numpy as np
import pytest

from mneme.memory.index import (
    HNSWIndex,
    NativeIndex,
    NumpyIndex,
    _hnsw_available,
    _native_available,
)


def _norm_rand(n: int, dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, dim)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    return v


@pytest.fixture
def vectors():
    return _norm_rand(200, 32, seed=1)


def _populate(index, vectors):
    for i, v in enumerate(vectors):
        index.add(f"v{i}", v)


def test_numpy_top1_is_self(vectors):
    idx = NumpyIndex(dim=32)
    _populate(idx, vectors)
    hits = idx.search(vectors[7], k=1)
    assert hits and hits[0][0] == "v7"
    assert hits[0][1] == pytest.approx(1.0, abs=1e-5)


def test_numpy_remove_excludes_id(vectors):
    idx = NumpyIndex(dim=32)
    _populate(idx, vectors)
    idx.remove("v3")
    hits = idx.search(vectors[3], k=5)
    assert "v3" not in {h[0] for h in hits}


@pytest.mark.skipif(not _native_available(), reason="native core not built")
def test_native_matches_numpy_top1(vectors):
    a = NumpyIndex(dim=32)
    b = NativeIndex(dim=32)
    _populate(a, vectors)
    _populate(b, vectors)
    for i in [0, 17, 99, 199]:
        ah = a.search(vectors[i], k=1)
        bh = b.search(vectors[i], k=1)
        assert ah[0][0] == bh[0][0] == f"v{i}"
        assert ah[0][1] == pytest.approx(bh[0][1], abs=1e-4)


@pytest.mark.skipif(not _native_available(), reason="native core not built")
def test_native_top5_overlaps_numpy(vectors):
    a = NumpyIndex(dim=32)
    b = NativeIndex(dim=32)
    _populate(a, vectors)
    _populate(b, vectors)
    q = _norm_rand(1, 32, seed=999)[0]
    a_ids = {h[0] for h in a.search(q, k=5)}
    b_ids = {h[0] for h in b.search(q, k=5)}
    # backends should pick the same top-5 (with deterministic data and tie
    # margins large at dim=32). Allow one slot of slack for ties.
    assert len(a_ids & b_ids) >= 4


@pytest.mark.skipif(not _hnsw_available(), reason="hnswlib not installed")
def test_hnsw_top1_is_self(vectors):
    idx = HNSWIndex(dim=32, max_elements=300)
    _populate(idx, vectors)
    hits = idx.search(vectors[42], k=1)
    assert hits and hits[0][0] == "v42"
