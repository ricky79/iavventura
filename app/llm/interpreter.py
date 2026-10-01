"""The LLM interpreter: turns a sentence the classic parser didn't understand into an Action.

The model answers with a JSON object whose values are constrained by a schema built every turn:
known verbs, the names of the items in reach or in sight and of the characters here, the topics
they can be asked about, the directions. The answer is then checked here, and the engine still
validates the action: the model never touches the game state.

The model has to pick from lists, and with nothing fitting it picks anything ("mangio una mora"
became "prendi il sasso"). So an item it chose must be named in the sentence, a move must be asked
for, and a topic the sentence names wins over the one it chose.
"""

import logging
from collections.abc import Sequence
from typing import Any, NamedTuple

from app.engine.models import (
    GESTURE_LABELS,
    Action,
    Character,
    Command,
    Conversation,
    Direction,
    Gesture,
    Item,
    Room,
    Topic,
    Verb,
)
from app.engine.parser import (
    DIRECTIONS,
    GO_WORDS,
    ITEM_VERBS,
    find_topic,
    gesture_said,
    is_named,
    names_said,
    names_the_way,
    significant_words,
    topics_named,
    words_of,
)
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import interpreter_system, interpreter_user

log = logging.getLogger(__name__)

NOT_AN_ACTION = "altro"
NOTHING = "nessuno"
MAX_TOKENS = 60  # the JSON answer is short: a low cap stops a model that rambles

# Words that ask for a move even without a direction or a place: "torno indietro", "scappa". Those
# of the parser, and more; "salgo", "scendo" are directions (DIRECTIONS).
MOVE_WORDS = GO_WORDS | frozenset(
    """
    andare andiamo tornare entrare esci esco uscire salire scendere corri corro scappa scappo raggiungi
    raggiungo cammino attraversa attraverso arrampica arrampico arrampicarmi avvicinati spostati sposto
    """.split()
)

# Words that ask for a jump: without one, the game asks before an interpreted jump, which may kill
# ("entro nel pozzo"). Those of the parser, and more.
JUMP_WORDS = frozenset(word for word, verb in ITEM_VERBS.items() if verb is Verb.JUMP) | frozenset(
    """
    saltare saltarci saltiamo tuffo tuffarmi tuffarsi tuffarti tuffiamoci butto buttarmi buttarsi buttarti
    buttiamoci getto gettarmi gettarsi lancio lanciarmi lanciarsi
    """.split()
)
# "lancio uno sguardo verso la valle", "getto un'occhiata nel pozzo": with a jump word, a look.
_GLANCE_WORDS = frozenset({"sguardo", "sguardi", "occhiata", "occhiate", "occhiatina", "occhio", "occhi"})

_VERBS = [verb.value for verb in Verb]
_CONVERSATION = [verb.value for verb in Conversation]
_COMMANDS = [Command.GO.value, Command.LOOK.value, Command.INVENTORY.value]
_DIRECTIONS = [direction.value for direction in Direction]

# The characters here, each with the topics the player can ask about (Engine.characters_here).
Characters = Sequence[tuple[Character, Sequence[Topic]]]


def interpreter_schema(in_reach: Sequence[Item], characters: Characters = ()) -> dict[str, Any]:
    names = [item.name for item in in_reach] + [character.name for character, _ in characters]
    topics = [topic.name for _, known in characters for topic in known]
    return {
        "type": "object",
        "properties": {
            "verbo": {"type": "string", "enum": [*_VERBS, *_CONVERSATION, *_COMMANDS, NOT_AN_ACTION]},
            "bersaglio": {"type": "string", "enum": [*names, *_DIRECTIONS, NOTHING]},
            # With "chiedi" the topic, with "parla" the gesture; a topic named like an item is offered once.
            "con": {
                "type": "string",
                "enum": list(dict.fromkeys([*names, *topics, *(GESTURE_LABELS if characters else ()), NOTHING])),
            },
        },
        "required": ["verbo", "bersaglio", "con"],
    }


