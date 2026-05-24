# API reference

This document covers both the REST surface (`mneme serve`) and the Python
classes that wrap it.

## REST endpoints

### Health

```
GET /healthz
```

```json
{ "status": "ok", "provider": "ollama", "model": "llama3.1" }
```

### Chat (OpenAI-compatible)

```
POST /v1/chat/completions
```

Request body:

```json
{
  "model": "llama3.1",
  "messages": [
    { "role": "system", "content": "you are a helpful assistant" },
    { "role": "user", "content": "where do I live?" }
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "stream": false
}
```

Mneme injects an additional system message in front of yours with the
retrieved memories. The response is in the same shape as OpenAI's:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1739023412,
  "model": "llama3.1",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "Berlin." },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 124, "completion_tokens": 4 }
}
```

When `"stream": true` the response is a `text/event-stream` of OpenAI
chunk objects ending with `data: [DONE]`.

### Memory CRUD

```
GET    /v1/memories?kind=episodic&limit=50
POST   /v1/memories                       (body: see below)
GET    /v1/memories/{id}
DELETE /v1/memories/{id}
```

Body for `POST /v1/memories`:

```json
{
  "kind": "episodic",          // "episodic" | "semantic" | "procedural"
  "content": "free-text...",
  "importance": 0.7,
  "tags": ["work", "rust"]
}
```

### Memory search

```
POST /v1/memories/search
```

```json
{ "query": "rust", "kind": "episodic", "k": 5 }
```

Response:

```json
{
  "hits": [
    {
      "memory": { "id": "...", "kind": "episodic", "content": "...", "...": "..." },
      "score": 0.812
    }
  ]
}
```

### Consolidate

```
POST /v1/consolidate
```

Triggers one consolidation pass. Returns `{ "created_semantic_memories": N }`.

### Stats

```
GET /v1/stats
```

```json
{ "working": 8, "episodic": 124, "semantic": 33, "procedural": 4, "total": 169 }
```

## Python API

```python
from mneme import Agent, MemoryStore
from mneme.agent import AgentConfig
from mneme.memory.types import EpisodicMemory, MemoryKind
```

### Agent

```python
agent = Agent(AgentConfig(provider="ollama", model="llama3.1"))

await agent.chat("hello")                   # str
async for piece in agent.stream("hello"):   # async iterator of text chunks
    ...

agent.remember("the user lives in Berlin", importance=0.9)
agent.forget(memory_id)
agent.close()
```

### MemoryStore

```python
store = MemoryStore(path="/data/mneme")
mem = store.add(EpisodicMemory(content="..."))
store.get(mem.id)                          # Memory | None
store.list(kind=MemoryKind.SEMANTIC, limit=100)
store.search("rust async", kind=MemoryKind.EPISODIC, k=10)
store.count(MemoryKind.EPISODIC)
store.decay(half_life_days=30, importance_floor=0.2)
store.delete(mem.id)
store.close()
```

`search()` returns `list[tuple[Memory, float]]` already ordered by score.
`add()` and `add_many()` compute embeddings in one batched call.

### Memory types

All four types share the same base fields and extend with their own:

```python
WorkingMemory(content="...", role="user", session_id="...")
EpisodicMemory(content="...", source="user", importance=0.6)
SemanticMemory(content="...", confidence=0.8, support=["episode_id1"])
ProceduralMemory(content="...", name="...", trigger="...", steps=[...])
```

### Providers

```python
from mneme.providers import get_provider, Message

provider = get_provider("openai", api_key="sk-...")
resp = await provider.chat(
    [Message(role="user", content="hi")],
    model="gpt-4o-mini",
)
print(resp.content)
```

Recognised provider names: `ollama`, `openai`, `anthropic`, `openrouter`,
`lmstudio`, `vllm`. All implement the same `LLMProvider` interface, so
swapping is one line.
