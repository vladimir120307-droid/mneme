# X / Twitter launch thread

8 tweets. Drop the demo GIF or banner on tweet 1. Keep each ≤270 chars.

---

**1/**

```
Released Mneme — an open-source layer that gives any LLM real long-term
memory.

Your assistant remembers you across weeks. Not just within one chat.

Local-first. Works with Ollama, OpenAI, Anthropic. MIT.

github.com/vladimir120307-droid/mneme

[attach: assets/demo.svg]
```

**2/**

```
The trick isn't "store embeddings". It's four kinds of memory, each
with its own retention rules — modelled on how human memory actually
works:

· working  — current chat
· episodic — events with time
· semantic — distilled facts
· procedural — skills / how-to
```

**3/**

```
A background consolidator distils episodes into durable facts.

"Remember I'm in Berlin"  (one episode)
"User asked about Berlin restaurants"  (another)
"User mentioned Berlin standup time"  (another)

→ semantic memory: "user lives in Berlin"

with provenance back to all three.
```

**4/**

```
Retrieval is hybrid:

similarity · 0.55
recency · 0.20
importance · 0.20
access_boost · 0.05

vectorised in numpy, with transparent dispatch to a C++17 SIMD+OpenMP
kernel when compiled.
```

**5/**

```
Three interchangeable vector-index backends behind one API:

· numpy brute force (default, no compiler)
· hnswlib
· custom C++17 with SIMD + OpenMP

Auto-select: best available wins.

100k vectors, single thread, k=10: 3.2 ms search · 4860 QPS at 10k.
```

**6/**

```
Surface area:

· Python lib
· CLI (mneme chat / serve / memory ...)
· OpenAI-compatible REST (any OpenAI SDK just points at it)
· MCP server for Cursor / Claude Desktop / Windsurf — shared memory
  across all of them

One install: pip install mneme.
```

**7/**

```
Why I built it: every chatbot loses its mind when a session ends. The
cloud ones just hide it behind longer context. I wanted an assistant
that genuinely accumulates knowledge of me over months.

Now I have one. And it's offline-capable.
```

**8/**

```
MIT-licensed. Bilingual docs (EN + RU). CI on Linux/macOS/Windows ×
Python 3.10–3.13.

Star, fork, break it:
github.com/vladimir120307-droid/mneme

Critique on the retrieval scoring formula especially welcome.
```

## Notes

- Don't @-tag anyone in the first hour. Let the thread breathe.
- Pin tweet 1 after thread completes.
- Quote-retweet from a second account ~30 min in to extend reach is fine,
  buying engagement is not.
