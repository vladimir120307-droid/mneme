"""OpenAI-compatible backend.

Works with the official OpenAI API and anything that mirrors its
/v1/chat/completions shape (vLLM, LM Studio, OpenRouter, Together, etc.).
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

from mneme.providers.base import ChatResponse, LLMProvider, Message


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _payload(
        self,
        messages: list[Message],
        model: str,
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict:
        body: dict = {
            "model": model,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages
            ],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        return body

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
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        choice = data["choices"][0]
        return ChatResponse(
            content=choice["message"]["content"] or "",
            model=data.get("model", model),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
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
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_s = line[5:].strip()
                    if data_s == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_s)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk["choices"][0].get("delta", {})
                    piece = delta.get("content")
                    if piece:
                        yield piece
