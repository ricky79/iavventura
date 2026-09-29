"""Fixed text: Italian articles and the rendering of an Outcome."""

import pytest

from app.engine.models import Action, Article, Direction, Item, Outcome, RoomView, World
from app.engine.text import action_text, articulated, confirmation, definite, indefinite, join, render, which_one


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


# --- How an action reads (shown when the LLM interpreted the sentence) ---------------------------


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (Action(verb="prendi", target="corda"), "prendi la corda"),
        (Action(verb="usa", target="corda", with_="gancio"), "usa la corda con il gancio"),
        (Action(verb="vai", direction="nord"), "vai a nord"),
        (Action(verb="vai", direction="su"), "vai su"),
        (Action(verb="vai", direction="giù"), "vai giù"),
        (Action(verb="guarda"), "guarda"),
        (Action(verb="inventario"), "inventario"),
        (Action(verb="salta", target="gancio"), "salta nel gancio"),
    ],
)
def test_actions_read_as_commands(world, action, expected):
    assert action_text(action, world) == expected


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (Action(verb="usa", target="corda", with_="gancio"), "Vuoi usare la corda con il gancio?"),
        (Action(verb="spingi", target="gancio"), "Vuoi spingere il gancio?"),
        (Action(verb="leggi", target="corda"), "Vuoi leggere la corda?"),
        (Action(verb="apri", target="gancio", with_="corda"), "Vuoi aprire il gancio con la corda?"),
        (Action(verb="vai", direction="ovest"), "Vuoi andare a ovest?"),
        (Action(verb="vai", direction="giù"), "Vuoi andare giù?"),
        (Action(verb="salta", target="corda"), "Vuoi saltare nella corda?"),
    ],
)
def test_an_unexpected_action_is_asked_as_a_question(world, action, expected):
    assert confirmation(action, world) == expected


# --- Characters ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "gender", "plural", "to_the", "of_the", "in_the"),
    [
        ("gancio", "m", False, "al gancio", "del gancio", "nel gancio"),
        ("specchio", "m", False, "allo specchio", "dello specchio", "nello specchio"),
        ("uncino", "m", False, "all'uncino", "dell'uncino", "nell'uncino"),
        ("corda", "f", False, "alla corda", "della corda", "nella corda"),
        ("ascia", "f", False, "all'ascia", "dell'ascia", "nell'ascia"),
        ("sassi", "m", True, "ai sassi", "dei sassi", "nei sassi"),
        ("attrezzi", "m", True, "agli attrezzi", "degli attrezzi", "negli attrezzi"),
        ("chiavi", "f", True, "alle chiavi", "delle chiavi", "nelle chiavi"),
    ],
)
def test_prepositions_join_the_article(name, gender, plural, to_the, of_the, in_the):
    assert articulated("a", item(name, gender, plural)) == to_the
    assert articulated("di", item(name, gender, plural)) == of_the
    assert articulated("in", item(name, gender, plural)) == in_the


@pytest.mark.parametrize(
    ("name", "gender", "article", "the", "a", "to_the", "of_the"),
    [
        ("Ettore", "m", "none", "Ettore", "Ettore", "a Ettore", "di Ettore"),
        ("Livia", "f", "none", "Livia", "Livia", "a Livia", "di Livia"),
        ("dottor Ferri", "m", "definite", "il dottor Ferri", "il dottor Ferri", "al dottor Ferri", "del dottor Ferri"),
        ("Stella di Valdimora", "f", "definite", "la Stella di Valdimora", "la Stella di Valdimora",
         "alla Stella di Valdimora", "della Stella di Valdimora"),
    ],
)  # fmt: skip
def test_proper_names_take_their_own_article(name, gender, article, the, a, to_the, of_the):
    proper = Item(id="nome", name=name, gender=gender, article=Article(article), description="-", location=None)

    assert (definite(proper), indefinite(proper)) == (the, a)
    assert (articulated("a", proper), articulated("di", proper)) == (to_the, of_the)


@pytest.fixture
def keeper(keeper_world) -> World:
    keeper_world["characters"]["cuoca"] = {
        "name": "cuoca",
        "gender": "f",
        "description": "Una cuoca.",
        "location": "cella",
        "greeting": "«Ciao.»",
        "unknown": "«Boh.»",
    }
    return World.model_validate(keeper_world)


def test_room_shows_the_characters_after_the_description(keeper):
    view = room(items=("moneta",), exits=(Direction.NORTH,)).model_copy(update={"characters": ("custode",)})

    assert render(Outcome(ok=True, room=view), keeper) == (
        "Atrio\n"
        "Un atrio spoglio.\n"
        "Qui c'è un custode.\n"
        "Qui vedi una moneta.\n"
        "Uscita: nord."
    )


def test_room_with_two_characters(keeper):
    view = room().model_copy(update={"characters": ("custode", "cuoca")})

    assert render(Outcome(ok=True, room=view), keeper) == "Atrio\nUn atrio spoglio.\nQui ci sono un custode e una cuoca."


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (Action(verb="parla", target="custode"), "parla con il custode"),
        (Action(verb="chiedi", target="custode", topic="cella"), "chiedi al custode della cella"),
        (Action(verb="chiedi", target="custode"), "chiedi al custode"),
        (Action(verb="esamina", target="custode"), "esamina il custode"),
        (Action(verb="usa", target="moneta", with_="custode"), "usa la moneta con il custode"),
        (Action(verb="dai", target="moneta", with_="custode"), "dai la moneta al custode"),
        (Action(verb="dai", target="custode", with_="moneta"), "dai la moneta al custode"),
        (Action(verb="dai", target="moneta"), "dai la moneta"),
    ],
)
def test_actions_on_characters_read_as_commands(keeper, action, expected):
    assert action_text(action, keeper) == expected


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (Action(verb="usa", target="moneta", with_="custode"), "Vuoi usare la moneta con il custode?"),
        (Action(verb="parla", target="cuoca"), "Vuoi parlare con la cuoca?"),
        (Action(verb="chiedi", target="custode", topic="leva"), "Vuoi chiedere al custode della leva?"),
        (Action(verb="dai", target="moneta", with_="custode"), "Vuoi dare la moneta al custode?"),
    ],
)
def test_actions_on_characters_are_asked_as_questions(keeper, action, expected):
    assert confirmation(action, keeper) == expected


def test_characters_with_a_proper_name(keeper_world):
    keeper_world["characters"]["custode"].update(name="Ettore", article="none")
    keeper_world["characters"]["custode"]["topics"]["cella"].update(name="Livia", article="none")
    world = World.model_validate(keeper_world)

    here = render(Outcome(ok=True, room=room_with(world, "custode")), world)

    assert "Qui c'è Ettore." in here
    assert action_text(Action(verb="chiedi", target="custode", topic="cella"), world) == "chiedi a Ettore di Livia"
    assert confirmation(Action(verb="dai", target="moneta", with_="custode"), world) == "Vuoi dare la moneta a Ettore?"


def test_a_title_is_always_definite(keeper_world):
    keeper_world["characters"]["custode"].update(name="dottor Ferri", article="definite")
    world = World.model_validate(keeper_world)

    here = render(Outcome(ok=True, room=room_with(world, "custode")), world)

    assert "Qui c'è il dottor Ferri." in here
    assert action_text(Action(verb="parla", target="custode"), world) == "parla con il dottor Ferri"


def room_with(world: World, *characters: str) -> RoomView:
    return RoomView(id="atrio", name="Atrio", description="Un atrio.", items=(), exits=(), first_visit=True,
                    characters=characters)  # fmt: skip
