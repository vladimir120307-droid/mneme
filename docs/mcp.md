# Mneme as an MCP server

[MCP](https://modelcontextprotocol.io) is the protocol that Cursor,
Claude Desktop, Windsurf and a growing list of other AI tools use to
plug in external tools. Running Mneme as an MCP server makes it the
shared, persistent memory layer for any of those clients — your chats
across all of them feed into one durable store.

> 🇷🇺 Русская версия: [`mcp.ru.md`](mcp.ru.md)

## What you get

Six tools, exposed over stdio:

| Tool | Purpose |
|---|---|
| `search_memory(query, kind?, k?)` | Hybrid search across stored memories |
| `add_memory(content, kind?, importance?, tags?)` | Save a new memory |
| `list_memories(kind?, limit?)` | Browse recent memories |
| `forget_memory(memory_id)` | Delete a memory |
| `memory_stats()` | Counts per kind |
| `consolidate(provider?, model?)` | Run one consolidation pass |

The AI client decides when to call them. With a good system prompt, it
will save durable facts on its own ("the user lives in Berlin", "this
project uses Postgres") and pull them back when relevant.

## Install

```bash
pip install mneme         # already brings in the MCP SDK
```

Run the server (for testing):

```bash
mneme mcp                 # speaks MCP over stdio — close with Ctrl-C
```

MCP clients launch the server themselves — you don't keep this open
manually. The snippets below tell each client how.

## Cursor

Edit `~/.cursor/mcp.json` (create it if missing):

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

Restart Cursor. In the chat panel you should see `mneme` listed under
the tools menu. Try: *"remember that I prefer terse code reviews"*. In a
new chat ask: *"what do you remember about how I like reviews?"* — the
fact comes back.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Restart Claude Desktop. Mneme appears in the 🔌 connectors list.

## Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

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

## Continue.dev / Cline / others

Any MCP-aware client follows the same shape: a `command` (`mneme`) and
`args` (`["mcp"]`). See your client's MCP-server documentation for the
exact config-file path.

## Suggested system prompt

To get the most out of the memory layer, add something like this to
your client's system / custom-instructions field:

> You have access to a long-term memory tool called Mneme. When the
> user shares durable facts about themselves, their projects, or their
> preferences, call `add_memory` to save them. Before answering a
> personal question, call `search_memory` to check what you already
> know. Don't announce that you are using memory — just behave as if
> you remember.

## Where the data lives

A single SQLite + vector-index pair, shared across every MCP client.
See [`configuration.md`](configuration.md) for the path defaults and
`MNEME_DATA_DIR` to relocate them.

## Multiple profiles

Run separate Mneme stores for separate contexts (work, personal, a
specific client project) by giving each MCP server a dedicated data
directory:

```json
{
  "mcpServers": {
    "mneme-work":     { "command": "mneme", "args": ["mcp"], "env": { "MNEME_DATA_DIR": "/data/mneme/work" } },
    "mneme-personal": { "command": "mneme", "args": ["mcp"], "env": { "MNEME_DATA_DIR": "/data/mneme/personal" } }
  }
}
```

Each one is independent, each one is searchable by the model.
