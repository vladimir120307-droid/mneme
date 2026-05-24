"""Compose retrieved memories into a context block for the model."""

from __future__ import annotations

from dataclasses import dataclass

from mneme.memory.store import MemoryStore
from mneme.memory.types import Memory, MemoryKind


@dataclass
class RetrievalConfig:
    semantic_k: int = 5
    episodic_k: int = 5
    procedural_k: int = 3
    max_chars: int = 4_000


@dataclass
class RetrievedContext:
    semantic: list[tuple[Memory, float]]
    episodic: list[tuple[Memory, float]]
    procedural: list[tuple[Memory, float]]

    def as_system_message(self, max_chars: int = 4_000) -> str:
        lines: list[str] = []

        if self.semantic:
            lines.append("# What you know about the user / context")
            for mem, _ in self.semantic:
                lines.append(f"- {mem.content}")
            lines.append("")

        if self.episodic:
            lines.append("# Relevant past interactions")
            for mem, _ in self.episodic:
                stamp = mem.created_at.strftime("%Y-%m-%d")
                lines.append(f"- ({stamp}) {mem.content}")
            lines.append("")

        if self.procedural:
            lines.append("# Skills that may apply")
            for mem, _ in self.procedural:
                name = getattr(mem, "name", "") or "skill"
                lines.append(f"- {name}: {mem.content}")
            lines.append("")

        text = "\n".join(lines).rstrip()
        if len(text) > max_chars:
            text = text[: max_chars - 20].rstrip() + "\n…(truncated)"
        return text


def retrieve(
    store: MemoryStore,
    query: str,
    config: RetrievalConfig | None = None,
) -> RetrievedContext:
    cfg = config or RetrievalConfig()
    semantic = store.search(query, kind=MemoryKind.SEMANTIC, k=cfg.semantic_k)
    episodic = store.search(query, kind=MemoryKind.EPISODIC, k=cfg.episodic_k)
    procedural = store.search(query, kind=MemoryKind.PROCEDURAL, k=cfg.procedural_k)
    return RetrievedContext(
        semantic=semantic, episodic=episodic, procedural=procedural
    )