class NotUnderstood(NamedTuple):
    """No action came out of the sentence. `reason` says why, for the logs; `not_an_action` is set
    when the model judged that the sentence isn't a game action at all ("altro"), `talking` when the
    player talks to someone and nobody is here. `guess` is what the sentence names in place of the
    model's pick: the game asks about it, and does it only after a yes. `to_whom` when several are here
    and the model names none of them: the game asks «A chi?»."""

    reason: str
    not_an_action: bool = False
    talking: bool = False
    guess: Action | None = None
    to_whom: bool = False


def interpret(
    llm: LLMClient,
    sentence: str,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Characters = (),
    examples: str | None = None,
    last_speaker: str | None = None,
) -> Action | NotUnderstood:
    """The action in the sentence, or why there is none: the model is unavailable, or its answer
    isn't an action on what the player can name.

    `exits` (Engine.known_exits) tell the model where each exit leads, for "torno nella scuderia".
    `characters` are those here, with their topics: the model is told about them only if there are any.
    `examples` are the world's own (`game.examples`), for the system prompt.
    `last_speaker` is who the model means by nobody, when several are here.
    """
    try:
        reply = llm.complete_json(
            interpreter_system(examples),
            interpreter_user(sentence, in_reach, exits, characters),
            interpreter_schema(in_reach, characters),
            max_tokens=MAX_TOKENS,
            temperature=0,
        )
        ids_by_name = _ids_by_name([*in_reach, *(character for character, _ in characters)])
        reply = _examining_not_inventory(reply, in_reach, words_of(sentence))
        result = _to_action(reply, ids_by_name, characters, last_speaker)
        if isinstance(result, Action):
            result = _checked(result, words_of(sentence), in_reach, exits, characters)
    except LLMError:
        result = NotUnderstood("il modello non ha dato una risposta valida")
    if isinstance(result, NotUnderstood):
        log.info("=== non capito: %s", result.reason)
    else:
        log.info("=== azione: %s", describe(result))
    return result


def _examining_not_inventory(reply: dict[str, Any], in_reach: Sequence[Item], words: list[str]) -> dict[str, Any]:
    """"frugo nella borsa del dottore": the model answered "inventario", with an item the sentence
    names as its target. The inventory has no target: that is looking at the item."""
    target = str(reply.get("bersaglio", ""))
    if reply.get("verbo") == Command.INVENTORY and any(item.name == target and is_named(item, words) for item in in_reach):
        return {**reply, "verbo": Verb.EXAMINE.value}
    return reply


def _ids_by_name(things: Sequence[Item | Character]) -> dict[str, str]:
    """Names, and the other names only one of the things has: the model sometimes answers with an
    alias ("grappa" for "bottiglia di grappa"), though the schema lists the names."""
    ids = {thing.name: thing.id for thing in things}
    owners: dict[str, set[str]] = {}
    for thing in things:
        for alias in thing.aliases:
            owners.setdefault(alias, set()).add(thing.id)
    for alias, owner in owners.items():
        if alias not in ids and len(owner) == 1:
            ids[alias] = next(iter(owner))
    return ids


def _to_action(
    reply: dict[str, Any], ids_by_name: dict[str, str], characters: Characters, last_speaker: str | None
) -> Action | NotUnderstood:
    verb, target, tool = (str(reply.get(key, "")) for key in ("verbo", "bersaglio", "con"))
    if verb == NOT_AN_ACTION:
        return NotUnderstood("la frase non è un'azione di gioco", not_an_action=True)
    if verb in _CONVERSATION:
        return _to_conversation(verb, target, tool, characters, last_speaker)
    if verb == Command.GO:
        if target not in _DIRECTIONS:
            return NotUnderstood(f"direzione non valida {target!r}")
        return Action(verb=Command.GO, direction=target)
    if verb == Command.INVENTORY:
        return Action(verb=Command.INVENTORY)
    if verb == Command.LOOK:
        # "guarda nel pozzo" is examining the well
        if target in ids_by_name:
            return Action(verb=Verb.EXAMINE, target=ids_by_name[target])
        return Action(verb=Command.LOOK)
    if verb not in _VERBS:
        return NotUnderstood(f"verbo sconosciuto {verb!r}")
    if target not in ids_by_name:
        return NotUnderstood(f"bersaglio non a portata {target!r}")
    with_ = ids_by_name.get(tool)
    if with_ == ids_by_name[target]:
        with_ = None  # the same item twice, by its name and by an alias ("bastone dal manico ricurvo", "bastone")
    if verb in (Verb.DROP, Verb.JUMP) and with_ is not None:
        # "butta il rampino nel pozzo": dropping one thing into another, or jumping with it, is using
        # them together
        verb = Verb.USE
    return Action(verb=verb, target=ids_by_name[target], with_=with_)


