# Configuration

Everything is overridable through environment variables, CLI flags, or
construction-time arguments. The precedence is: explicit CLI flag /
constructor arg > environment variable > built-in default.

## Environment variables

| Variable | Default | What it controls |
|---|---|---|
| `MNEME_PROVIDER` | `ollama` | LLM backend: `ollama`, `openai`, `anthropic`, `openrouter`, `lmstudio`, `vllm` |
| `MNEME_MODEL` | `llama3.1` | Model name on the chosen provider |
| `MNEME_DATA_DIR` | OS user data dir | Where the SQLite + vector index live |
| `MNEME_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model used to compute vectors |
| `MNEME_HOST` | `127.0.0.1` | REST server bind address |
| `MNEME_PORT` | `8077` | REST server port |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint (read by the Ollama provider) |
| `OPENAI_API_KEY` | — | API key for OpenAI provider |
| `OPENROUTER_API_KEY` | — | API key for OpenRouter provider |
| `ANTHROPIC_API_KEY` | — | API key for Anthropic provider |

## CLI flags

```
mneme chat   --provider OPENAI --model gpt-4o-mini
mneme ask    --provider ollama --model llama3.1 "your question"
mneme serve  --host 0.0.0.0 --port 9000 --provider ollama --model llama3.1
mneme remember "fact..." --importance 0.8
mneme memory list   --kind episodic --limit 50
mneme memory search "query" --kind semantic --top 20
mneme memory forget <id-prefix>
mneme memory stats
mneme memory decay --half-life 30 --importance 0.2
```

## AgentConfig

The Python API mirrors the env defaults.

```python
from mneme.agent import AgentConfig
from mneme.memory.retrieval import RetrievalConfig

config = AgentConfig(
    provider="ollama",
    model="llama3.1",
    temperature=0.7,
    max_tokens=None,            # provider default
    working_window=12,          # last N turns kept in the context
    system_prompt="You are ...",
    retrieval=RetrievalConfig(
        semantic_k=5,
        episodic_k=5,
        procedural_k=3,
        max_chars=4_000,
    ),
    consolidate_every=10,       # turns between consolidation passes
    provider_options={},        # forwarded to the provider's __init__
)
```

## MemoryStore

```python
from mneme.memory.store import MemoryStore
from mneme.memory.embeddings import Embedder

store = MemoryStore(
    path="/path/to/data",       # or None — uses MNEME_DATA_DIR / OS default
    embedder=Embedder("BAAI/bge-small-en-v1.5"),  # any sentence-transformers model
    index_backend="auto",       # "auto", "native", "hnsw", "numpy"
)
```

## Retrieval scoring weights

Tune these in `MemoryStore.search()` if the defaults don't fit your data:

```python
store.search(
    "query",
    k=10,
    recency_half_life_days=30.0,
    weights=(0.55, 0.20, 0.20, 0.05),  # (similarity, recency, importance, access)
)
```

The weights need not sum to 1.0 — scoring is a linear combination and the
final ranking is what matters.

## Decay policy

`MemoryStore.decay()` prunes low-value episodic memories. Defaults:

```python
store.decay(
    half_life_days=30.0,     # only consider items past this age
    importance_floor=0.2,    # only consider items below this importance
    min_access=1,            # only consider items rarely accessed
)
```

Semantic and procedural memories are never auto-pruned — they're produced
by the consolidator and outlive episodes by design.

## Where data lives by default

- **Linux:** `~/.local/share/mneme/`
- **macOS:** `~/Library/Application Support/mneme/`
- **Windows:** `%LOCALAPPDATA%\mneme\`

Override with `MNEME_DATA_DIR`. Inside that directory:

```
mneme/
├── memories.db          SQLite (durable copy)
├── memories.idx.npz     numpy-backend vector index
└── memories.idx.bin     native-backend vector index (if compiled)
```
