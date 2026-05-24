"""Request / response models for the REST API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── OpenAI-compatible chat ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: dict[str, int] = Field(default_factory=dict)


# ── Memory endpoints ────────────────────────────────────────────────────

class MemoryOut(BaseModel):
    id: str
    kind: str
    content: str
    created_at: str
    last_accessed_at: str
    access_count: int
    importance: float
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class CreateMemoryRequest(BaseModel):
    content: str
    kind: Literal["episodic", "semantic", "procedural"] = "episodic"
    importance: float = 0.6
    tags: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str
    kind: str | None = None
    k: int = 10


class SearchHit(BaseModel):
    memory: MemoryOut
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class StatsResponse(BaseModel):
    working: int
    episodic: int
    semantic: int
    procedural: int
    total: int


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
