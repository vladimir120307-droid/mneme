"""MCP server: expose Mneme's memory layer to MCP-capable clients.

A single command — ``mneme mcp`` — runs this over stdio so that Cursor,
Claude Desktop, Windsurf, and any other MCP client can use Mneme as
their long-term memory layer.

Tools exposed:
- ``search_memory``: hybrid search across all stored memories.
- ``add_memory``: write a new episodic / semantic / procedural memory.
- ``list_memories``: enumerate recent memories, optionally filtered by kind.
- ``forget_memory``: delete a memory by id.
- ``memory_stats``: counts per kind.
- ``consolidate``: run a consolidation pass on demand.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

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
from mneme.providers.registry import get_provider


def _memory_dict(mem: Memory) -> dict[str, Any]:
    return {
        "id": mem.id,
        "kind": mem.kind.value,
        "content": mem.content,
        "created_at": mem.created_at.isoformat(),
        "last_accessed_at": mem.last_accessed_at.isoformat(),
        "access_count": mem.access_count,
        "importance": mem.importance,
        "tags": list(mem.tags),
    }


def _build_memory(kind: str, content: str, importance: float, tags: list[str]) -> Memory:
    if kind == "episodic":
        return EpisodicMemory(
            content=content, importance=importance, tags=tags, source="mcp"
        )
    if kind == "semantic":
        return SemanticMemory(content=content, importance=importance, tags=tags)
    if kind == "procedural":
        return ProceduralMemory(content=content, importance=importance, tags=tags)
    raise ValueError(
        f"unknown kind '{kind}'; expected episodic / semantic / procedural"
    )


def build_server(store: MemoryStore | None = None, *, name: str = "mneme") -> FastMCP:
    """Construct the FastMCP server with all Mneme tools bound."""
    settings = load_settings()
    store = store or MemoryStore(
        path=settings.data_dir,
        embedder=Embedder(settings.embedding_model),
    )
    mcp = FastMCP(name)

    @mcp.tool()
    def search_memory(
        query: str,
        kind: str | None = None,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Hybrid vector + recency + importance search over memory.

        Args:
            query: free-text search query.
            kind: restrict to one kind: episodic / semantic / procedural.
            k: how many hits to return (default 10, max 100).
        """
        k = max(1, min(int(k), 100))
        mk = MemoryKind(kind) if kind else None
        results = store.search(query, kind=mk, k=k)
        return [{"score": float(s), **_memory_dict(m)} for m, s in results]

    @mcp.tool()
    def add_memory(
        content: str,
        kind: str = "episodic",
        importance: float = 0.6,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save a new memory.

        Use this when you learn something durable about the user, project,
        or environment that future conversations should remember.

        Args:
            content: the fact or event, as natural-language text.
            kind: episodic (event) | semantic (general fact) | procedural (how-to).
            importance: 0.0 to 1.0, weights the memory's retrieval and decay.
            tags: optional list of short string tags.
        """
        importance = max(0.0, min(1.0, float(importance)))
        mem = _build_memory(kind, content, importance, list(tags or []))
        store.add(mem)
        return _memory_dict(mem)

    @mcp.tool()
    def list_memories(
        kind: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List the most recent memories, newest first."""
        limit = max(1, min(int(limit), 200))
        mk = MemoryKind(kind) if kind else None
        return [_memory_dict(m) for m in store.list(kind=mk, limit=limit)]

    @mcp.tool()
    def forget_memory(memory_id: str) -> dict[str, Any]:
        """Delete a memory by its id."""
        store.delete(memory_id)
        return {"deleted": memory_id}

    @mcp.tool()
    def memory_stats() -> dict[str, int]:
        """Counts per memory kind plus total."""
        return {
            "working": store.count(MemoryKind.WORKING),
            "episodic": store.count(MemoryKind.EPISODIC),
            "semantic": store.count(MemoryKind.SEMANTIC),
            "procedural": store.count(MemoryKind.PROCEDURAL),
            "total": store.count(),
        }

    @mcp.tool()
    async def consolidate(
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, int]:
        """Run one consolidation pass — distil episodic → semantic.

        Uses the configured provider/model unless overridden here. Cheap
        to call; bounded by one model call per pass.
        """
        from mneme.consolidation import Consolidator

        prov_name = provider or settings.provider
        model_name = model or settings.model
        prov = get_provider(prov_name)
        consolidator = Consolidator(store, prov, model_name)
        n = await consolidator.run_once()
        return {"created_semantic_memories": n}

    return mcp


def run_stdio() -> None:
    """Entry point — runs the MCP server on stdio."""
    server = build_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover
    run_stdio()
