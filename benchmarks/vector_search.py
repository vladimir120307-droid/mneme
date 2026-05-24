"""Throughput benchmark for the available index backends.

    python benchmarks/vector_search.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from mneme.memory.index import (
    HNSWIndex,
    NativeIndex,
    NumpyIndex,
    VectorIndex,
    _hnsw_available,
    _native_available,
)


@dataclass
class Result:
    backend: str
    n: int
    add_ms: float
    search_ms_mean: float
    qps: float


def _norm_rand(n: int, dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, dim)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    return v


def _bench(make: callable, name: str, vectors: np.ndarray, queries: np.ndarray, k: int) -> Result:
    n, dim = vectors.shape
    idx: VectorIndex = make(dim)
    t0 = time.perf_counter()
    for i in range(n):
        idx.add(f"v{i}", vectors[i])
    add_ms = (time.perf_counter() - t0) * 1000.0

    # warm
    for q in queries[:5]:
        idx.search(q, k)
    t0 = time.perf_counter()
    for q in queries:
        idx.search(q, k)
    total = time.perf_counter() - t0
    search_ms_mean = total / len(queries) * 1000.0
    qps = len(queries) / total if total > 0 else float("inf")
    return Result(name, n, add_ms, search_ms_mean, qps)


def run(sizes: list[int], dim: int = 384, num_queries: int = 100, k: int = 10) -> None:
    backends: list[tuple[str, callable]] = [("numpy", NumpyIndex)]
    if _native_available():
        backends.append(("native", NativeIndex))
    if _hnsw_available():
        backends.append(("hnsw", lambda d: HNSWIndex(dim=d, max_elements=max(sizes) + 10)))

    print(f"dim={dim}  queries={num_queries}  k={k}  backends={[b[0] for b in backends]}\n")
    header = f"{'backend':<8} {'N':>10} {'add (ms)':>10} {'search (ms)':>12} {'QPS':>10}"
    print(header)
    print("-" * len(header))

    queries = _norm_rand(num_queries, dim, seed=42)
    for n in sizes:
        vectors = _norm_rand(n, dim, seed=n)
        for name, make in backends:
            r = _bench(make, name, vectors, queries, k)
            print(
                f"{r.backend:<8} {r.n:>10} {r.add_ms:>10.1f} "
                f"{r.search_ms_mean:>12.3f} {r.qps:>10.1f}"
            )
        print()


if __name__ == "__main__":
    run(sizes=[10_000, 50_000, 100_000])
