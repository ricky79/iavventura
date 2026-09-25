"""Engine behaviour on the small test world of conftest.py, extended in `data` below."""

import pytest

from app.engine import engine as messages
from app.engine.engine import Engine, holds
from app.engine.models import Action, Direction, GameState, World


@pytest.fixture
def data(world_data) -> dict:
    """Adds a portable item in each room and a description variant to the test world."""
    world_data["rooms"]["atrio"]["variants"] = [
        {"when": {"flag": "porta_aperta"}, "text": "Un atrio spoglio. A nord la porta è aperta."}
    ]
    world_data["items"]["candela"] = {
        "name": "candela",
        "gender": "f",
        "description": "Una candela spenta.",
        "location": "atrio",
        "variants": [{"when": {"flag": "candela_accesa"}, "text": "Una candela accesa."}],
    }
    world_data["items"]["libro"] = {"name": "libro", "gender": "m", "description": "Un libro.", "location": "cella"}
    world_data["rules"]["usa_moneta"]["text"] = "La moneta tintinna contro la leva."
    return world_data


def start(data: dict) -> tuple[Engine, GameState]:
    engine = Engine(World.model_validate(data))
    state, _ = engine.new_game()
    return engine, state


def snapshot(state: GameState) -> dict:
    """What an action may change, apart from the turn counter."""
    return state.model_dump(exclude={"turns"})


# --- Start, reach, look, inventory ---------------------------------------------


def test_new_game_shows_intro_and_first_room(data):
    engine = Engine(World.model_validate(data))

    state, outcome = engine.new_game()

    assert state.current_room == "atrio"
    assert outcome.ok
    assert outcome.text == "Inizio."
    assert outcome.room.id == "atrio"
    assert outcome.room.name == "Atrio"
    assert outcome.room.description == "Un atrio spoglio."
    assert outcome.room.first_visit is True


def test_room_lists_only_portable_items_lying_there(data):
    _, outcome = Engine(World.model_validate(data)).new_game()

    # leva is scenery, moneta is carried, chiave is out of play, libro is in the cella
    assert outcome.room.items == ("candela",)
    assert outcome.room.exits == (Direction.NORTH,)


def test_items_in_reach_are_those_in_the_room_and_in_the_inventory(data):
    engine, state = start(data)

    assert [item.id for item in engine.in_reach(state)] == ["leva", "moneta", "candela"]


def test_look_shows_the_room_with_its_current_variant(data):
    engine, state = start(data)
    state.flags.add("porta_aperta")

    outcome = engine.execute(state, Action(verb="guarda"))

    assert outcome.ok
    assert outcome.room.description == "Un atrio spoglio. A nord la porta è aperta."
    assert outcome.room.first_visit is False


def test_inventory_lists_carried_items(data):
    engine, state = start(data)
    state.item_locations["libro"] = "inventory"

    outcome = engine.execute(state, Action(verb="inventario"))

    assert outcome.ok
    assert outcome.inventory == ("moneta", "libro")


# --- Conditions ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ({"flag": "porta_aperta"}, True),
        ({"flag": "altro"}, False),
        ({"has": "moneta"}, True),
        ({"has": "candela"}, False),
        ({"player_in": "atrio"}, True),
        ({"player_in": "cella"}, False),
        ({"all": [{"flag": "porta_aperta"}, {"has": "moneta"}]}, True),
        ({"all": [{"flag": "porta_aperta"}, {"has": "candela"}]}, False),
        ({"any": [{"flag": "altro"}, {"has": "moneta"}]}, True),
        ({"any": [{"flag": "altro"}, {"has": "candela"}]}, False),
        ({"not": {"has": "candela"}}, True),
        ({"not": {"has": "moneta"}}, False),
    ],
)
def test_conditions_are_evaluated_on_the_state(data, condition, expected):
    data["game"]["endings"].append({"when": condition, "text": "Condizione da provare."})
    engine, state = start(data)
    state.flags.add("porta_aperta")

    assert holds(engine.world.game.endings[-1].when, state) is expected


# --- Moving ----------------------------------------------------------------------


def test_going_where_there_is_no_exit_is_refused(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="vai", direction="sud"))

    assert not outcome.ok
    assert outcome.text == messages.NO_EXIT
    assert state.current_room == "atrio"


def test_closed_exit_shows_its_otherwise_text(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="vai", direction="nord"))

    assert not outcome.ok
    assert outcome.text == "La porta è chiusa."
    assert state.current_room == "atrio"


def test_closed_exit_without_otherwise_gives_the_generic_refusal(data):
    del data["rooms"]["atrio"]["exits"]["nord"]["otherwise"]
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="vai", direction="nord"))

    assert outcome.text == messages.NO_EXIT


