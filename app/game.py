"""A game session, one turn at a time: what both the terminal and the web use.

A turn: classic parser -> (if not understood) LLM interpreter -> engine -> fixed text.
The LLM only interprets the player's sentence: every answer is fixed text written by the
world's author or by the engine. Without an LLM the game works with simple commands only.

An interpreted action that nothing in the world foresees is asked about first ("Vuoi usare la
corda con gancio con il portone?"): the model may have misunderstood, and the player can say no.
"""

from app.engine.engine import Engine
from app.engine.models import INVENTORY, Action, GameState, Verb, World
from app.engine.parser import Ambiguous, parse, words_of
from app.engine.text import action_text, confirmation, render, which_one
from app.llm.client import LLMClient
from app.llm.interpreter import interpret

NOT_UNDERSTOOD = "Non ho capito."
ALL_RIGHT = "Va bene."
HELP = """Scrivi comandi semplici, per esempio:
  nord, sud, est, ovest, su, giù (oppure n, s, e, o)
  guarda, inventario (oppure i)
  esamina X, prendi X, lascia X, apri X, chiudi X, leggi X, spingi X, tira X
  usa X con Y
Per terminare la partita: fine."""

_HELP_WORDS = frozenset({"aiuto", "help"})
# Answers to "Vuoi…?", by their first word. Not "s" and "n": they are south and north.
_YES_WORDS = frozenset({"si", "certo", "ok", "okay", "sicuro", "confermo"})
_NO_WORDS = frozenset({"no"})


class Game:
    def __init__(
        self,
        engine: Engine,
        llm: LLMClient | None = None,
        state: GameState | None = None,
        pending: Action | None = None,
    ) -> None:
        """A new game, or one that goes on from `state` (the web keeps it in the browser), with the
        action asked about in the last turn, if any, still waiting for an answer."""
        self.engine = engine
        self.llm = llm
        self.pending = pending
        if state is None:
            self.state, self._opening = engine.new_game()
        else:
            self.state, self._opening = state, None

    @property
    def world(self) -> World:
        return self.engine.world

    @property
    def finished(self) -> bool:
        return self.state.finished

    def opening(self) -> str:
        """Intro and first room; only a new game has one."""
        if self._opening is None:
            raise ValueError("a game going on from a saved state has no opening")
        return render(self._opening, self.world)

    def turn(self, line: str) -> str:
        """The answer to one line typed by the player; empty for an empty line."""
        words = words_of(line)
        if not words:
            return ""
        pending, self.pending = self.pending, None
        if pending is not None:
            if words[0] in _YES_WORDS:
                return render(self.engine.execute(self.state, pending), self.world)
            if words[0] in _NO_WORDS:
                return ALL_RIGHT
            # Anything else is a new command: the question is dropped.
        if len(words) == 1 and words[0] in _HELP_WORDS:
            return HELP
        # What the player can name: items in reach, then those only in sight (the key in the well).
        near = self.engine.in_reach(self.state) + self.engine.visible(self.state)
        exits = self.engine.known_exits(self.state)
        result = parse(line, self.world, near, exits)
        shown = ""
        if result is None and self.llm is not None:
            result = interpret(self.llm, line, near, exits)
            if result is not None and not self.engine.expects(result):
                self.pending = self._carried_first(result)
                return confirmation(self.pending, self.world)
            if result is not None:
                # Show how the sentence was understood: if the model got it wrong, the player sees why.
                shown = f"({action_text(result, self.world)})\n"
        if result is None:
            return NOT_UNDERSTOOD
        if isinstance(result, Ambiguous):
            return which_one(result.candidates)
        return shown + render(self.engine.execute(self.state, result), self.world)

    def _carried_first(self, action: Action) -> Action:
        """"usa" with the carried item first, so the question reads "usare la corda con il portone".
        Rules take their two items in either order, so the action stays the same."""
        carried = {item_id for item_id, place in self.state.item_locations.items() if place == INVENTORY}
        if action.verb is Verb.USE and action.with_ in carried and action.target not in carried:
            return Action(verb=action.verb, target=action.with_, with_=action.target)
        return action
