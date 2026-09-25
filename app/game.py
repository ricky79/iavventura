"""A game session, one turn at a time: what the terminal uses now and the web will use later.

A turn: classic parser -> (if not understood) LLM interpreter -> engine -> fixed text.
The LLM only interprets the player's sentence: every answer is fixed text written by the
world's author or by the engine. Without an LLM the game works with simple commands only.
"""

from app.engine.engine import Engine
from app.engine.models import World
from app.engine.parser import Ambiguous, parse, words_of
from app.engine.text import action_text, render, which_one
from app.llm.client import LLMClient
from app.llm.interpreter import interpret

NOT_UNDERSTOOD = "Non ho capito."
HELP = """Scrivi comandi semplici, per esempio:
  nord, sud, est, ovest, su, giù (oppure n, s, e, o)
  guarda, inventario (oppure i)
  esamina X, prendi X, lascia X, apri X, chiudi X, leggi X, spingi X, tira X
  usa X con Y
Per terminare la partita: fine."""

_HELP_WORDS = frozenset({"aiuto", "help"})


class Game:
    def __init__(self, engine: Engine, llm: LLMClient | None = None) -> None:
        self.engine = engine
        self.llm = llm
        self.state, self._opening = engine.new_game()

    @property
    def world(self) -> World:
        return self.engine.world

    @property
    def finished(self) -> bool:
        return self.state.finished

    def opening(self) -> str:
        return render(self._opening, self.world)

    def turn(self, line: str) -> str:
        """The answer to one line typed by the player; empty for an empty line."""
        words = words_of(line)
        if not words:
            return ""
        if len(words) == 1 and words[0] in _HELP_WORDS:
            return HELP
        in_reach = self.engine.in_reach(self.state)
        result = parse(line, self.world, in_reach)
        shown = ""
        if result is None and self.llm is not None:
            result = interpret(self.llm, line, in_reach)
            if result is not None:
                # Show how the sentence was understood: if the model got it wrong, the player sees why.
                shown = f"({action_text(result, self.world)})\n"
        if result is None:
            return NOT_UNDERSTOOD
        if isinstance(result, Ambiguous):
            return which_one(result.candidates)
        return shown + render(self.engine.execute(self.state, result), self.world)
