"""Clients for the language model. Switching provider must only take configuration.

The game only asks a model for one thing: a JSON object that follows a schema, to interpret
the player's sentence.
"""

import json
from collections.abc import Iterable
from typing import Any, Protocol

import httpx


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

    def complete_json(
        self, system: str, user: str, schema: dict[str, Any], max_tokens: int, temperature: float = 0
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "keep_alive": self.KEEP_ALIVE,
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": self.NUM_CTX},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            response = self._http.post("/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMError(f"Ollama: {exc}") from exc
        if "error" in body:
            raise LLMError(f"Ollama: {body['error']}")
        try:
            reply = json.loads(body["message"]["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMError(f"Ollama: the reply is not JSON: {exc}") from exc
        if not isinstance(reply, dict):
            raise LLMError("Ollama: the reply is not a JSON object")
        return reply

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
