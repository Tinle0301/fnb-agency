"""Model access behind a small interface, so agents can be tested with a fake.

Two backends: the model API (AnthropicLLM, needs an API key) and a local assistant CLI
(CliLLM, uses that tool's own sign-in).
"""

from __future__ import annotations

import asyncio
import json
import re
import shlex
import tempfile
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Generic, Protocol, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

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


@dataclass
class SearchResult:
    """What a web lookup found, in the model's words, with the pages it used."""

    text: str
    sources: list[dict[str, str]]  # {"title", "url"}
    model: str
    input_tokens: int
    output_tokens: int
    searches: int


WEB_SEARCH_TOOL = "web_search_20260209"
_MAX_CONTINUATIONS = 4


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


class WebSearchLLM(Protocol):
    """An LLM that can also look things up on the web (optional; agents skip lookups without it)."""

    async def search(self, *, system: str, prompt: str, model: str, max_searches: int = 5) -> SearchResult: ...


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

    async def search(self, *, system: str, prompt: str, model: str, max_searches: int = 5) -> SearchResult:
        """Free-text answer grounded in the server-side web search tool.

        Kept apart from generate(): the lookup is plain text the structured call then reads,
        so the parse path never mixes search citations with a response schema.
        """
        tools = [{"type": WEB_SEARCH_TOOL, "name": "web_search", "max_uses": max_searches}]
        messages: list[dict] = [{"role": "user", "content": prompt}]
        content: list = []
        input_tokens = output_tokens = 0
        for _ in range(_MAX_CONTINUATIONS + 1):
            response = await self._client.messages.create(
                model=model,
                max_tokens=16000,
                system=system,
                messages=messages,
                tools=tools,
                thinking={"type": "adaptive"},
            )
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            content.extend(response.content)
            if response.stop_reason == "refusal":
                raise LLMError(f"model declined the web lookup: {getattr(response, 'stop_details', None)}")
            if response.stop_reason != "pause_turn":
                break
            # The server paused its search loop; send the turn back unchanged and it resumes.
            messages = [messages[0], {"role": "assistant", "content": response.content}]

        text = "".join(getattr(b, "text", "") for b in content if b.type == "text").strip()
        sources: list[dict[str, str]] = []
        seen: set[str] = set()
        searches = 0
        for block in content:
            if block.type == "server_tool_use":
                searches += 1
            if block.type == "web_search_tool_result" and isinstance(block.content, list):
                for hit in block.content:
                    url = getattr(hit, "url", "")
                    if url.startswith(("https://", "http://")) and url not in seen:
                        seen.add(url)
                        sources.append({"title": getattr(hit, "title", "") or url, "url": url})
        if not text:
            raise LLMError("web lookup returned no text")
        return SearchResult(text, sources[:12], model, input_tokens, output_tokens, searches)


_URL = re.compile(r"https?://[^\s)>\]\"']+")


class CliLLM:
    """Runs every model call through a desktop assistant's command-line tool in headless print mode.

    The CLI uses its own sign-in (for example a personal subscription), so no API key is needed.
    Set LLM_BACKEND=cli and AGENT_CLI to the command in .env. Each call runs in an empty temporary
    folder with no tools (or only web search for lookups), so it cannot touch files.
    """

    def __init__(self, command: str, timeout_s: int = 900) -> None:
        if not command.strip():
            raise ValueError("Set AGENT_CLI in .env to the command of the assistant CLI")
        self._command = shlex.split(command)
        self._timeout_s = timeout_s

    async def _run(self, prompt: str, args: list[str]) -> dict:
        with tempfile.TemporaryDirectory(prefix="fnb-agency-") as cwd:
            proc = await asyncio.create_subprocess_exec(
                *self._command, "-p", "--output-format", "json", "--no-session-persistence",
                "--strict-mcp-config", *args,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), self._timeout_s)
            except asyncio.TimeoutError:
                proc.kill()
                raise LLMError(f"assistant CLI took longer than {self._timeout_s}s")
        try:
            data = json.loads(out.decode() or "{}")
        except json.JSONDecodeError:
            raise LLMError(f"assistant CLI did not return JSON (exit {proc.returncode}): {err.decode()[-400:]}")
        if proc.returncode != 0 or data.get("is_error"):
            raise LLMError(f"assistant CLI failed: {str(data.get('result') or err.decode())[-400:]}")
        return data

    @staticmethod
    def _tokens(data: dict) -> tuple[int, int]:
        u = data.get("usage") or {}
        return (
            int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0)),
            int(u.get("output_tokens", 0)),
        )

    async def generate(self, *, system, prompt, output_type, model, effort=None, max_tokens=16000):
        args = ["--model", model, "--system-prompt", system, "--tools", "",
                "--json-schema", json.dumps(output_type.model_json_schema())]
        if effort:
            args += ["--effort", effort]
        data = await self._run(prompt, args)
        raw = data.get("structured_output")
        if raw is None:
            raise LLMError("assistant CLI returned no structured output")
        try:
            output = output_type.model_validate(raw)
        except ValidationError as exc:
            raise LLMError(f"assistant CLI output did not match the schema: {exc}") from exc
        tokens_in, tokens_out = self._tokens(data)
        return LLMResult(output=output, model=model, input_tokens=tokens_in, output_tokens=tokens_out,
                         stop_reason=data.get("stop_reason"))

    async def search(self, *, system, prompt, model, max_searches=5):
        args = ["--model", model, "--system-prompt", system, "--tools", "WebSearch,WebFetch",
                "--allowedTools", "WebSearch", "WebFetch"]
        data = await self._run(
            f"{prompt}\n\nUse at most {max_searches} web searches. End with a line 'Sources:' and then one URL per line.",
            args,
        )
        text = str(data.get("result") or "").strip()
        if not text:
            raise LLMError("web lookup returned no text")
        body, _, tail = text.rpartition("Sources:")
        urls = list(dict.fromkeys(_URL.findall(tail if body else text)))[:12]
        sources = [{"title": urlparse(u).netloc or u, "url": u} for u in urls]
        searches = int(((data.get("usage") or {}).get("server_tool_use") or {}).get("web_search_requests", 0))
        tokens_in, tokens_out = self._tokens(data)
        return SearchResult((body or text).strip(), sources, model, tokens_in, tokens_out, searches)
