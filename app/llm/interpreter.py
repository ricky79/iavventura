"""The LLM interpreter: turns a sentence the classic parser didn't understand into an Action.

The model answers with a JSON object whose values are constrained by a schema built every turn:
known verbs, the names of the items in reach or in sight and of the characters here, the topics
they can be asked about, the directions. The answer is then checked here, and the engine still
validates the action: the model never touches the game state.
"""

import logging
from collections.abc import Sequence
from typing import Any, NamedTuple

from app.engine.models import Action, Character, Command, Conversation, Direction, Item, Room, Topic, Verb
from app.engine.parser import find_topic, significant_words
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import interpreter_system, interpreter_user

log = logging.getLogger(__name__)

NOT_AN_ACTION = "altro"
NOTHING = "nessuno"
MAX_TOKENS = 60  # the JSON answer is short: a low cap stops a model that rambles

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
    when the model judged that the sentence isn't a game action at all ("altro")."""

    reason: str
    not_an_action: bool = False


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
        return NotUnderstood("non c'è nessuno con cui parlare", not_an_action=True)
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


def describe(action: Action) -> str:
    """The action with ids, as the engine receives it: "usa corda_con_gancio con pozzo", "chiedi pellegrino di torre"."""
    words = [
        action.verb,
        action.direction or action.target or "",
        f"con {action.with_}" if action.with_ else "",
        f"di {action.topic}" if action.topic else "",
    ]
    return " ".join(word for word in words if word)
