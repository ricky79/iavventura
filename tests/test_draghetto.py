"""Il draghetto raffreddato, the adventure for kids: invariants of its puzzles, then the game played
through the engine and with typed commands.

Chain: berries -> the bear gives the honey; the branch knocks the feather out of the nest; honey to
the dragon (its throat), then the feather (a sneeze) -> its fire is back and the game ends.
"""

import pytest

from app.engine import engine as messages
from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Direction, GameState, World
from app.game import Game


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
    ],
    ids=["branch on the nest", "branch on the tree", "branch on the feather", "take the feather with the branch"],
)
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
