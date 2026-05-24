# Mneme Memory Model

Mneme borrows its memory architecture from human cognitive science. There are four
distinct kinds of memory, each with different retention, retrieval and update rules.
This separation is what lets the agent stay coherent over weeks and months, instead
of forgetting everything past its context window like a stateless chatbot.

## Overview

```
                       ┌────────────────────┐
                       │   Working memory   │  ← current conversation, volatile
                       └─────────┬──────────┘
                                 │ flush
                                 ▼
   ┌────────────┐  consolidate  ┌────────────┐
   │  Episodic  │ ─────────────▶│  Semantic  │  ← long-term knowledge
   │   memory   │               │   memory   │
   └─────┬──────┘               └────────────┘
         │                              ▲
         │ extract                      │
         ▼                              │
   ┌────────────┐  patterns / how-to   │
   │ Procedural │ ─────────────────────┘
   │   memory   │
   └────────────┘
```

## Working memory

The short-term buffer that sits in the model's context window during a conversation.

- Holds the last N turns (configurable, default 20).
- Volatile: dropped when the session ends, unless promoted.
- On every turn, salient items are tagged for promotion to episodic.

## Episodic memory

Specific events: "user said X on date Y", "tool Z returned this error", "we agreed
to use stack W". Each episode is timestamped and tied to a source.

- **Fields:** `id`, `content`, `embedding`, `created_at`, `last_accessed_at`,
  `access_count`, `importance` (0..1), `source` (user / tool / self), `tags`.
- **Retrieval:** vector similarity + recency boost + importance boost +
  access-count boost. The exact formula lives in `mneme.memory.retrieval`.
- **Decay:** an episode with low importance that has not been accessed within
  the configured half-life becomes eligible for pruning.

## Semantic memory

Generalised, time-independent facts derived from episodes. "The user is named
Vladimir." "The user prefers terse responses in Russian." "Project X uses Postgres."

- **Fields:** `id`, `statement`, `embedding`, `confidence` (0..1), `support`
  (list of episodic ids that produced it), `updated_at`.
- **Sourcing:** built only by the consolidation pass, never by the foreground
  agent. This keeps semantic memory clean.
- **Conflict handling:** when a new fact contradicts an existing one, both are
  kept but the older one is marked superseded; the agent sees the freshest and
  can dig into history if needed.

## Procedural memory

How to do things. Stored skills, scripts, tool sequences, workflows.

- **Fields:** `id`, `name`, `trigger` (when to use), `steps`, `tools_used`,
  `success_rate`.
- **Sourcing:** can be added explicitly by the user, or extracted from episodic
  by the consolidator when it spots a repeated successful pattern.

## Consolidation ("sleep")

Periodically (or on demand), Mneme runs a background pass:

1. **Promote.** Salient working-memory items become episodic.
2. **Generalise.** Clusters of related episodes become semantic facts.
3. **Pattern.** Repeated successful action sequences become procedural skills.
4. **Forget.** Low-importance, low-access episodes past their half-life are
   pruned. Semantic facts they supported either keep their other support or
   are demoted to low confidence.

Consolidation runs in a worker thread with a small LLM call budget per cycle,
so it is cheap to run continuously.

## Retrieval at request time

When the user sends a message, Mneme assembles context like this:

1. **Working** memory (verbatim, last N turns).
2. Top-K **semantic** facts ranked by `similarity * confidence`.
3. Top-K **episodic** memories ranked by the composite score above.
4. Any **procedural** skill whose `trigger` matches the request.

The retrieval module enforces an overall token budget and drops the
lowest-ranked items until the budget is met. The selected pieces become the
system message that frames the model call.
