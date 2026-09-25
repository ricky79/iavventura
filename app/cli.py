"""The game in the terminal.

    python -m app.cli

The LLM (Ollama by default, see app/config.py) interprets the sentences the classic parser
doesn't understand; without it the game goes on with simple commands only.
"""

import logging
import sys
from collections.abc import Callable

from app.config import Settings, make_client, start_llm_log
from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.parser import words_of
from app.game import Game

CONFIRM_QUIT = "Vuoi davvero terminare la partita? (s/n)"
GOODBYE = "Alla prossima!"
GO_ON = "Allora continuiamo."

_log = logging.getLogger("app.llm")

_QUIT_WORDS = frozenset({"fine", "esci"})  # "esci" may also mean "leave the room": hence the confirmation
_YES_WORDS = frozenset({"s", "si"})


def run(game: Game, read_line: Callable[[], str], write: Callable[[str], None]) -> None:
    """Plays until the game ends, the player quits, or the input runs out (EOFError)."""
    write(game.opening())
    try:
        while not game.finished:
            line = read_line()
            words = words_of(line)
            if len(words) == 1 and words[0] in _QUIT_WORDS:
                write(CONFIRM_QUIT)
                answer = words_of(read_line())
                if answer and answer[0] in _YES_WORDS:
                    write(GOODBYE)
                    return
                write(GO_ON)
                continue
            answer = game.turn(line)
            if answer:
                write(answer)
    except EOFError:
        return


def main() -> None:
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        sys.exit(str(exc))
    start_llm_log(settings.llm_log)
    llm = make_client(settings)
    if llm is not None and (reason := llm.unavailable_reason()):
        print(f"[{reason} Si gioca con i soli comandi semplici.]\n")
        llm = None
    if llm is None:
        _log.info("--- nuova partita, senza LLM ---")
    else:
        _log.info("--- nuova partita: %s su %s ---", settings.model, settings.ollama_url)
    game = Game(Engine(load_world()), llm)
    try:
        run(game, lambda: input("\n> "), print)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
