"""The dialogues of every adventure: each character answers every gesture in its own words, and no
gesture or new topic changes the game."""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Gesture
from app.game import Game

WORLDS = {world_id: load_world(WORLDS_DIR / world_id) for world_id in ("rocca", "draghetto", "valdimora")}
CHARACTERS = [(world_id, character_id) for world_id, world in WORLDS.items() for character_id in world.characters]


@pytest.mark.parametrize(("world_id", "character_id"), CHARACTERS, ids=[f"{w}: {c}" for w, c in CHARACTERS])
def test_every_character_answers_every_gesture(world_id, character_id):
    character = WORLDS[world_id].characters[character_id]

    assert set(character.gestures) == set(Gesture)
    assert character.greeting_again is not None


def test_the_pilgrim_tells_who_he_is_as_a_gesture():
    pilgrim = WORLDS["rocca"].characters["pellegrino"]

    assert "chi sei" not in pilgrim.topics["pellegrino"].aliases
    assert "santuario" in pilgrim.gestures[Gesture.WHO_ARE_YOU].text


def test_asked_again_the_pilgrim_does_not_repeat_himself():
    game = Game(Engine(WORLDS["rocca"]))
    game.state.current_room = "scuderia"

    first, second = game.turn("chiedi al pellegrino della bufera"), game.turn("chiedi al pellegrino della bufera")

    assert first == WORLDS["rocca"].characters["pellegrino"].topics["bufera"].text
    assert second == "«Non smetterà prima di sera, te l'ho detto.»"


def test_the_kids_characters_forgive_rudeness():
    dragon = WORLDS["draghetto"]

    assert "perdono" in dragon.characters["draghetto"].gestures[Gesture.RUDENESS].text
    assert "perdono" in dragon.characters["orso"].gestures[Gesture.RUDENESS].text


def test_greeted_again_the_dragon_still_says_what_to_ask_about():
    # For a kid, hearing the hint again helps (spec): «come posso aiutarti?» gets the greeting.
    assert "Chiedimi del mio raffreddore" in WORLDS["draghetto"].characters["draghetto"].greeting_again
