# Show HN

**Title (≤80 chars, no emoji, no marketing speak):**

```
Show HN: Mneme – local-first AI agent with human-like long-term memory
```

**URL:** https://github.com/vladimir120307-droid/mneme

**Text (optional but encouraged on Show HN, plain text, no Markdown):**

```
Hi HN — Mneme is a small open-source layer that sits between you and any
LLM (Ollama, OpenAI, Anthropic, OpenRouter, LM Studio, vLLM) and gives
it persistent, structured memory.

Every chatbot loses its mind the moment a session ends. I wanted an
assistant that actually remembers across weeks. The interesting part
isn't "store embeddings"; it's that there are four kinds of memory,
each with its own retention and retrieval rules, modelled on the
cognitive-science split: working / episodic / semantic / procedural.
A background consolidator distils episodes into durable facts with
provenance.

Concretely:

- Library + CLI + OpenAI-compatible REST + MCP server, one install.
  Any OpenAI SDK or any MCP client (Cursor, Claude Desktop, Windsurf)
  can plug in unchanged.
- SQLite is the single source of truth. Vector index has three back-
  ends behind one API: a pure-numpy brute force (default, no compiler
  needed), hnswlib, and a C++17 SIMD+OpenMP native core via pybind11.
- The numpy backend uses a doubling-capacity buffer so add() is O(1)
  amortised. On a laptop, dim=384, k=10: ~3.2 ms search and ~183 ms to
  insert 100k vectors.
- 21 unit tests, ruff clean, CI on Linux/macOS/Windows × Python 3.10-3.13.
  Docs and README are bilingual EN/RU.

What I'd love feedback on:

1. The four-tier memory model — does the split feel right, or should
   semantic and procedural be the same thing?
2. Retrieval scoring is similarity 0.55 + recency 0.20 + importance 0.20
   + access 0.05. Anyone tried something better?
3. Is the MCP integration the right primary entry point in 2026, or
   should I lean harder on the standalone agent?

Repo: https://github.com/vladimir120307-droid/mneme
Quickstart: https://github.com/vladimir120307-droid/mneme/blob/master/docs/quickstart.md
```

## Notes

- Show HN rule: this must be something you built and others can use.
  Don't post until the README, install, and demo all work cleanly on a
  fresh machine.
- Don't post during US morning if you're outside US-friendly hours and
  can't be there for replies for 4+ hours.
- First comment should be from the author with one concrete question
  that invites response.
