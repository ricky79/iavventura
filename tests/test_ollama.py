"""The real model on the sample castle: skipped unless OLLAMA_TESTS=1 (needs Ollama running).

    $env:OLLAMA_TESTS=1; .venv\\Scripts\\python -m pytest tests/test_ollama.py -v -s

Each sentence is interpreted, then executed by the engine: the test checks the effect on the game,
so equivalent actions ("apri la porta con la chiave" / "usa la chiave con la porta") both pass.
With -s it also prints how long each call took.
"""

import os
import time

import pytest

from app.config import Settings, make_client
from app.engine.engine import Engine
from app.engine.loader import load_world
from app.engine.models import Action, GameState, Item
from app.game import Game
from app.llm.interpreter import NotUnderstood, interpret

pytestmark = pytest.mark.skipif(os.environ.get("OLLAMA_TESTS") != "1", reason="needs Ollama: set OLLAMA_TESTS=1")

CASTLE = load_world()
RULE = {rule_id: rule.text for rule_id, rule in CASTLE.rules.items()}


@pytest.fixture(scope="module")
def llm():
    client = make_client(Settings.from_env())
    if client is None or (reason := client.unavailable_reason()):
        pytest.skip(f"LLM not available: {reason if client else 'LLM=off'}")
    return client


def near(engine: Engine, state: GameState) -> list[Item]:
    """What the game passes to the interpreter: items in reach, then those in sight."""
    return engine.in_reach(state) + engine.visible(state)


def game_in(room: str, *carried: str) -> tuple[Engine, GameState]:
    engine = Engine(CASTLE)
    state, _ = engine.new_game()
    state.current_room = room
    for item_id in carried:
        state.item_locations[item_id] = "inventory"
    if "corda_con_gancio" in carried:
        state.item_locations["corda"] = state.item_locations["gancio"] = None
    return engine, state


CASES = [
    # (room, carried items, sentence, check on (outcome, state))
    ("cucina", (), "raccogli quel vecchio gancio", lambda o, s: s.item_locations["gancio"] == "inventory"),
    ("scuderia", ("gancio",), "lega la corda al gancio", lambda o, s: o.text == RULE["lega_gancio"]),
    ("cortile", ("corda_con_gancio",), "cala il rampino giù nel pozzo", lambda o, s: o.text == RULE["pesca_chiave"]),
    ("cortile", ("chiave_torre",), "provo ad aprire la porta usando la chiave", lambda o, s: o.text == RULE["apri_torre"]),
    ("cortile", (), "dai un'occhiata al pozzo", lambda o, s: o.text == CASTLE.items["pozzo"].description),
    ("cortile", (), "torna verso ovest", lambda o, s: s.current_room == "cucina"),
    ("cortile", ("corda",), "metti giù la corda", lambda o, s: s.item_locations["corda"] == "cortile"),
    ("cortile", ("corda",), "cosa ho con me?", lambda o, s: o.inventory == ("corda",)),
    ("cortile", (), "vado in cucina", lambda o, s: s.current_room == "cucina"),
    ("cortile", (), "torno di corsa nella scuderia", lambda o, s: s.current_room == "scuderia"),
]


@pytest.mark.parametrize(("room", "carried", "sentence", "check"), CASES, ids=[case[2] for case in CASES])
def test_free_sentences_become_the_right_action(llm, room, carried, sentence, check):
    engine, state = game_in(room, *carried)

    start = time.perf_counter()
    action = interpret(llm, sentence, near(engine, state), engine.known_exits(state))
    print(f"\n  {time.perf_counter() - start:4.1f}s  {sentence!r} -> {action}")

    assert isinstance(action, Action)
    assert check(engine.execute(state, action), state)


# The bug found while playing: a sentence with a purpose. The player had examined the well,
# so the key was in sight at the bottom of it.
PURPOSE = [
    "usa il rampino per recuperare la chiave dal pozzo",
    "provo a ripescare la chiave nel pozzo col rampino",
    "recupera la chiave dal pozzo con il rampino",
]


@pytest.mark.parametrize("sentence", PURPOSE)
def test_the_grapple_fishes_the_key_seen_in_the_well(llm, sentence):
    engine, state = game_in("cortile", "corda_con_gancio")
    engine.execute(state, Action(verb="esamina", target="pozzo"))

    start = time.perf_counter()
    action = interpret(llm, sentence, near(engine, state), engine.known_exits(state))
    print(f"\n  {time.perf_counter() - start:4.1f}s  {sentence!r} -> {action}")

    assert isinstance(action, Action)
    assert engine.execute(state, action).text == RULE["pesca_chiave"]


@pytest.mark.parametrize("sentence", ["ciao, come stai?", "che tempo farà domani?"])
def test_small_talk_is_not_understood(llm, sentence):
    engine, state = game_in("cortile")

    assert isinstance(interpret(llm, sentence, near(engine, state), engine.known_exits(state)), NotUnderstood)


def test_an_unknown_place_does_not_move_the_player(llm):
    engine, state = game_in("cortile")
    game = Game(engine, llm, state=state)

    answer = game.turn("vado nella cantina")
    print(f"\n  'vado nella cantina' -> {answer!r}")

    assert state.current_room == "cortile"

