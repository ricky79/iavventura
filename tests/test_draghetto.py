"""Il draghetto raffreddato, the adventure for kids: invariants of its puzzles, then the game played
through the engine and with typed commands.

Chain: berries -> the bear gives the honey; the branch knocks the feather out of the nest; honey to
the dragon (its throat), then the feather (a sneeze) -> its fire is back and the game ends.
"""

import re

import pytest

from app.engine import engine as messages
from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Direction, GameState, World
from app.game import Game
from app.llm.client import FakeLLMClient


@pytest.fixture(scope="module")
def dragon() -> World:
    return load_world(WORLDS_DIR / "draghetto")


def start(world: World) -> tuple[Engine, GameState]:
    engine = Engine(world)
    state, _ = engine.new_game()
    return engine, state


def play(engine: Engine, state: GameState, actions: list[Action]) -> None:
    for action in actions:
        outcome = engine.execute(state, action)
        assert outcome.ok, f"{action} was refused: {outcome.text}"


# From the clearing: berries, branch, the bear's honey; back in the clearing with both.
TO_THE_HONEY = [
    Action(verb="vai", direction="est"),
    Action(verb="prendi", target="more"),
    Action(verb="vai", direction="ovest"),
    Action(verb="vai", direction="ovest"),
    Action(verb="prendi", target="ramo"),
    Action(verb="vai", direction="ovest"),
    Action(verb="dai", target="more", with_="orso"),
    Action(verb="vai", direction="est"),
    Action(verb="vai", direction="est"),
]
# From the clearing: the feather from the nest, and back.
TO_THE_FEATHER = [
    Action(verb="vai", direction="nord"),
    Action(verb="usa", target="ramo", with_="nido"),
    Action(verb="vai", direction="sud"),
]
HONEY = Action(verb="dai", target="vasetto_miele", with_="draghetto")
FEATHER = Action(verb="dai", target="piuma", with_="draghetto")


# --- Invariants ----------------------------------------------------------------------------------


def test_five_places_around_the_clearing(dragon):
    assert dragon.game.start_room == "radura"
    exits = dragon.rooms["radura"].exits
    assert {exits[d].to for d in (Direction.NORTH, Direction.EAST, Direction.WEST)} == {"quercia", "roveto", "ruscello"}
    assert dragon.rooms["ruscello"].exits[Direction.WEST].to == "tana"


def test_the_dragon_and_the_bear_only_give_hints(dragon):
    assert dragon.characters["draghetto"].location == "radura"
    assert dragon.characters["orso"].location == "tana"
    # No topic changes the game: talking can't open a shortcut.
    for character in dragon.characters.values():
        assert all(topic.effects == () for topic in character.topics.values())


def test_no_item_is_called_fuoco(dragon):
    # "dai fuoco a…" would become giving.
    assert all("fuoco" not in (item.name, *item.aliases) for item in dragon.items.values())


# --- Playing through the engine ----------------------------------------------------------------


def test_the_whole_game_can_be_played_to_the_end(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + TO_THE_FEATHER + [HONEY])

    last = engine.execute(state, FEATHER)

    assert last.text == dragon.rules["solletico"].text
    assert last.ending == dragon.game.endings[0].text
    assert state.finished


def test_the_feather_before_the_honey_is_only_a_hint(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + TO_THE_FEATHER)

    early = engine.execute(state, FEATHER)

    assert not early.ok
    assert early.text == dragon.rules["solletico"].otherwise
    assert state.item_locations["piuma"] == "inventory"
    assert not state.finished


@pytest.mark.parametrize(
    ("looked", "action"),
    [
        (False, Action(verb="usa", target="ramo", with_="nido")),
        (False, Action(verb="usa", target="ramo", with_="quercia")),
        (True, Action(verb="usa", target="ramo", with_="piuma")),
        (True, Action(verb="prendi", target="piuma", with_="ramo")),
        (False, Action(verb="tira", target="nido", with_="ramo")),
        (False, Action(verb="spingi", target="nido", with_="ramo")),
        (True, Action(verb="tira", target="piuma", with_="ramo")),
        (True, Action(verb="spingi", target="piuma", with_="ramo")),
    ],
    ids=["branch on the nest", "branch on the tree", "branch on the feather", "take the feather with the branch",
         "pull the nest with the branch", "push the nest with the branch",
         "pull the feather with the branch", "push the feather with the branch"],
)  # fmt: skip
def test_every_way_of_knocking_the_feather_down_works(dragon, looked, action):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + [Action(verb="vai", direction="nord")])
    if looked:
        play(engine, state, [Action(verb="esamina", target="nido")])

    outcome = engine.execute(state, action)

    assert outcome.text == dragon.rules["stacca_piuma"].text
    assert state.item_locations["piuma"] == "inventory"


