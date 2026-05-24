from mneme.memory.types import (
    EpisodicMemory,
    MemoryKind,
    ProceduralMemory,
    SemanticMemory,
    WorkingMemory,
)


def test_kind_defaults_match_class():
    assert WorkingMemory(content="x").kind == MemoryKind.WORKING
    assert EpisodicMemory(content="x").kind == MemoryKind.EPISODIC
    assert SemanticMemory(content="x").kind == MemoryKind.SEMANTIC
    assert ProceduralMemory(content="x").kind == MemoryKind.PROCEDURAL


def test_touch_increments_and_dates_forward():
    m = EpisodicMemory(content="hello")
    before = m.last_accessed_at
    m.touch()
    assert m.access_count == 1
    assert m.last_accessed_at >= before


def test_importance_clamped():
    m = EpisodicMemory(content="x", importance=0.5)
    assert 0.0 <= m.importance <= 1.0


def test_semantic_supports_links():
    s = SemanticMemory(content="user likes Rust", support=["abc", "def"], confidence=0.9)
    assert s.support == ["abc", "def"]
    assert s.confidence == 0.9
