from datetime import datetime, timedelta, timezone

from mneme.memory.types import EpisodicMemory, MemoryKind, SemanticMemory


def test_add_and_get(store):
    mem = EpisodicMemory(content="user lives in Berlin")
    store.add(mem)
    fetched = store.get(mem.id)
    assert fetched is not None
    assert fetched.content == "user lives in Berlin"
    assert fetched.kind == MemoryKind.EPISODIC


def test_list_filters_by_kind(store):
    store.add(EpisodicMemory(content="episode 1"))
    store.add(SemanticMemory(content="fact 1"))
    eps = store.list(kind=MemoryKind.EPISODIC)
    sems = store.list(kind=MemoryKind.SEMANTIC)
    assert len(eps) == 1 and eps[0].content == "episode 1"
    assert len(sems) == 1 and sems[0].content == "fact 1"


def test_search_returns_most_relevant(store):
    store.add(EpisodicMemory(content="user lives in Berlin", importance=0.8))
    store.add(EpisodicMemory(content="user enjoys Rust programming"))
    store.add(EpisodicMemory(content="weather is rainy today"))
    results = store.search("user lives in Berlin", k=3)
    assert results, "expected at least one hit"
    assert results[0][0].content == "user lives in Berlin"


def test_delete_removes_row(store):
    mem = store.add(EpisodicMemory(content="forget me"))
    store.delete(mem.id)
    assert store.get(mem.id) is None


def test_decay_prunes_old_low_value(store):
    old = EpisodicMemory(content="old chitchat", importance=0.05)
    # backdate
    old.created_at = datetime.now(timezone.utc) - timedelta(days=120)
    old.last_accessed_at = old.created_at
    store.add(old)
    keep = EpisodicMemory(content="important fact", importance=0.9)
    store.add(keep)
    removed = store.decay(half_life_days=30, importance_floor=0.2, min_access=1)
    assert removed == 1
    remaining = [m.id for m in store.list()]
    assert keep.id in remaining
    assert old.id not in remaining


def test_count_per_kind(store):
    store.add(EpisodicMemory(content="a"))
    store.add(EpisodicMemory(content="b"))
    store.add(SemanticMemory(content="fact"))
    assert store.count(MemoryKind.EPISODIC) == 2
    assert store.count(MemoryKind.SEMANTIC) == 1
    assert store.count() == 3
