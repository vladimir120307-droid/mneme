"""Consolidation pass: episodic → semantic.

Runs periodically. Takes a batch of recent episodic memories, asks the model
to extract durable facts about the user / world, and stores them as
SemanticMemory entries with links back to the source episodes.

Designed to be cheap: one model call per cycle, bounded batch size.
"""

from __future__ import annotations

import json
import re

from mneme.memory.store import MemoryStore
from mneme.memory.types import EpisodicMemory, MemoryKind, SemanticMemory
from mneme.providers.base import LLMProvider, Message


_PROMPT = """You are extracting durable facts from a stream of recent interactions.

Below are recent EPISODES (timestamped events). From them, extract general,
time-independent facts about the user, their preferences, or the world that
will still be useful months from now. Skip anything ephemeral or one-off.

Return strictly valid JSON of this shape:
{{"facts": [
   {{"statement": "...", "confidence": 0.0-1.0, "support_ids": ["id1", ...]}}
]}}

Episodes:
{episodes}
"""


class Consolidator:
    def __init__(
        self,
        store: MemoryStore,
        provider: LLMProvider,
        model: str,
        *,
        batch_size: int = 20,
    ):
        self.store = store
        self.provider = provider
        self.model = model
        self.batch_size = batch_size

    async def run_once(self) -> int:
        episodes = self.store.list(kind=MemoryKind.EPISODIC, limit=self.batch_size)
        if not episodes:
            return 0
        facts = await self._extract_facts(episodes)
        if not facts:
            return 0
        sem_memories: list[SemanticMemory] = []
        for f in facts:
            statement = f.get("statement", "").strip()
            if not statement:
                continue
            confidence = float(f.get("confidence", 0.7))
            support = [s for s in f.get("support_ids", []) if isinstance(s, str)]
            sem_memories.append(
                SemanticMemory(
                    content=statement,
                    confidence=max(0.0, min(1.0, confidence)),
                    support=support,
                    importance=0.7,
                    tags=["consolidated"],
                )
            )
        if sem_memories:
            self.store.add_many(sem_memories)
        return len(sem_memories)

    async def _extract_facts(self, episodes: list[EpisodicMemory]) -> list[dict]:
        rendered = "\n".join(
            f"- [id={e.id}] ({e.created_at.strftime('%Y-%m-%d')}) {e.content}"
            for e in episodes
        )
        prompt = _PROMPT.format(episodes=rendered)
        try:
            resp = await self.provider.chat(
                [Message(role="user", content=prompt)],
                model=self.model,
                temperature=0.2,
                max_tokens=800,
            )
        except Exception:
            return []
        return _parse_facts(resp.content)


def _parse_facts(text: str) -> list[dict]:
    """Best-effort JSON extraction — models sometimes wrap or pad output."""
    text = text.strip()
    candidate = _strip_fences(text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    facts = data.get("facts") if isinstance(data, dict) else None
    return facts if isinstance(facts, list) else []


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text
