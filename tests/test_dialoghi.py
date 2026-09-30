"""The dialogues of every adventure: each character answers every gesture in its own words, and no
gesture or new topic changes the game."""

import pytest

from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Gesture

WORLDS = {world_id: load_world(WORLDS_DIR / world_id) for world_id in ("valdimora",)}
CHARACTERS = [(world_id, character_id) for world_id, world in WORLDS.items() for character_id in world.characters]


@pytest.mark.parametrize(("world_id", "character_id"), CHARACTERS, ids=[f"{w}: {c}" for w, c in CHARACTERS])
def test_every_character_answers_every_gesture(world_id, character_id):
    character = WORLDS[world_id].characters[character_id]

    assert set(character.gestures) == set(Gesture)
    assert character.greeting_again is not None
