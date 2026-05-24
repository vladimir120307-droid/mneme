# Mneme

> **Локальный AI-агент с человекоподобной долговременной памятью.**
> Ассистент, который помнит тебя неделями и месяцами — а не одной сессией.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![English](https://img.shields.io/badge/lang-english-blue)](README.md)

---

Любой современный чат-бот теряет память в момент закрытия сессии. Mneme —
это небольшая open-source прослойка, которая садится между тобой и любой
LLM и даёт ей настоящую память: четыре её вида, по модели человеческого мозга —
*рабочая*, *эпизодическая*, *семантическая*, *процедурная*. Подключается к
Ollama для полностью локальной работы либо к OpenAI, Anthropic, OpenRouter,
LM Studio, vLLM — всему, что совместимо с OpenAI API.

```
   ┌──────────────┐    ┌────────────────────┐    ┌──────────────┐
   │  твой ввод   │ →  │ Mneme: достать     │ →  │   любой LLM  │
   └──────────────┘    │ → ответить → сохр. │    └──────────────┘
                       └────────────────────┘
                                  │
                                  ▼
                       ┌────────────────────┐
                       │ долговременное хр. │
                       │ (4 типа памяти)    │
                       └────────────────────┘
```

## Зачем Mneme

| Проблема | Mneme |
|---|---|
| Боты забывают всё между сессиями | Память переживает рестарты и перезагрузки |
| Векторные «помойки» отдают мусор | Четыре типа памяти со своими правилами |
| Облачные memory-сервисы | Local-first, работает офлайн с Ollama/llama.cpp |
| Только библиотека (Letta, Mem0) | Библиотека **+ CLI + REST API** OpenAI-совместимый |
| Привязка к одному провайдеру | Смена бэкенда — одна настройка |

## Установка

```bash
pip install mneme
# ускоренный векторный поиск на больших объёмах (опционально, нужен C/C++):
pip install "mneme[fast]"
# из исходников
git clone https://github.com/vladimir120307-droid/mneme
cd mneme && pip install -e ".[dev]"
```

## Старт за 60 секунд

### 1. Чат в терминале (полностью локально)

```bash
ollama pull llama3.1
mneme chat --provider ollama --model llama3.1
```

Скажи ему своё имя в понедельник. Зайди в пятницу — он помнит.

### 2. Python

```python
import asyncio
from mneme import Agent
from mneme.agent import AgentConfig

async def main():
    agent = Agent(AgentConfig(provider="ollama", model="llama3.1"))
    agent.remember("Живу в Берлине, пишу на Rust.", importance=0.9)
    print(await agent.chat("Где я живу и на чём пишу?"))
    agent.close()

asyncio.run(main())
```

### 3. REST API (OpenAI-совместимый)

```bash
mneme serve --port 8077
```

```bash
curl http://localhost:8077/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"привет"}]}'
```

Любой инструмент, говорящий по OpenAI API — SDK `openai`, LangChain,
твой свой клиент — достаточно указать `base_url` равным
`http://localhost:8077/v1`.

## Четыре типа памяти

| Тип | Срок | Что хранит |
|---|---|---|
| **Рабочая** | минуты | Текущее окно диалога |
| **Эпизодическая** | дни–недели | Конкретные события с временем |
| **Семантическая** | бессрочно | Обобщённые факты («юзер живёт в Берлине») |
| **Процедурная** | бессрочно | Навыки и последовательности действий |

Фоновый **консолидатор** превращает повторяющиеся эпизоды в семантические
факты, а низкоценные старые эпизоды угасают по half-life. Полная спека:
[`docs/memory-model.md`](docs/memory-model.md).

## Конфигурация

Всё переопределяется через env-переменные или флаги CLI.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `MNEME_PROVIDER` | `ollama` | `ollama` · `openai` · `anthropic` · `openrouter` · `lmstudio` · `vllm` |
| `MNEME_MODEL` | `llama3.1` | Имя модели у выбранного провайдера |
| `MNEME_DATA_DIR` | каталог пользователя ОС | Где лежит SQLite + HNSW |
| `MNEME_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Модель эмбеддингов |
| `MNEME_HOST` / `MNEME_PORT` | `127.0.0.1:8077` | Адрес REST-сервера |

## Команды CLI

```
mneme chat                    интерактивный REPL со стримингом
mneme ask "вопрос..."         одноразовый запрос
mneme serve                   запустить REST-сервер
mneme remember "факт..."      добавить эпизодическую память
mneme memory list             список памятей
mneme memory search "..."     гибридный поиск (similarity + recency + importance)
mneme memory stats            счётчики по типам
mneme memory forget <id>      удалить (можно префикс id)
mneme memory decay            прорежить старые низкоценные эпизоды
```

## Структура

```
src/mneme/
├── agent.py              верхнеуровневый Agent
├── consolidation.py      episodic → semantic
├── config.py             настройки из env
├── memory/
│   ├── types.py          pydantic-модели
│   ├── store.py          SQLite + векторный индекс
│   ├── index.py          бэкенды numpy / hnswlib
│   ├── embeddings.py     sentence-transformers
│   └── retrieval.py      гибридный скоринг + контекстный блок
├── providers/
│   ├── ollama.py
│   ├── openai_compat.py
│   ├── anthropic.py
│   └── registry.py
├── api/server.py         FastAPI REST (OpenAI-совместимый)
└── cli.py                Typer
```

## Нативное ускорение (опционально)

Ядро на C++17 (`native/`, параллелится через OpenMP, авто-векторизуется
с AVX2) — drop-in более быстрый бэкенд. Собирается одной командой и
Mneme подхватывает его сам:

```bash
python -m mneme.build_native
```

Подробности — [`native/README.md`](native/README.md). Без него работает
pure-Python путь, всё функционирует одинаково.

## Дорожная карта

- [x] Деление памяти на рабочую / эпизодическую / семантическую / процедурную
- [x] Гибридный retrieval (similarity + recency + importance + access)
- [x] OpenAI-совместимый REST-сервер
- [x] Провайдеры Ollama / OpenAI / Anthropic / OpenRouter / LM Studio / vLLM
- [x] Нативное C++ ядро памяти (drop-in быстрее)
- [ ] Tool use и structured function calling
- [ ] Мульти-юзер сессии и пер-юзер namespaces
- [ ] Кросс-платформенный десктоп-UI (Flutter)
- [ ] Расширение для браузера
- [ ] Импорт памяти из Markdown, дневников, экспортов чатов

## Вклад

Issues и PR приветствуются. Тесты:

```bash
pip install -e ".[dev]"
pytest
```

## Лицензия

MIT — см. [LICENSE](LICENSE).
