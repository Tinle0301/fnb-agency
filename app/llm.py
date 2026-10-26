"""Model API access behind a small interface, so agents can be tested with a fake."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    """The model returned something the pipeline cannot use."""


@dataclass
class LLMResult(Generic[T]):
    output: T
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None


class LLM(Protocol):
    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        output_type: type[T],
        model: str,
        effort: str | None = None,
        max_tokens: int = 16000,
    ) -> LLMResult[T]: ...


class AnthropicLLM:
    """Calls the model with a Pydantic structured-output schema and returns the parsed object."""

    def __init__(
        self, client: anthropic.AsyncAnthropic | None = None, use_refusal_fallbacks: bool = False
    ) -> None:
        self._client = client or anthropic.AsyncAnthropic()
        self._use_fallbacks = use_refusal_fallbacks

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        output_type: type[T],
        model: str,
        effort: str | None = None,
        max_tokens: int = 16000,
    ) -> LLMResult[T]:
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_format": output_type,
            "thinking": {"type": "adaptive"},
        }
        if effort:
            kwargs["output_config"] = {"effort": effort}
        if self._use_fallbacks:
            kwargs["betas"] = [_FALLBACK_BETA]
            kwargs["fallbacks"] = "default"

        response = await self._client.beta.messages.parse(**kwargs)

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise LLMError(f"model declined the request: {details}")
        if response.stop_reason == "max_tokens":
            raise LLMError(f"output hit max_tokens={max_tokens} before the schema was complete")
        if response.parsed_output is None:
            raise LLMError(f"no parsed output (stop_reason={response.stop_reason})")

        return LLMResult(
            output=response.parsed_output,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )
