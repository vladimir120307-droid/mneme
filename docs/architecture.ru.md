# Архитектура

С высоты птичьего полёта: какие модули есть, как связаны и какие
решения — несущие.

## Общая картина

```
┌──────────────────────────────────────────────────────────────────────┐
│                              Agent                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────────┐  │
│  │  Получаем   │ →  │  Достаём     │ →  │  Provider.chat / stream │ │
│  │  ход юзера  │    │  контекст    │    │  (Ollama / OpenAI / …)  │ │
│  └─────────────┘    └──────┬───────┘    └────────┬────────────────┘ │
│                            │                      │                  │
│                            ▼                      ▼                  │
│                  ┌──────────────────┐   ┌────────────────────┐       │
│                  │  MemoryStore     │ ◀ │  Сохраняем ход,    │       │
│                  │  (SQLite +       │   │  по графику запус- │       │
│                  │  векторный инд.) │   │  каем консолидацию │       │
│                  └──────────────────┘   └────────────────────┘       │
└──────────────────────────────────────────────────────────────────────┘
```

## Модули

```
src/mneme/
├── agent.py              верхнеуровневый Agent, точка входа
├── consolidation.py      эпизодическое → семантическое через LLM
├── config.py             настройки из env
├── memory/
│   ├── types.py          pydantic-модели четырёх типов памяти
│   ├── store.py          SQLite-backed долгое хранилище
│   ├── index.py          бэкенды векторного индекса (native / hnsw / numpy)
│   ├── embeddings.py     обёртка над sentence-transformers (lazy)
│   └── retrieval.py      гибридный скоринг + сборка контекстного блока
├── providers/
│   ├── base.py           абстрактный LLMProvider + Message
│   ├── ollama.py
│   ├── openai_compat.py  OpenAI, OpenRouter, LM Studio, vLLM
│   ├── anthropic.py
│   └── registry.py       резолвер по короткому имени
├── api/server.py         REST на FastAPI (OpenAI-совместимый)
├── api/schemas.py        request/response-модели
├── build_native.py       обёртка вокруг CMake для C++ ядра
└── cli.py                Typer-CLI
```

## Горячий путь: один ход

1. Вызывается `Agent.chat(user_input)`.
2. `retrieve()` (`memory/retrieval.py`) спрашивает у `MemoryStore.search()`
   top-K эпизодических, семантических и процедурных воспоминаний по запросу.
   - `search` сначала прогоняет вектор через индекс, потом скорит
     кандидатов **гибридной** формулой: similarity · 0.55 +
     recency · 0.20 + importance · 0.20 + access-boost · 0.05.
     Сам скоринг векторизован (numpy либо нативное ядро если собрано).
3. Найденные памяти форматируются в system-сообщение и подмешиваются к
   истории диалога.
4. Вызывается провайдер (`provider.chat` или `provider.stream`).
5. И ход пользователя, и ответ ассистента пишутся как `WorkingMemory`.
   Ход юзера дополнительно промоутится в `EpisodicMemory` с эвристической
   важностью.
6. Каждые N ходов (настраивается) запускается `Consolidator.run_once()` —
   модель достаёт устойчивые факты из недавних эпизодов и записывает их
   как `SemanticMemory` со ссылками-источниками.

## Бэкенды векторного индекса

Три реализации за одним интерфейсом `VectorIndex`:

| Бэкенд | Когда выбирается | Плюсы | Нюансы |
|---|---|---|---|
| `NativeIndex` | `auto`, native собран | SIMD + OpenMP, самый быстрый single-thread | Нужен C++ компилятор на сборке |
| `HNSWIndex` | `auto`, установлен hnswlib | Sub-linear поиск для очень больших хранилищ | Approximate; hnswlib тоже C/C++ |
| `NumpyIndex` | `auto`, всегда | Чистый Python install; точный | Линейный скан |

Выбор: `make_index(dim, backend="auto")` пробует native → hnsw → numpy.
Принудительно — `backend="numpy" / "hnsw" / "native"`.

Numpy-бэкенд использует буфер с амортизированным ростом (capacity удваивается
при переполнении), поэтому `add` — O(1) амортизированно. Поиск — одно плотное
матрично-векторное умножение + partial top-K через `argpartition`.

## Хранилище

SQLite — единственный источник истины. Схема — одна таблица:

```sql
CREATE TABLE memories (
  id                TEXT PRIMARY KEY,
  kind              TEXT NOT NULL,
  content           TEXT NOT NULL,
  created_at        REAL NOT NULL,        -- unix-секунды
  last_accessed_at  REAL NOT NULL,
  access_count      INTEGER NOT NULL DEFAULT 0,
  importance        REAL NOT NULL DEFAULT 0.5,
  tags              TEXT NOT NULL DEFAULT '[]',
  metadata          TEXT NOT NULL DEFAULT '{}',
  type_fields       TEXT NOT NULL DEFAULT '{}'
);
```

Индексы по `kind`, `created_at`, `importance` ускоряют listing и decay.
Тип-специфичные поля (например, `confidence` у семантической памяти) лежат в
JSON-колонке `type_fields` — эволюционировать проще, чем колонками.

Векторный индекс живёт в соседнем файле (`memories.idx.npz` или
`memories.idx.bin` в зависимости от бэкенда) и при необходимости
перестраивается из SQLite.

## REST-поверхность

FastAPI выставляет и OpenAI-совместимый чат, и Mneme-специфичные роуты:

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/v1/chat/completions` | OpenAI-совместимый, с памятью в контексте |
| GET  | `/v1/memories?kind=…&limit=…` | Список |
| POST | `/v1/memories` | Создать |
| GET  | `/v1/memories/{id}` | Получить |
| DELETE | `/v1/memories/{id}` | Удалить |
| POST | `/v1/memories/search` | Гибридный поиск |
| POST | `/v1/consolidate` | Прогнать консолидацию |
| GET  | `/v1/stats` | Счётчики по типам |
| GET  | `/healthz` | Проба живости |

## Замечания по дизайну

- **Один источник истины.** SQLite — долгая копия; индекс выводится из неё.
  Файл индекса можно удалить — пересоберётся.
- **Без магии.** Никаких фоновых потоков, неявных сетевых вызовов.
  Консолидатор — `await`-абельная функция, агент сам решает когда её звать.
- **Не зависим от провайдера.** Агент не знает про конкретный класс
  провайдера. Переключение между локалом и облаком — одна настройка.
- **Drop-in native.** C++ ядро прячется за тем же Python-интерфейсом,
  пользовательский код не ветвится на тип бэкенда.
