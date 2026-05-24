# Mneme как MCP-сервер

[MCP](https://modelcontextprotocol.io) — протокол, через который Cursor,
Claude Desktop, Windsurf и растущий список других AI-инструментов
подключают внешние тулзы. Запуск Mneme как MCP-сервера делает её
общим долговременным слоем памяти для всех этих клиентов: ваши чаты
по всем ним собираются в одно хранилище.

> 🇬🇧 English version: [`mcp.md`](mcp.md)

## Что получаешь

Шесть инструментов через stdio:

| Tool | Назначение |
|---|---|
| `search_memory(query, kind?, k?)` | Гибридный поиск по памяти |
| `add_memory(content, kind?, importance?, tags?)` | Сохранить новую запись |
| `list_memories(kind?, limit?)` | Показать недавние записи |
| `forget_memory(memory_id)` | Удалить запись |
| `memory_stats()` | Счётчики по типам |
| `consolidate(provider?, model?)` | Прогнать консолидацию |

AI-клиент сам решает когда их вызывать. С нормальным системным промптом
он будет сохранять устойчивые факты сам («юзер живёт в Берлине», «этот
проект на Postgres») и вытаскивать их когда нужно.

## Установка

```bash
pip install mneme         # MCP SDK уже идёт в зависимостях
```

Запуск сервера для тестов:

```bash
mneme mcp                 # говорит MCP по stdio — закрыть Ctrl-C
```

В реальной работе MCP-клиент запускает сервер сам, держать терминал
открытым не нужно. Сниппеты ниже — как подключить в каждом клиенте.

## Cursor

Отредактируй `~/.cursor/mcp.json` (создай если нет):

```json
{
  "mcpServers": {
    "mneme": {
      "command": "mneme",
      "args": ["mcp"]
    }
  }
}
```

Перезапусти Cursor. В чат-панели `mneme` появится в меню инструментов.
Попробуй: *«запомни что я люблю краткие code review»*. В новом чате
спроси: *«как мне нравятся code review?»* — факт вернётся.

## Claude Desktop

Отредактируй `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) или `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "mneme": {
      "command": "mneme",
      "args": ["mcp"]
    }
  }
}
```

Перезапусти Claude Desktop. Mneme появится в списке 🔌-коннекторов.

## Windsurf

Отредактируй `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "mneme": {
      "command": "mneme",
      "args": ["mcp"]
    }
  }
}
```

## Continue.dev / Cline / другие

Любой MCP-клиент следует той же форме: `command` (`mneme`) и `args`
(`["mcp"]`). Точный путь к конфигу — в документации твоего клиента
по MCP.

## Рекомендованный системный промпт

Чтобы реально использовать память, добавь что-то такое в кастомные
инструкции клиента:

> У тебя есть доступ к долговременной памяти — инструмент Mneme. Когда
> пользователь делится устойчивыми фактами о себе, своих проектах или
> предпочтениях, вызывай `add_memory` чтобы сохранить. Прежде чем
> отвечать на личный вопрос, вызывай `search_memory` чтобы проверить
> что ты уже знаешь. Не объявляй о пользовании памятью — просто веди
> себя так, будто помнишь.

## Где данные

Один файл SQLite + векторный индекс рядом, общие на все MCP-клиенты.
См. [`configuration.ru.md`](configuration.ru.md) — там пути по умолчанию
и `MNEME_DATA_DIR` для переноса.

## Несколько профилей

Можно держать отдельные хранилища Mneme под отдельные контексты (работа,
личное, конкретный проект клиента), дав каждому MCP-серверу свой каталог
данных:

```json
{
  "mcpServers": {
    "mneme-work":     { "command": "mneme", "args": ["mcp"], "env": { "MNEME_DATA_DIR": "/data/mneme/work" } },
    "mneme-personal": { "command": "mneme", "args": ["mcp"], "env": { "MNEME_DATA_DIR": "/data/mneme/personal" } }
  }
}
```

Каждое независимо и каждое модель может искать.
