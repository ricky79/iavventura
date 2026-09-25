"""The game in the terminal: typed commands in, fixed text out."""

import logging
import re
import subprocess
import sys

import pytest

from app.cli import run, start_llm_log
from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import World
from app.game import HELP, Game


def play(*commands: str, world: World | None = None) -> str:
    """Runs a whole session (on the sample castle by default) and returns everything it printed."""
    output: list[str] = []
    lines = iter(commands)

    def read_line() -> str:
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    run(Game(Engine(world or load_world())), read_line, output.append)
    return "\n".join(output)


def test_session_opens_with_the_intro_and_the_first_room():
    output = play()

    assert output.startswith("La bufera ti ha sorpreso sul passo")
    assert "\n\nCortile\nUn cortile lastricato" in output
    assert output.endswith("Uscite: nord, est, ovest.")


def test_a_sentence_the_parser_does_not_know_is_not_understood():
    assert play("balla la tarantella").endswith("Non ho capito.")


def test_empty_lines_are_ignored():
    assert play("", "   ") == play()


def test_items_are_listed_with_their_articles():
    assert "Qui vedi un gancio da macellaio." in play("ovest")


def test_ambiguous_names_get_a_question(world_data):
    world_data["items"]["moneta_antica"] = {
        "name": "moneta antica",
        "gender": "f",
        "aliases": ["moneta"],
        "description": "Una moneta antica.",
        "location": "atrio",
    }

    output = play("esamina la moneta", world=World.model_validate(world_data))

    assert output.endswith("Quale intendi: la moneta o la moneta antica?")


def test_help_lists_the_commands():
    assert play("aiuto").endswith(HELP)


def test_quitting_asks_for_confirmation():
    output = play("fine", "s", "guarda")

    assert "Vuoi davvero terminare la partita? (s/n)" in output
    assert output.count("Cortile") == 1


def test_not_confirming_goes_on_with_the_game():
    output = play("esci", "no", "guarda")

    assert output.count("Cortile") == 2


def test_the_castle_can_be_finished_by_typing_commands():
    output = play(
        "nord",
        "vai a ovest",
        "prendi il gancio",
        "e",
        "usa il gancio nel pozzo",
        "est",
        "raccogli la corda",
        "usa la corda con il gancio",
        "o",
        "usa il rampino sul pozzo",
        "apri la porta di ferro con la chiave",
        "n",
        "guarda",
    )

    assert "La porta della torre è chiusa a chiave." in output
    assert "Il gancio da solo non arriva nemmeno a metà del pozzo." in output
    assert "Ora hai un rampino improvvisato." in output
    assert output.endswith("da lì una scala di pietra scende fino al sentiero. Sei libero.")

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


def test_no_log_file_when_switched_off(tmp_path, llm_logger):
    start_llm_log("off")
    logging.getLogger("app.llm.client").info("niente")

    assert all(isinstance(handler, logging.NullHandler) for handler in llm_logger.handlers)


def test_without_a_log_file_llm_warnings_stay_out_of_the_terminal():
    # In a separate interpreter: pytest's own logging handlers would hide the problem.
    code = "import logging, app.llm.client; logging.getLogger('app.llm.client').warning('Ollama: errore')"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert result.stderr == ""
