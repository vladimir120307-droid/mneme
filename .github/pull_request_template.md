<!--
Title format:
  Imperative, under 70 chars. Examples:
    Fix decay leaving zero-row in the index
    Add OpenRouter base_url override
    Speed up MemoryStore.search hot path
-->

## What changes

<!-- One short paragraph. The "what" lives in the diff — focus on the why. -->

## Why

<!-- What problem does this solve? Link an issue if applicable. -->

## Tests

- [ ] `pytest` passes locally
- [ ] `ruff check src/ tests/ benchmarks/` clean
- [ ] If you touched the C++ core: `python -m mneme.build_native` and parity tests pass

## Notes for reviewer

<!-- Tricky bits, follow-ups deferred, things you almost did but didn't. Optional. -->

---

By submitting this PR you confirm that:

- [ ] Your change follows [CONTRIBUTING.md](../CONTRIBUTING.md).
- [ ] You did **not** add a heavy dependency without discussing it first.
- [ ] No `print()` debugging / dead code left in the diff.
