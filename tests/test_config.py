"""Configuration from environment variables: switching model or provider is only configuration."""

import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest

import json

from app.config import Settings, make_client, start_command_log, start_llm_log
from app.llm.client import OllamaClient


def test_defaults_use_the_local_ollama_with_the_small_qwen():
    settings = Settings.from_env({})

    # 127.0.0.1, not localhost: on Windows localhost tries IPv6 first and each connection costs ~2 s
    assert settings == Settings(llm="ollama", ollama_url="http://127.0.0.1:11434", model="qwen2.5:3b")


def test_environment_variables_override_the_defaults():
    settings = Settings.from_env({"LLM": "OFF", "OLLAMA_URL": "http://pc-di-casa:11434", "LLM_MODEL": "llama3.2:3b"})

    assert settings == Settings(llm="off", ollama_url="http://pc-di-casa:11434", model="llama3.2:3b")


def test_an_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="ollama, off"):
        Settings.from_env({"LLM": "gpt"})


def test_ollama_settings_make_an_ollama_client():
    client = make_client(Settings(llm="ollama", ollama_url="http://pc-di-casa:11434/", model="llama3.2:3b"))

    assert isinstance(client, OllamaClient)
    assert client.base_url == "http://pc-di-casa:11434"
    assert client.model == "llama3.2:3b"


def test_llm_off_means_no_client():
    assert make_client(Settings(llm="off")) is None


def test_the_llm_log_goes_to_the_logs_folder_of_the_project_by_default():
    log_file = Path(Settings.from_env({}).llm_log)

    assert log_file == Path(__file__).resolve().parents[1] / "logs" / "llm.log"


@pytest.mark.parametrize(("value", "expected"), [("OFF", "off"), ("C:/temp/llm.log", "C:/temp/llm.log")])
def test_the_llm_log_can_be_moved_or_switched_off(value, expected):
    assert Settings.from_env({"LLM_LOG": value}).llm_log == expected


def test_each_front_end_may_have_its_own_default_log():
    web_log = Path("logs/llm-web.log")

    assert Settings.from_env({}, default_llm_log=web_log).llm_log == str(web_log)
    assert Settings.from_env({"LLM_LOG": "altro.log"}, default_llm_log=web_log).llm_log == "altro.log"


# --- Log of the LLM calls --------------------------------------------------------------------------


@pytest.fixture
def llm_logger():
    logger = logging.getLogger("app.llm")
    handlers, level = list(logger.handlers), logger.level
    yield logger
    for handler in logger.handlers:
        if handler not in handlers:
            handler.close()
            logger.removeHandler(handler)
    logger.setLevel(level)


def test_the_llm_log_is_appended_to_a_file_with_timestamps(tmp_path, llm_logger):
    log_file = tmp_path / "logs" / "llm.log"
    log_file.parent.mkdir()
    log_file.write_text("partita precedente\n", encoding="utf-8")

    start_llm_log(str(log_file))
    logging.getLogger("app.llm.client").info("qwen2.5:3b  5.1 s\n>>> Frase: cala la corda")

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "partita precedente"
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  qwen2\.5:3b  5\.1 s", lines[-2])
    assert lines[-1] == ">>> Frase: cala la corda"


def test_the_logs_folder_is_created_when_missing(tmp_path, llm_logger):
    log_file = tmp_path / "logs" / "llm.log"

    start_llm_log(str(log_file))
    logging.getLogger("app.llm.interpreter").info("=== azione: guarda")

    assert log_file.read_text(encoding="utf-8").endswith("=== azione: guarda\n")


@pytest.mark.parametrize(("value", "expected"), [(None, False), ("0", False), ("1", True), (" 1 ", True)])
def test_the_full_llm_log_is_off_unless_asked_for(value, expected):
    env = {} if value is None else {"LLM_LOG_FULL": value}

    assert Settings.from_env(env).llm_log_full is expected


def test_the_full_llm_log_wants_0_or_1():
    with pytest.raises(ValueError, match="LLM_LOG_FULL"):
        Settings.from_env({"LLM_LOG_FULL": "sì"})


@pytest.mark.parametrize("full", [False, True])
def test_the_full_llm_log_also_writes_the_details(tmp_path, llm_logger, full):
    log_file = tmp_path / "llm.log"

    start_llm_log(str(log_file), full=full)
    logging.getLogger("app.llm.client").debug("richiesta a Ollama: {}")
    logging.getLogger("app.llm.client").info("qwen2.5:3b  5.1 s")

    written = log_file.read_text(encoding="utf-8")
    assert ("richiesta a Ollama" in written) is full
    assert "qwen2.5:3b  5.1 s" in written


def test_no_log_file_when_switched_off(tmp_path, llm_logger):
    start_llm_log("off")
    logging.getLogger("app.llm.client").info("niente")

    assert all(isinstance(handler, logging.NullHandler) for handler in llm_logger.handlers)


def test_without_a_log_file_llm_warnings_stay_out_of_the_terminal():
    # In a separate interpreter: pytest's own logging handlers would hide the problem.
    code = "import logging, app.llm.client; logging.getLogger('app.llm.client').warning('Ollama: errore')"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert result.stderr == ""


# --- Log of the commands that went wrong (JSON lines) ----------------------------------------------


def test_the_command_log_goes_to_the_logs_folder_by_default():
    assert Path(Settings.from_env({}).command_log) == Path(__file__).resolve().parents[1] / "logs" / "comandi.jsonl"


@pytest.mark.parametrize(("value", "expected"), [("off", "off"), ("C:/temp/comandi.jsonl", "C:/temp/comandi.jsonl")])
def test_the_command_log_can_be_moved_or_switched_off(value, expected):
    assert Settings.from_env({"COMMAND_LOG": value}).command_log == expected


@pytest.fixture
def commands_logger():
    logger = logging.getLogger("app.commands")
    handlers, level = list(logger.handlers), logger.level
    yield logger
    for handler in logger.handlers:
        if handler not in handlers:
            handler.close()
            logger.removeHandler(handler)
    logger.setLevel(level)


def test_each_command_is_one_json_line_with_time_and_front_end(tmp_path, commands_logger):
    log_file = tmp_path / "logs" / "comandi.jsonl"
    entry = {"stanza": "cortile", "frase": "nord", "da": "parser", "azione": "vai nord", "esito": "fallita",
             "dettaglio": "La porta della torre è chiusa a chiave."}  # fmt: skip

    start_command_log(str(log_file), origin="web")
    commands_logger.info("fallita: nord", extra={"command": entry})
    commands_logger.info("fallita: nord", extra={"command": entry})

    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", lines[0].pop("ora"))
    assert lines[0] == {"origine": "web", **entry}


def test_no_command_log_when_switched_off(commands_logger):
    start_command_log("off", origin="terminale")

    assert all(isinstance(handler, logging.NullHandler) for handler in commands_logger.handlers)
