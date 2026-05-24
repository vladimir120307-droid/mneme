"""Memory data types.

Four kinds of memory live in Mneme: working, episodic, semantic, procedural.
See docs/memory-model.md for the full rationale.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryKind(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


class Memory(BaseModel):
    """Base type for any stored memory."""

    id: str = Field(default_factory=_new_id)
    kind: MemoryKind
    content: str
    created_at: datetime = Field(default_factory=_now)
    last_accessed_at: datetime = Field(default_factory=_now)
    access_count: int = 0
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.last_accessed_at = _now()
        self.access_count += 1


class WorkingMemory(Memory):
    kind: MemoryKind = MemoryKind.WORKING
    role: str = "user"
    session_id: str = ""


class EpisodicMemory(Memory):
    kind: MemoryKind = MemoryKind.EPISODIC
    source: str = "user"


class SemanticMemory(Memory):
    """A generalised, time-independent fact."""

    kind: MemoryKind = MemoryKind.SEMANTIC
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    support: list[str] = Field(default_factory=list)
    superseded_by: str | None = None


class ProceduralMemory(Memory):
    """A how-to: a sequence of steps that accomplish a task."""

    kind: MemoryKind = MemoryKind.PROCEDURAL
    name: str = ""
    trigger: str = ""
    steps: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
