"""Settings from environment variables.

    LLM          ollama (default) | off
    OLLAMA_URL   default http://localhost:11434
    LLM_MODEL    default qwen2.5:3b
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from app.llm.client import LLMClient, OllamaClient

PROVIDERS = ("ollama", "off")


@dataclass(frozen=True)
class Settings:
    llm: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        llm = env.get("LLM", cls.llm).strip().lower()
        if llm not in PROVIDERS:
            raise ValueError(f"LLM={llm!r}: valid values are {', '.join(PROVIDERS)}")
        return cls(llm=llm, ollama_url=env.get("OLLAMA_URL", cls.ollama_url), model=env.get("LLM_MODEL", cls.model))


def make_client(settings: Settings) -> LLMClient | None:
    """None when the LLM is switched off."""
    if settings.llm == "off":
        return None
    return OllamaClient(settings.ollama_url, settings.model)
