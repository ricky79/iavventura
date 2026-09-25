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
