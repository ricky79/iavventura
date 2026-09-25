import json

import pytest

from app.engine.engine import Engine, StateError
from app.engine.models import GameState, World


def test_new_game_starts_from_the_world(world_data):
    state = GameState.new(World.model_validate(world_data))

    assert state.current_room == "atrio"
    assert state.item_locations == {"leva": "atrio", "moneta": "inventory", "chiave": None}
    assert state.flags == set()
    assert state.visited == {"atrio"}
    assert state.turns == 0
    assert state.finished is False


def test_state_survives_a_json_round_trip(world_data):
    state = GameState.new(World.model_validate(world_data))
    state.current_room = "cella"
    state.item_locations["chiave"] = "inventory"
    state.flags.add("porta_aperta")
    state.visited.add("cella")
    state.turns = 3

    restored = GameState.model_validate_json(state.model_dump_json())

    assert restored == state


# --- Restoring a state that comes from outside (the browser) ---------------------------------------


def saved(world_data) -> dict:
    """A state as the browser keeps it: JSON, after a few moves."""
    state = GameState.new(World.model_validate(world_data))
    state.item_locations["chiave"] = "inventory"
    state.flags.add("porta_aperta")
    state.turns = 4
    return json.loads(state.model_dump_json())


def test_a_saved_state_is_restored(world_data):
    engine = Engine(World.model_validate(world_data))

    state = engine.restore(saved(world_data))

    assert state.item_locations["chiave"] == "inventory"
    assert state.flags == {"porta_aperta"}
    assert state.turns == 4


def test_texts_may_change_without_breaking_a_saved_state(world_data):
    data = saved(world_data)
    world_data["rooms"]["atrio"]["description"] = "Un atrio ridipinto."

    Engine(World.model_validate(world_data)).restore(data)


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda s: s.update(current_room="cantina"), "cantina"),
        (lambda s: s["item_locations"].pop("leva"), "leva"),
        (lambda s: s["item_locations"].update(drago="atrio"), "drago"),
        (lambda s: s["item_locations"].update(moneta="cantina"), "cantina"),
        (lambda s: s.update(visited=["atrio", "soffitta"]), "soffitta"),
        (lambda s: s.update(turns="molti"), "turns"),
        (lambda s: s.update(punteggio=10), "punteggio"),
    ],
    ids=["unknown room", "missing item", "unknown item", "item in unknown room", "unknown visited room",
         "wrong type", "unknown field"],
)  # fmt: skip
def test_a_state_that_does_not_fit_the_world_is_refused_with_the_reason(world_data, change, problem):
    data = saved(world_data)
    change(data)

    with pytest.raises(StateError, match=problem):
        Engine(World.model_validate(world_data)).restore(data)


@pytest.mark.parametrize("data", [None, "stato", [1, 2]])
def test_something_that_is_not_a_state_is_refused(world_data, data):
    with pytest.raises(StateError):
        Engine(World.model_validate(world_data)).restore(data)
