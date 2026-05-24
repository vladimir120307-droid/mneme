# Changelog

All notable changes to this project are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-05-24

The initial public release. Mneme is a local-first AI agent with
human-like long-term memory.

### Added

- Four-tier memory model (working / episodic / semantic / procedural)
  backed by SQLite plus a pluggable vector index.
- Vector index backends: pure-numpy brute force (default, amortised
  O(1) inserts via doubling capacity buffer), `hnswlib` for sub-linear
  search on very large stores, and an optional C++17 SIMD + OpenMP
  native backend wrapped with pybind11.
- Hybrid retrieval scoring vectorised over candidates with a transparent
  dispatch to the native kernel when available.
- LLM provider adapters: Ollama, OpenAI, Anthropic, OpenRouter,
  LM Studio, vLLM — all behind one `LLMProvider` interface.
- Background consolidator: periodically asks the model to distil
  durable semantic facts from recent episodes, with confidence and
  provenance.
- CLI (`mneme`) on Typer + Rich with `chat`, `ask`, `serve`,
  `remember`, and `memory list/search/forget/stats/decay`.
- REST server (`mneme serve`) on FastAPI, OpenAI-compatible chat plus
  Mneme-specific memory CRUD, search, consolidate and stats endpoints.
- Bilingual documentation (EN + RU) covering quickstart, architecture,
  configuration, API reference, memory model, and benchmarks.
- GitHub Actions CI matrix: pytest + ruff on Linux / macOS / Windows
  across Python 3.10–3.13, plus a separate job that builds the native
  core and runs parity tests.

### Performance

- numpy backend, dim=384, k=10, single thread:
  - 10 000 vectors: 0.21 ms search · 4 860 QPS
  - 50 000 vectors: 1.64 ms search · 609 QPS
  - 100 000 vectors: 3.20 ms search · 312 QPS · 183 ms add
- `add` complexity dropped from O(N) per insert to O(1) amortised by
  replacing `np.vstack` with a doubling capacity buffer (~7400×
  speed-up at 50 k vectors).

[Unreleased]: https://github.com/vladimir120307-droid/mneme/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vladimir120307-droid/mneme/releases/tag/v0.1.0
