"""Talk to a running Mneme server (start it with: mneme serve)."""

from __future__ import annotations

import httpx


def main() -> None:
    base = "http://127.0.0.1:8077"

    # Seed memory
    httpx.post(
        f"{base}/v1/memories",
        json={
            "kind": "semantic",
            "content": "The user is named Vladimir and codes in Rust and Python.",
            "importance": 0.9,
        },
        timeout=30,
    ).raise_for_status()

    # OpenAI-compatible chat — works with any OpenAI client
    r = httpx.post(
        f"{base}/v1/chat/completions",
        json={
            "messages": [
                {"role": "user", "content": "Remind me what languages I work with."}
            ],
            "temperature": 0.4,
        },
        timeout=120,
    )
    r.raise_for_status()
    print(r.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
