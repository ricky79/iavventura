"""The LLM interpreter: player's sentence -> Action, with the model replaced by canned answers."""

import pytest

from app.engine.loader import load_world
from app.engine.models import Action, Direction, Item, World
from app.llm.client import FakeLLMClient
from app.llm.interpreter import NotUnderstood, interpret, interpreter_schema
from app.llm.prompts import INTERPRETER_SYSTEM


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world()


@pytest.fixture
def in_reach(castle) -> list[Item]:
    return [castle.items[item_id] for item_id in ("pozzo", "porta_torre", "portone", "corda_con_gancio")]


def test_schema_limits_the_answer_to_known_verbs_items_in_reach_and_directions(in_reach):
    schema = interpreter_schema(in_reach)
    properties = schema["properties"]

    assert schema["required"] == ["verbo", "bersaglio", "con"]
    assert properties["verbo"]["enum"] == [
        "esamina", "prendi", "lascia", "usa", "apri", "chiudi", "spingi", "tira", "leggi",
        "vai", "guarda", "inventario", "altro",
    ]  # fmt: skip
    assert properties["bersaglio"]["enum"] == [
        "pozzo", "porta della torre", "portone", "corda con gancio",
        "nord", "sud", "est", "ovest", "su", "giù", "nessuno",
    ]  # fmt: skip
    assert properties["con"]["enum"] == ["pozzo", "porta della torre", "portone", "corda con gancio", "nessuno"]


def test_the_model_gets_a_fixed_system_prompt_then_items_exits_and_sentence(castle, in_reach):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}, {"verbo": "altro"}])
    rooms = castle.rooms

    exits = [(Direction.NORTH, rooms["torre"]), (Direction.EAST, rooms["scuderia"]), (Direction.WEST, rooms["cucina"])]
    interpret(fake, "cala il rampino nel pozzo", in_reach, exits)
    interpret(fake, "saluta", in_reach[:1], [(Direction.NORTH, None), (Direction.WEST, rooms["cucina"])])

    (first_system, first_user), (second_system, second_user) = fake.calls
    assert first_system == second_system  # the fixed part comes first, so Ollama can cache it
    assert first_user == (
        "Oggetti: pozzo; porta della torre (porta, porta di ferro); portone; "
        "corda con gancio (corda, fune, gancio, uncino, rampino)\n"
        "Uscite: nord (Torre), est (Scuderia), ovest (Cucina)\n"
        "Frase: cala il rampino nel pozzo"
    )
    assert second_user == "Oggetti: pozzo\nUscite: nord, ovest (Cucina)\nFrase: saluta"


