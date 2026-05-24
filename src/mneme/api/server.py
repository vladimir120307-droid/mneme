"""FastAPI server exposing Mneme over HTTP.

Endpoints:
- POST /v1/chat/completions   — OpenAI-compatible
- GET  /v1/memories           — list
- POST /v1/memories           — create
- GET  /v1/memories/{id}      — fetch
- DELETE /v1/memories/{id}    — delete
- POST /v1/memories/search    — semantic search
- POST /v1/consolidate        — run consolidation pass
- GET  /v1/stats              — counts
- GET  /healthz               — health probe
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from mneme.agent import Agent, AgentConfig
from mneme.api.schemas import (
    ChatChoice,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CreateMemoryRequest,
    HealthResponse,
    MemoryOut,
    SearchHit,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)
from mneme.config import load_settings
from mneme.memory.embeddings import Embedder
from mneme.memory.store import MemoryStore
from mneme.memory.types import (
    EpisodicMemory,
    Memory,
    MemoryKind,
    ProceduralMemory,
    SemanticMemory,
)
from mneme.providers.base import Message
from mneme.providers.registry import get_provider


def create_app(provider: str | None = None, model: str | None = None) -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="Mneme", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    embedder = Embedder(settings.embedding_model)
    store = MemoryStore(path=settings.data_dir, embedder=embedder)
    config = AgentConfig(
        provider=provider or settings.provider,
        model=model or settings.model,
    )
    agent = Agent(config, store=store, provider=get_provider(config.provider))

    app.state.agent = agent
    app.state.store = store

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            provider=agent.config.provider,
            model=agent.config.model,
        )

    # ── OpenAI-compatible chat ─────────────────────────────────────

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        model_name = req.model or agent.config.model
        messages = [Message(role=m.role, content=m.content) for m in req.messages]
        # Treat the last user message as the "query"; let the agent pull
        # extra context from memory while keeping caller-supplied history.
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"), ""
        )
        ctx_block = ""
        if last_user:
            from mneme.memory.retrieval import retrieve

            ctx_block = retrieve(store, last_user).as_system_message()
        if ctx_block:
            messages = [Message(role="system", content=ctx_block), *messages]

        if req.stream:
            return StreamingResponse(
                _stream_openai(agent, messages, model_name, req),
                media_type="text/event-stream",
            )
        provider_inst = agent.provider
        resp = await provider_inst.chat(
            messages,
            model=model_name,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        # Remember the turn so server use cases also accumulate memory.
        if last_user:
            agent._remember_turn(last_user, resp.content)
        return ChatResponse(
            id=f"chatcmpl-{uuid4().hex[:24]}",
            created=int(time.time()),
            model=resp.model,
            choices=[
                ChatChoice(
                    message=ChatMessage(role="assistant", content=resp.content),
                    finish_reason=resp.finish_reason,
                )
            ],
            usage=resp.usage,
        )

    # ── Memory CRUD ───────────────────────────────────────────────

    @app.get("/v1/memories", response_model=list[MemoryOut])
    async def list_memories(kind: str | None = None, limit: int = 50) -> list[MemoryOut]:
        mk = MemoryKind(kind) if kind else None
        return [_to_out(m) for m in store.list(kind=mk, limit=limit)]

    @app.post("/v1/memories", response_model=MemoryOut)
    async def create_memory(req: CreateMemoryRequest) -> MemoryOut:
        mem = _build_memory(req)
        store.add(mem)
        return _to_out(mem)

    @app.get("/v1/memories/{memory_id}", response_model=MemoryOut)
    async def get_memory(memory_id: str) -> MemoryOut:
        mem = store.get(memory_id)
        if mem is None:
            raise HTTPException(status_code=404, detail="memory not found")
        return _to_out(mem)

    @app.delete("/v1/memories/{memory_id}")
    async def delete_memory(memory_id: str) -> dict:
        store.delete(memory_id)
        return {"deleted": memory_id}

    @app.post("/v1/memories/search", response_model=SearchResponse)
    async def search_memories(req: SearchRequest) -> SearchResponse:
        mk = MemoryKind(req.kind) if req.kind else None
        results = store.search(req.query, kind=mk, k=req.k)
        return SearchResponse(
            hits=[SearchHit(memory=_to_out(m), score=s) for m, s in results]
        )

    @app.post("/v1/consolidate")
    async def consolidate() -> dict:
        n = await agent.consolidator.run_once()
        return {"created_semantic_memories": n}

    @app.get("/v1/stats", response_model=StatsResponse)
    async def stats() -> StatsResponse:
        return StatsResponse(
            working=store.count(MemoryKind.WORKING),
            episodic=store.count(MemoryKind.EPISODIC),
            semantic=store.count(MemoryKind.SEMANTIC),
            procedural=store.count(MemoryKind.PROCEDURAL),
            total=store.count(),
        )

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        agent.close()

    return app


async def _stream_openai(agent: Agent, messages: list[Message], model: str, req: ChatRequest):
    chunk_id = f"chatcmpl-{uuid4().hex[:24]}"
    created = int(time.time())
    pieces: list[str] = []
    async for piece in agent.provider.stream(
        messages,
        model=model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    ):
        pieces.append(piece)
        chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
    done = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done)}\n\n"
    yield "data: [DONE]\n\n"
    # Persist as a single turn for memory accumulation.
    last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
    if last_user:
        agent._remember_turn(last_user, "".join(pieces))


def _build_memory(req: CreateMemoryRequest) -> Memory:
    if req.kind == "episodic":
        return EpisodicMemory(
            content=req.content,
            importance=req.importance,
            tags=req.tags,
            source="api",
        )
    if req.kind == "semantic":
        return SemanticMemory(
            content=req.content,
            importance=req.importance,
            tags=req.tags,
        )
    if req.kind == "procedural":
        return ProceduralMemory(
            content=req.content,
            importance=req.importance,
            tags=req.tags,
        )
    raise HTTPException(status_code=400, detail=f"unknown kind '{req.kind}'")


def _to_out(m: Memory) -> MemoryOut:
    return MemoryOut(
        id=m.id,
        kind=m.kind.value,
        content=m.content,
        created_at=m.created_at.isoformat(),
        last_accessed_at=m.last_accessed_at.isoformat(),
        access_count=m.access_count,
        importance=m.importance,
        tags=list(m.tags),
        metadata=dict(m.metadata),
    )
