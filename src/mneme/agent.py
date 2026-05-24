"""High-level Agent.

The Agent owns a MemoryStore and an LLMProvider, and wires them together so
each turn looks like: receive → retrieve → think → respond → remember.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import uuid4

from mneme.consolidation import Consolidator
from mneme.memory.retrieval import RetrievalConfig, retrieve
from mneme.memory.store import MemoryStore
from mneme.memory.types import EpisodicMemory, MemoryKind, WorkingMemory
from mneme.providers.base import LLMProvider, Message
from mneme.providers.registry import get_provider

DEFAULT_SYSTEM = (
    "You are Mneme, a helpful assistant with long-term memory. "
    "When context from prior interactions is provided, use it naturally — "
    "do not announce that you are reading memory."
)


@dataclass
class AgentConfig:
    provider: str = "ollama"
    model: str = "llama3.1"
    temperature: float = 0.7
    max_tokens: int | None = None
    working_window: int = 12
    system_prompt: str = DEFAULT_SYSTEM
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    consolidate_every: int = 10  # episodes between consolidation passes
    provider_options: dict = field(default_factory=dict)


class Agent:
    def __init__(
        self,
        config: AgentConfig | None = None,
        *,
        store: MemoryStore | None = None,
        provider: LLMProvider | None = None,
        session_id: str | None = None,
    ):
        self.config = config or AgentConfig()
        self.store = store or MemoryStore()
        self.provider = provider or get_provider(
            self.config.provider, **self.config.provider_options
        )
        self.session_id = session_id or uuid4().hex
        self.consolidator = Consolidator(self.store, self.provider, self.config.model)
        self._turns_since_consolidate = 0

    # ── public API ──────────────────────────────────────────────────────

    async def chat(self, user_input: str) -> str:
        messages = self._build_messages(user_input)
        response = await self.provider.chat(
            messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        self._remember_turn(user_input, response.content)
        await self._maybe_consolidate()
        return response.content

    async def stream(self, user_input: str) -> AsyncIterator[str]:
        messages = self._build_messages(user_input)
        pieces: list[str] = []
        async for piece in self.provider.stream(
            messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            pieces.append(piece)
            yield piece
        self._remember_turn(user_input, "".join(pieces))
        await self._maybe_consolidate()

    def remember(self, content: str, *, importance: float = 0.5) -> EpisodicMemory:
        """Manually add an episodic fact, e.g. from external import."""
        mem = EpisodicMemory(content=content, importance=importance, source="manual")
        self.store.add(mem)
        return mem

    def forget(self, memory_id: str) -> None:
        self.store.delete(memory_id)

    def close(self) -> None:
        self.store.close()

    # ── internals ───────────────────────────────────────────────────────

    def _build_messages(self, user_input: str) -> list[Message]:
        ctx = retrieve(self.store, user_input, self.config.retrieval)
        system_blocks = [self.config.system_prompt]
        retrieved = ctx.as_system_message(max_chars=self.config.retrieval.max_chars)
        if retrieved:
            system_blocks.append(retrieved)
        messages: list[Message] = [
            Message(role="system", content="\n\n".join(system_blocks))
        ]
        for w in self._working_window():
            role = w.role if w.role in ("user", "assistant") else "user"
            messages.append(Message(role=role, content=w.content))  # type: ignore[arg-type]
        messages.append(Message(role="user", content=user_input))
        return messages

    def _working_window(self) -> list[WorkingMemory]:
        all_working = self.store.list(
            kind=MemoryKind.WORKING, limit=self.config.working_window * 4
        )
        same_session = [
            m for m in all_working
            if isinstance(m, WorkingMemory) and m.session_id == self.session_id
        ]
        # store.list returns newest-first; reverse to chronological
        same_session.sort(key=lambda m: m.created_at)
        return same_session[-self.config.working_window:]

    def _remember_turn(self, user_input: str, assistant_output: str) -> None:
        u = WorkingMemory(
            content=user_input,
            role="user",
            session_id=self.session_id,
        )
        a = WorkingMemory(
            content=assistant_output,
            role="assistant",
            session_id=self.session_id,
        )
        self.store.add_many([u, a])
        # also promote the user turn straight to episodic with a default importance
        episode = EpisodicMemory(
            content=f"User said: {user_input}",
            source="user",
            importance=_quick_importance(user_input),
            tags=["chat"],
        )
        self.store.add(episode)
        self._turns_since_consolidate += 1

    async def _maybe_consolidate(self) -> None:
        if self._turns_since_consolidate < self.config.consolidate_every:
            return
        self._turns_since_consolidate = 0
        # run consolidation off the event loop's critical path
        await asyncio.shield(self.consolidator.run_once())


def _quick_importance(text: str) -> float:
    """Cheap heuristic until the consolidator scores things properly."""
    text = text.strip()
    if not text:
        return 0.0
    base = 0.5
    if any(k in text.lower() for k in ("remember", "important", "always", "never")):
        base += 0.2
    if "?" in text:
        base += 0.05
    if len(text) > 200:
        base += 0.05
    return max(0.0, min(1.0, base))