def test_no_items_in_reach_and_no_exits(castle):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "salta", [])

    assert fake.calls[0][1] == "Oggetti: nessuno\nUscite: nessuna\nFrase: salta"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"},
         Action(verb="usa", target="corda_con_gancio", with_="pozzo")),
        ({"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}, Action(verb="spingi", target="portone")),
        ({"verbo": "lascia", "bersaglio": "corda con gancio", "con": "nessuno"},
         Action(verb="lascia", target="corda_con_gancio")),
        ({"verbo": "prendi", "bersaglio": "corda con gancio", "con": "corda con gancio"},
         Action(verb="prendi", target="corda_con_gancio")),
        ({"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}, Action(verb="vai", direction="nord")),
        ({"verbo": "vai", "bersaglio": "giù", "con": "nessuno"}, Action(verb="vai", direction="giù")),
        ({"verbo": "guarda", "bersaglio": "nessuno", "con": "nessuno"}, Action(verb="guarda")),
        ({"verbo": "guarda", "bersaglio": "pozzo", "con": "nessuno"}, Action(verb="esamina", target="pozzo")),
        ({"verbo": "inventario", "bersaglio": "nessuno", "con": "nessuno"}, Action(verb="inventario")),
    ],
)  # fmt: skip
def test_replies_become_actions_on_item_ids(in_reach, reply, expected):
    assert interpret(FakeLLMClient(json_replies=[reply]), "frase", in_reach) == expected


def test_the_model_may_say_the_sentence_is_not_a_game_action(in_reach):
    reply = {"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}

    result = interpret(FakeLLMClient(json_replies=[reply]), "che ore sono?", in_reach)

    assert result == NotUnderstood("la frase non è un'azione di gioco", not_an_action=True)


@pytest.mark.parametrize(
    "reply",
    [
        {"verbo": "prendi", "bersaglio": "nessuno", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "nord", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "chiave di ferro", "con": "nessuno"},
        {"verbo": "vai", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": "vola", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": ["usa"], "bersaglio": {"x": 1}, "con": None},
        {},
    ],
    ids=["no target", "direction as target", "item out of reach", "go to an item",
         "unknown verb", "wrong types", "empty"],
)  # fmt: skip
def test_replies_that_make_no_sense_are_not_understood(in_reach, reply):
    result = interpret(FakeLLMClient(json_replies=[reply]), "frase", in_reach)

    assert isinstance(result, NotUnderstood)
    assert not result.not_an_action


def test_a_broken_model_means_not_understood(in_reach):
    result = interpret(FakeLLMClient(), "frase", in_reach)

    assert result == NotUnderstood("il modello non ha dato una risposta valida")


# --- Log of how the answer was understood ---------------------------------------------------------


@pytest.mark.parametrize(
    ("reply", "logged"),
    [
        ({"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"},
         "=== azione: usa corda_con_gancio con pozzo"),
        ({"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}, "=== azione: spingi portone"),
        ({"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}, "=== azione: vai nord"),
        ({"verbo": "inventario", "bersaglio": "nessuno", "con": "nessuno"}, "=== azione: inventario"),
        ({"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"},
         "=== non capito: la frase non è un'azione di gioco"),
        ({"verbo": "vola", "bersaglio": "pozzo", "con": "nessuno"}, "=== non capito: verbo sconosciuto 'vola'"),
        ({"verbo": "vai", "bersaglio": "pozzo", "con": "nessuno"}, "=== non capito: direzione non valida 'pozzo'"),
        ({"verbo": "prendi", "bersaglio": "nessuno", "con": "nessuno"},
         "=== non capito: bersaglio non a portata 'nessuno'"),
    ],
)  # fmt: skip
def test_how_the_answer_was_understood_is_logged(in_reach, caplog, reply, logged):
    with caplog.at_level("INFO", logger="app.llm"):
        interpret(FakeLLMClient(json_replies=[reply]), "frase", in_reach)

    assert caplog.records[-1].getMessage() == logged


def test_a_broken_model_is_logged_as_not_understood(in_reach, caplog):
    with caplog.at_level("INFO", logger="app.llm"):
        interpret(FakeLLMClient(), "frase", in_reach)

    assert caplog.records[-1].getMessage() == "=== non capito: il modello non ha dato una risposta valida"


# --- The sentence with a purpose (bug found while playing) ------------------------------------------


def test_the_prompt_shows_a_sentence_with_a_purpose(castle):
    # Without this example qwen2.5:3b aimed the grapple at the door: "per recuperare la chiave" confused it.
    assert INTERPRETER_SYSTEM.endswith(
        "Frase: usa il rampino per recuperare la chiave dal pozzo\n"
        '{"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}'
    )


def test_the_grapple_sentence_becomes_fishing_in_the_well(castle, in_reach):
    near = [*in_reach, castle.items["chiave_torre"]]
    fake = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}])

    action = interpret(fake, "usa il rampino per recuperare la chiave dal pozzo", near)

    assert action == Action(verb="usa", target="pozzo", with_="corda_con_gancio")
    assert fake.calls[0][1].startswith("Oggetti: pozzo; porta della torre (porta, porta di ferro); portone; ")
    assert "; chiave di ferro (chiave)\n" in fake.calls[0][1]


# --- Throwing one thing into another (bug found while playing) -------------------------------------


def test_dropping_one_thing_into_another_is_using_them_together(in_reach):
    # "butta il rampino nel pozzo": qwen2.5:3b answers "lascia" with both items, even with "buttare"
    # moved under "usa" in the glossary. Dropping needs no second item: the two go together.
    fake = FakeLLMClient(json_replies=[{"verbo": "lascia", "bersaglio": "pozzo", "con": "corda con gancio"}])

    action = interpret(fake, "butta il rampino nel pozzo", in_reach)

    assert action == Action(verb="usa", target="pozzo", with_="corda_con_gancio")
