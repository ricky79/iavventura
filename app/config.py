"""Settings from environment variables.

    LLM          ollama (default) | off
    OLLAMA_URL   default http://127.0.0.1:11434
    LLM_MODEL    default qwen2.5:3b
    LLM_LOG      file for what goes to the model and comes back; default logs/llm.log, off to disable
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.llm.client import LLMClient, OllamaClient

PROVIDERS = ("ollama", "off")
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LLM_LOG = LOGS_DIR / "llm.log"


@dataclass(frozen=True)
class Settings:
    llm: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"  # not localhost: on Windows it tries IPv6 first (~2 s)
    model: str = "qwen2.5:3b"
    llm_log: str = str(DEFAULT_LLM_LOG)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ, default_llm_log: Path = DEFAULT_LLM_LOG) -> "Settings":
        """`default_llm_log` lets each front end (terminal, web) keep its own log file."""
        llm = env.get("LLM", cls.llm).strip().lower()
        if llm not in PROVIDERS:
            raise ValueError(f"LLM={llm!r}: valid values are {', '.join(PROVIDERS)}")
        llm_log = env.get("LLM_LOG", str(default_llm_log)).strip()
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


def start_llm_log(path: str) -> None:
    """Appends what goes to the model and what comes back to `path` ("off": no log)."""
    if path == "off":
        return
    log_file = Path(path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger = logging.getLogger("app.llm")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