def _to_conversation(
    verb: str, target: str, tool: str, characters: Characters, last_speaker: str | None
) -> Action | NotUnderstood:
    """"parla"/"chiedi" to a character here; without a name, the only one here or the one spoken to last
    ("salutalo"). With a gesture, it is said to them. The topic is looked up among those the character
    knows, also by alias ("chiave di ferro" for the key the pilgrim talks about); anything else is a
    topic it doesn't know."""
    if not characters:
        # "ciao, come stai?" with nobody around
        return NotUnderstood("non c'è nessuno con cui parlare", not_an_action=True, talking=True)
    found = next(((person, topics) for person, topics in characters if person.name == target), None)
    if found is None and target == NOTHING:
        found = characters[0] if len(characters) == 1 else next(
            ((person, topics) for person, topics in characters if person.id == last_speaker), None
        )
        if found is None:
            return NotUnderstood("più personaggi e nessuno nominato", to_whom=True)
    if found is None:
        return NotUnderstood(f"nessun personaggio {target!r} qui")
    character, topics = found
    if verb == Conversation.TALK or tool in GESTURE_LABELS:
        # "chiedi" with a gesture ("come stai") is saying it: no topic is named like a gesture.
        return Action(verb=Conversation.TALK, target=character.id, gesture=GESTURE_LABELS.get(tool))
    topic = find_topic(significant_words(tool), topics)
    return Action(verb=Conversation.ASK, target=character.id, topic=topic.id if topic else None)


def _checked(
    action: Action,
    words: list[str],
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]],
    characters: Characters,
) -> Action | NotUnderstood:
    """The action, if the sentence asks for it; a question about a topic the sentence names, the
    gesture it says."""
    if action.verb is Command.GO:
        return _checked_move(action, words, exits)
    if action.verb is Conversation.ASK:
        action = _about_the_topic_named(action, words, characters)
        if action.topic is None and (said := gesture_said(words)) is not None:
            # «gli chiedo il suo nome», «gli chiedo scusa»: no topic, a gesture.
            return Action(verb=Conversation.TALK, target=action.target, gesture=said)
        return action
    if action.verb is Conversation.TALK and (said := gesture_said(words)) is not None:
        # "perdonatemi se vi disturbo": the model said "saluto", as for almost any gesture.
        return Action(verb=Conversation.TALK, target=action.target, gesture=said)
    if not isinstance(action.verb, Verb):
        return action
    if action.verb is Verb.JUMP and _GLANCE_WORDS.intersection(words):
        action = Action(verb=Verb.EXAMINE, target=action.target)
    if action.verb is Verb.JUMP:
        if action.target in {character.id for character, _ in characters}:
            return NotUnderstood("'salta' su un personaggio")
        said = _directions_said(words)
        if said and not JUMP_WORDS.intersection(words):
            # "salgo sul sasso": the model heard a jump in "salgo", and climbing is a move
            return _checked_move(Action(verb=Command.GO, direction=min(said)), words, exits)
        # Jumping may kill: with another item named ("lancio il rampino nel pozzo") it's throwing that.
        thrown = next((item.id for item in in_reach if item.id != action.target and is_named(item, words)), None)
        if thrown is not None:
            action = Action(verb=Verb.USE, target=action.target, with_=thrown)
    action = _read_what_is_named(action, words, in_reach)
    things = {thing.id: thing for thing in [*in_reach, *(character for character, _ in characters)]}
    ids = [thing_id for thing_id in (action.target, action.with_) if thing_id is not None]
    if action.verb in (Verb.GIVE, Verb.USE):
        # "gli do il miele", "ti faccio il solletico con la piuma": the character needs no name.
        people = {character.id for character, _ in characters}
        ids = [thing_id for thing_id in ids if thing_id not in people]
        if not ids:
            return NotUnderstood(f"'{action.verb}' senza un oggetto")
    for thing_id in ids:
        if not is_named(things[thing_id], words):
            guess = _guess(action, thing_id, words, in_reach)
            return NotUnderstood(f"la frase non nomina {things[thing_id].name!r}", guess=guess)
    return action


