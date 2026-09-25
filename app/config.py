"""Settings from environment variables.

    LLM          ollama (default) | off
    OLLAMA_URL   default http://localhost:11434
    LLM_MODEL    default qwen2.5:3b
    LLM_LOG      file for what goes to the model and comes back; default logs/llm.log, off to disable
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.llm.client import LLMClient, OllamaClient

PROVIDERS = ("ollama", "off")
DEFAULT_LLM_LOG = Path(__file__).resolve().parents[1] / "logs" / "llm.log"


@dataclass(frozen=True)
class Settings:
    llm: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    llm_log: str = str(DEFAULT_LLM_LOG)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        llm = env.get("LLM", cls.llm).strip().lower()
        if llm not in PROVIDERS:
            raise ValueError(f"LLM={llm!r}: valid values are {', '.join(PROVIDERS)}")
        llm_log = env.get("LLM_LOG", cls.llm_log).strip()
        return cls(
            llm=llm,
            ollama_url=env.get("OLLAMA_URL", cls.ollama_url),
            model=env.get("LLM_MODEL", cls.model),
            llm_log="off" if llm_log.lower() == "off" else llm_log,
        )


def make_client(settings: Settings) -> LLMClient | None:
    """None when the LLM is switched off."""
    if settings.llm == "off":
        return None
    return OllamaClient(settings.ollama_url, settings.model)
