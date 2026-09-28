"""The game in the terminal.

    python -m app.cli

First the menu of the adventures (data/worlds/avventure.yaml), then the game; when it ends, won or
lost, the player may play again.
The LLM (Ollama by default, see app/config.py) interprets the sentences the classic parser
doesn't understand; without it the game goes on with simple commands only.
"""

import logging
import sys
from collections.abc import Callable, Mapping

from app.config import Settings, make_client, start_command_log, start_llm_log
from app.engine.engine import Engine
from app.engine.loader import load_adventures
from app.engine.models import World
from app.engine.parser import words_of
from app.game import Game

CONFIRM_QUIT = "Vuoi davvero terminare la partita? (s/n)"
GOODBYE = "Alla prossima!"
GO_ON = "Allora continuiamo."
PLAY_AGAIN = "\nVuoi giocare ancora? (s/n)"  # a blank line after the ending
CHOOSE = "Scegli la tua avventura:"
WHICH_ADVENTURE = "Scrivi il numero dell'avventura."

_log = logging.getLogger("app.llm")

_QUIT_WORDS = frozenset({"fine", "esci"})  # "esci" may also mean "leave the room": hence the confirmation
_YES_WORDS = frozenset({"s", "si"})


def menu(worlds: Mapping[str, World]) -> str:
    """The adventures numbered as on the page: the title, and the summary indented below it."""
    entries = [
        f" {number}. {world.game.title}\n    {world.game.summary}" for number, world in enumerate(worlds.values(), start=1)
    ]
    return "\n\n".join([CHOOSE, *entries])


def pick(worlds: Mapping[str, World], line: str) -> str | None:
    """The adventure chosen by its number, or by a word of its title of at least three letters
    ("rocca"); None when the answer fits no adventure, or more than one. The page does the same."""
    words = words_of(line)
    ids = list(worlds)
    if len(words) == 1 and words[0].isdigit():
        number = int(words[0])
        return ids[number - 1] if 1 <= number <= len(ids) else None
    matching = {
        adventure_id
        for adventure_id, world in worlds.items()
        for word in words
        if len(word) >= 3 and word in words_of(world.game.title)
    }
    return matching.pop() if len(matching) == 1 else None


def choose(worlds: Mapping[str, World], read_line: Callable[[], str], write: Callable[[str], None]) -> str:
    """Shows the menu and asks until the answer is an adventure (EOFError if the input runs out)."""
    write(menu(worlds))
    while (adventure_id := pick(worlds, read_line())) is None:
        write(WHICH_ADVENTURE)
    return adventure_id


def session(
    worlds: Mapping[str, World],
    new_game: Callable[[str], Game],
    read_line: Callable[[], str],
    write: Callable[[str], None],
) -> None:
    """Menu and game, again and again: a game that ends (won or lost) asks whether to play another.
    Quitting, or the input running out, ends the session."""
    try:
        while True:
            game = new_game(choose(worlds, read_line, write))
            run(game, read_line, write)
            if not game.finished:
                return
            write(PLAY_AGAIN)
            answer = words_of(read_line())
            if not (answer and answer[0] in _YES_WORDS):
                write(GOODBYE)
                return
    except EOFError:
        return


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
    start_command_log(settings.command_log, origin="terminale")
    llm = make_client(settings)
    if llm is not None and (reason := llm.unavailable_reason()):
        print(f"[{reason} Si gioca con i soli comandi semplici.]\n")
        llm = None
    worlds = load_adventures()

    def new_game(adventure_id: str) -> Game:
        if llm is None:
            _log.info("--- nuova partita (%s), senza LLM ---", adventure_id)
        else:
            _log.info("--- nuova partita (%s): %s su %s ---", adventure_id, settings.model, settings.ollama_url)
        return Game(Engine(worlds[adventure_id]), llm, adventure=adventure_id)

    try:
        session(worlds, new_game, lambda: input("\n> "), print)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
