"""The LLM interpreter: turns a sentence the classic parser didn't understand into an Action.

The model answers with a JSON object whose values are constrained by a schema built every turn:
known verbs, the names of the items in reach, the directions. The answer is then checked here,
and the engine still validates the action: the model never touches the game state.
"""

import logging
from collections.abc import Sequence
from typing import Any

from app.engine.models import Action, Command, Direction, Item, Verb
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


def interpret(llm: LLMClient, sentence: str, in_reach: Sequence[Item]) -> Action | None:
    """None when the model is unavailable, or its answer isn't an action on what is in reach."""
    try:
        reply = llm.complete_json(
            INTERPRETER_SYSTEM,
            interpreter_user(sentence, in_reach),
            interpreter_schema(in_reach),
            max_tokens=MAX_TOKENS,
            temperature=0,
        )
        action = _to_action(reply, {item.name: item.id for item in in_reach})
    except LLMError:
        log.info("=== non capito: il modello non ha dato una risposta valida")
        return None
    except _NotUnderstood as reason:
        log.info("=== non capito: %s", reason)
        return None
    log.info("=== azione: %s", _describe(action))
    return action


class _NotUnderstood(Exception):
    """The model answered, but not with an action on what is in reach; the message says why."""


def _to_action(reply: dict[str, Any], ids_by_name: dict[str, str]) -> Action:
    verb, target, tool = (str(reply.get(key, "")) for key in ("verbo", "bersaglio", "con"))
    if verb == NOT_AN_ACTION:
        raise _NotUnderstood("la frase non è un'azione di gioco")
    if verb == Command.GO:
        if target not in _DIRECTIONS:
            raise _NotUnderstood(f"direzione non valida {target!r}")
        return Action(verb=Command.GO, direction=target)
    if verb == Command.INVENTORY:
        return Action(verb=Command.INVENTORY)
    if verb == Command.LOOK:
        # "guarda nel pozzo" is examining the well
        if target in ids_by_name:
            return Action(verb=Verb.EXAMINE, target=ids_by_name[target])
        return Action(verb=Command.LOOK)
    if verb not in _VERBS:
        raise _NotUnderstood(f"verbo sconosciuto {verb!r}")
    if target not in ids_by_name:
        raise _NotUnderstood(f"bersaglio non a portata {target!r}")
    with_ = ids_by_name.get(tool) if tool != target else None
    return Action(verb=verb, target=ids_by_name[target], with_=with_)


def _describe(action: Action) -> str:
    """The action with item ids, as the engine receives it: "usa corda_con_gancio con pozzo"."""
    words = [action.verb, action.direction or action.target or "", f"con {action.with_}" if action.with_ else ""]
    return " ".join(word for word in words if word)
