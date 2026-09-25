"""The LLM narrator: retells a generic engine reply from the facts only."""

import pytest

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import Action, GameState, World
from app.llm.client import FakeLLMClient, LLMError
from app.llm.narrator import narrate


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world()


@pytest.fixture
def state(castle) -> GameState:
    state, _ = Engine(castle).new_game()
    return state


def test_the_narration_streams_what_the_model_writes(castle, state):
    fake = FakeLLMClient(text_replies=["Il pozzo è di pietra massiccia: non puoi portarlo via."])
    action = Action(verb="prendi", target="pozzo")
    outcome = Engine(castle).execute(state, action)

    pieces = list(narrate(fake, castle, state, action, outcome))

    assert len(pieces) > 1
    assert "".join(pieces) == "Il pozzo è di pietra massiccia: non puoi portarlo via."


def test_the_model_gets_place_action_items_and_outcome(castle, state):
    fake = FakeLLMClient(text_replies=["..."])
    action = Action(verb="prendi", target="pozzo")
    outcome = Engine(castle).execute(state, action)

    list(narrate(fake, castle, state, action, outcome))

    assert fake.calls[0][2] == (
        "Luogo: Cortile\n"
        "Azione: prendi il pozzo\n"
        f"pozzo: {castle.items['pozzo'].description}\n"
        "Esito: Non si può prendere. L'azione non riesce."
    )


def test_both_items_are_described_as_they_are_now(castle, state):
    fake = FakeLLMClient(text_replies=["..."])
    state.flags.add("chiave_pescata")
    state.item_locations["corda_con_gancio"] = "inventory"
    action = Action(verb="spingi", target="pozzo", with_="corda_con_gancio")
    outcome = Engine(castle).execute(state, action)

    list(narrate(fake, castle, state, action, outcome))

    assert fake.calls[0][2] == (
        "Luogo: Cortile\n"
        "Azione: spingi il pozzo con la corda con gancio\n"
        "pozzo: Un pozzo asciutto e profondo. Sul fondo restano solo sassi e foglie secche.\n"
        f"corda con gancio: {castle.items['corda_con_gancio'].description}\n"
        "Esito: Non succede niente. L'azione non riesce."
    )


def test_a_successful_action_is_stated_as_such(castle, state):
    fake = FakeLLMClient(text_replies=["..."])
    state.item_locations["corda_con_gancio"] = "inventory"
    action = Action(verb="lascia", target="corda_con_gancio")
    outcome = Engine(castle).execute(state, action)

    list(narrate(fake, castle, state, action, outcome))

    assert fake.calls[0][2].endswith("Esito: Fatto. L'azione riesce.")


def test_the_system_prompt_is_the_same_every_time(castle, state):
    fake = FakeLLMClient(text_replies=["...", "..."])
    engine = Engine(castle)
    for action in (Action(verb="prendi", target="pozzo"), Action(verb="apri", target="pozzo")):
        list(narrate(fake, castle, state, action, engine.execute(state, action)))

    assert fake.calls[0][1] == fake.calls[1][1]


def test_a_broken_model_raises_so_the_game_can_fall_back(castle, state):
    action = Action(verb="prendi", target="pozzo")
    outcome = Engine(castle).execute(state, action)

    with pytest.raises(LLMError):
        list(narrate(FakeLLMClient(), castle, state, action, outcome))
