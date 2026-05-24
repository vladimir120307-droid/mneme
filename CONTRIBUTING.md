# Contributing to Mneme

Thanks for thinking about helping. Mneme is small enough that a single
afternoon can move it forward in a meaningful way.

> 🇷🇺 Русская версия: [`CONTRIBUTING.ru.md`](CONTRIBUTING.ru.md)

## Ground rules

1. **Open an issue before a large PR.** A few lines of agreement up front
   saves a rewrite later.
2. **Keep the surface small.** Mneme is library + CLI + REST, nothing
   else. Features that don't serve all three usually don't belong here.
3. **Tests + ruff must be green** before review.
4. **No new heavy dependencies** without a good reason. Pure-Python and
   numpy first, native acceleration second, third-party DBs / clouds last.

## Getting set up

```bash
git clone https://github.com/vladimir120307-droid/mneme
cd mneme
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check src/ tests/ benchmarks/
```

Optional, for the C++ core (drop-in faster backend):

```bash
pip install pybind11
python -m mneme.build_native
```

## How to propose a change

1. Fork → branch off `master`.
2. Make the change. Keep commits focused; one logical step per commit.
3. Run the test suite and the linter locally.
4. Open a PR. Title is imperative ("Add foo", "Fix bar"). Body explains
   the why; the diff explains the what.
5. CI will run the test/lint matrix and the native parity job. If
   anything goes red, it's yours to fix before review.

## Coding style

- Python 3.10+. Use modern type hints (`list[str]`, `X | None`).
- Ruff config in `pyproject.toml` is the source of truth. Don't bypass.
- No comments that just describe what the code does — only the
  non-obvious *why*.
- No print-debugging left in the diff.

## What's a good first contribution?

- Add a provider: implement `LLMProvider` for another OpenAI-compatible
  endpoint and register it.
- Sharpen retrieval: experiment with a different scoring formula in
  `memory/store.py` and add a benchmark.
- Bring in a memory-import format: ChatGPT export, journal Markdown, etc.
- Improve docs — typos, clearer examples, better diagrams.

## Reporting bugs

Please file via GitHub Issues with a minimal reproducer. The bug template
will ask for: Mneme version, Python version, OS, provider/model used,
and the exact error message and traceback.

## Security

See [`SECURITY.md`](SECURITY.md) for how to report vulnerabilities
privately.
