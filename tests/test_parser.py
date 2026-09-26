"""The classic parser: simple Italian commands -> Action, Ambiguous or None."""

import pytest

from app.engine.models import Action, Direction, World
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


# --- Going to a room by its name ----------------------------------------------------------------


def exits_to(world: World, *pairs: tuple[str, str | None]):
    return [(Direction(direction), world.rooms[room] if room else None) for direction, room in pairs]


@pytest.mark.parametrize("text", ["vai nella cella", "vai in cella", "va alla cella", "cammina verso la Cella"])
def test_going_to_a_known_room_by_name(world, text):
    exits = exits_to(world, ("sud", None), ("ovest", "cella"))

    assert parse(text, world, [], exits) == Action(verb="vai", direction="ovest")


def test_directions_still_work_when_rooms_are_known(world):
    assert parse("vai a sud", world, [], exits_to(world, ("ovest", "cella"))) == Action(verb="vai", direction="sud")


def test_a_room_the_player_does_not_know_is_not_understood(world):
    assert parse("vai nella cella", world, [], exits_to(world, ("ovest", None))) is None


def test_a_room_that_is_not_through_an_exit_is_not_understood(world):
    assert parse("vai nell'atrio", world, [], exits_to(world, ("ovest", "cella"))) is None


def test_every_significant_word_of_the_room_name_is_needed(world_data):
    world_data["rooms"]["cella"]["name"] = "Cella del conte"
    world = World.model_validate(world_data)
    exits = exits_to(world, ("ovest", "cella"))

    assert parse("vai nella cella del conte", world, [], exits) == Action(verb="vai", direction="ovest")
    assert parse("vai nella cella", world, [], exits) is None


# --- Talking to characters -----------------------------------------------------------------------


@pytest.fixture
def keeper(keeper_world) -> World:
    return World.model_validate(keeper_world)


def parse_near_keeper(world: World, text: str, topics: tuple[str, ...] = ("cella", "leva")):
    """The custode is here, and the player can ask about `topics`."""
    custode = world.characters["custode"]
    return parse(text, world, [], (), [(custode, [custode.topics[topic_id] for topic_id in topics])])


@pytest.mark.parametrize(
    "text", ["parla con il custode", "parla al guardiano", "saluta il vecchio", "parla", "saluta"]
)
def test_talking_to_a_character(keeper, text):
    assert parse_near_keeper(keeper, text) == Action(verb="parla", target="custode")


@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("chiedi al custode della cella", "cella"),
        ("domanda al guardiano della prigione", "cella"),
        ("chiedi al vecchio della leva", "leva"),
        ("chiedi della cella", "cella"),  # to the only character here
    ],
)
def test_asking_a_character_about_a_topic(keeper, text, topic):
    assert parse_near_keeper(keeper, text) == Action(verb="chiedi", target="custode", topic=topic)


@pytest.mark.parametrize(
    "text",
    [
        "chiedi al custode della chiave",  # a topic the player can't ask about yet
        "chiedi al custode del tempo",  # the LLM decides: unknown topic, or a way of naming a known one
        "chiedi al custode",
        "parla con il custode della cella",
    ],
)
def test_questions_without_a_known_topic_are_left_to_the_llm(keeper, text):
    assert parse_near_keeper(keeper, text) is None


def test_with_nobody_here_there_is_no_one_to_talk_to(keeper):
    assert parse("parla", keeper, [], (), []) is None
    assert parse("chiedi della cella", keeper, [], (), []) is None


def test_a_character_in_another_room_still_reaches_the_engine(keeper):
    assert parse("parla con il custode", keeper, [], (), []) == Action(verb="parla", target="custode")


def test_a_character_can_be_examined(keeper):
    assert parse_near_keeper(keeper, "esamina il custode") == Action(verb="esamina", target="custode")
    assert parse_near_keeper(keeper, "guarda il vecchio") == Action(verb="esamina", target="custode")


def test_two_characters_with_the_same_name_are_ambiguous(keeper_world):
    keeper_world["characters"]["eremita"] = {
        "name": "eremita",
        "gender": "m",
        "aliases": ["vecchio"],
        "description": "Un eremita.",
        "location": "atrio",
        "greeting": "«Pace.»",
        "unknown": "«Chissà.»",
    }
    world = World.model_validate(keeper_world)
    here = [(character, []) for character in world.characters.values()]

    parsed = parse("parla con il vecchio", world, [], (), here)

    assert parsed == Ambiguous((world.characters["custode"], world.characters["eremita"]))


# --- Giving ----------------------------------------------------------------------------------------


def parse_giving(world: World, text: str):
    """The custode is here and the player carries the coin."""
    return parse(text, world, [world.items["moneta"]], (), [(world.characters["custode"], [])])


@pytest.mark.parametrize(
    "text",
    [
        "dai la moneta al custode",
        "dà la moneta al guardiano",
        "porgi la moneta al vecchio",
        "offri il soldo al custode",
        "regala la moneta al custode",
        "consegna la moneta al custode",
    ],
)
def test_giving_an_item_to_a_character(keeper, text):
    assert parse_giving(keeper, text) == Action(verb="dai", target="moneta", with_="custode")


def test_the_character_may_come_first(keeper):
    assert parse_giving(keeper, "dai al custode la moneta") == Action(verb="dai", target="custode", with_="moneta")


def test_giving_without_naming_the_character_reaches_the_engine(keeper):
    assert parse_giving(keeper, "dai la moneta") == Action(verb="dai", target="moneta")


@pytest.mark.parametrize("text", ["dai un'occhiata alla leva", "dai una spinta alla moneta"])
def test_sayings_with_dai_are_left_to_the_llm(keeper, text):
    assert parse_giving(keeper, text) is None
