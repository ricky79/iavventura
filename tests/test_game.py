"""A game turn: parser first, then the LLM interpreter, the engine and the fixed text."""

import pytest

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import World
from app.game import HELP, NOT_UNDERSTOOD, Game
from app.llm.client import FakeLLMClient


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world()


def say(game: Game, line: str) -> str:
    return game.turn(line)


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


def test_an_interpreted_sentence_is_shown_before_the_answer(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}])

    output = say(Game(Engine(castle), llm), "dai una spinta al portone")

    assert output == "(spingi il portone)\nNon succede niente."


def test_going_to_a_named_room_needs_no_llm(castle):
    llm = FakeLLMClient()
    game = Game(Engine(castle), llm)

    output = say(game, "vai in cucina")

    assert output.startswith("Cucina\n")
    assert game.state.current_room == "cucina"
    assert llm.calls == []


def test_the_llm_is_told_where_the_exits_lead(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": "est", "con": "nessuno"}])
    game = Game(Engine(castle), llm)

    output = say(game, "torno di corsa nella scuderia")

    assert "\nUscite: nord (Torre), est (Scuderia), ovest (Cucina)\n" in llm.calls[0][1]
    assert output.startswith("(vai a est)\nScuderia\n")


def test_a_game_can_go_on_from_a_saved_state(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    state.current_room = "cucina"
    state.visited.add("cucina")

    game = Game(engine, state=state)

    assert say(game, "est").startswith("Cortile\n")
    assert game.state is state


def test_only_a_new_game_has_an_opening(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()

    with pytest.raises(ValueError):
        Game(engine, state=state).opening()
