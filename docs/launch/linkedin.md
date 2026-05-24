# LinkedIn post

Less technical, more "what & why". Builds your dev brand.

```
Open-sourcing a project I've been building: Mneme.

It's an open-source layer that gives AI assistants real long-term
memory. Plug it into any large language model — Ollama for fully
local inference, or OpenAI / Anthropic / OpenRouter for cloud — and
your assistant remembers you across sessions, not just within one
chat.

Why I built it: every modern chatbot loses its mind the moment the
session ends. The cloud ones hide this behind ever-larger context
windows, but the problem doesn't go away — it just gets postponed.

What's interesting about the implementation:

→ Four kinds of memory, modelled on cognitive science: working,
  episodic, semantic, procedural. Each has its own retention and
  retrieval rules.

→ A background "consolidator" distils raw events into durable facts
  with provenance, so the assistant builds a real model of you over
  time instead of a vector dump.

→ Library + CLI + OpenAI-compatible REST + an MCP server — so it
  drops into Cursor, Claude Desktop, Windsurf and any existing
  OpenAI-SDK code with zero rewrites.

→ Three interchangeable vector-search backends including an optional
  C++17 SIMD + OpenMP core. On a laptop: ~3 ms search on 100k
  memories, single thread.

MIT-licensed, bilingual documentation (English + Russian), CI matrix
on Linux / macOS / Windows × Python 3.10–3.13.

Repo: https://github.com/vladimir120307-droid/mneme

Would love early adopters and critique — especially on the retrieval
scoring formula. If you've thought about long-term agent memory, the
"why" section in the README is the part I'd love feedback on.

#opensource #ai #llm #python #cpp #agents #memory
```

## Notes

- LinkedIn rewards comments more than likes. Reply to every comment in
  the first 24 hours, even short replies.
- 5-7 tasteful hashtags max. The ones above are intentional.
- Don't paste the same image as on X — LinkedIn's preview rendering
  for SVG is unreliable. Use a screenshot of the README hero.
