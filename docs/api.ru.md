# API

Документ покрывает REST-поверхность (`mneme serve`) и Python-классы,
которые её оборачивают.

## REST-эндпоинты

### Здоровье

```
GET /healthz
```

```json
{ "status": "ok", "provider": "ollama", "model": "llama3.1" }
```

### Чат (OpenAI-совместимый)

```
POST /v1/chat/completions
```

Тело запроса:

```json
{
  "model": "llama3.1",
  "messages": [
    { "role": "system", "content": "ты полезный ассистент" },
    { "role": "user", "content": "где я живу?" }
  ],
  "temperature": 0.7,
  "max_tokens": 512,
  "stream": false
}
```

Mneme добавляет в начало свой system-блок с найденными памятями. Формат
ответа совпадает с OpenAI:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1739023412,
  "model": "llama3.1",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "В Берлине." },
      "finish_reason": "stop"
    }
  ],
  "usage": { "prompt_tokens": 124, "completion_tokens": 4 }
}
```

При `"stream": true` — `text/event-stream` с чанками в формате OpenAI,
завершается `data: [DONE]`.

### CRUD памяти

```
GET    /v1/memories?kind=episodic&limit=50
POST   /v1/memories                       (тело ниже)
GET    /v1/memories/{id}
DELETE /v1/memories/{id}
```

Тело `POST /v1/memories`:

```json
{
  "kind": "episodic",
  "content": "произвольный текст...",
  "importance": 0.7,
  "tags": ["work", "rust"]
}
```

### Поиск по памяти

```
POST /v1/memories/search
```

```json
{ "query": "rust", "kind": "episodic", "k": 5 }
```

Ответ:

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

### Консолидация

```
POST /v1/consolidate
```

Запускает один прогон консолидации. Возвращает
`{ "created_semantic_memories": N }`.

### Статистика

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

await agent.chat("привет")
async for piece in agent.stream("привет"):
    ...

agent.remember("юзер живёт в Берлине", importance=0.9)
agent.forget(memory_id)
agent.close()
```

### MemoryStore

```python
store = MemoryStore(path="/data/mneme")
mem = store.add(EpisodicMemory(content="..."))
store.get(mem.id)
store.list(kind=MemoryKind.SEMANTIC, limit=100)
store.search("rust async", kind=MemoryKind.EPISODIC, k=10)
store.count(MemoryKind.EPISODIC)
store.decay(half_life_days=30, importance_floor=0.2)
store.delete(mem.id)
store.close()
```

`search()` возвращает `list[tuple[Memory, float]]`, уже отсортированный.
`add()` и `add_many()` считают эмбеддинги одним батчем.

### Типы памяти

Все четыре типа делят базовые поля и расширяют свои:

```python
WorkingMemory(content="...", role="user", session_id="...")
EpisodicMemory(content="...", source="user", importance=0.6)
SemanticMemory(content="...", confidence=0.8, support=["episode_id1"])
ProceduralMemory(content="...", name="...", trigger="...", steps=[...])
```

### Провайдеры

```python
from mneme.providers import get_provider, Message

provider = get_provider("openai", api_key="sk-...")
resp = await provider.chat(
    [Message(role="user", content="hi")],
    model="gpt-4o-mini",
)
print(resp.content)
```

Имена: `ollama`, `openai`, `anthropic`, `openrouter`, `lmstudio`, `vllm`.
Все реализуют общий интерфейс `LLMProvider`, переход — одна строчка.
