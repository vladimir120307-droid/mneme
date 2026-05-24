# Быстрый старт

Минута от нуля до чата, который тебя помнит.

## 1. Установка

```bash
pip install mneme
```

Опциональное ускорение — нативное (C++17) ядро для быстрого поиска и
скоринга. Нужен компилятор C++.

```bash
pip install pybind11
python -m mneme.build_native
```

Если native собран — Mneme подхватит его сам. Иначе работает чистый Python
путь, поведение идентичное.

## 2. Выбери бэкенд

Mneme говорит с любым провайдером, реализующим интерфейс `LLMProvider`.
Короче всего — Ollama для полностью локального вывода:

```bash
ollama pull llama3.1
```

…или ключ к облачному провайдеру:

```bash
set MNEME_PROVIDER=openai
set OPENAI_API_KEY=sk-...
set MNEME_MODEL=gpt-4o-mini
```

## 3. Чат из терминала

```bash
mneme chat
```

```
you ›  Меня зовут Владимир, отвечай кратко.
mneme › Принято.
you ›  exit
```

Возвращайся через неделю:

```bash
mneme chat
```

```
you ›  Как меня зовут и как я люблю ответы?
mneme › Владимир. Кратко.
```

Постоянное хранилище живёт по умолчанию в каталоге данных пользователя ОС
(см. `mneme/config.py`); переопределяется через `MNEME_DATA_DIR=/путь`.

## 4. Использование из Python

```python
import asyncio
from mneme import Agent
from mneme.agent import AgentConfig

async def main():
    agent = Agent(AgentConfig(provider="ollama", model="llama3.1"))
    agent.remember("Живу в Берлине.", importance=0.9)
    answer = await agent.chat("Где я живу?")
    print(answer)
    agent.close()

asyncio.run(main())
```

## 5. REST-сервер (OpenAI-совместимый)

```bash
mneme serve --port 8077
```

Любой OpenAI-совместимый клиент просто указывает на него:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8077/v1", api_key="ignored")
print(client.chat.completions.create(
    model="llama3.1",
    messages=[{"role": "user", "content": "привет"}],
).choices[0].message.content)
```

Эндпоинты `/v1/memories` и `/v1/consolidate` позволяют управлять памятью
напрямую — см. [`api.ru.md`](api.ru.md).

## Дальше

- [Модель памяти](memory-model.ru.md) — четыре типа памяти и их взаимодействие.
- [Архитектура](architecture.ru.md) — как устроены модули.
- [Конфигурация](configuration.ru.md) — все переменные среды и флаги.
- [API](api.ru.md) — REST-эндпоинты и Python-классы.
