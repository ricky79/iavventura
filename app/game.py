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
from collections.abc import Iterable

from app.engine.engine import NOBODY_HERE, NOT_HERE, Engine
from app.engine.models import (
    INVENTORY,
    Action,
    Character,
    Command,
    Conversation,
    Direction,
    GameState,
    Item,
    Room,
    Topic,
    Verb,
    World,
)
from app.engine.parser import Ambiguous, is_named, names_said, names_the_way, parse, topics_named, words_of
from app.engine.text import action_text, confirmation, render, which_one
from app.llm.client import LLMClient
from app.llm.interpreter import NotUnderstood, describe, interpret

NOT_UNDERSTOOD = "Non ho capito."
NOT_A_GAME_ACTION = "Non sembra un'azione del gioco. Scrivi «aiuto» per qualche esempio."
NOBODY_TO_TALK_TO = "Qui non c'è nessuno con cui parlare."
ALREADY_HERE = "Sei già qui."
ALL_RIGHT = "Va bene."
HELP = """Scrivi comandi semplici, per esempio:
  nord, sud, est, ovest, su, giù (oppure n, s, e, o)
  guarda, inventario (oppure i)
  esamina X, prendi X, lascia X, apri X, chiudi X, leggi X, spingi X, tira X
  usa X con Y
  parla con X, chiedi a X di Y, dai X a Y
Per terminare la partita: fine."""

