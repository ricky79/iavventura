"""The sample castle: invariants of its puzzle, then the game played through the engine.

The invariants fail if a data change opens a shortcut. Chain: gancio + corda -> corda_con_gancio
-> fish chiave_torre out of the well -> open the tower door -> entering the tower ends the game.
"""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, FlagSet, GameState, Give, Place, PlayerIn, Remove, Rule, SetFlag, World
from app.game import Game


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world(WORLDS_DIR / "rocca")


def rules_bringing_in(world: World, item_id: str) -> list[Rule]:
    return [
        rule
        for rule in world.rules.values()
        if Give(give=item_id) in rule.effects
        or any(isinstance(effect, Place) and effect.place.item == item_id for effect in rule.effects)
    ]


def items_used_by(rule: Rule) -> list[set[str]]:
    """The items of each trigger: a puzzle may be solved in more than one way."""
    return [{trigger.target, trigger.with_} - {None} for trigger in rule.triggers]


def test_castle_has_four_rooms_and_starts_in_the_courtyard(castle):
    assert set(castle.rooms) == {"cortile", "cucina", "scuderia", "torre"}
    assert castle.game.start_room == "cortile"


def test_hook_and_rope_are_waiting_in_the_castle(castle):
    assert castle.items["gancio"].location == "cucina"
    assert castle.items["corda"].location == "scuderia"


def test_grapple_exists_only_by_combining_hook_and_rope(castle):
    assert castle.items["corda_con_gancio"].location is None

    [combine] = rules_bringing_in(castle, "corda_con_gancio")

    assert items_used_by(combine) == [{"gancio", "corda"}]
    assert Remove(remove="gancio") in combine.effects
    assert Remove(remove="corda") in combine.effects


def test_key_can_only_be_fished_out_with_the_grapple(castle):
    assert castle.items["chiave_torre"].location is None

    fishers = rules_bringing_in(castle, "chiave_torre")

    assert fishers
    assert all("corda_con_gancio" in items for rule in fishers for items in items_used_by(rule))


