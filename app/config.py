"""Settings from environment variables.

    LLM          ollama (default) | off
    OLLAMA_URL   default http://127.0.0.1:11434
    LLM_MODEL    default qwen2.5:3b
    LLM_LOG      file for what goes to the model and comes back; default logs/llm.log, off to disable
    COMMAND_LOG  JSON lines of the commands that went wrong; default logs/comandi.jsonl, off to disable
"""

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.llm.client import LLMClient, OllamaClient

PROVIDERS = ("ollama", "off")
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LLM_LOG = LOGS_DIR / "llm.log"
DEFAULT_COMMAND_LOG = LOGS_DIR / "comandi.jsonl"


@dataclass(frozen=True)
class Settings:
    llm: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"  # not localhost: on Windows it tries IPv6 first (~2 s)
    model: str = "qwen2.5:3b"
    llm_log: str = str(DEFAULT_LLM_LOG)
    command_log: str = str(DEFAULT_COMMAND_LOG)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ, default_llm_log: Path = DEFAULT_LLM_LOG) -> "Settings":
        """`default_llm_log` lets each front end (terminal, web) keep its own log file."""
        llm = env.get("LLM", cls.llm).strip().lower()
        if llm not in PROVIDERS:
            raise ValueError(f"LLM={llm!r}: valid values are {', '.join(PROVIDERS)}")
        llm_log = env.get("LLM_LOG", str(default_llm_log)).strip()
        command_log = env.get("COMMAND_LOG", cls.command_log).strip()
        return cls(
            llm=llm,
            ollama_url=env.get("OLLAMA_URL", cls.ollama_url),
            model=env.get("LLM_MODEL", cls.model),
            llm_log="off" if llm_log.lower() == "off" else llm_log,
            command_log="off" if command_log.lower() == "off" else command_log,
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


def start_command_log(path: str, origin: str) -> None:
    """Appends the commands that went wrong (see app/game.py) to `path`, one JSON object per line,
    with the time and the front end that played them: "terminale" or "web" ("off": no log)."""
    if path == "off":
        return
    log_file = Path(path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(_JsonLine(origin))
    logger = logging.getLogger("app.commands")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class _JsonLine(logging.Formatter):
    def __init__(self, origin: str) -> None:
        super().__init__()
        self.origin = origin

    def format(self, record: logging.LogRecord) -> str:
        time = datetime.fromtimestamp(record.created).isoformat(timespec="seconds")
        return json.dumps({"ora": time, "origine": self.origin, **record.command}, ensure_ascii=False)
