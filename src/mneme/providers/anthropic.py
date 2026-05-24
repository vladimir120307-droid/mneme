"""Anthropic backend.

Talks to the Messages API directly via httpx so we don't pull in another SDK.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

from mneme.providers.base import ChatResponse, LLMProvider, Message


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        base_url: str = "https://api.anthropic.com",
        api_key: str | None = None,
        version: str = "2023-06-01",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.version = version
        self.timeout = timeout

    def _split(self, messages: list[Message]) -> tuple[str, list[dict]]:
        system_parts: list[str] = []
        convo: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                role = "assistant" if m.role == "assistant" else "user"
                convo.append({"role": role, "content": m.content})
        return "\n\n".join(system_parts), convo

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
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
        system, convo = self._split(messages)
        payload = {
            "model": model,
            "messages": convo,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        content = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        return ChatResponse(
            content=content,
            model=data.get("model", model),
            finish_reason=data.get("stop_reason", "stop"),
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
        system, convo = self._split(messages)
        payload = {
            "model": model,
            "messages": convo,
            "max_tokens": max_tokens or 1024,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=self.timeout) as client, client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            headers=self._headers(),
            json=payload,
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    evt = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if evt.get("type") == "content_block_delta":
                    delta = evt.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield delta.get("text", "")
