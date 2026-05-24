"""Runtime config loaded from env vars."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    data_dir: str | None
    embedding_model: str
    host: str
    port: int


def load_settings() -> Settings:
    return Settings(
        provider=os.environ.get("MNEME_PROVIDER", "ollama"),
        model=os.environ.get("MNEME_MODEL", "llama3.1"),
        data_dir=os.environ.get("MNEME_DATA_DIR"),
        embedding_model=os.environ.get(
            "MNEME_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        host=os.environ.get("MNEME_HOST", "127.0.0.1"),
        port=int(os.environ.get("MNEME_PORT", "8077")),
    )
