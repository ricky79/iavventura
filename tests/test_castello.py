"""Invariants of the sample castle's puzzle: they fail if a data change opens a shortcut.

Chain: gancio + corda -> corda_con_gancio -> fish chiave_torre out of the well
-> open the tower door -> entering the tower ends the game.
"""

import pytest

from app.engine.loader import load_world
from app.engine.models import FlagSet, Give, Place, PlayerIn, Remove, Rule, SetFlag, World


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


def items_used_by(rule: Rule) -> set[str]:
    return {rule.trigger.target, rule.trigger.with_} - {None}


def test_castle_has_four_rooms_and_starts_in_the_courtyard(castle):
    assert set(castle.rooms) == {"cortile", "cucina", "scuderia", "torre"}
    assert castle.game.start_room == "cortile"


def test_hook_and_rope_are_waiting_in_the_castle(castle):
    assert castle.items["gancio"].location == "cucina"
    assert castle.items["corda"].location == "scuderia"


def test_grapple_exists_only_by_combining_hook_and_rope(castle):
    assert castle.items["corda_con_gancio"].location is None

    [combine] = rules_bringing_in(castle, "corda_con_gancio")

    assert items_used_by(combine) == {"gancio", "corda"}
    assert Remove(remove="gancio") in combine.effects
    assert Remove(remove="corda") in combine.effects


def test_key_can_only_be_fished_out_with_the_grapple(castle):
    assert castle.items["chiave_torre"].location is None

    fishers = rules_bringing_in(castle, "chiave_torre")

    assert fishers
    assert all("corda_con_gancio" in items_used_by(rule) for rule in fishers)


def test_tower_opens_only_with_the_key(castle):
    ways_into_tower = [exit_ for room in castle.rooms.values() for exit_ in room.exits.values() if exit_.to == "torre"]
    assert ways_into_tower

    for exit_ in ways_into_tower:
        assert isinstance(exit_.when, FlagSet)
        openers = [rule for rule in castle.rules.values() if SetFlag(set_flag=exit_.when.flag) in rule.effects]
        assert openers
        assert all("chiave_torre" in items_used_by(rule) for rule in openers)


def test_entering_the_tower_ends_the_game(castle):
    assert any(ending.when == PlayerIn(player_in="torre") for ending in castle.game.endings)