def test_open_exit_moves_the_player_into_the_room(data):
    data["game"]["endings"] = [{"when": {"flag": "mai"}, "text": "Fine."}]
    engine, state = start(data)
    state.flags.add("porta_aperta")

    outcome = engine.execute(state, Action(verb="vai", direction="nord"))

    assert outcome.ok
    assert state.current_room == "cella"
    assert state.visited == {"atrio", "cella"}
    assert outcome.room.id == "cella"
    assert outcome.room.items == ("libro",)
    assert outcome.room.first_visit is True


def test_coming_back_to_a_room_is_not_a_first_visit(data):
    data["game"]["endings"] = [{"when": {"flag": "mai"}, "text": "Fine."}]
    engine, state = start(data)
    state.flags.add("porta_aperta")
    engine.execute(state, Action(verb="vai", direction="nord"))

    outcome = engine.execute(state, Action(verb="vai", direction="sud"))

    assert outcome.room.id == "atrio"
    assert outcome.room.first_visit is False


# --- Turns and endings -------------------------------------------------------------


def test_every_action_takes_a_turn_even_when_refused(data):
    engine, state = start(data)

    engine.execute(state, Action(verb="guarda"))
    engine.execute(state, Action(verb="vai", direction="sud"))

    assert state.turns == 2


def test_the_first_ending_that_holds_ends_the_game(data):
    data["game"]["endings"].insert(0, {"when": {"has": "candela"}, "text": "Fine prematura."})
    data["game"]["endings"].append({"when": {"flag": "porta_aperta"}, "text": "Fine alternativa."})
    engine, state = start(data)
    state.flags.add("porta_aperta")

    outcome = engine.execute(state, Action(verb="vai", direction="nord"))

    assert outcome.ending == "Fine."
    assert outcome.room.id == "cella"
    assert state.finished


def test_no_ending_while_no_condition_holds(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="guarda"))

    assert outcome.ending is None
    assert not state.finished


def test_nothing_can_be_done_once_the_game_is_over(data):
    engine, state = start(data)
    state.finished = True

    outcome = engine.execute(state, Action(verb="guarda"))

    assert not outcome.ok
    assert outcome.text == messages.GAME_OVER
    assert state.turns == 0


# --- Reach ----------------------------------------------------------------------------


@pytest.mark.parametrize("target", ["libro", "chiave", "drago"], ids=["other room", "out of play", "unknown"])
def test_acting_on_an_item_out_of_reach_is_refused(data, target):
    engine, state = start(data)
    before = snapshot(state)

    outcome = engine.execute(state, Action(verb="prendi", target=target))

    assert not outcome.ok
    assert outcome.text == messages.NOT_HERE
    assert snapshot(state) == before


def test_using_an_item_out_of_reach_is_refused(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="usa", target="leva", with_="libro"))

    assert outcome.text == messages.NOT_HERE


# --- Rules --------------------------------------------------------------------------------


def test_matching_rule_applies_its_effects_and_shows_its_text(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="tira", target="leva"))

    assert outcome.ok
    assert outcome.text == "Clac! Qualcosa cade ai tuoi piedi."
    assert "porta_aperta" in state.flags
    assert state.item_locations["chiave"] == "inventory"


def test_rule_whose_condition_fails_shows_otherwise_and_changes_nothing(data):
    engine, state = start(data)
    state.flags.add("porta_aperta")
    before = snapshot(state)

    outcome = engine.execute(state, Action(verb="tira", target="leva"))

    assert not outcome.ok
    assert outcome.text == "La leva non si muove più."
    assert snapshot(state) == before


def test_rule_whose_condition_fails_without_otherwise_gives_the_generic_answer(data):
    del data["rules"]["tira_leva"]["otherwise"]
    engine, state = start(data)
    state.flags.add("porta_aperta")

    outcome = engine.execute(state, Action(verb="tira", target="leva"))

    assert outcome.text == messages.NOTHING_HAPPENS


def test_rule_without_effects_is_just_an_answer(data):
    engine, state = start(data)
    before = snapshot(state)

    outcome = engine.execute(state, Action(verb="usa", target="leva", with_="moneta"))

    assert outcome.ok
    assert outcome.text == "La moneta tintinna contro la leva."
    assert snapshot(state) == before


def test_rule_items_match_in_either_order(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="usa", target="moneta", with_="leva"))

    assert outcome.text == "La moneta tintinna contro la leva."


def test_rule_without_with_ignores_actions_with_a_tool(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="tira", target="leva", with_="moneta"))

    assert not outcome.ok
    assert "porta_aperta" not in state.flags


