"""The LLM interpreter: turns a sentence the classic parser didn't understand into an Action.

The model answers with a JSON object whose values are constrained by a schema built every turn:
known verbs, the names of the items in reach or in sight, the directions. The answer is then
checked here, and the engine still validates the action: the model never touches the game state.
"""

import logging
from collections.abc import Sequence
from typing import Any, NamedTuple

from app.engine.models import Action, Command, Direction, Item, Room, Verb
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import INTERPRETER_SYSTEM, interpreter_user

log = logging.getLogger(__name__)

NOT_AN_ACTION = "altro"
NOTHING = "nessuno"
MAX_TOKENS = 60  # the JSON answer is short: a low cap stops a model that rambles

_VERBS = [verb.value for verb in Verb]
_COMMANDS = [Command.GO.value, Command.LOOK.value, Command.INVENTORY.value]
_DIRECTIONS = [direction.value for direction in Direction]


def interpreter_schema(in_reach: Sequence[Item]) -> dict[str, Any]:
    names = [item.name for item in in_reach]
    return {
        "type": "object",
        "properties": {
            "verbo": {"type": "string", "enum": [*_VERBS, *_COMMANDS, NOT_AN_ACTION]},
            "bersaglio": {"type": "string", "enum": [*names, *_DIRECTIONS, NOTHING]},
            "con": {"type": "string", "enum": [*names, NOTHING]},
        },
        "required": ["verbo", "bersaglio", "con"],
    }


class NotUnderstood(NamedTuple):
    """No action came out of the sentence. `reason` says why, for the logs; `not_an_action` is set
    when the model judged that the sentence isn't a game action at all ("altro")."""

    reason: str
    not_an_action: bool = False


def interpret(
    llm: LLMClient, sentence: str, in_reach: Sequence[Item], exits: Sequence[tuple[Direction, Room | None]] = ()
) -> Action | NotUnderstood:
    """The action in the sentence, or why there is none: the model is unavailable, or its answer
    isn't an action on what the player can name.

    `exits` (Engine.known_exits) tell the model where each exit leads, for "torno nella scuderia".
    """
    try:
        reply = llm.complete_json(
            INTERPRETER_SYSTEM,
            interpreter_user(sentence, in_reach, exits),
            interpreter_schema(in_reach),
            max_tokens=MAX_TOKENS,
            temperature=0,
        )
        result = _to_action(reply, {item.name: item.id for item in in_reach})
    except LLMError:
        result = NotUnderstood("il modello non ha dato una risposta valida")
    if isinstance(result, NotUnderstood):
        log.info("=== non capito: %s", result.reason)
    else:
        log.info("=== azione: %s", describe(result))
    return result


def _to_action(reply: dict[str, Any], ids_by_name: dict[str, str]) -> Action | NotUnderstood:
    verb, target, tool = (str(reply.get(key, "")) for key in ("verbo", "bersaglio", "con"))
    if verb == NOT_AN_ACTION:
        return NotUnderstood("la frase non è un'azione di gioco", not_an_action=True)
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


def describe(action: Action) -> str:
    """The action with item ids, as the engine receives it: "usa corda_con_gancio con pozzo"."""
    words = [action.verb, action.direction or action.target or "", f"con {action.with_}" if action.with_ else ""]
    return " ".join(word for word in words if word)
