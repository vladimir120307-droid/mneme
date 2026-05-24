from __future__ import annotations

from typing import AsyncIterator

import pytest

from mneme.agent import Agent, AgentConfig
from mneme.memory.types import MemoryKind
from mneme.providers.base import ChatResponse, LLMProvider, Message


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, reply: str = "ok"):
        self.reply = reply
        self.calls: list[list[Message]] = []

    async def chat(self, messages, *, model, temperature=0.7, max_tokens=None, **_):
        self.calls.append(list(messages))
        return ChatResponse(content=self.reply, model=model)

    async def stream(self, messages, *, model, temperature=0.7, max_tokens=None, **_) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        for word in self.reply.split():
            yield word + " "


@pytest.mark.asyncio
async def test_chat_stores_working_and_episodic(store):
    provider = FakeProvider(reply="hi there")
    agent = Agent(AgentConfig(consolidate_every=999), store=store, provider=provider)
    answer = await agent.chat("Hello, I am Vladimir")
    assert answer == "hi there"
    working = store.list(kind=MemoryKind.WORKING)
    episodic = store.list(kind=MemoryKind.EPISODIC)
    assert len(working) == 2  # user + assistant
    assert any("Vladimir" in m.content for m in episodic)


@pytest.mark.asyncio
async def test_stream_collects_full_response(store):
    provider = FakeProvider(reply="one two three")
    agent = Agent(AgentConfig(consolidate_every=999), store=store, provider=provider)
    chunks = []
    async for piece in agent.stream("ping"):
        chunks.append(piece)
    assert "".join(chunks).strip() == "one two three"
    working = store.list(kind=MemoryKind.WORKING)
    assert any("one two three" in m.content for m in working)


@pytest.mark.asyncio
async def test_retrieval_feeds_system_prompt(store):
    provider = FakeProvider()
    agent = Agent(AgentConfig(consolidate_every=999), store=store, provider=provider)
    agent.remember("The user lives in Berlin", importance=0.9)
    await agent.chat("Where do I live?")
    system_content = provider.calls[-1][0].content
    assert "Berlin" in system_content
