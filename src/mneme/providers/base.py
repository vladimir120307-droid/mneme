"""Provider abstraction.

Every backend (Ollama, OpenAI, Anthropic, any OpenAI-compatible endpoint)
implements this protocol so the agent can switch backends with one config value.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    name: str | None = None


@dataclass
class ChatResponse:
    content: str
    model: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> ChatResponse: ...

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> AsyncIterator[str]:
        """Default streaming: call chat() and yield the whole content once.

        Providers that support real streaming should override this.
        """
        resp = await self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield resp.content
