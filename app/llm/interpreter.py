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

from app.engine.models import Action, Character, Command, Conversation, Direction, Item, Room, Topic, Verb
from app.engine.parser import (
    DIRECTIONS,
    GO_WORDS,
    find_topic,
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
            # With "chiedi" the topic; a topic named like an item is offered once.
            "con": {"type": "string", "enum": list(dict.fromkeys([*names, *topics, NOTHING]))},
        },
        "required": ["verbo", "bersaglio", "con"],
    }


class NotUnderstood(NamedTuple):
    """No action came out of the sentence. `reason` says why, for the logs; `not_an_action` is set
    when the model judged that the sentence isn't a game action at all ("altro"), `talking` when the
    player talks to someone and nobody is here."""

    reason: str
    not_an_action: bool = False
    talking: bool = False


def interpret(
    llm: LLMClient,
    sentence: str,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Characters = (),
    examples: str | None = None,
) -> Action | NotUnderstood:
    """The action in the sentence, or why there is none: the model is unavailable, or its answer
    isn't an action on what the player can name.

    `exits` (Engine.known_exits) tell the model where each exit leads, for "torno nella scuderia".
    `characters` are those here, with their topics: the model is told about them only if there are any.
    `examples` are the world's own (`game.examples`), for the system prompt.
    """
    try:
        reply = llm.complete_json(
            interpreter_system(examples),
            interpreter_user(sentence, in_reach, exits, characters),
            interpreter_schema(in_reach, characters),
            max_tokens=MAX_TOKENS,
            temperature=0,
        )
        ids_by_name = {thing.name: thing.id for thing in [*in_reach, *(character for character, _ in characters)]}
        result = _to_action(reply, ids_by_name, characters)
        if isinstance(result, Action):
            result = _checked(result, words_of(sentence), in_reach, exits, characters)
    except LLMError:
        result = NotUnderstood("il modello non ha dato una risposta valida")
    if isinstance(result, NotUnderstood):
        log.info("=== non capito: %s", result.reason)
    else:
        log.info("=== azione: %s", describe(result))
    return result


def _to_action(reply: dict[str, Any], ids_by_name: dict[str, str], characters: Characters) -> Action | NotUnderstood:
    verb, target, tool = (str(reply.get(key, "")) for key in ("verbo", "bersaglio", "con"))
    if verb == NOT_AN_ACTION:
        return NotUnderstood("la frase non è un'azione di gioco", not_an_action=True)
    if verb in _CONVERSATION:
        return _to_conversation(verb, target, tool, characters)
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
    with_ = ids_by_name.get(tool) if tool != target else None
    if verb == Verb.DROP and with_ is not None:
        # "butta il rampino nel pozzo": dropping one thing into another is using them together
        verb = Verb.USE
    return Action(verb=verb, target=ids_by_name[target], with_=with_)


def _to_conversation(verb: str, target: str, tool: str, characters: Characters) -> Action | NotUnderstood:
    """"parla"/"chiedi" to a character here, the only one if the model names none ("salutalo").
    The topic is looked up among those the character knows, also by alias ("chiave di ferro" for the
    key the pilgrim talks about); anything else is a topic it doesn't know."""
    if not characters:
        # "ciao, come stai?" with nobody around
        return NotUnderstood("non c'è nessuno con cui parlare", not_an_action=True, talking=True)
    found = next(((person, topics) for person, topics in characters if person.name == target), None)
    if found is None and target == NOTHING and len(characters) == 1:
        found = characters[0]
    if found is None:
        return NotUnderstood(f"nessun personaggio {target!r} qui")
    character, topics = found
    if verb == Conversation.TALK:
        return Action(verb=Conversation.TALK, target=character.id)
    topic = find_topic(significant_words(tool), topics)
    return Action(verb=Conversation.ASK, target=character.id, topic=topic.id if topic else None)


def _checked(
    action: Action,
    words: list[str],
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]],
    characters: Characters,
) -> Action | NotUnderstood:
    """The action, if the sentence asks for it; a question about a topic the sentence names."""
    if action.verb is Command.GO:
        return _checked_move(action, words, exits)
    if action.verb is Conversation.ASK:
        return _about_the_topic_named(action, words, characters)
    if not isinstance(action.verb, Verb):
        return action
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
            return NotUnderstood(f"la frase non nomina {things[thing_id].name!r}")
    return action


def _checked_move(
    action: Action, words: list[str], exits: Sequence[tuple[Direction, Room | None]]
) -> Action | NotUnderstood:
    """A move needs a verb of motion, a direction or a place named by its own name: not only what is
    there ("mangio una mora" doesn't go to the brambles). Then the way the sentence names wins over the
    model's: its direction ("salgo sul sasso": up), or the only exit it names ("attraverso il ponte")."""
    said = {DIRECTIONS[word] for word in words if len(word) > 1 and word in DIRECTIONS}  # "e" is also "and"
    places = [room for _, room in exits if room is not None and significant_words(room.name) in names_said(room, words)]
    if not (said or places or MOVE_WORDS.intersection(words)):
        return NotUnderstood("la frase non chiede di spostarsi")
    if names_the_way(action.direction, words, exits):
        return action
    if len(said) == 1:
        return Action(verb=Command.GO, direction=said.pop())
    ways = [direction for direction, _ in exits if names_the_way(direction, words, exits)]
    return Action(verb=Command.GO, direction=ways[0]) if len(ways) == 1 else action


def _about_the_topic_named(action: Action, words: list[str], characters: Characters) -> Action:
    """The topic the sentence names, if the model chose another."""
    character, topics = next((person, topics) for person, topics in characters if person.id == action.target)
    named = [topic.id for topic in topics_named(character, topics, words)]
    if not named or action.topic in named:
        return action
    return Action(verb=Conversation.ASK, target=character.id, topic=named[0])


def describe(action: Action) -> str:
    """The action with ids, as the engine receives it: "usa corda_con_gancio con pozzo", "chiedi pellegrino di torre"."""
    words = [
        action.verb,
        action.direction or action.target or "",
        f"con {action.with_}" if action.with_ else "",
        f"di {action.topic}" if action.topic else "",
    ]
    return " ".join(word for word in words if word)
