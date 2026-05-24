"""Persistent memory store.

SQLite for durable storage, HNSW for vector search. Designed so the API is
stable enough that a native (C++) backend can replace the Python path later
without touching callers.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from platformdirs import user_data_dir

from mneme.memory.embeddings import DEFAULT_MODEL, Embedder
from mneme.memory.index import VectorIndex, make_index
from mneme.memory.types import (
    EpisodicMemory,
    Memory,
    MemoryKind,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id                TEXT PRIMARY KEY,
    kind              TEXT NOT NULL,
    content           TEXT NOT NULL,
    created_at        REAL NOT NULL,
    last_accessed_at  REAL NOT NULL,
    access_count      INTEGER NOT NULL DEFAULT 0,
    importance        REAL NOT NULL DEFAULT 0.5,
    tags              TEXT NOT NULL DEFAULT '[]',
    metadata          TEXT NOT NULL DEFAULT '{}',
    type_fields       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
"""


def _default_data_dir() -> Path:
    return Path(user_data_dir("mneme", appauthor=False))


def _ts(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


_TYPE_MAP: dict[MemoryKind, type[Memory]] = {
    MemoryKind.WORKING: WorkingMemory,
    MemoryKind.EPISODIC: EpisodicMemory,
    MemoryKind.SEMANTIC: SemanticMemory,
    MemoryKind.PROCEDURAL: ProceduralMemory,
}

_BASE_FIELDS = {
    "id", "kind", "content", "created_at", "last_accessed_at",
    "access_count", "importance", "tags", "metadata",
}


class MemoryStore:
    """All four memory kinds in one durable store, with vector search."""

    def __init__(
        self,
        path: str | Path | None = None,
        embedder: Embedder | None = None,
        model_name: str = DEFAULT_MODEL,
        index_backend: str = "auto",
    ):
        base = Path(path) if path else _default_data_dir()
        base.mkdir(parents=True, exist_ok=True)
        self.base = base
        self.db_path = base / "memories.db"
        self.index_path = base / "memories.idx"
        self.index_backend = index_backend

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

        self.embedder = embedder or Embedder(model_name)
        self._index: VectorIndex | None = None  # lazy

    # ── lifecycle ───────────────────────────────────────────────────────

    @property
    def index(self) -> VectorIndex:
        if self._index is None:
            try:
                self._index = VectorIndex.load(
                    self.index_path, dim=self.embedder.dim, backend=self.index_backend
                )
            except Exception:
                self._index = make_index(self.embedder.dim, backend=self.index_backend)
            # if the persisted index is empty but the db has rows, rebuild
            if len(self._index) == 0:
                self._rebuild_index()
        return self._index

    def close(self) -> None:
        with self._lock:
            if self._index is not None:
                self._index.save(self.index_path)
            self._conn.commit()
            self._conn.close()

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── write path ──────────────────────────────────────────────────────

    def add(self, memory: Memory) -> Memory:
        vec = self.embedder.embed(memory.content)
        with self._lock:
            self._write_row(memory)
            self.index.add(memory.id, vec)
        return memory

    def add_many(self, memories: Iterable[Memory]) -> list[Memory]:
        items = list(memories)
        if not items:
            return []
        vecs = self.embedder.embed_many([m.content for m in items])
        with self._lock:
            for mem, vec in zip(items, vecs, strict=True):
                self._write_row(mem)
                self.index.add(mem.id, vec)
        return items

    def delete(self, memory_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.commit()
            if self._index is not None:
                self._index.remove(memory_id)

    def touch(self, memory_id: str) -> None:
        now = _ts(datetime.now(timezone.utc))
        with self._lock:
            self._conn.execute(
                "UPDATE memories SET last_accessed_at = ?, "
                "access_count = access_count + 1 WHERE id = ?",
                (now, memory_id),
            )
            self._conn.commit()

    def update_importance(self, memory_id: str, importance: float) -> None:
        importance = max(0.0, min(1.0, importance))
        with self._lock:
            self._conn.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (importance, memory_id),
            )
            self._conn.commit()

    # ── read path ───────────────────────────────────────────────────────

    def get(self, memory_id: str) -> Memory | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
        return _row_to_memory(row) if row else None

    def list(
        self,
        kind: MemoryKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Memory]:
        sql = "SELECT * FROM memories"
        args: list[object] = []
        if kind is not None:
            sql += " WHERE kind = ?"
            args.append(kind.value)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        args.extend([limit, offset])
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [_row_to_memory(r) for r in rows]

    def count(self, kind: MemoryKind | None = None) -> int:
        if kind is None:
            sql, args = "SELECT COUNT(*) FROM memories", ()
        else:
            sql, args = "SELECT COUNT(*) FROM memories WHERE kind = ?", (kind.value,)
        with self._lock:
            return int(self._conn.execute(sql, args).fetchone()[0])

    def search(
        self,
        query: str,
        kind: MemoryKind | None = None,
        k: int = 10,
        *,
        recency_half_life_days: float = 30.0,
        weights: tuple[float, float, float, float] = (0.55, 0.20, 0.20, 0.05),
    ) -> list[tuple[Memory, float]]:
        """Hybrid scoring: similarity + recency + importance + access boost.

        Scoring is vectorised (numpy or, when compiled, the native kernel)
        and only the top-K rows are materialised into ``Memory`` objects.
        """
        if not query:
            return []
        qvec = self.embedder.embed(query)
        # over-fetch then filter by kind, since the index has no kind filter
        candidates = self.index.search(qvec, k=k * 4 if kind else k * 2)
        if not candidates:
            return []
        ids = [mid for mid, _ in candidates]
        placeholders = ",".join("?" * len(ids))
        sql = (
            "SELECT id, created_at, access_count, importance "
            f"FROM memories WHERE id IN ({placeholders})"
        )
        args: list[object] = list(ids)
        if kind is not None:
            sql += " AND kind = ?"
            args.append(kind.value)
        with self._lock:
            light_rows = self._conn.execute(sql, args).fetchall()
        if not light_rows:
            return []

        sim_lookup = dict(candidates)
        n = len(light_rows)
        sim = np.empty(n, dtype=np.float32)
        created_ts = np.empty(n, dtype=np.float64)
        access = np.empty(n, dtype=np.int64)
        importance = np.empty(n, dtype=np.float32)
        for i, r in enumerate(light_rows):
            sim[i] = sim_lookup.get(r["id"], 0.0)
            created_ts[i] = r["created_at"]
            access[i] = r["access_count"]
            importance[i] = r["importance"]

        now_ts = datetime.now(timezone.utc).timestamp()
        scores = _hybrid_score(
            sim, created_ts, access, importance,
            now_ts=now_ts,
            half_life_days=recency_half_life_days,
            weights=weights,
        )

        # partial sort: find indices of top-K largest scores
        kk = min(k, n)
        if kk <= 0:
            return []
        top_idx = np.argpartition(-scores, kth=kk - 1)[:kk]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        top_ids = [light_rows[int(i)]["id"] for i in top_idx]

        # only now hydrate the top-K rows into Memory objects
        full_placeholders = ",".join("?" * len(top_ids))
        with self._lock:
            full_rows = self._conn.execute(
                f"SELECT * FROM memories WHERE id IN ({full_placeholders})",
                top_ids,
            ).fetchall()
        by_id = {r["id"]: r for r in full_rows}
        out: list[tuple[Memory, float]] = []
        for i in top_idx:
            mid = light_rows[int(i)]["id"]
            row = by_id.get(mid)
            if row is None:
                continue
            out.append((_row_to_memory(row), float(scores[int(i)])))
        for mem, _ in out:
            self.touch(mem.id)
        return out

    # ── maintenance ─────────────────────────────────────────────────────

    def decay(
        self,
        *,
        half_life_days: float = 30.0,
        importance_floor: float = 0.2,
        min_access: int = 1,
    ) -> int:
        """Prune low-value episodic memories. Returns rows removed."""
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - half_life_days * 86_400.0
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM memories "
                "WHERE kind = ? AND importance < ? "
                "AND access_count <= ? AND last_accessed_at < ?",
                (MemoryKind.EPISODIC.value, importance_floor, min_access, cutoff),
            ).fetchall()
            ids = [r["id"] for r in rows]
            for mid in ids:
                self._conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
                if self._index is not None:
                    self._index.remove(mid)
            self._conn.commit()
        return len(ids)

    # ── internals ───────────────────────────────────────────────────────

    def _write_row(self, memory: Memory) -> None:
        data = memory.model_dump(mode="json")
        type_fields = {k: v for k, v in data.items() if k not in _BASE_FIELDS}
        self._conn.execute(
            "INSERT OR REPLACE INTO memories "
            "(id, kind, content, created_at, last_accessed_at, access_count, "
            " importance, tags, metadata, type_fields) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                memory.id,
                memory.kind.value,
                memory.content,
                _ts(memory.created_at),
                _ts(memory.last_accessed_at),
                memory.access_count,
                memory.importance,
                json.dumps(memory.tags),
                json.dumps(memory.metadata),
                json.dumps(type_fields),
            ),
        )
        self._conn.commit()

    def _rebuild_index(self) -> None:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, content FROM memories"
            ).fetchall()
        if not rows:
            return
        vecs = self.embedder.embed_many([r["content"] for r in rows])
        for row, vec in zip(rows, vecs, strict=True):
            assert self._index is not None
            self._index.add(row["id"], vec)


