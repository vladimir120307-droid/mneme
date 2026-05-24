# r/LocalLLaMA post

**Flair:** Resources / Tutorial (whichever the subreddit uses for tools)

**Title:**

```
[Tool] Mneme — give any local LLM real long-term memory (Ollama, llama.cpp, anything OpenAI-compatible)
```

**Body (Markdown):**

```markdown
I kept hitting the same wall: I'd set up a local Ollama, chat for an
hour, close it, and the model forgets everything next time. The cloud
ones aren't different — they just hide it behind longer context.

So I built **Mneme**: a small open-source layer that gives any LLM
persistent, structured memory.

**What's different from "just stuff it in a vector DB":**

- Four kinds of memory: *working* (current chat), *episodic* (events
  with timestamps), *semantic* (distilled facts), *procedural* (how-to).
  Each has its own retention and retrieval rules.
- A background consolidator runs LLM calls to extract durable facts
  out of episodes — so "the user lives in Berlin" eventually becomes
  a clean semantic memory, not a vector dump of every "where do I
  live?" exchange.
- Hybrid retrieval: similarity + recency + importance + access boost,
  vectorised; optional C++ SIMD+OpenMP backend.

**Why you might care if you live on local stacks:**

- Pure local: works with Ollama and any OpenAI-compatible local
  server (LM Studio, vLLM, llama-cpp's server, etc).
- SQLite single-file durable; nothing leaves the machine.
- Drop-in: serves an OpenAI-compatible REST so your existing tools
  point at `http://localhost:8077/v1` and just work.
- Also runs as an **MCP server** — Cursor/Claude Desktop/Windsurf
  can use it as shared memory across all of them.

**Numbers** (laptop, single thread, dim=384):

| N | search | QPS |
|---:|---:|---:|
| 10k | 0.21 ms | 4 860 |
| 50k | 1.64 ms | 609 |
| 100k | 3.20 ms | 312 |

**Repo:** https://github.com/vladimir120307-droid/mneme
**Quickstart:** docs/quickstart.md
**Memory model writeup:** docs/memory-model.md

MIT, bilingual docs (EN/RU). Critique very welcome — the retrieval
scoring formula in particular is a guess that I'd love to see beaten.
```

## Notes

- r/LocalLLaMA hates marketing tone. Lead with the problem.
- Mods often remove self-promotion if it's your first post. Comment on
  a few other threads in the prior week.
- Mention Ollama early — it's their lingua franca.
