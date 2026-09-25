"""The classic parser: simple Italian commands -> Action, Ambiguous or None."""

import pytest

from app.engine.models import Action, World
from app.engine.parser import Ambiguous, parse


@pytest.fixture
def world(world_data) -> World:
    """Names with prepositions inside and aliases shared between items, as in the castle."""
    world_data["items"] = {
        "corda": {"name": "corda", "gender": "f", "aliases": ["fune"], "description": "-", "location": "atrio"},
        "gancio": {
            "name": "gancio da macellaio",
            "gender": "m",
            "aliases": ["gancio", "uncino"],
            "description": "-",
            "location": "atrio",
        },
        "corda_con_gancio": {
            "name": "corda con gancio",
            "gender": "f",
            "aliases": ["corda", "gancio", "rampino"],
            "description": "-",
            "location": None,
        },
        "pozzo": {"name": "pozzo", "gender": "m", "description": "-", "location": "atrio", "scenery": True},
        "porta": {
            "name": "porta della torre",
            "gender": "f",
            "aliases": ["porta", "porta di ferro"],
            "description": "-",
            "location": "atrio",
            "scenery": True,
        },
        "chiave": {"name": "chiave di ferro", "gender": "f", "aliases": ["chiave"], "description": "-", "location": None},
    }
    return World.model_validate(world_data)


def parse_with(world: World, text: str, *in_reach: str):
    return parse(text, world, [world.items[item_id] for item_id in in_reach])


# --- Commands without items ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("nord", Action(verb="vai", direction="nord")),
        ("n", Action(verb="vai", direction="nord")),
        ("s", Action(verb="vai", direction="sud")),
        ("e", Action(verb="vai", direction="est")),
        ("o", Action(verb="vai", direction="ovest")),
        ("vai a nord", Action(verb="vai", direction="nord")),
        ("va verso sud", Action(verb="vai", direction="sud")),
        ("vai su", Action(verb="vai", direction="su")),
        ("sali", Action(verb="vai", direction="su")),
        ("giù", Action(verb="vai", direction="giù")),
        ("giu", Action(verb="vai", direction="giù")),
        ("scendi", Action(verb="vai", direction="giù")),
        ("  Nord! ", Action(verb="vai", direction="nord")),
        ("guarda", Action(verb="guarda")),
        ("g", Action(verb="guarda")),
        ("descrivi", Action(verb="guarda")),
        ("inventario", Action(verb="inventario")),
        ("inv", Action(verb="inventario")),
        ("i", Action(verb="inventario")),
    ],
)
def test_commands_without_items(world, text, expected):
    assert parse_with(world, text) == expected


# --- Commands on items ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("prendi la corda", Action(verb="prendi", target="corda")),
        ("raccogli la fune", Action(verb="prendi", target="corda")),
        ("PRENDI LA CORDA.", Action(verb="prendi", target="corda")),
        ("prendi l'uncino", Action(verb="prendi", target="gancio")),
        ("prendi il gancio da macellaio", Action(verb="prendi", target="gancio")),
        ("lascia la corda", Action(verb="lascia", target="corda")),
        ("x pozzo", Action(verb="esamina", target="pozzo")),
        ("guarda nel pozzo", Action(verb="esamina", target="pozzo")),
        ("usa la corda con il gancio", Action(verb="usa", target="corda", with_="gancio")),
        ("usa il gancio sulla corda", Action(verb="usa", target="gancio", with_="corda")),
        ("spingi la porta", Action(verb="spingi", target="porta")),
        ("apri la porta di ferro", Action(verb="apri", target="porta")),
    ],
)
def test_commands_on_items_in_reach(world, text, expected):
    assert parse_with(world, text, "corda", "gancio", "pozzo", "porta") == expected


def test_longest_name_wins_even_when_it_contains_a_preposition(world):
    action = parse_with(world, "usa la corda con gancio nel pozzo", "corda_con_gancio", "pozzo")

    assert action == Action(verb="usa", target="corda_con_gancio", with_="pozzo")


def test_names_of_items_out_of_reach_do_not_hide_those_in_reach(world):
    # "corda con gancio" is the name of an item out of play: here the words mean two items.
    action = parse_with(world, "usa la corda con il gancio", "corda", "gancio")

    assert action == Action(verb="usa", target="corda", with_="gancio")


def test_names_with_prepositions_on_both_sides(world):
    action = parse_with(world, "apri la porta di ferro con la chiave di ferro", "porta", "chiave")

    assert action == Action(verb="apri", target="porta", with_="chiave")


def test_an_alias_is_resolved_among_items_in_reach(world):
    assert parse_with(world, "esamina il rampino", "corda_con_gancio") == Action(
        verb="esamina", target="corda_con_gancio"
    )
    assert parse_with(world, "prendi la corda", "corda_con_gancio") == Action(verb="prendi", target="corda_con_gancio")


def test_an_item_out_of_reach_still_reaches_the_engine(world):
    # The engine then answers "Non vedi niente del genere qui."
    assert parse_with(world, "prendi la chiave", "corda") == Action(verb="prendi", target="chiave")


def test_items_out_of_reach_are_never_ambiguous(world):
    # "gancio" is both the hook and the grapple: asking which one would reveal the grapple.
    assert parse_with(world, "prendi il gancio", "pozzo") == Action(verb="prendi", target="gancio")


def test_two_items_in_reach_with_the_same_name_are_ambiguous(world):
    result = parse_with(world, "prendi la corda", "corda", "corda_con_gancio")

    assert result == Ambiguous(candidates=(world.items["corda"], world.items["corda_con_gancio"]))


# --- What the parser does not understand --------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "?!",
        "balla",
        "prendi",
        "prendi la",
        "prendi la vecchia corda",
        "prendi la corda e il gancio",
        "usa la corda con il gancio nel pozzo",
        "usa la corda con la fune",
        "vai",
        "vai in cucina",
        "nord sud",
        "inventario corda",
        "guarda nord",
    ],
)
def test_anything_else_is_not_understood(world, text):
    assert parse_with(world, text, "corda", "gancio", "pozzo") is None