def test_rule_with_a_tool_ignores_actions_without_one(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="usa", target="leva"))

    assert not outcome.ok
    assert outcome.text == messages.NOTHING_HAPPENS


def test_first_matching_rule_wins_even_when_its_condition_fails(data):
    data["rules"] = {
        "tira_prima": {
            "trigger": {"verb": "tira", "target": "leva"},
            "when": {"has": "candela"},
            "otherwise": "Al buio non trovi la leva.",
            "text": "Tiri la leva alla luce della candela.",
        },
        **data["rules"],
    }
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="tira", target="leva"))

    assert outcome.text == "Al buio non trovi la leva."
    assert "porta_aperta" not in state.flags


def test_every_kind_of_effect_is_applied_in_order(data):
    data["rules"]["spingi_leva"] = {
        "trigger": {"verb": "spingi", "target": "leva"},
        "effects": [
            {"give": "candela"},
            {"remove": "moneta"},
            {"place": {"item": "libro", "room": "atrio"}},
            {"set_flag": "candela_accesa"},
            {"clear_flag": "porta_aperta"},
            {"give": "chiave"},
            {"place": {"item": "chiave", "room": "cella"}},
        ],
        "text": "Succedono molte cose.",
    }
    engine, state = start(data)
    state.flags.add("porta_aperta")

    engine.execute(state, Action(verb="spingi", target="leva"))

    assert state.item_locations == {
        "leva": "atrio",
        "moneta": None,
        "chiave": "cella",
        "candela": "inventory",
        "libro": "atrio",
    }
    assert state.flags == {"candela_accesa"}


def test_a_rule_replaces_the_default_behaviour_of_its_verb(data):
    data["rules"]["prendi_candela"] = {
        "trigger": {"verb": "prendi", "target": "candela"},
        "text": "È incollata al pavimento con la cera.",
    }
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="prendi", target="candela"))

    assert outcome.text == "È incollata al pavimento con la cera."
    assert state.item_locations["candela"] == "atrio"


def test_every_trigger_of_a_rule_fires_it(data):
    data["rules"]["tira_leva"]["trigger"] = [
        {"verb": "tira", "target": "leva"},
        {"verb": "spingi", "target": "leva", "with": "candela"},
    ]
    engine, state = start(data)

    first = engine.execute(state, Action(verb="spingi", target="candela", with_="leva"))
    again = engine.execute(state, Action(verb="tira", target="leva"))

    assert first.text == "Clac! Qualcosa cade ai tuoi piedi."
    assert "porta_aperta" in state.flags
    assert again.text == "La leva non si muove più."


def test_use_falls_back_on_any_trigger_of_a_list(data):
    data["rules"]["tira_leva"]["trigger"] = [
        {"verb": "tira", "target": "leva"},
        {"verb": "spingi", "target": "leva", "with": "candela"},
    ]
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="usa", target="leva", with_="candela"))

    assert outcome.text == "Clac! Qualcosa cade ai tuoi piedi."


# --- "usa X con Y" falls back on the other verbs ---------------------------------------------


@pytest.fixture
def data_with_push(data) -> dict:
    data["rules"]["spingi_leva_con_candela"] = {
        "trigger": {"verb": "spingi", "target": "leva", "with": "candela"},
        "effects": [{"set_flag": "candela_accesa"}],
        "text": "Spingi la leva con la candela, che si accende per lo sfregamento.",
    }
    data["rules"]["tira_leva_con_moneta"] = {
        "trigger": {"verb": "tira", "target": "leva", "with": "moneta"},
        "text": "Tiri la leva con la moneta.",
    }
    return data


def test_use_with_two_items_falls_back_on_a_rule_of_another_verb(data_with_push):
    engine, state = start(data_with_push)

    outcome = engine.execute(state, Action(verb="usa", target="candela", with_="leva"))

    assert outcome.text == "Spingi la leva con la candela, che si accende per lo sfregamento."
    assert "candela_accesa" in state.flags


def test_a_use_rule_comes_before_the_rules_of_other_verbs(data_with_push):
    engine, state = start(data_with_push)

    outcome = engine.execute(state, Action(verb="usa", target="leva", with_="moneta"))

    assert outcome.text == "La moneta tintinna contro la leva."


def test_use_with_one_item_does_not_fall_back(data_with_push):
    engine, state = start(data_with_push)

    outcome = engine.execute(state, Action(verb="usa", target="leva"))

    assert outcome.text == messages.NOTHING_HAPPENS
    assert "porta_aperta" not in state.flags


def test_other_verbs_do_not_fall_back(data_with_push):
    engine, state = start(data_with_push)

    outcome = engine.execute(state, Action(verb="tira", target="leva", with_="candela"))

    assert not outcome.ok
    assert "candela_accesa" not in state.flags


