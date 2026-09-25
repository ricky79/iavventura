"""The game in the terminal, with the classic parser and fixed text (no LLM yet).

    python -m app.cli
"""

from collections.abc import Callable

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.parser import Ambiguous, parse, words_of
from app.engine.text import render, which_one

NOT_UNDERSTOOD = "Non ho capito."
HELP = """Scrivi comandi semplici, per esempio:
  nord, sud, est, ovest, su, giù (oppure n, s, e, o)
  guarda, inventario (oppure i)
  esamina X, prendi X, lascia X, apri X, chiudi X, leggi X, spingi X, tira X
  usa X con Y
Per terminare la partita: fine."""
CONFIRM_QUIT = "Vuoi davvero terminare la partita? (s/n)"
GOODBYE = "Alla prossima!"
GO_ON = "Allora continuiamo."

_HELP_WORDS = frozenset({"aiuto", "help"})
_QUIT_WORDS = frozenset({"fine", "esci"})  # "esci" may also mean "leave the room": hence the confirmation
_YES_WORDS = frozenset({"s", "si"})


def run(engine: Engine, read_line: Callable[[], str], write: Callable[[str], None]) -> None:
    """Plays one game until it ends, the player quits, or the input runs out (EOFError)."""
    state, opening = engine.new_game()
    write(render(opening, engine.world))
    try:
        while not state.finished:
            line = read_line()
            words = words_of(line)
            if not words:
                continue
            if len(words) == 1 and words[0] in _HELP_WORDS:
                write(HELP)
                continue
            if len(words) == 1 and words[0] in _QUIT_WORDS:
                write(CONFIRM_QUIT)
                answer = words_of(read_line())
                if answer and answer[0] in _YES_WORDS:
                    write(GOODBYE)
                    return
                write(GO_ON)
                continue
            result = parse(line, engine.world, engine.in_reach(state))
            if result is None:
                write(NOT_UNDERSTOOD)
            elif isinstance(result, Ambiguous):
                write(which_one(result.candidates))
            else:
                write(render(engine.execute(state, result), engine.world))
    except EOFError:
        return


def main() -> None:
    try:
        run(Engine(load_world()), lambda: input("\n> "), print)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
