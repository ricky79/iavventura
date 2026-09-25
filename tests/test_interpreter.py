"""The LLM interpreter: player's sentence -> Action, with the model replaced by canned answers."""

import pytest

from app.engine.loader import load_world
from app.engine.models import Action, Item, World
from app.llm.client import FakeLLMClient
from app.llm.interpreter import interpret, interpreter_schema


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


def test_the_model_gets_a_fixed_system_prompt_and_the_items_with_the_sentence(in_reach):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}, {"verbo": "altro"}])

    interpret(fake, "cala il rampino nel pozzo", in_reach)
    interpret(fake, "saluta", in_reach[:1])

    (first_system, first_user), (second_system, second_user) = fake.calls
    assert first_system == second_system  # the fixed part comes first, so Ollama can cache it
    assert first_user == (
        "Oggetti: pozzo; porta della torre (porta, porta di ferro); portone; "
        "corda con gancio (corda, gancio, rampino)\n"
        "Frase: cala il rampino nel pozzo"
    )
    assert second_user == "Oggetti: pozzo\nFrase: saluta"


def test_no_items_in_reach(castle):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "salta", [])

    assert fake.calls[0][1] == "Oggetti: nessuno\nFrase: salta"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"},
         Action(verb="usa", target="corda_con_gancio", with_="pozzo")),
        ({"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}, Action(verb="spingi", target="portone")),
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


@pytest.mark.parametrize(
    "reply",
    [
        {"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "nessuno", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "nord", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "chiave di ferro", "con": "nessuno"},
        {"verbo": "vai", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": "vola", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": ["usa"], "bersaglio": {"x": 1}, "con": None},
        {},
    ],
    ids=["not an action", "no target", "direction as target", "item out of reach", "go to an item",
         "unknown verb", "wrong types", "empty"],
)  # fmt: skip
def test_replies_that_make_no_sense_are_not_understood(in_reach, reply):
    assert interpret(FakeLLMClient(json_replies=[reply]), "frase", in_reach) is None


def test_a_broken_model_means_not_understood(in_reach):
    assert interpret(FakeLLMClient(), "frase", in_reach) is None


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