def test_the_feather_has_to_be_seen_before_it_can_be_named(dragon):
    engine, state = start(dragon)
    play(engine, state, [Action(verb="vai", direction="nord")])

    unseen = engine.execute(state, Action(verb="prendi", target="piuma"))
    engine.execute(state, Action(verb="esamina", target="nido"))
    seen = engine.execute(state, Action(verb="prendi", target="piuma"))

    assert unseen.text == messages.NOT_HERE
    assert seen.text == messages.OUT_OF_REACH


def test_the_way_home_and_the_top_of_the_tree_stay_closed(dragon):
    engine, state = start(dragon)

    home = engine.execute(state, Action(verb="vai", direction="sud"))
    engine.execute(state, Action(verb="vai", direction="nord"))
    climb = engine.execute(state, Action(verb="vai", direction="su"))

    assert home.text == dragon.rooms["radura"].exits[Direction.SOUTH].otherwise
    assert climb.text == dragon.rooms["quercia"].exits[Direction.UP].otherwise
    assert state.current_room == "quercia"


def test_the_berries_can_be_dropped_and_taken_again(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:3])

    play(engine, state, [Action(verb="lascia", target="more"), Action(verb="prendi", target="more")])

    assert state.item_locations["more"] == "inventory"


@pytest.mark.parametrize(
    ("before", "gift", "rule"),
    [
        (TO_THE_HONEY[:3], Action(verb="dai", target="more", with_="draghetto"), "more_al_drago"),
        (TO_THE_HONEY[:7], Action(verb="dai", target="vasetto_miele", with_="orso"), "miele_all_orso"),
    ],
    ids=["berries to the dragon", "honey to the bear"],
)
def test_the_wrong_gift_gets_a_hint_and_changes_nothing(dragon, before, gift, rule):
    engine, state = start(dragon)
    play(engine, state, before)
    carried = gift.target
    before_gift = state.model_dump(exclude={"turns"})

    outcome = engine.execute(state, gift)

    assert outcome.text == dragon.rules[rule].text
    assert state.model_dump(exclude={"turns"}) == before_gift
    assert state.item_locations[carried] == "inventory"


def test_the_bear_remembers_the_trade(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:6])
    ask = Action(verb="chiedi", target="orso", topic="miele")

    before = engine.execute(state, ask).text
    play(engine, state, [TO_THE_HONEY[6]])
    after = engine.execute(state, ask).text

    topic = dragon.characters["orso"].topics["miele"]
    assert before == topic.text
    assert after == topic.variants[0].text


def test_the_bear_greets_differently_after_the_trade(dragon):
    # Found while playing: after the trade the bear still said «Grrr… chi va là?».
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:6])
    talk = Action(verb="parla", target="orso")

    before = engine.execute(state, talk).text
    play(engine, state, [TO_THE_HONEY[6]])
    after = engine.execute(state, talk).text

    bear = dragon.characters["orso"]
    assert before == bear.greeting
    assert after == bear.greeting_variants[0].text
    assert "chi va là" not in after


# --- Typed commands ------------------------------------------------------------------------------

TYPED = [
    "est",
    "prendi le more",
    "ovest",
    "ovest",
    "prendi il ramo",
    "ovest",
    "dai le more all'orso",
    "est",
    "est",
    "nord",
    "esamina il nido",
    "usa il ramo con il nido",
    "sud",
    "dai il miele al draghetto",
    "dai la piuma al draghetto",
]


def test_a_kid_can_finish_with_simple_commands(dragon):
    game = Game(Engine(dragon))
    outputs = [game.turn(line) for line in TYPED]

    assert outputs[6].startswith(dragon.rules["scambia_more"].text)
    assert outputs[-1].endswith(dragon.game.endings[0].text)
    assert game.finished


# --- What a kid meets while playing (found by the review) ---------------------------------------


def test_the_bush_does_not_promise_berries_that_are_gone(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:2])

    room = engine.execute(state, Action(verb="guarda")).room.description
    bush = engine.execute(state, Action(verb="esamina", target="cespugli")).text

    assert "more mature" not in room
    assert "more mature" not in bush


def test_the_greeting_says_what_to_ask_about(dragon):
    # "come posso aiutarti?" gets the greeting: it has to name a topic, not answer with a question.
    dragonet = dragon.characters["draghetto"]

    invitation = re.search(r"[Cc]hiedimi (?:del|della|dello|dei|delle) (?:mio |mia )?(\w+)", dragonet.greeting)

    assert invitation is not None
    assert invitation.group(1) in {topic.name for topic in dragonet.topics.values()}


