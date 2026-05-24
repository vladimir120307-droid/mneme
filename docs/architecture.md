# Architecture

This document is the bird's-eye view: every box that exists, how they
connect, and which decisions are load-bearing.

## Big picture

```
┌──────────────────────────────────────────────────────────────────────┐
│                              Agent                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │  Receive    │ →  │  Retrieve    │ →  │  Provider.chat / stream │ │
│  │  user turn  │    │  context     │    │  (Ollama / OpenAI / …)  │ │
│  └─────────────┘    └──────┬───────┘    └────────┬────────────────┘ │
│                            │                      │                  │
│                            ▼                      ▼                  │
│                  ┌──────────────────┐   ┌────────────────────┐       │
│                  │  MemoryStore     │ ◀ │  Remember turn,    │       │
│                  │  (SQLite +       │   │  trigger consolida │       │
│                  │   vector index)  │   │  tion on schedule  │       │
│                  └──────────────────┘   └────────────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

## Modules

```
src/mneme/
├── agent.py              high-level Agent class, the entry point
├── consolidation.py      LLM-driven episodic → semantic distillation
├── config.py             env-based settings
├── memory/
│   ├── types.py          pydantic models for the four kinds
│   ├── store.py          SQLite-backed durable store
│   ├── index.py          vector index backends (native / hnsw / numpy)
│   ├── embeddings.py     sentence-transformers wrapper (lazy)
│   └── retrieval.py      hybrid scoring + context-block assembly
├── providers/
│   ├── base.py           LLMProvider abstract base + Message dataclass
│   ├── ollama.py
│   ├── openai_compat.py  OpenAI, OpenRouter, LM Studio, vLLM
│   ├── anthropic.py
│   └── registry.py       short-name lookup
├── api/server.py         FastAPI REST surface, OpenAI-compatible
├── api/schemas.py        request/response models
├── build_native.py       CMake wrapper for the optional C++ core
└── cli.py                Typer-based command line
```

## The hot path: a single turn

1. `Agent.chat(user_input)` is called.
2. `retrieve()` (in `memory/retrieval.py`) asks `MemoryStore.search()` for
   the top-K episodic, semantic and procedural memories given the query.
   - `search` first runs vector similarity through the index backend, then
     scores candidates with a **hybrid** formula: similarity · 0.55 +
     recency · 0.20 + importance · 0.20 + access-boost · 0.05. The scoring
     itself is vectorised (numpy, or the native kernel when compiled).
3. The retrieved memories are formatted as a system message and prepended
   to the chat history.
4. The provider is called (`provider.chat` or `provider.stream`).
5. Both the user turn and the assistant response are written as
   `WorkingMemory`. The user turn is additionally promoted to
   `EpisodicMemory` with a heuristic importance.
6. Every N turns (configurable), `Consolidator.run_once()` fires: it asks
   the model to extract durable facts from recent episodes and writes
   them as `SemanticMemory` with provenance links.

## Vector index backends

Three implementations live behind the same `VectorIndex` interface:

| Backend | When picked | Strengths | Caveats |
|---|---|---|---|
| `NativeIndex` | `auto`, native built | SIMD + OpenMP brute force; fastest single-thread; predictable | Needs C++ compiler at build time |
| `HNSWIndex` | `auto` fallback, hnswlib installed | Sub-linear search for very large stores | Approximate; hnswlib needs C/C++ build |
| `NumpyIndex` | `auto` fallback, always available | Pure Python install; exact | Linear scan |

Selection: `make_index(dim, backend="auto")` tries native → hnsw → numpy.
Override with `backend="numpy"`, `"hnsw"`, or `"native"`.

The numpy backend uses an amortised-growth backing buffer (capacity
doubles on overflow) so `add` is O(1) amortised. Search is a single dense
matrix-vector product plus partial top-K via `argpartition`.

## Storage

SQLite is the single source of truth. The schema is one table:

```sql
CREATE TABLE memories (
  id                TEXT PRIMARY KEY,
  kind              TEXT NOT NULL,
  content           TEXT NOT NULL,
  created_at        REAL NOT NULL,        -- unix seconds
  last_accessed_at  REAL NOT NULL,
  access_count      INTEGER NOT NULL DEFAULT 0,
  importance        REAL NOT NULL DEFAULT 0.5,
  tags              TEXT NOT NULL DEFAULT '[]',
  metadata          TEXT NOT NULL DEFAULT '{}',
  type_fields       TEXT NOT NULL DEFAULT '{}'
);
```

Indexes on `kind`, `created_at` and `importance` keep listing and decay
queries fast. Type-specific fields (e.g. `confidence` on semantic memories)
live in the `type_fields` JSON column — easier to evolve than columns.

The vector index lives in a sibling file (`memories.idx.npz` or
`memories.idx.bin` depending on backend) and is rebuilt from the SQLite
content on demand if the persisted file is missing.

## REST surface

The FastAPI server exposes both an OpenAI-compatible chat endpoint and
Mneme-specific routes:

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/chat/completions` | OpenAI-compatible, with memory-augmented context |
| GET  | `/v1/memories?kind=…&limit=…` | List |
| POST | `/v1/memories` | Create |
| GET  | `/v1/memories/{id}` | Fetch |
| DELETE | `/v1/memories/{id}` | Delete |
| POST | `/v1/memories/search` | Hybrid search |
| POST | `/v1/consolidate` | Run a consolidation pass synchronously |
| GET  | `/v1/stats` | Counts per kind |
| GET  | `/healthz` | Liveness |

## Design notes

- **One source of truth.** SQLite holds the durable copy; the vector
  index is derivable from it. If the index file is missing or corrupt,
  it is rebuilt.
- **No magic.** No background threads, no implicit network calls. The
  consolidator is an `await`-able pass that the agent triggers on
  schedule; nothing happens behind your back.
- **Provider-agnostic.** The agent never depends on a specific provider
  class. Swapping `MNEME_PROVIDER` is the only change needed to move
  between local and cloud inference.
- **Drop-in native.** The C++ core wraps the exact same Python
  interface, so user code never branches on which backend is loaded.
