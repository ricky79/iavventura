"""The sample castle: invariants of its puzzle, then the game played through the engine.

The invariants fail if a data change opens a shortcut. Chain: gancio + corda -> corda_con_gancio
-> fish chiave_torre out of the well -> open the tower door -> entering the tower ends the game.
"""

import pytest

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import Action, FlagSet, GameState, Give, Place, PlayerIn, Remove, Rule, SetFlag, World


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world()


def rules_bringing_in(world: World, item_id: str) -> list[Rule]:
    return [
        rule
        for rule in world.rules.values()
        if Give(give=item_id) in rule.effects
        or any(isinstance(effect, Place) and effect.place.item == item_id for effect in rule.effects)
    ]


def items_used_by(rule: Rule) -> list[set[str]]:
    """The items of each trigger: a puzzle may be solved in more than one way."""
    return [{trigger.target, trigger.with_} - {None} for trigger in rule.triggers]


def test_castle_has_four_rooms_and_starts_in_the_courtyard(castle):
    assert set(castle.rooms) == {"cortile", "cucina", "scuderia", "torre"}
    assert castle.game.start_room == "cortile"


def test_hook_and_rope_are_waiting_in_the_castle(castle):
    assert castle.items["gancio"].location == "cucina"
    assert castle.items["corda"].location == "scuderia"


def test_grapple_exists_only_by_combining_hook_and_rope(castle):
    assert castle.items["corda_con_gancio"].location is None

    [combine] = rules_bringing_in(castle, "corda_con_gancio")

    assert items_used_by(combine) == [{"gancio", "corda"}]
    assert Remove(remove="gancio") in combine.effects
    assert Remove(remove="corda") in combine.effects


def test_key_can_only_be_fished_out_with_the_grapple(castle):
    assert castle.items["chiave_torre"].location is None

    fishers = rules_bringing_in(castle, "chiave_torre")

    assert fishers
    assert all("corda_con_gancio" in items for rule in fishers for items in items_used_by(rule))


def test_the_key_is_seen_at_the_bottom_of_the_well_until_fished_out(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    assert [item.id for item in engine.visible(state)] == ["chiave_torre"]

    play(engine, state, UP_TO_THE_KEY)

    assert engine.visible(state) == []


def test_tower_opens_only_with_the_key(castle):
    ways_into_tower = [exit_ for room in castle.rooms.values() for exit_ in room.exits.values() if exit_.to == "torre"]
    assert ways_into_tower

    for exit_ in ways_into_tower:
        assert isinstance(exit_.when, FlagSet)
        openers = [rule for rule in castle.rules.values() if SetFlag(set_flag=exit_.when.flag) in rule.effects]
        assert openers
        assert all("chiave_torre" in items for rule in openers for items in items_used_by(rule))


def test_entering_the_tower_ends_the_game(castle):
    assert any(ending.when == PlayerIn(player_in="torre") for ending in castle.game.endings)


# --- Playing through the engine -------------------------------------------------

UP_TO_THE_KEY = [
    Action(verb="vai", direction="ovest"),
    Action(verb="prendi", target="gancio"),
    Action(verb="vai", direction="est"),
    Action(verb="vai", direction="est"),
    Action(verb="prendi", target="corda"),
    Action(verb="usa", target="corda", with_="gancio"),
    Action(verb="vai", direction="ovest"),
    Action(verb="usa", target="pozzo", with_="corda_con_gancio"),
]


def play(engine: Engine, state: GameState, actions: list[Action]) -> None:
    for action in actions:
        outcome = engine.execute(state, action)
        assert outcome.ok, f"{action} was refused: {outcome.text}"


def test_whole_game_can_be_played_to_the_end(castle):
    engine = Engine(castle)
    state, intro = engine.new_game()
    assert intro.room.id == "cortile"

    locked = engine.execute(state, Action(verb="vai", direction="nord"))
    assert not locked.ok
    assert locked.text == "La porta della torre è chiusa a chiave."

    play(engine, state, UP_TO_THE_KEY)
    assert engine.execute(state, Action(verb="inventario")).inventory == ("corda_con_gancio", "chiave_torre")

    play(engine, state, [Action(verb="apri", target="porta_torre", with_="chiave_torre")])
    last = engine.execute(state, Action(verb="vai", direction="nord"))

    assert last.room.id == "torre"
    assert last.ending == castle.game.endings[0].text
    assert state.finished


def test_one_piece_alone_only_gives_a_hint(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY[:2] + [Action(verb="vai", direction="est")])

    hint = engine.execute(state, Action(verb="usa", target="gancio", with_="pozzo"))

    assert hint.text == castle.rules["cala_gancio"].text
    assert state.item_locations["chiave_torre"] is None


def test_the_key_can_be_fished_out_only_once(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY)

    again = engine.execute(state, Action(verb="usa", target="pozzo", with_="corda_con_gancio"))

    assert not again.ok
    assert again.text == castle.rules["pesca_chiave"].otherwise


def test_using_the_key_on_the_door_opens_it_too(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY)

    opened = engine.execute(state, Action(verb="usa", target="chiave_torre", with_="porta_torre"))

    assert opened.text == castle.rules["apri_torre"].text
    assert "torre_aperta" in state.flags


def test_the_key_can_also_be_taken_with_the_grapple(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY[:-1])

    fished = engine.execute(state, Action(verb="prendi", target="chiave_torre", with_="corda_con_gancio"))

    assert fished.text == castle.rules["pesca_chiave"].text
    assert state.item_locations["chiave_torre"] == "inventory"
