from mneme.consolidation import _parse_facts


def test_parse_plain_json():
    txt = '{"facts": [{"statement": "user likes Rust", "confidence": 0.8, "support_ids": ["a"]}]}'
    facts = _parse_facts(txt)
    assert facts == [{"statement": "user likes Rust", "confidence": 0.8, "support_ids": ["a"]}]


def test_parse_fenced_json():
    txt = '```json\n{"facts": [{"statement": "x", "confidence": 0.5}]}\n```'
    facts = _parse_facts(txt)
    assert len(facts) == 1
    assert facts[0]["statement"] == "x"


def test_parse_with_surrounding_chatter():
    txt = 'Sure! Here are the facts:\n{"facts": [{"statement": "ok"}]}\nLet me know.'
    facts = _parse_facts(txt)
    assert facts == [{"statement": "ok"}]


def test_parse_invalid_returns_empty():
    assert _parse_facts("nope") == []
    assert _parse_facts("{not json") == []