def test_the_key_is_in_sight_once_the_well_is_examined_until_fished_out(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    assert engine.visible(state) == []

    play(engine, state, [LOOK_IN_THE_WELL])
    assert [item.id for item in engine.visible(state)] == ["chiave_torre"]

    play(engine, state, UP_TO_THE_KEY)
    assert engine.visible(state) == []


def test_tower_opens_only_with_the_key(castle):
    ways_into_tower = [exit_ for room in castle.rooms.values() for exit_ in room.exits.values() if exit_.to == "torre"]
    assert ways_into_tower

    for exit_ in ways_into_tower:
        assert isinstance(exit_.when, FlagSet)
        openers = [rule for rule in castle.rules.values() if SetFlag(set_flag=exit_.when.flag) in rule.effects]
        assert openers
        assert all("chiave_torre" in items for rule in openers for items in items_used_by(rule))


def test_entering_the_tower_ends_the_game(castle):
    assert any(ending.when == PlayerIn(player_in="torre") for ending in castle.game.endings)



def test_jumping_into_the_well_ends_the_game_with_a_death(castle):
    [jump] = [rule for rule in castle.rules.values() if Action(verb="salta", target="pozzo") in actions_of(rule)]
    [death] = [ending for ending in castle.game.endings if ending.when == FlagSet(flag="caduto_nel_pozzo")]

    assert SetFlag(set_flag="caduto_nel_pozzo") in jump.effects
    assert jump.when is None  # always deadly, even with the key already fished out
    assert "Sei morto" in death.text


def actions_of(rule: Rule) -> list[Action]:
    return [Action(verb=trigger.verb, target=trigger.target, with_=trigger.with_) for trigger in rule.triggers]


def test_the_pilgrim_waits_in_the_stable_and_only_gives_hints(castle):
    pilgrim = castle.characters["pellegrino"]

    assert pilgrim.location == "scuderia"
    # No topic changes the game: talking can't open a shortcut through the puzzle.
    assert all(topic.effects == () for topic in pilgrim.topics.values())
    # Nor does giving him things: no rule reacts to it.
    assert not any(trigger.verb == "dai" for rule in castle.rules.values() for trigger in rule.triggers)


def test_the_pilgrim_refuses_what_he_is_given(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    state.current_room = "scuderia"
    state.item_locations["corda"] = "inventory"
    before = state.model_dump(exclude={"turns"})

    outcome = engine.execute(state, Action(verb="dai", target="corda", with_="pellegrino"))

    assert outcome.text == "Il pellegrino scuote la testa: «Tienilo tu, figliolo: a me basta il bastone.»"
    assert state.model_dump(exclude={"turns"}) == before


# --- Playing through the engine -------------------------------------------------

UP_TO_THE_KEY = [
    Action(verb="vai", direction="ovest"),
    Action(verb="prendi", target="gancio"),
    Action(verb="vai", direction="est"),
    Action(verb="vai", direction="est"),
    Action(verb="prendi", target="corda"),
    Action(verb="usa", target="corda", with_="gancio"),
    Action(verb="vai", direction="ovest"),
    Action(verb="usa", target="pozzo", with_="corda_con_gancio"),
]


LOOK_IN_THE_WELL = Action(verb="esamina", target="pozzo")


def play(engine: Engine, state: GameState, actions: list[Action]) -> None:
    for action in actions:
        outcome = engine.execute(state, action)
        assert outcome.ok, f"{action} was refused: {outcome.text}"


def test_whole_game_can_be_played_to_the_end(castle):
    engine = Engine(castle)
    state, intro = engine.new_game()
    assert intro.room.id == "cortile"

    locked = engine.execute(state, Action(verb="vai", direction="nord"))
    assert not locked.ok
    assert locked.text == "La porta della torre è chiusa a chiave."

    play(engine, state, UP_TO_THE_KEY)
    assert engine.execute(state, Action(verb="inventario")).inventory == ("corda_con_gancio", "chiave_torre")

    play(engine, state, [Action(verb="apri", target="porta_torre", with_="chiave_torre")])
    last = engine.execute(state, Action(verb="vai", direction="nord"))

    assert last.room.id == "torre"
    assert last.ending == castle.game.endings[0].text
    assert state.finished


def test_one_piece_alone_only_gives_a_hint(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY[:2] + [Action(verb="vai", direction="est")])

    hint = engine.execute(state, Action(verb="usa", target="gancio", with_="pozzo"))

    assert hint.text == castle.rules["cala_gancio"].text
    assert state.item_locations["chiave_torre"] is None


def test_the_key_can_be_fished_out_only_once(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY)

    again = engine.execute(state, Action(verb="usa", target="pozzo", with_="corda_con_gancio"))

    assert not again.ok
    assert again.text == castle.rules["pesca_chiave"].otherwise


def test_using_the_key_on_the_door_opens_it_too(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY)

    opened = engine.execute(state, Action(verb="usa", target="chiave_torre", with_="porta_torre"))

    assert opened.text == castle.rules["apri_torre"].text
    assert "torre_aperta" in state.flags


def test_the_key_can_also_be_taken_with_the_grapple_once_seen(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    play(engine, state, UP_TO_THE_KEY[:-1])
    take_the_key = Action(verb="prendi", target="chiave_torre", with_="corda_con_gancio")

    unseen = engine.execute(state, take_the_key)
    play(engine, state, [LOOK_IN_THE_WELL])
    fished = engine.execute(state, take_the_key)

    assert unseen.text == "Non vedi niente del genere qui."
    assert fished.text == castle.rules["pesca_chiave"].text
    assert state.item_locations["chiave_torre"] == "inventory"


@pytest.mark.parametrize("flags", [set(), {"chiave_pescata"}], ids=["key in the well", "key fished out"])
def test_the_player_who_jumps_into_the_well_dies(castle, flags):
    game = Game(Engine(castle))
    game.state.flags.update(flags)

    answer = game.turn("salta nel pozzo")

    death = next(ending for ending in castle.game.endings if ending.when == FlagSet(flag="caduto_nel_pozzo"))
    assert answer == f"{castle.rules['salto_nel_pozzo'].text}\n\n{death.text}"
    assert game.finished
    assert game.turn("guarda") == "La partita è finita."
    assert game.state.lost
    assert game.resumable is None  # the castle has no acts: a new game, as before


@pytest.mark.parametrize(
    ("room", "line", "expected_room"),
    [
        # Found while playing: "vai alle scuderie" and "torna al pozzo" were asked about.
        ("cortile", "vai alle scuderie", "scuderia"),
        ("cortile", "vai dal pellegrino", "scuderia"),
        ("scuderia", "torna al pozzo", "cortile"),
        ("cucina", "torno al pozzo", "cortile"),
    ],
)
def test_places_can_be_named_by_who_or_what_is_there(castle, room, line, expected_room):
    game = Game(Engine(castle))
    game.state.current_room = room
    game.state.visited.update({"cortile", "scuderia"})

    game.turn(line)

    assert game.state.current_room == expected_room


def test_the_rim_of_the_well_is_the_well(castle):
    # "aggancia la corda alla vera di pietra" went to the door of the tower.
    assert Game(Engine(castle)).turn("esamina la vera") == castle.items["pozzo"].description


@pytest.mark.parametrize("line", ["esamina il ceppo", "guarda il ceppo di legno"])
def test_the_chopping_block_in_the_kitchen_can_be_examined(castle, line):
    # Found while playing: the kitchen tells of a chopping block, and "esamina il ceppo" found nothing.
    game = Game(Engine(castle))
    game.state.current_room = "cucina"

    assert game.turn(line) == castle.items["ceppo"].description
    assert game.turn("prendi il ceppo") == "Non si può prendere."


def test_the_kitchen_promises_no_tools_once_the_hook_is_taken(castle):
    # The kitchen said someone had left their tools on the block, even with the hook taken.
    game = Game(Engine(castle))
    game.state.current_room = "cucina"
    game.turn("prendi il gancio")

    kitchen = game.turn("guarda")

    assert "gancio" not in kitchen
    assert "attrezzi" not in kitchen
