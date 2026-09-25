"""The LLM narrator: retells a generic engine reply ("Non si può prendere.") in a livelier way.

It only receives facts (place, action, the items as they are now, the outcome) and it is only
used for generic replies: authored texts are always shown as they are.
"""

from collections.abc import Iterator

from app.engine.engine import describe
from app.engine.models import Action, GameState, Outcome, World
from app.engine.text import action_text
from app.llm.client import LLMClient
from app.llm.prompts import NARRATOR_SYSTEM, narrator_user

MAX_TOKENS = 100  # one or two sentences
TEMPERATURE = 0.7


def narrate(llm: LLMClient, world: World, state: GameState, action: Action, outcome: Outcome) -> Iterator[str]:
    """The narration, piece by piece. Raises LLMError: the caller falls back on the fixed text."""
    items = [world.items[item_id] for item_id in (action.target, action.with_) if item_id is not None]
    facts = narrator_user(
        place=world.rooms[state.current_room].name,
        action=action_text(action, world),
        items=[(item.name, describe(item, state)) for item in items],
        result=outcome.text or "",
        succeeded=outcome.ok,
    )
    yield from llm.stream_text(NARRATOR_SYSTEM, facts, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)
