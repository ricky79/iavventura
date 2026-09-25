"""A game session, one turn at a time: what the terminal uses now and the web will use later.

A turn: classic parser -> (if not understood) LLM interpreter -> engine -> fixed text, or the
LLM narrator for the engine's generic replies. Without an LLM the game still works, with
simple commands and fixed text only.
"""

from collections.abc import Iterator

from app.engine.engine import Engine
from app.engine.models import Action, Outcome, World
from app.engine.parser import Ambiguous, parse, words_of
from app.engine.text import action_text, render, which_one
from app.llm.client import LLMClient, LLMError
from app.llm.interpreter import interpret
from app.llm.narrator import narrate

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

    def turn(self, line: str) -> Iterator[str]:
        """The answer to one line typed by the player, piece by piece: the narrator streams."""
        words = words_of(line)
        if not words:
            return
        if len(words) == 1 and words[0] in _HELP_WORDS:
            yield HELP
            return
        in_reach = self.engine.in_reach(self.state)
        result = parse(line, self.world, in_reach)
        if result is None and self.llm is not None:
            result = interpret(self.llm, line, in_reach)
            if result is not None:
                # Show how the sentence was understood: if the model got it wrong, the player sees why.
                yield f"({action_text(result, self.world)})\n"
        if result is None:
            yield NOT_UNDERSTOOD
            return
        if isinstance(result, Ambiguous):
            yield which_one(result.candidates)
            return
        outcome = self.engine.execute(self.state, result)
        if outcome.generic and self.llm is not None:
            yield from self._narrate(result, outcome)
        else:
            yield render(outcome, self.world)

    def _narrate(self, action: Action, outcome: Outcome) -> Iterator[str]:
        """The narrator retells the generic text; the rest of the outcome (an ending) stays fixed."""
        told = False
        try:
            for piece in narrate(self.llm, self.world, self.state, action, outcome):
                yield piece
                told = True
        except LLMError:
            if told:
                yield "\n"
            told = False
        if not told:
            yield outcome.text or ""
        rest = render(outcome.model_copy(update={"text": None}), self.world)
        if rest:
            yield f"\n\n{rest}"