def _read_what_is_named(action: Action, words: list[str], in_reach: Sequence[Item]) -> Action:
    """Reading and examining have no tool: when the model picked the wrong item and put the one the
    sentence names as the tool ("leggo il biglietto della contessa"), that one is what is read."""
    if action.verb not in (Verb.READ, Verb.EXAMINE) or action.with_ is None:
        return action
    items = {item.id: item for item in in_reach}
    target = action.target
    if target in items and not is_named(items[target], words) and action.with_ in items and is_named(items[action.with_], words):
        target = action.with_
    return Action(verb=action.verb, target=target)


def _guess(action: Action, unnamed: str, words: list[str], in_reach: Sequence[Item]) -> Action | None:
    """For a tool the sentence doesn't name, the only other item it names ("infilo il medaglione
    nell'incavo"): the model picks anything when nothing fits. Only a guess, which the game asks about:
    a question names things too («cosa c'è scritto sul biglietto, Livia?»)."""
    if unnamed != action.with_:
        return None
    others = {item.id for item in in_reach if is_named(item, words)} - {action.target}
    return Action(verb=action.verb, target=action.target, with_=others.pop()) if len(others) == 1 else None


def _checked_move(
    action: Action, words: list[str], exits: Sequence[tuple[Direction, Room | None]]
) -> Action | NotUnderstood:
    """A move needs a verb of motion, a direction or a place named by its own name: not only what is
    there ("mangio una mora" doesn't go to the brambles). Then the way the sentence names wins over the
    model's: its direction ("salgo sul sasso": up), or the only exit it names ("attraverso il ponte")."""
    said = _directions_said(words)
    places = [room for _, room in exits if room is not None and significant_words(room.name) in names_said(room, words)]
    if not (said or places) and gesture_said(words) is Gesture.FAREWELL:
        # "adesso vado, ci vediamo più tardi": leaving the conversation, not the room
        return NotUnderstood("la frase si congeda, non chiede di spostarsi")
    if not (said or places or MOVE_WORDS.intersection(words)):
        return NotUnderstood("la frase non chiede di spostarsi")
    if names_the_way(action.direction, words, exits):
        return action
    if len(said) == 1:
        return Action(verb=Command.GO, direction=said.pop())
    ways = [direction for direction, _ in exits if names_the_way(direction, words, exits)]
    return Action(verb=Command.GO, direction=ways[0]) if len(ways) == 1 else action


def _directions_said(words: list[str]) -> set[Direction]:
    """The directions the words say, also by a verb ("salgo": up); not by a single letter, since "e"
    is also "and"."""
    return {DIRECTIONS[word] for word in words if len(word) > 1 and word in DIRECTIONS}


def _about_the_topic_named(action: Action, words: list[str], characters: Characters) -> Action:
    """The topic the sentence names, if the model chose another."""
    character, topics = next((person, topics) for person, topics in characters if person.id == action.target)
    named = [topic.id for topic in topics_named(character, topics, words)]
    if not named or action.topic in named:
        return action
    return Action(verb=Conversation.ASK, target=character.id, topic=named[0])


def describe(action: Action) -> str:
    """The action with ids, as the engine receives it: "usa corda_con_gancio con pozzo", "chiedi pellegrino
    di torre", "parla livia: grazie"."""
    words = [
        action.verb,
        action.direction or action.target or "",
        f"con {action.with_}" if action.with_ else "",
        f"di {action.topic}" if action.topic else "",
    ]
    described = " ".join(word for word in words if word)
    return f"{described}: {action.gesture}" if action.gesture else described
