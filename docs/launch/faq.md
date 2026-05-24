# FAQ for launch threads

These are the predictable comments. Have answers ready.

---

**Q: "Isn't this just MemGPT / Letta / Mem0 / Cognee?"**

Closest relatives, but different positioning. Letta is a server-style
agent runtime with paged context; Mem0 is a memory library with a
managed cloud; Cognee is closer in spirit but heavier (graph database,
multi-process). Mneme is single-process, single SQLite file, drop-in
under any OpenAI-SDK code or any MCP client. The four-tier memory model
and the consolidator are the design pieces I haven't seen in any of
them; the C++ SIMD core is the implementation piece.

---

**Q: "Why not just put it in the system prompt / use long context?"**

Long context doesn't compose: every session re-pays the token cost,
costs grow with the assistant's age, and retrieval still loses to
recency bias inside the model. Persistent memory is cheap, structured,
and survives provider switches.

---

**Q: "Why SQLite? Why not Postgres / Qdrant / Chroma?"**

Because the goal is local-first, single-file install, zero-config.
The day someone needs to scale past one machine, the storage layer
already isolates that decision — `MemoryStore` is an interface.

---

**Q: "Embeddings model is small (MiniLM). Won't that hurt recall?"**

It's a default, swappable for any `sentence-transformers` model via
`MNEME_EMBEDDING_MODEL`. MiniLM was picked for fast install and small
download. For a real workload, `bge-small-en-v1.5` or
`bge-large-en-v1.5` is usually a strict improvement.

---

**Q: "Brute force scales horribly at 1M+ vectors."**

Yes. That's why `hnswlib` is an opt-in backend (`pip install mneme[fast]`).
For most personal-assistant scenarios the store is well under 100k
items and the linear scan wins on simplicity and exactness.

---

**Q: "The 'AI consolidator' is just another LLM call?"**

Yes — bounded to one call per cycle, with a strict JSON schema. The
cost is in the noise compared to actual chat turns, and you can run it
manually (`POST /v1/consolidate`) or never.

---

**Q: "Why pybind11 and not Rust+PyO3?"**

Personal stack preference. The C++ side is ~200 lines; rewriting in
Rust would be a couple of hours but doesn't change the externally
visible behaviour. PRs welcome.

---

**Q: "Will you support tool use / function calling?"**

On the roadmap. The architecture already separates the provider layer
from the agent loop, so adding structured function calls is local to
the `LLMProvider` adapters.

---

**Q: "Is this safe to put on a public server?"**

`mneme serve` binds to `127.0.0.1` by default and has no auth — same
posture as Ollama. If you need to expose it, put it behind a reverse
proxy with auth. The `SECURITY.md` documents this explicitly.

---

**Q: "Why bilingual docs in EN + RU? Doesn't that dilute focus?"**

Two of the loudest open-source AI communities right now are English
and Russian-speaking. Both are full of capable contributors. The two
languages don't compete for attention; they double the surface area.