# --- Verbs without a matching rule ----------------------------------------------------------


def test_examine_shows_the_description_with_its_current_variant(data):
    engine, state = start(data)

    plain = engine.execute(state, Action(verb="esamina", target="candela"))
    state.flags.add("candela_accesa")
    lit = engine.execute(state, Action(verb="esamina", target="candela"))

    assert plain.ok
    assert plain.text == "Una candela spenta."
    assert lit.text == "Una candela accesa."


def test_take_puts_the_item_in_the_inventory(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="prendi", target="candela"))

    assert outcome.ok
    assert outcome.text == messages.DONE
    assert state.item_locations["candela"] == "inventory"


def test_scenery_cannot_be_taken(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="prendi", target="leva"))

    assert not outcome.ok
    assert outcome.text == messages.CANT_TAKE
    assert state.item_locations["leva"] == "atrio"


def test_taking_a_carried_item_again_is_refused(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="prendi", target="moneta"))

    assert not outcome.ok
    assert outcome.text == messages.ALREADY_HAVE


def test_drop_leaves_the_item_in_the_current_room(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="lascia", target="moneta"))

    assert outcome.ok
    assert outcome.text == messages.DONE
    assert state.item_locations["moneta"] == "atrio"


def test_dropping_an_item_not_carried_is_refused(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="lascia", target="candela"))

    assert not outcome.ok
    assert outcome.text == messages.DONT_HAVE
    assert state.item_locations["candela"] == "atrio"


@pytest.mark.parametrize(
    ("verb", "expected"),
    [
        ("apri", messages.CANT_OPEN),
        ("chiudi", messages.CANT_CLOSE),
        ("leggi", messages.NOTHING_TO_READ),
        ("usa", messages.NOTHING_HAPPENS),
        ("spingi", messages.NOTHING_HAPPENS),
        ("tira", messages.NOTHING_HAPPENS),
    ],
    ids=["apri", "chiudi", "leggi", "usa", "spingi", "tira"],
)
def test_verbs_that_need_a_rule_do_nothing_without_one(data, verb, expected):
    engine, state = start(data)
    before = snapshot(state)

    outcome = engine.execute(state, Action(verb=verb, target="candela"))

    assert not outcome.ok
    assert outcome.text == expected
    assert snapshot(state) == before


def test_default_behaviour_ignores_the_tool(data):
    engine, state = start(data)

    outcome = engine.execute(state, Action(verb="prendi", target="candela", with_="moneta"))

    assert outcome.ok
    assert state.item_locations["candela"] == "inventory"


# --- Exits and the rooms the player knows about ------------------------------------------------


def test_an_exit_to_a_room_never_seen_nor_named_is_only_a_direction(data):
    engine, state = start(data)

    assert engine.known_exits(state) == [(Direction.NORTH, None)]


def test_a_room_named_in_the_description_is_known(data):
    data["rooms"]["atrio"]["description"] = "Un atrio spoglio. A nord c'è la cella."
    engine, state = start(data)

    assert engine.known_exits(state) == [(Direction.NORTH, engine.world.rooms["cella"])]


def test_only_the_current_description_variant_counts(data):
    data["rooms"]["atrio"]["variants"] = [{"when": {"flag": "porta_aperta"}, "text": "La porta della cella è aperta."}]
    engine, state = start(data)

    before = engine.known_exits(state)
    state.flags.add("porta_aperta")

    assert before == [(Direction.NORTH, None)]
    assert engine.known_exits(state) == [(Direction.NORTH, engine.world.rooms["cella"])]


def test_a_visited_room_is_known(data):
    engine, state = start(data)
    state.visited.add("cella")

    assert engine.known_exits(state) == [(Direction.NORTH, engine.world.rooms["cella"])]


def test_every_word_of_the_room_name_must_be_named(data):
    data["rooms"]["cella"]["name"] = "Cella del conte"
    data["rooms"]["atrio"]["description"] = "Un atrio spoglio. A nord c'è una cella."
    engine, state = start(data)

    assert engine.known_exits(state) == [(Direction.NORTH, None)]


def test_exits_come_in_compass_order(data):
    data["rooms"]["atrio"]["exits"] = {"ovest": {"to": "cella"}, "su": {"to": "cella"}, "nord": {"to": "atrio"}}
    engine, state = start(data)

    assert [direction for direction, _ in engine.known_exits(state)] == [Direction.NORTH, Direction.WEST, Direction.UP]
    assert engine.known_exits(state)[0] == (Direction.NORTH, engine.world.rooms["atrio"])
