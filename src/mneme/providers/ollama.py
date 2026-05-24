"""Ollama backend.

Talks to a local Ollama server (default http://localhost:11434).
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from mneme.providers.base import ChatResponse, LLMProvider, Message


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _payload(
        self,
        messages: list[Message],
        model: str,
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict:
        options: dict = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        return {
            "model": model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "options": options,
            "stream": stream,
        }

    async def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **_: object,
    ) -> ChatResponse:
        payload = self._payload(messages, model, temperature, max_tokens, stream=False)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        content = data.get("message", {}).get("content", "")
        usage = {
            "prompt_tokens": int(data.get("prompt_eval_count", 0)),
            "completion_tokens": int(data.get("eval_count", 0)),
        }
        return ChatResponse(
            content=content,
            model=model,
            finish_reason="stop" if data.get("done") else "length",
            usage=usage,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **_: object,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, model, temperature, max_tokens, stream=True)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if chunk.get("done"):
                        break

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{self.base_url}/api/tags")
            r.raise_for_status()
            data = r.json()
        return [m["name"] for m in data.get("models", [])]
