"""Minimal Mneme usage example.

Prerequisite: a running Ollama instance with a model pulled, e.g.
    ollama pull llama3.1
"""

from __future__ import annotations

import asyncio

from mneme import Agent
from mneme.agent import AgentConfig


async def main() -> None:
    agent = Agent(AgentConfig(provider="ollama", model="llama3.1"))
    try:
        # Seed a fact, then ask a question that should pull it from memory.
        agent.remember("My name is Vladimir and I live in Berlin.", importance=0.9)
        agent.remember("I work primarily with C++ and Python.", importance=0.8)

        print(await agent.chat("Where do I live?"))
        print(await agent.chat("What stack do I work with?"))
    finally:
        agent.close()


if __name__ == "__main__":
    asyncio.run(main())