def test_the_jar_is_already_open_and_not_for_the_player(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:7])
    before = state.model_dump(exclude={"turns"})

    outcome = engine.execute(state, Action(verb="apri", target="vasetto_miele"))

    assert outcome.text == dragon.rules["apri_vasetto"].text
    assert state.model_dump(exclude={"turns"}) == before


@pytest.mark.parametrize(
    ("room", "line", "expected_room"),
    [
        ("radura", "vai alla quercia", "quercia"),
        ("ruscello", "vai nella tana", "tana"),
        ("ruscello", "vai alla tana", "tana"),
        # Found while playing: who or what is there names the place too.
        ("quercia", "torna dal drago", "radura"),
        ("ruscello", "torno dal draghetto", "radura"),
        ("ruscello", "vado dall'orso", "tana"),
        ("radura", "vado alle more", "roveto"),
        ("radura", "vai al ponte", "ruscello"),
    ],
)
def test_places_can_be_named_the_way_a_kid_says_them(dragon, room, line, expected_room):
    game = Game(Engine(dragon))
    game.state.current_room = room

    game.turn(line)

    assert game.state.current_room == expected_room


@pytest.mark.parametrize(
    ("room", "line", "direction"),
    [
        ("radura", "vai a casa", Direction.SOUTH),
        ("quercia", "vai sull'albero", Direction.UP),
        ("quercia", "vai sulla quercia", Direction.UP),
    ],
)
def test_the_closed_ways_answer_even_when_named(dragon, room, line, direction):
    game = Game(Engine(dragon))
    game.state.current_room = room

    assert game.turn(line) == dragon.rooms[room].exits[direction].otherwise
    assert game.state.current_room == room


# --- The kids' sentences through the whole turn, with the model's answers from the real runs ------

DRAGON_REPLIES = [
    # (room, carried, flags, seen, sentence, the model's answer, rule or character text the turn shows)
    ("radura", (), (), (), "ciao draghetto", {"verbo": "parla", "bersaglio": "draghetto", "con": "nessuno"},
     lambda w: w.characters["draghetto"].greeting),
    ("radura", (), (), (), "come posso aiutarti?", {"verbo": "parla", "bersaglio": "draghetto", "con": "nessuno"},
     lambda w: w.characters["draghetto"].greeting),
    ("radura", (), (), (), "dai un'occhiata al draghetto",
     {"verbo": "esamina", "bersaglio": "draghetto", "con": "nessuno"}, lambda w: w.characters["draghetto"].description),
    ("roveto", (), (), (), "raccolgo le more", {"verbo": "prendi", "bersaglio": "more", "con": "nessuno"},
     lambda w: messages.DONE),
    ("tana", ("more",), (), (), "do le more all'orso", {"verbo": "dai", "bersaglio": "more", "con": "orso"},
     lambda w: w.rules["scambia_more"].text),
    ("quercia", ("ramo",), (), (), "salgo sull'albero", {"verbo": "vai", "bersaglio": "su", "con": "nessuno"},
     lambda w: w.rooms["quercia"].exits[Direction.UP].otherwise),
    ("quercia", ("ramo",), (), ("piuma",), "stacco la piuma col bastone",
     {"verbo": "usa", "bersaglio": "ramo", "con": "piuma"}, lambda w: w.rules["stacca_piuma"].text),
    ("radura", ("vasetto_miele",), (), (), "gli do il miele",
     {"verbo": "dai", "bersaglio": "draghetto", "con": "vasetto di miele"}, lambda w: w.rules["miele_al_drago"].text),
    ("radura", ("piuma",), ("gola_guarita",), (), "faccio il solletico al drago con la piuma",
     {"verbo": "usa", "bersaglio": "draghetto", "con": "piuma"}, lambda w: w.rules["solletico"].text),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "seen", "sentence", "reply", "expected"),
    DRAGON_REPLIES,
    ids=[case[4] for case in DRAGON_REPLIES],
)
def test_kids_sentences_get_their_answer_at_once(dragon, room, carried, flags, seen, sentence, reply, expected):
    game = Game(Engine(dragon), FakeLLMClient(json_replies=[reply]))
    game.state.current_room = room
    for item_id in carried:
        game.state.item_locations[item_id] = "inventory"
    game.state.flags.update(flags)
    game.state.seen.update(seen)

    shown, answer = game.turn(sentence).split("\n", 1)

    # "(parla con il draghetto)", then the answer: no "Vuoi…?" first.
    assert shown.startswith("(") and shown.endswith(")")
    assert answer.startswith(expected(dragon))
    assert game.pending is None
