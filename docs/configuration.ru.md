# Конфигурация

Всё переопределяется через переменные среды, флаги CLI или аргументы
конструктора. Приоритет: явный флаг/аргумент > переменная среды > дефолт.

## Переменные среды

| Переменная | По умолчанию | Что управляет |
|---|---|---|
| `MNEME_PROVIDER` | `ollama` | LLM-бэкенд: `ollama`, `openai`, `anthropic`, `openrouter`, `lmstudio`, `vllm` |
| `MNEME_MODEL` | `llama3.1` | Имя модели у провайдера |
| `MNEME_DATA_DIR` | каталог пользователя ОС | Где живут SQLite + индекс |
| `MNEME_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Модель эмбеддингов |
| `MNEME_HOST` | `127.0.0.1` | Адрес REST-сервера |
| `MNEME_PORT` | `8077` | Порт REST-сервера |
| `OLLAMA_HOST` | `http://localhost:11434` | Эндпоинт Ollama |
| `OPENAI_API_KEY` | — | Ключ для OpenAI |
| `OPENROUTER_API_KEY` | — | Ключ для OpenRouter |
| `ANTHROPIC_API_KEY` | — | Ключ для Anthropic |

## Флаги CLI

```
mneme chat   --provider OPENAI --model gpt-4o-mini
mneme ask    --provider ollama --model llama3.1 "вопрос"
mneme serve  --host 0.0.0.0 --port 9000 --provider ollama --model llama3.1
mneme remember "факт..." --importance 0.8
mneme memory list   --kind episodic --limit 50
mneme memory search "запрос" --kind semantic --top 20
mneme memory forget <префикс-id>
mneme memory stats
mneme memory decay --half-life 30 --importance 0.2
```

## AgentConfig

Python-API повторяет env-дефолты.

```python
from mneme.agent import AgentConfig
from mneme.memory.retrieval import RetrievalConfig

config = AgentConfig(
    provider="ollama",
    model="llama3.1",
    temperature=0.7,
    max_tokens=None,            # дефолт провайдера
    working_window=12,          # сколько последних ходов держать в контексте
    system_prompt="You are ...",
    retrieval=RetrievalConfig(
        semantic_k=5,
        episodic_k=5,
        procedural_k=3,
        max_chars=4_000,
    ),
    consolidate_every=10,       # ходов между прогонами консолидации
    provider_options={},        # пробрасывается в __init__ провайдера
)
```

## MemoryStore

```python
from mneme.memory.store import MemoryStore
from mneme.memory.embeddings import Embedder

store = MemoryStore(
    path="/путь/к/данным",         # None → MNEME_DATA_DIR / дефолт ОС
    embedder=Embedder("BAAI/bge-small-en-v1.5"),  # любая sentence-transformers
    index_backend="auto",          # "auto", "native", "hnsw", "numpy"
)
```

## Веса гибридного скоринга

Тонкая настройка `MemoryStore.search()`:

```python
store.search(
    "запрос",
    k=10,
    recency_half_life_days=30.0,
    weights=(0.55, 0.20, 0.20, 0.05),  # (similarity, recency, importance, access)
)
```

Сумма весов может быть не 1.0 — скоринг линейный, важен только итоговый
порядок.

## Политика забывания (decay)

`MemoryStore.decay()` отсеивает низкоценные старые эпизоды. Дефолты:

```python
store.decay(
    half_life_days=30.0,     # рассматриваем только записи старше этого
    importance_floor=0.2,    # и с importance ниже этого
    min_access=1,            # и с малым числом обращений
)
```

Семантическая и процедурная память не вычищается автоматически — её
производит консолидатор, она по дизайну переживает эпизоды.

## Где данные по умолчанию

- **Linux:** `~/.local/share/mneme/`
- **macOS:** `~/Library/Application Support/mneme/`
- **Windows:** `%LOCALAPPDATA%\mneme\`

Переопределяется через `MNEME_DATA_DIR`. Внутри каталога:

```
mneme/
├── memories.db          SQLite (долгая копия)
├── memories.idx.npz     индекс numpy-бэкенда
└── memories.idx.bin     индекс native-бэкенда (если собран)
```
