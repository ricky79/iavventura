"""Fixed text: Italian articles and the rendering of an Outcome."""

import pytest

from app.engine.models import Direction, Item, Outcome, RoomView, World
from app.engine.text import definite, indefinite, join, render, which_one


def item(name: str, gender: str = "m", plural: bool = False) -> Item:
    return Item(id="oggetto", name=name, gender=gender, plural=plural, description="Un oggetto.", location=None)


@pytest.mark.parametrize(
    ("name", "gender", "plural", "the", "a"),
    [
        ("gancio da macellaio", "m", False, "il gancio da macellaio", "un gancio da macellaio"),
        ("corda", "f", False, "la corda", "una corda"),
        ("uncino", "m", False, "l'uncino", "un uncino"),
        ("ascia", "f", False, "l'ascia", "un'ascia"),
        ("specchio", "m", False, "lo specchio", "uno specchio"),
        ("zaino", "m", False, "lo zaino", "uno zaino"),
        ("gnomo", "m", False, "lo gnomo", "uno gnomo"),
        ("pneumatico", "m", False, "lo pneumatico", "uno pneumatico"),
        ("iodio", "m", False, "lo iodio", "uno iodio"),
        ("stella", "f", False, "la stella", "una stella"),
        ("zucca", "f", False, "la zucca", "una zucca"),
        ("sassi", "m", True, "i sassi", "dei sassi"),
        ("attrezzi", "m", True, "gli attrezzi", "degli attrezzi"),
        ("specchi", "m", True, "gli specchi", "degli specchi"),
        ("chiavi", "f", True, "le chiavi", "delle chiavi"),
        ("armi", "f", True, "le armi", "delle armi"),
        ("Orologio", "m", False, "l'Orologio", "un Orologio"),
    ],
)
def test_articles_follow_gender_number_and_first_letters(name, gender, plural, the, a):
    assert definite(item(name, gender, plural)) == the
    assert indefinite(item(name, gender, plural)) == a


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (["una corda"], "una corda"),
        (["una corda", "un gancio"], "una corda e un gancio"),
        (["una corda", "un gancio", "una chiave"], "una corda, un gancio e una chiave"),
    ],
)
def test_join_lists_words_the_italian_way(words, expected):
    assert join(words) == expected


def test_join_can_use_another_conjunction():
    assert join(["la corda", "il gancio", "la chiave"], "o") == "la corda, il gancio o la chiave"


def test_which_one_asks_among_the_candidates():
    candidates = [item("corda", "f"), item("corda con gancio", "f")]

    assert which_one(candidates) == "Quale intendi: la corda o la corda con gancio?"


# --- Rendering an outcome ---------------------------------------------------------------


@pytest.fixture
def world(world_data) -> World:
    world_data["items"]["corda"] = {"name": "corda", "gender": "f", "description": "Una corda.", "location": "atrio"}
    world_data["items"]["gancio"] = {"name": "gancio", "gender": "m", "description": "Un gancio.", "location": "atrio"}
    return World.model_validate(world_data)


def room(items: tuple[str, ...] = (), exits: tuple[Direction, ...] = ()) -> RoomView:
    return RoomView(
        id="atrio", name="Atrio", description="Un atrio spoglio.", items=items, exits=exits, first_visit=True
    )


def test_plain_text_is_shown_as_it_is(world):
    assert render(Outcome(ok=True, text="Fatto."), world) == "Fatto."


def test_room_shows_name_description_items_and_exits_in_compass_order(world):
    outcome = Outcome(
        ok=True,
        room=room(items=("corda", "gancio"), exits=(Direction.WEST, Direction.NORTH, Direction.DOWN, Direction.EAST)),
    )

    assert render(outcome, world) == (
        "Atrio\n"
        "Un atrio spoglio.\n"
        "Qui vedi una corda e un gancio.\n"
        "Uscite: nord, est, ovest, giù."
    )


def test_room_without_items_and_with_a_single_exit(world):
    outcome = Outcome(ok=True, room=room(exits=(Direction.SOUTH,)))

    assert render(outcome, world) == "Atrio\nUn atrio spoglio.\nUscita: sud."


def test_room_without_exits_has_no_exit_line(world):
    assert render(Outcome(ok=True, room=room()), world) == "Atrio\nUn atrio spoglio."


def test_inventory_lists_what_the_player_carries(world):
    outcome = Outcome(ok=True, inventory=("gancio", "moneta"))

    assert render(outcome, world) == "Hai con te un gancio e una moneta."


def test_empty_inventory(world):
    assert render(Outcome(ok=True, inventory=()), world) == "Non hai niente con te."


def test_text_room_and_ending_are_separate_paragraphs(world):
    outcome = Outcome(ok=True, text="Entri.", room=room(), ending="Hai vinto.")

    assert render(outcome, world) == "Entri.\n\nAtrio\nUn atrio spoglio.\n\nHai vinto."