def _hybrid_score(
    sim: np.ndarray,
    created_ts: np.ndarray,
    access: np.ndarray,
    importance: np.ndarray,
    *,
    now_ts: float,
    half_life_days: float,
    weights: tuple[float, float, float, float],
) -> np.ndarray:
    """Vectorised hybrid retrieval score. Uses native kernel when present."""
    try:
        from mneme import _native  # type: ignore[attr-defined]

        w = _native.ScoreWeights()
        w.w_sim, w.w_recency, w.w_importance, w.w_access = weights
        w.recency_half_life_days = float(half_life_days)
        return np.asarray(
            _native.compute_scores(sim, created_ts, access, importance, w, now_ts)
        )
    except ImportError:
        pass

    w_sim, w_recency, w_imp, w_access = weights
    age_days = np.maximum(0.0, (now_ts - created_ts) / 86_400.0)
    recency = np.exp(-age_days / half_life_days).astype(np.float32)
    access_boost = (1.0 - np.exp(-access.astype(np.float32) / 5.0)).astype(np.float32)
    return (
        np.float32(w_sim) * sim
        + np.float32(w_recency) * recency
        + np.float32(w_imp) * importance
        + np.float32(w_access) * access_boost
    )


def _row_to_memory(row: sqlite3.Row) -> Memory:
    kind = MemoryKind(row["kind"])
    cls = _TYPE_MAP[kind]
    type_fields: dict = json.loads(row["type_fields"] or "{}")
    payload = {
        "id": row["id"],
        "kind": kind,
        "content": row["content"],
        "created_at": _dt(row["created_at"]),
        "last_accessed_at": _dt(row["last_accessed_at"]),
        "access_count": row["access_count"],
        "importance": row["importance"],
        "tags": json.loads(row["tags"] or "[]"),
        "metadata": json.loads(row["metadata"] or "{}"),
        **{k: v for k, v in type_fields.items() if k != "kind"},
    }
    return cls(**payload)


# silence "unused" complaints in static analysis for re-exported types
_REEXPORT = (EpisodicMemory, WorkingMemory, SemanticMemory, ProceduralMemory, np)
