# Benchmarks

Numbers below are reproducible via:

```bash
python benchmarks/vector_search.py
```

Hardware: Windows 11, Python 3.13, single thread (numpy backend doesn't
parallelise the matvec; the native backend does via OpenMP).

## Vector search · numpy backend

`dim = 384` (matching `all-MiniLM-L6-v2`), `k = 10`, 100 queries.

| N (vectors) | add (total ms) | search (mean ms) | QPS |
|---:|---:|---:|---:|
| 10 000 | 18 | 0.21 | 4 860 |
| 50 000 | 94 | 1.64 | 609 |
| 100 000 | 183 | 3.20 | 312 |

`add` is O(1) amortised thanks to a doubling capacity buffer — inserting
100 k vectors costs ~180 ms total, not ~10 minutes.

## Notes on the native backend

When `mneme._native` is compiled (via `python -m mneme.build_native`),
the same brute-force algorithm runs in C++17 with auto-vectorised
SIMD inner loops and OpenMP parallelism across rows. The Python wrapper
adds essentially no overhead — measurements track the same shape but
with a lower constant.

The CI run on a fresh runner publishes its own numbers as a build
artefact under the `native` workflow job.

## When to switch backends

- **< 100 k vectors:** numpy is fine; sub-5 ms search means hundreds of
  QPS on a single thread.
- **100 k – 1 M:** native gives a clean multiplier on top.
- **> 1 M:** consider HNSW (`pip install "mneme[fast]"`) — sub-linear
  search at the cost of being approximate.

## How scoring scales

The hybrid scoring kernel (`_hybrid_score` in `memory/store.py`) is
vectorised over the K candidates returned by the index. With the native
core present it dispatches to `_native.compute_scores`. End-to-end
`MemoryStore.search()` latency is dominated by the index lookup, not
scoring, for K up to a few hundred.
