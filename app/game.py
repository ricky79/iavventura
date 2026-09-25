"""A game session, one turn at a time: what both the terminal and the web use.

A turn: classic parser -> (if not understood) LLM interpreter -> engine -> fixed text.
The LLM only interprets the player's sentence: every answer is fixed text written by the
world's author or by the engine. Without an LLM the game works with simple commands only.

An interpreted action that nothing in the world foresees is asked about first ("Vuoi usare la
corda con gancio con il portone?"): the model may have misunderstood, and the player can say no.

The commands that went wrong (not understood, not a game action, refused, asked about) go to the
logger "app.commands", which the front ends write to logs/comandi.jsonl (app/config.py).
"""

import logging

from app.engine.engine import Engine
from app.engine.models import INVENTORY, Action, Direction, GameState, Room, Verb, World
from app.engine.parser import DIRECTIONS, Ambiguous, parse, significant_words, words_of
from app.engine.text import action_text, confirmation, render, which_one
from app.llm.client import LLMClient
from app.llm.interpreter import NotUnderstood, describe, interpret

NOT_UNDERSTOOD = "Non ho capito."
NOT_A_GAME_ACTION = "Non sembra un'azione del gioco. Scrivi «aiuto» per qualche esempio."
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

_commands = logging.getLogger("app.commands")
_commands.addHandler(logging.NullHandler())  # silent unless a front end writes the log


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
        self._line = self._room = ""

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
        self._line, self._room = line, self.state.current_room
        pending, self.pending = self.pending, None
        if pending is not None:
            if words[0] in _YES_WORDS:
                return self._execute(pending, "llm")
            if words[0] in _NO_WORDS:
                return ALL_RIGHT
            # Anything else is a new command: the question is dropped.
        if len(words) == 1 and words[0] in _HELP_WORDS:
            return HELP
        # What the player can name: items in reach, then those only in sight (the key in the well).
        near = self.engine.in_reach(self.state) + self.engine.visible(self.state)
        exits = self.engine.known_exits(self.state)
        parsed = parse(line, self.world, near, exits)
        if isinstance(parsed, Ambiguous):
            return which_one(parsed.candidates)
        if parsed is not None:
            return self._execute(parsed, "parser")
        if self.llm is None:
            self._log("parser", None, "non capito", "il parser non la capisce e l'LLM è spento")
            return NOT_UNDERSTOOD
        interpreted = interpret(self.llm, line, near, exits)
        if isinstance(interpreted, NotUnderstood):
            if interpreted.not_an_action:
                self._log("llm", None, "altro", interpreted.reason)
                return NOT_A_GAME_ACTION
            self._log("llm", None, "non capito", interpreted.reason)
            return NOT_UNDERSTOOD
        if not self._foreseen(interpreted, words, exits):
            self.pending = self._carried_first(interpreted)
            question = confirmation(self.pending, self.world)
            self._log("llm", self.pending, "conferma", question)
            return question
        # Show how the sentence was understood: if the model got it wrong, the player sees why.
        return f"({action_text(interpreted, self.world)})\n" + self._execute(interpreted, "llm")

    def _foreseen(self, action: Action, words: list[str], exits: list[tuple[Direction, Room | None]]) -> bool:
        """Whether the world foresees an interpreted action (Engine.expects). A move must also name
        its way, by direction or by the room it leads to: for a place that isn't among the exits
        ("vado in cantina") the model may pick a door at random."""
        if not self.engine.expects(action):
            return False
        if action.direction is None or any(DIRECTIONS.get(word) == action.direction for word in words):
            return True
        room = dict(exits).get(action.direction)
        return room is not None and set(significant_words(room.name)) <= set(words)

    def _execute(self, action: Action, source: str) -> str:
        outcome = self.engine.execute(self.state, action)
        if not outcome.ok:
            self._log(source, action, "fallita", outcome.text)
        return render(outcome, self.world)

    def _log(self, source: str, action: Action | None, result: str, detail: str | None) -> None:
        """A command that went wrong: where, what was typed, how it was understood, what came of it."""
        entry = {
            "stanza": self._room,
            "frase": self._line,
            "da": source,
            "azione": describe(action) if action is not None else None,
            "esito": result,
            "dettaglio": detail,
        }
        _commands.info("%s: %s", result, self._line, extra={"command": entry})

    def _carried_first(self, action: Action) -> Action:
        """"usa" with the carried item first, so the question reads "usare la corda con il portone".
        Rules take their two items in either order, so the action stays the same."""
        carried = {item_id for item_id, place in self.state.item_locations.items() if place == INVENTORY}
        if action.verb is Verb.USE and action.with_ in carried and action.target not in carried:
            return Action(verb=action.verb, target=action.with_, with_=action.target)
        return action
