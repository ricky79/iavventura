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

from app.engine.engine import GAME_OVER, GIVE_TO_WHOM, NOBODY_HERE, NOT_HERE, Engine
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
from app.engine.parser import (
    Ambiguous,
    ToWhom,
    gesture_said,
    is_named,
    names_said,
    names_the_way,
    parse,
    significant_words,
    topics_named,
    words_of,
    words_saying,
)
from app.engine.text import action_text, confirmation, render, which_one
from app.llm.client import LLMClient
from app.llm.interpreter import JUMP_WORDS, NotUnderstood, describe, interpret

NOT_UNDERSTOOD = "Non ho capito."
NOT_A_GAME_ACTION = "Non sembra un'azione del gioco. Scrivi «aiuto» per qualche esempio."
NOBODY_TO_TALK_TO = "Qui non c'è nessuno con cui parlare."
ALREADY_HERE = "Sei già qui."
ALL_RIGHT = "Va bene."
RESUME_WORD = "riprendi"  # after a death: the game again from the beginning of the last act
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

    @property
    def resumable(self) -> str | None:
        """After a death, the act the game can go on from ("secondo atto"); otherwise None."""
        return self.engine.resumable(self.state)

    def resume(self) -> str:
        """The game again from the beginning of the last act, after a death."""
        self.state, outcome = self.engine.resume(self.state)
        self.pending = None
        return render(outcome, self.world)

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
        if self.finished:
            # Nothing to do and nothing for the LLM to interpret, but going on after a death.
            if words == [RESUME_WORD] and self.resumable is not None:
                return self.resume()
            return GAME_OVER
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
        parsed = parse(line, self.world, near, exits, characters, self.state.last_speaker)
        if isinstance(parsed, Ambiguous):
            return which_one(parsed.candidates)
        if isinstance(parsed, ToWhom):
            return GIVE_TO_WHOM if parsed.people else NOBODY_TO_TALK_TO
        if parsed is not None:
            return self._execute(parsed, "parser")
        if self.llm is None:
            self._log("parser", None, "non capito", "il parser non la capisce e l'LLM è spento")
            return NOT_UNDERSTOOD
        interpreted = interpret(self.llm, line, near, exits, characters, self.world.game.examples, self.state.last_speaker)
        here = {item.id for item in near} | {person.id for person, _ in characters}
        asking = _is_question(line, words)
        if isinstance(interpreted, NotUnderstood):
            asked = _topic_asked(words, characters) if asking else None
            if asked is None and interpreted.guess is not None:
                # What the sentence names in place of the model's pick: asked about, done after a yes.
                self.pending = self._carried_first(interpreted.guess)
                question = confirmation(self.pending, self.world)
                self._log("llm", self.pending, "conferma", question)
                return question
            if asked is None and not interpreted.not_an_action:
                asked = self._gesture_said(words, characters, here)
            if asked is not None:
                answer = f"({action_text(asked, self.world)})\n" + self._execute(asked, "llm")
            else:
                answer = self._not_understood(interpreted, words, here, len(characters))
            # What the game answered instead, if it isn't the usual: the log is for finding sentences to fix.
            detail = interpreted.reason
            if answer not in (NOT_UNDERSTOOD, NOT_A_GAME_ACTION):
                detail += f"; risposta: {answer.splitlines()[0]}"
            self._log("llm", None, "altro" if interpreted.not_an_action else "non capito", detail)
            return answer
        to_whom = self._to_whom(interpreted, words, asking, characters, here)
        if isinstance(to_whom, str):
            self._log("llm", interpreted, "fallita", to_whom)
            return to_whom
        interpreted = to_whom
        if interpreted.verb is Command.GO and not names_the_way(interpreted.direction, words, exits):
            instead = self._place_instead(interpreted.direction, words)
            if instead is not None:
                self._log("llm", interpreted, "fallita", instead)
                return instead
        in_hand = self._using_what_is_in_hand(interpreted, words, near)
        if in_hand is not None or not self._foreseen(interpreted, words, exits) or self._would_kill(interpreted):
            self.pending = self._carried_first(in_hand or interpreted)
            question = confirmation(self.pending, self.world)
            self._log("llm", self.pending, "conferma", question)
            return question
        # Show how the sentence was understood: if the model got it wrong, the player sees why.
        return f"({action_text(interpreted, self.world)})\n" + self._execute(interpreted, "llm")

    def _not_understood(self, result: NotUnderstood, words: list[str], here: set[str], people_here: int) -> str:
        """Why nothing is done: better than "Non ho capito" when the sentence names someone or something
        that isn't here ("ciao orso" at the brook, "mangio una mora" in the glade), or is said to nobody
        by name among several ("grazie" to Corrado and the doctor: «A chi?»)."""
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
        said_to_nobody = not result.not_an_action and gesture_said(words) is not None and people_here > 1
        if result.to_whom or said_to_nobody:
            return GIVE_TO_WHOM
        return NOT_A_GAME_ACTION if result.not_an_action else NOT_UNDERSTOOD

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

    def _to_whom(
        self,
        action: Action,
        words: list[str],
        asking: bool,
        characters: list[tuple[Character, list[Topic]]],
        here: set[str],
    ) -> Action | str:
        """An action on the character here, checked against who the sentence names. A question about
        one of its topics is asked ("conosci l'orso?", "chi sei?": the model said "parla"); otherwise,
        naming only someone elsewhere is "Non vedi nessuno del genere qui." ("ciao orso", or "do le
        more al drago" in the den, where the model gave them to the bear)."""
        person = next((person for person, _ in characters if person.id in (action.target, action.with_)), None)
        if person is None and action.verb is Verb.GIVE:
            # "dai le more" goes to the only one here, or to the one spoken to last
            people = [someone for someone, _ in characters]
            person = people[0] if len(people) == 1 else next((p for p in people if p.id == self.state.last_speaker), None)
        if person is None:
            return action
        topics = next(topics for someone, topics in characters if someone is person)
        if action.verb is Conversation.ASK and action.topic is not None and not topics_named(person, topics, words):
            chosen = next((topic for topic in topics if topic.id == action.topic), None)
            if chosen is not None and self._names_something_else(person, chosen, words):
                # «chiedi a Livia di Corrado»: no topic of hers is named, and the model picked one (Ettore).
                return Action(verb=Conversation.ASK, target=person.id)
        # A question naming a topic is that question, whatever the gesture ("scusate, cosa sapete della
        # contessa?", "come va con Livia?"); otherwise only a greeting may be a question in disguise:
        # "grazie per la storia della torre" stays a thanks.
        if action.verb is Conversation.TALK and asking and (question := _topic_asked(words, [(person, topics)])):
            return question
        greeting = action.verb is Conversation.TALK and action.gesture is None
        someone_elsewhere = not is_named(person, words) and self._names_one_elsewhere(
            self.world.characters.values(), words, here
        )
        if someone_elsewhere and (action.verb is not Conversation.ASK or action.topic is None):
            return NOBODY_HERE
        if greeting and (named := topics_named(person, topics, words)):
            # A greeting naming a topic: "com'è andato il viaggio" is about the journey.
            return Action(verb=Conversation.ASK, target=person.id, topic=named[0].id)
        return action

    def _gesture_said(
        self, words: list[str], characters: list[tuple[Character, list[Topic]]], here: set[str]
    ) -> Action | None:
        """The gesture the sentence says, when the model's answer made no sense ("ti ringrazio tanto,
        draghetto" came back as "dai" with no item): to the one here it names, the only one here or the
        one spoken to last; to nobody if it names only someone who isn't here."""
        gesture = gesture_said(words)
        if gesture is None:
            return None
        named = [person for person, _ in characters if is_named(person, words)]
        if not named and self._names_one_elsewhere(self.world.characters.values(), words, here):
            return None
        people = named or [person for person, _ in characters]
        person = people[0] if len(people) == 1 else next((p for p in people if p.id == self.state.last_speaker), None)
        return None if person is None else Action(verb=Conversation.TALK, target=person.id, gesture=gesture)

    def _names_one_elsewhere(self, things: Iterable[Item | Character], words: list[str], here: set[str]) -> bool:
        """A name said only by words that say something here doesn't count: "corda" is also the grapple,
        "biglietto" is in "biglietto della contessa", and "velluti" (the dressing table's) is nearly the
        drape's "velluto"."""
        names_here = [name for thing_id in here for name in names_said(self.world.thing(thing_id), words)]
        said_here = {word for name in names_here for word in words_saying(name, words)}
        return any(
            thing.id not in here and any(not words_saying(name, words) <= said_here for name in names_said(thing, words))
            for thing in things
        )

    def _names_one_here(self, words: list[str], here: set[str]) -> bool:
        return any(is_named(self.world.thing(thing_id), words) for thing_id in here)

    def _names_something_else(self, person: Character, topic: Topic, words: list[str]) -> bool:
        """Whether the words name another character or an item of the world, by words that are not in
        the names of the topic ("chiave" is also in «chiave dello scalone»)."""
        topic_words = {word for name in (topic.name, *topic.aliases) for word in significant_words(name)}
        others = [character for character in self.world.characters.values() if character.id != person.id]
        return any(
            not set(name) & topic_words
            for thing in [*others, *self.world.items.values()]
            for name in names_said(thing, words)
        )

    def _foreseen(self, action: Action, words: list[str], exits: list[tuple[Direction, Room | None]]) -> bool:
        """Whether the world foresees an interpreted action (Engine.expects). A move must also name
        its way, by direction or by the room it leads to: for a place that isn't among the exits
        ("vado in cantina") the model may pick a door at random. A jump, which may kill, must be
        asked for with a word for jumping ("entro nel pozzo" isn't)."""
        if not self.engine.expects(action):
            return False
        if action.verb is Verb.JUMP and not JUMP_WORDS.intersection(words):
            return False
        return action.direction is None or names_the_way(action.direction, words, exits)

    def _would_kill(self, action: Action) -> bool:
        """Whether an interpreted action would end the game with a death: it is asked about first, since
        the model may have misunderstood («tocco la balaustra» taken for pushing it). Jumps have their own
        rule (_foreseen): asked for with a word for jumping, they are done at once."""
        if action.verb is Verb.JUMP:
            return False
        trial = self.state.model_copy(deep=True)
        self.engine.execute(trial, action)
        return trial.lost

    def _using_what_is_in_hand(self, action: Action, words: list[str], near: list[Item]) -> Action | None:
        """«carico il carillon con la chiavetta»: the model took what the player already holds, while the
        sentence names one other thing here. Using the two together is only a guess, asked about."""
        if action.verb is not Verb.TAKE or action.with_ is not None:
            return None
        if self.state.item_locations.get(action.target) != INVENTORY:
            return None
        others = [item.id for item in near if item.id != action.target and is_named(item, words)]
        return Action(verb=Verb.USE, target=action.target, with_=others[0]) if len(others) == 1 else None

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


def _is_question(line: str, words: list[str]) -> bool:
    """"?" at the end, or a first word like perché, cosa, come: kids leave the "?" out."""
    return line.rstrip().endswith("?") or words[0] in _QUESTION_WORDS


def _topic_asked(words: list[str], characters: list[tuple[Character, list[Topic]]]) -> Action | None:
    """The question about the topic a sentence names ("mi dai il miele?"), if it names a topic of
    exactly one of the characters here."""
    asked = [(person, named[0]) for person, topics in characters if (named := topics_named(person, topics, words))]
    if len(asked) != 1:
        return None
    person, topic = asked[0]
    return Action(verb=Conversation.ASK, target=person.id, topic=topic.id)
