"""Clients for the language model. Switching provider must only take configuration.

The game only asks a model for one thing: a JSON object that follows a schema, to interpret
the player's sentence.
"""

import json
import logging
import time
from collections.abc import Iterable
from typing import Any, Protocol

import httpx

# What goes to the model and what comes back; app/cli.py writes it to logs/llm.log.
log = logging.getLogger(__name__)


class LLMError(Exception):
    """The model didn't answer, or answered something unusable: the sentence is not understood."""


class LLMClient(Protocol):
    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int, temperature: float = 0
    ) -> dict[str, Any]: ...

    def unavailable_reason(self) -> str | None:
        """None when the model can be used, otherwise why not (in Italian, for the player)."""
        ...


class OllamaClient:
    """Ollama's own API (/api/chat), with structured output through `format`."""

    NUM_CTX = 2048  # the prompts are short: a small context is faster on CPU
    KEEP_ALIVE = "30m"  # loading the model takes seconds: keep it in memory between turns

    def __init__(
        self, base_url: str, model: str, transport: httpx.BaseTransport | None = None, timeout: float = 120
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._http = httpx.Client(
            base_url=self.base_url, transport=transport, timeout=httpx.Timeout(timeout, connect=5)
        )
        self._logged_system_prompt: str | None = None

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int, temperature: float = 0
    ) -> dict[str, Any]:
        self._log_system_prompt(system)
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "keep_alive": self.KEEP_ALIVE,
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": self.NUM_CTX},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        started = time.perf_counter()
        body: dict[str, Any] = {}
        try:
            body = self._chat(payload)
            reply = _json_object(body)
        except LLMError as exc:
            log.warning("%s  errore: %s\n%s", self.model, exc, _exchange(user, _content(body)))
            raise
        elapsed = time.perf_counter() - started
        log.info("%s  %.1f s  %s\n%s", self.model, elapsed, _counters(body), _exchange(user, _content(body)))
        return reply

    def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.post("/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMError(f"Ollama: {exc}") from exc
        if not isinstance(body, dict):
            raise LLMError("Ollama: unexpected reply")
        if "error" in body:
            raise LLMError(f"Ollama: {body['error']}")
        return body

    def _log_system_prompt(self, system: str) -> None:
        """Only when it changes: it is long, and the same for every call."""
        if system != self._logged_system_prompt:
            log.info("prompt di sistema:\n%s", "\n".join(f"    {line}" for line in system.splitlines()))
            self._logged_system_prompt = system

    def unavailable_reason(self) -> str | None:
        try:
            response = self._http.get("/api/tags", timeout=5)
            response.raise_for_status()
            pulled = {model.get("name") for model in response.json().get("models", [])}
        except (httpx.HTTPError, ValueError, AttributeError):
            return f"Ollama non risponde su {self.base_url}."
        wanted = {self.model} if ":" in self.model else {self.model, f"{self.model}:latest"}
        if pulled.isdisjoint(wanted):
            return f"Il modello {self.model} non è scaricato: esegui «ollama pull {self.model}»."
        return None


def _json_object(body: dict[str, Any]) -> dict[str, Any]:
    try:
        reply = json.loads(body["message"]["content"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LLMError(f"Ollama: the reply is not JSON: {exc}") from exc
    if not isinstance(reply, dict):
        raise LLMError("Ollama: the reply is not a JSON object")
    return reply


def _content(body: dict[str, Any]) -> str | None:
    message = body.get("message")
    return message.get("content") if isinstance(message, dict) else None


def _counters(body: dict[str, Any]) -> str:
    prompt = body.get("prompt_eval_count", "?")
    cached = body.get("prompt_eval_cached_count", "?")
    reply = body.get("eval_count", "?")
    return f"prompt {prompt} token ({cached} in cache), risposta {reply} token"


def _exchange(sent: str, received: str | None) -> str:
    """>>> what was sent, <<< what came back, line by line."""
    lines = [f">>> {line}" for line in sent.splitlines()]
    if received is not None:
        lines += [f"<<< {line}" for line in received.splitlines() or [""]]
    return "\n".join(lines)


class FakeLLMClient:
    """Canned answers, for tests: each call takes the next one; with none left it fails like a broken model."""

    def __init__(self, json_replies: Iterable[dict[str, Any]] = ()) -> None:
        self._json_replies = list(json_replies)
        self.calls: list[tuple[str, str]] = []  # (system, user)

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int, temperature: float = 0
    ) -> dict[str, Any]:
        self.calls.append((system, user))
        if not self._json_replies:
            raise LLMError("no canned reply left")
        return self._json_replies.pop(0)

    def unavailable_reason(self) -> str | None:
        return None