_HELP_WORDS = frozenset({"aiuto", "help"})
# A sentence starting with one of these is a question, even without "?" (kids leave it out).
_QUESTION_WORDS = frozenset({"perche", "cosa", "come", "chi", "dove", "quanto", "quanti", "quale", "quali", "quando"})
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
        adventure: str | None = None,
    ) -> None:
        """A new game, or one that goes on from `state` (the web keeps it in the browser), with the
        action asked about in the last turn, if any, still waiting for an answer.
        `adventure` is the id of the world, for the log."""
        self.engine = engine
        self.llm = llm
        self.pending = pending
        self.adventure = adventure
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
        # What the player can name: items in reach, then those only in sight (the key in the well),
        # and the characters here with the topics they can be asked about.
        near = self.engine.in_reach(self.state) + self.engine.visible(self.state)
        exits = self.engine.known_exits(self.state)
        characters = self.engine.characters_here(self.state)
        parsed = parse(line, self.world, near, exits, characters)
        if isinstance(parsed, Ambiguous):
            return which_one(parsed.candidates)
        if parsed is not None:
            return self._execute(parsed, "parser")
        if self.llm is None:
            self._log("parser", None, "non capito", "il parser non la capisce e l'LLM è spento")
            return NOT_UNDERSTOOD
        interpreted = interpret(self.llm, line, near, exits, characters, self.world.game.examples)
        here = {item.id for item in near} | {person.id for person, _ in characters}
        if isinstance(interpreted, NotUnderstood):
            self._log("llm", None, "altro" if interpreted.not_an_action else "non capito", interpreted.reason)
            asked = self._question_about_a_topic(words, characters)
            if asked is not None:
                return f"({action_text(asked, self.world)})\n" + self._execute(asked, "llm")
            return self._not_understood(interpreted, words, here)
        if interpreted.verb is Conversation.TALK:
            if self._greets_someone_else(interpreted.target, words, here):
                # "ciao orso" with only the dragon here: the model greets the dragon.
                self._log("llm", interpreted, "fallita", NOBODY_HERE)
                return NOBODY_HERE
            # "chi sei?": the model answered "parla", the pilgrim has a topic about himself.
            character = [(person, topics) for person, topics in characters if person.id == interpreted.target]
            interpreted = self._question_about_a_topic(words, character) or interpreted
        if interpreted.verb is Command.GO and not names_the_way(interpreted.direction, words, exits):
            instead = self._place_instead(interpreted.direction, words)
            if instead is not None:
                self._log("llm", interpreted, "fallita", instead)
                return instead
        if not self._foreseen(interpreted, words, exits):
            self.pending = self._carried_first(interpreted)
            question = confirmation(self.pending, self.world)
            self._log("llm", self.pending, "conferma", question)
            return question
        # Show how the sentence was understood: if the model got it wrong, the player sees why.
        return f"({action_text(interpreted, self.world)})\n" + self._execute(interpreted, "llm")

    def _not_understood(self, result: NotUnderstood, words: list[str], here: set[str]) -> str:
        """Why nothing is done: better than "Non ho capito" when the sentence names someone or something
        that isn't here ("ciao orso" at the brook, "mangio una mora" in the glade)."""
        someone_elsewhere = self._names_one_elsewhere(self.world.characters.values(), words, here)
        if result.talking and someone_elsewhere:
            return NOBODY_HERE
        if self._names_one_elsewhere(self.world.items.values(), words, here):
            return NOT_HERE
        if result.talking:
            return NOBODY_TO_TALK_TO
        # Not for a word that is also an adjective ("il vecchio pozzo"): only if nothing here is named.
        if someone_elsewhere and not self._names_one_here(words, here):
            return NOBODY_HERE
        return NOT_A_GAME_ACTION if result.not_an_action else NOT_UNDERSTOOD

    def _question_about_a_topic(
        self, words: list[str], characters: list[tuple[Character, list[Topic]]]
    ) -> Action | None:
        """A question ("mi dai il miele?", "perche hai il naso rosso") that names a topic of the one here:
        it is asked. Only a question: "mangio una mora" is no question about the berries."""
        if not self._line.rstrip().endswith("?") and words[0] not in _QUESTION_WORDS:
            return None
        asked = [(person, named[0]) for person, topics in characters if (named := topics_named(person, topics, words))]
        if len(asked) != 1:
            return None
        person, topic = asked[0]
        return Action(verb=Conversation.ASK, target=person.id, topic=topic.id)

    def _place_instead(self, direction: Direction, words: list[str]) -> str | None:
        """For a move the sentence doesn't name the way of: it names where the player already is
        ("torno dal draghetto" in the glade), or a place farther on that the direction doesn't lead
        to ("vai a casa" at the oak, and the model says up). Toward it, the move is asked about as
        usual ("vai dall'orso" in the glade: west, past the brook)."""
        room = self.world.rooms[self.state.current_room]
        if is_named(room, words):
            return ALREADY_HERE
        nearby = {room.id} | {exit_.to for exit_ in room.exits.values()}
        farther = [place.id for place in self.world.rooms.values() if place.id not in nearby and is_named(place, words)]
        if any(self._first_step_to(place_id) != direction for place_id in farther):
            return NOT_UNDERSTOOD
        return None

    def _first_step_to(self, room_id: str) -> Direction | None:
        """The first exit on a shortest way from the current room to another (closed exits too)."""
        start = self.state.current_room
        first: dict[str, Direction | None] = {start: None}
        queue = [start]
        for current in queue:
            for direction, exit_ in self.world.rooms[current].exits.items():
                if exit_.to not in first:
                    first[exit_.to] = direction if current == start else first[current]
                    queue.append(exit_.to)
        return first.get(room_id)

    def _greets_someone_else(self, character_id: str, words: list[str], here: set[str]) -> bool:
        return not is_named(self.world.characters[character_id], words) and self._names_one_elsewhere(
            self.world.characters.values(), words, here
        )

    def _names_one_elsewhere(self, things: Iterable[Item | Character], words: list[str], here: set[str]) -> bool:
        """A name shared with something here doesn't count: "corda" is also the grapple."""
        said_here = {name for thing_id in here for name in names_said(self.world.thing(thing_id), words)}
        return any(thing.id not in here and set(names_said(thing, words)) - said_here for thing in things)

    def _names_one_here(self, words: list[str], here: set[str]) -> bool:
        return any(is_named(self.world.thing(thing_id), words) for thing_id in here)

    def _foreseen(self, action: Action, words: list[str], exits: list[tuple[Direction, Room | None]]) -> bool:
        """Whether the world foresees an interpreted action (Engine.expects). A move must also name
        its way, by direction or by the room it leads to: for a place that isn't among the exits
        ("vado in cantina") the model may pick a door at random."""
        if not self.engine.expects(action):
            return False
        return action.direction is None or names_the_way(action.direction, words, exits)

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
        if self.adventure is not None:
            entry = {"avventura": self.adventure, **entry}
        _commands.info("%s: %s", result, self._line, extra={"command": entry})

    def _carried_first(self, action: Action) -> Action:
        """"usa" with the carried item first, so the question reads "usare la corda con il portone".
        Rules take their two items in either order, so the action stays the same."""
        carried = {item_id for item_id, place in self.state.item_locations.items() if place == INVENTORY}
        if action.verb is Verb.USE and action.with_ in carried and action.target not in carried:
            return Action(verb=action.verb, target=action.with_, with_=action.target)
        return action
