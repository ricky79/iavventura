"""The game in the terminal.

    python -m app.cli

The LLM (Ollama by default, see app/config.py) handles the sentences the classic parser
doesn't understand; without it the game goes on with simple commands only.
"""

import sys
from collections.abc import Callable

from app.config import Settings, make_client
from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.parser import words_of
from app.game import Game

CONFIRM_QUIT = "Vuoi davvero terminare la partita? (s/n)"
GOODBYE = "Alla prossima!"
GO_ON = "Allora continuiamo."

_QUIT_WORDS = frozenset({"fine", "esci"})  # "esci" may also mean "leave the room": hence the confirmation
_YES_WORDS = frozenset({"s", "si"})


def run(game: Game, read_line: Callable[[], str], write: Callable[[str], None]) -> None:
    """Plays until the game ends, the player quits, or the input runs out (EOFError).

    `write` receives the text piece by piece, as the narrator streams it: it must not add newlines.
    """
    write(game.opening() + "\n")
    try:
        while not game.finished:
            line = read_line()
            words = words_of(line)
            if len(words) == 1 and words[0] in _QUIT_WORDS:
                write(CONFIRM_QUIT + "\n")
                answer = words_of(read_line())
                if answer and answer[0] in _YES_WORDS:
                    write(GOODBYE + "\n")
                    return
                write(GO_ON + "\n")
                continue
            answered = False
            for piece in game.turn(line):
                write(piece)
                answered = True
            if answered:
                write("\n")
    except EOFError:
        return


def main() -> None:
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        sys.exit(str(exc))
    llm = make_client(settings)
    if llm is not None and (reason := llm.unavailable_reason()):
        print(f"[{reason} Si gioca con i soli comandi semplici.]\n")
        llm = None
    game = Game(Engine(load_world()), llm)
    try:
        run(game, lambda: input("\n> "), lambda text: print(text, end="", flush=True))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
