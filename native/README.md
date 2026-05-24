# Native core

C++17 implementation of the hot path: brute-force cosine vector search
(auto-vectorised, OpenMP-parallel) and the hybrid retrieval scoring kernel.
The Python package works without this — it's a drop-in accelerator selected
automatically when present.

## Prerequisites

* CMake ≥ 3.18
* A C++17 compiler
  * Windows: Visual Studio Build Tools (MSVC ≥ 19.14) **or** MinGW-w64
  * macOS / Linux: gcc ≥ 9 or clang ≥ 10
* The project's Python venv must be active (we use it to locate Python and pybind11)

```bash
pip install pybind11
```

## Build

From the repo root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j
```

CMake's install step drops the compiled module next to the Python package:

```bash
cmake --install build --prefix src
```

Verify:

```bash
python -c "from mneme import _native; print(_native.VectorIndex(384))"
```

When import succeeds, `mneme.memory.index.make_index(..., backend="auto")`
will pick the native backend automatically. Otherwise it falls back to the
numpy implementation.

## What lives here

| File | Purpose |
|---|---|
| `include/mneme/vector_index.hpp` | Header for the brute-force index |
| `include/mneme/scoring.hpp`     | Header for the hybrid score kernel |
| `src/vector_index.cpp`          | Cosine search with OpenMP, file persistence |
| `src/scoring.cpp`               | Batched score computation |
| `src/bindings.cpp`              | pybind11 module `mneme._native` |

## Benchmark

```bash
python benchmarks/vector_search.py
```

The script ramps from 10k to 1M vectors and prints latency for the numpy
and native backends side by side.
