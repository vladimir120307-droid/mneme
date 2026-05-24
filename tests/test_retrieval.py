from mneme.memory.retrieval import retrieve
from mneme.memory.types import EpisodicMemory, SemanticMemory


def test_retrieve_assembles_context_block(store):
    store.add(SemanticMemory(content="The user's name is Vladimir"))
    store.add(EpisodicMemory(content="User asked about Rust async"))
    ctx = retrieve(store, "what was the user asking?")
    text = ctx.as_system_message()
    assert "Vladimir" in text or "Rust" in text


def test_retrieve_empty_store_returns_empty_block(store):
    ctx = retrieve(store, "anything")
    assert ctx.as_system_message() == ""
