# Quickstart

This walks you from zero to a chat session that remembers you, in about a
minute.

## 1. Install

```bash
pip install mneme
```

Optional speed-up: build the native (C++17) core for faster search and
scoring. Needs a C++ compiler.

```bash
pip install pybind11
python -m mneme.build_native
```

When the native core is present, Mneme picks it up automatically. Otherwise
the pure-Python path is used — everything works the same.

## 2. Pick a backend

Mneme talks to any provider that implements the `LLMProvider` interface.
The shortest path is Ollama for fully-local inference:

```bash
ollama pull llama3.1
```

…or set an API key for a cloud provider:

```bash
export MNEME_PROVIDER=openai      # or anthropic, openrouter, ...
export OPENAI_API_KEY=sk-...
export MNEME_MODEL=gpt-4o-mini
```

## 3. Chat from the CLI

```bash
mneme chat
```

```
you ›  My name is Vladimir and I prefer terse answers.
mneme › Got it.
you ›  exit
```

Come back a week later:

```bash
mneme chat
```

```
you ›  What's my name and how do I like answers?
mneme › Vladimir. Terse.
```

The persistent memory store lives by default under your OS data dir
(see `mneme/config.py`); use `MNEME_DATA_DIR=/path` to override.

## 4. Use it from Python

```python
import asyncio
from mneme import Agent
from mneme.agent import AgentConfig

async def main():
    agent = Agent(AgentConfig(provider="ollama", model="llama3.1"))
    agent.remember("I live in Berlin.", importance=0.9)
    answer = await agent.chat("Where do I live?")
    print(answer)
    agent.close()

asyncio.run(main())
```

## 5. Run a REST server (OpenAI-compatible)

```bash
mneme serve --port 8077
```

Now any OpenAI-compatible client just points at it:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8077/v1", api_key="ignored")
print(client.chat.completions.create(
    model="llama3.1",
    messages=[{"role": "user", "content": "hi"}],
).choices[0].message.content)
```

Mneme-specific endpoints under `/v1/memories` and `/v1/consolidate` let you
inspect and reshape the store directly — see [`api.md`](api.md).

## Next steps

- [Memory model](memory-model.md) — the four kinds of memory and how they
  interact.
- [Architecture](architecture.md) — how the pieces fit together.
- [Configuration](configuration.md) — every env var and flag.
- [API reference](api.md) — REST endpoints and Python class surface.
