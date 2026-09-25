from collections.abc import Callable

import pytest

from app.engine.models import World
from app.engine.validation import find_problems


def problems_for(world_data: dict) -> list[str]:
    return find_problems(World.model_validate(world_data))


def test_minimal_world_has_no_problems(world_data):
    assert problems_for(world_data) == []


def add_room(world_data: dict, room_id: str, exits: dict) -> None:
    world_data["rooms"][room_id] = {"name": "Stanza", "description": "Una stanza.", "exits": exits}


def add_effect(effect: dict) -> Callable[[dict], None]:
    return lambda d: d["rules"]["tira_leva"]["effects"].append(effect)


# Each case: how to break the minimal world, and the words one single problem must contain
# (where the error is and what is wrong), so the author can find it.
BROKEN_WORLDS = {
    "unknown start room": (
        lambda d: d["game"].update(start_room="salone"),
        ["game.start_room", "salone"],
    ),
    "exit to unknown room": (
        lambda d: d["rooms"]["cella"]["exits"]["sud"].update(to="cantina"),
        ["rooms.cella.exits.sud.to", "cantina"],
    ),
    "item in unknown room": (
        lambda d: d["items"]["leva"].update(location="cantina"),
        ["items.leva.location", "cantina"],
    ),
    "room id reserved for the inventory": (
        lambda d: add_room(d, "inventory", {"nord": {"to": "atrio"}}),
        ["rooms.inventory", "reserved"],
    ),
    "trigger on unknown item": (
        lambda d: d["rules"]["usa_moneta"]["trigger"].update(target="specchio"),
        ["rules.usa_moneta.trigger.0.target", "specchio"],
    ),
    "trigger with unknown item": (
        lambda d: d["rules"]["usa_moneta"]["trigger"].update({"with": "specchio"}),
        ["rules.usa_moneta.trigger.0.with", "specchio"],
    ),
    "unknown item in the second trigger of a list": (
        lambda d: d["rules"]["tira_leva"].update(
            trigger=[{"verb": "tira", "target": "leva"}, {"verb": "spingi", "target": "leva", "with": "specchio"}]
        ),
        ["rules.tira_leva.trigger.1.with", "specchio"],
    ),
    "effect gives unknown item": (
        add_effect({"give": "spada"}),
        ["rules.tira_leva.effects.2.give", "spada"],
    ),
    "effect removes unknown item": (
        add_effect({"remove": "spada"}),
        ["rules.tira_leva.effects.2.remove", "spada"],
    ),
    "effect places unknown item": (
        add_effect({"place": {"item": "spada", "room": "cella"}}),
        ["rules.tira_leva.effects.2.place.item", "spada"],
    ),
    "effect places into unknown room": (
        add_effect({"place": {"item": "moneta", "room": "cantina"}}),
        ["rules.tira_leva.effects.2.place.room", "cantina"],
    ),
    "condition on unknown item": (
        lambda d: d["game"]["endings"][0].update(when={"has": "spada"}),
        ["game.endings.0.when", "spada"],
    ),
    "condition on unknown room": (
        lambda d: d["game"]["endings"][0].update(when={"player_in": "cantina"}),
        ["game.endings.0.when", "cantina"],
    ),
    "unknown item deep inside a condition": (
        lambda d: d["rules"]["tira_leva"].update(when={"not": {"any": [{"flag": "porta_aperta"}, {"has": "spada"}]}}),
        ["rules.tira_leva.when", "spada"],
    ),
    "room variant condition is checked": (
        lambda d: d["rooms"]["atrio"].update(variants=[{"when": {"has": "spada"}, "text": "Altro."}]),
        ["rooms.atrio.variants.0.when", "spada"],
    ),
    "item variant condition is checked": (
        lambda d: d["items"]["leva"].update(variants=[{"when": {"has": "spada"}, "text": "Altro."}]),
        ["items.leva.variants.0.when", "spada"],
    ),
    "flag read but never set (typo)": (
        lambda d: d["rooms"]["atrio"]["exits"]["nord"].update(when={"flag": "porta_apreta"}),
        ["rooms.atrio.exits.nord.when", "porta_apreta"],
    ),
    "out-of-play item never brought into play": (
        lambda d: d["rules"]["tira_leva"].update(effects=[{"set_flag": "porta_aperta"}]),
        ["items.chiave", "never"],
    ),
    "room unreachable from the start": (
        lambda d: add_room(d, "soffitta", {"giù": {"to": "atrio"}}),
        ["rooms.soffitta", "reachable"],
    ),
    "two items with the same name": (
        lambda d: d["items"]["chiave"].update(name="Moneta "),
        ["name", "moneta", "chiave"],
    ),
}


@pytest.mark.parametrize(("break_world", "expected_words"), BROKEN_WORLDS.values(), ids=BROKEN_WORLDS.keys())
def test_broken_world_is_reported(world_data, break_world, expected_words):
    break_world(world_data)

    problems = problems_for(world_data)

    assert any(all(word in problem for word in expected_words) for problem in problems), problems


def test_aliases_may_repeat_another_items_name(world_data):
    # "corda" must still work after the rope becomes "corda con gancio": the engine picks by scope.
    world_data["items"]["moneta"]["aliases"] = ["chiave"]

    assert problems_for(world_data) == []


def test_item_brought_into_play_by_place_is_fine(world_data):
    world_data["rules"]["tira_leva"]["effects"] = [
        {"set_flag": "porta_aperta"},
        {"place": {"item": "chiave", "room": "cella"}},
    ]

    assert problems_for(world_data) == []


def test_all_problems_are_reported_together(world_data):
    world_data["game"]["start_room"] = "salone"
    world_data["items"]["leva"]["location"] = "cantina"

    problems = problems_for(world_data)

    assert any("salone" in problem for problem in problems)
    assert any("cantina" in problem for problem in problems)
