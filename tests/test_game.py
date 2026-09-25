"""A game turn: parser first, then the LLM interpreter, the engine, and the narration."""

import pytest

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import World
from app.game import HELP, NOT_UNDERSTOOD, Game
from app.llm.client import FakeLLMClient, LLMError


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world()


def say(game: Game, line: str) -> str:
    return "".join(game.turn(line))


def test_a_free_sentence_goes_through_the_llm_interpreter(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"

    output = say(game, "cala il rampino giù nel pozzo")

    assert output.startswith("(usa la corda con gancio con il pozzo)\n")
    assert output.endswith(castle.rules["pesca_chiave"].text)
    assert game.state.item_locations["chiave_torre"] == "inventory"


def test_opening_shows_intro_and_first_room(castle):
    opening = Game(Engine(castle)).opening()

    assert opening.startswith("La bufera ti ha sorpreso")
    assert opening.endswith("Uscite: nord, est, ovest.")


def test_simple_commands_never_reach_the_llm(castle):
    llm = FakeLLMClient()
    game = Game(Engine(castle), llm)

    assert say(game, "nord") == "La porta della torre è chiusa a chiave."
    assert say(game, "apri il portone").startswith("Spingi, tiri, dai una spallata")
    assert say(game, "aiuto") == HELP
    assert say(game, "   ") == ""
    assert llm.calls == []


def test_without_llm_a_free_sentence_is_not_understood(castle):
    assert say(Game(Engine(castle)), "cala il rampino giù nel pozzo") == NOT_UNDERSTOOD


@pytest.mark.parametrize(
    "llm",
    [FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}]), FakeLLMClient()],
    ids=["not an action", "broken model"],
)
def test_when_the_llm_cannot_interpret_the_sentence_is_not_understood(castle, llm):
    game = Game(Engine(castle), llm)

    assert say(game, "che bella giornata") == NOT_UNDERSTOOD
    assert game.state.turns == 0


def test_ambiguous_names_get_a_question_without_asking_the_llm(world_data):
    world_data["items"]["moneta_antica"] = {
        "name": "moneta antica",
        "gender": "f",
        "aliases": ["moneta"],
        "description": "Una moneta antica.",
        "location": "atrio",
    }
    llm = FakeLLMClient()

    output = say(Game(Engine(World.model_validate(world_data)), llm), "esamina la moneta")

    assert output == "Quale intendi: la moneta o la moneta antica?"
    assert llm.calls == []


# --- Narration -----------------------------------------------------------------------------------


def test_generic_replies_are_told_by_the_narrator(castle):
    llm = FakeLLMClient(text_replies=["Il pozzo è di pietra massiccia: non puoi portarlo via."])

    output = say(Game(Engine(castle), llm), "prendi il pozzo")

    assert output == "Il pozzo è di pietra massiccia: non puoi portarlo via."


def test_an_interpreted_sentence_with_a_generic_reply_uses_both(castle):
    llm = FakeLLMClient(
        json_replies=[{"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}],
        text_replies=["Il portone non si muove."],
    )

    output = say(Game(Engine(castle), llm), "dai una spinta al portone")

    assert output == "(spingi il portone)\nIl portone non si muove."


def test_without_llm_generic_replies_stay_fixed(castle):
    assert say(Game(Engine(castle)), "prendi il pozzo") == "Non si può prendere."


def test_a_broken_narrator_falls_back_on_the_fixed_text(castle):
    assert say(Game(Engine(castle), FakeLLMClient()), "prendi il pozzo") == "Non si può prendere."


class _NarratorBreakingMidway(FakeLLMClient):
    def stream_text(self, system, user, max_tokens, temperature):
        yield "Il pozzo "
        raise LLMError("connection lost")


def test_a_narrator_breaking_midway_is_followed_by_the_fixed_text(castle):
    output = say(Game(Engine(castle), _NarratorBreakingMidway()), "prendi il pozzo")

    assert output == "Il pozzo \nNon si può prendere."


def test_an_empty_narration_falls_back_on_the_fixed_text(castle):
    assert say(Game(Engine(castle), FakeLLMClient(text_replies=[""])), "prendi il pozzo") == "Non si può prendere."


def test_the_ending_follows_the_narration(world_data):
    world_data["items"]["candela"] = {"name": "candela", "gender": "f", "description": "-", "location": "atrio"}
    world_data["game"]["endings"].insert(0, {"when": {"has": "candela"}, "text": "Ora hai la luce. Fine."})
    game = Game(Engine(World.model_validate(world_data)), FakeLLMClient(text_replies=["Prendi la candela."]))

    output = say(game, "prendi la candela")

    assert output == "Prendi la candela.\n\nOra hai la luce. Fine."
    assert game.finished
