# r/Python post

**Title:**

```
Mneme — a Python library for long-term AI agent memory (SQLite + numpy + optional C++)
```

**Body (Markdown):**

```markdown
I built a Python library called **Mneme** for giving AI agents real
persistent memory. Sharing here because the implementation side is the
fun part for this audience.

**Highlights for the r/Python crowd:**

- Pure-Python install via `pip install mneme`. No native dependencies
  required to use it.
- SQLite is the durable store, sentence-transformers for embeddings,
  a custom in-process vector index. The vector index has three
  interchangeable backends behind one Python `VectorIndex` interface:
  - **numpy** brute force, default — uses a doubling-capacity buffer so
    `add()` is O(1) amortised instead of O(N) per insert (yes, I shipped
    `np.vstack` first; fixed it after benchmarking).
  - **hnswlib** when you install `mneme[fast]`.
  - **C++17 SIMD + OpenMP** native core via pybind11, drop-in when
    compiled with `python -m mneme.build_native`.
- Typer/Rich CLI, FastAPI REST (OpenAI-compatible), MCP server for
  Cursor/Claude Desktop integration — all under 60 source files.
- Ruff-clean, 21 unit tests, CI matrix on Linux/macOS/Windows ×
  Python 3.10–3.13.

**Numbers** (laptop, dim=384, k=10, numpy backend):

| N | search | QPS |
|---:|---:|---:|
| 10k | 0.21 ms | 4 860 |
| 100k | 3.20 ms | 312 |

**Why interesting Python-wise:**

1. The pure-Python path matches the API of the C++ backend exactly, so
   library code never branches on which backend is loaded.
2. The hybrid retrieval scoring is vectorised over candidate rows with
   numpy and dispatches transparently to a C kernel when present —
   uses an opt-in import inside the hot function.
3. Pydantic v2 for all memory types; SQLite rows store the type-specific
   fields as a JSON column to keep migrations cheap.

Repo: https://github.com/vladimir120307-droid/mneme
Docs: https://github.com/vladimir120307-droid/mneme/tree/master/docs

MIT. Feedback welcome, especially on the numpy backend — there's
probably a smarter way to do the partial top-K than `argpartition`+`argsort`.
```

## Notes

- r/Python rules say no self-promotion blast — frame it as a technical
  share.
- Lead with implementation details, not the product story.
