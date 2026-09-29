from collections.abc import Callable

import pytest

from app.engine.models import World
from app.engine.validation import find_problems


def problems_for(world_data: dict) -> list[str]:
    return find_problems(World.model_validate(world_data))


def test_minimal_world_has_no_problems(world_data):
    assert problems_for(world_data) == []


def add_room(world_data: dict, room_id: str, exits: dict) -> None:
    world_data["rooms"][room_id] = {"name": "Stanza", "description": "Una stanza.", "exits": exits}


def add_effect(effect: dict) -> Callable[[dict], None]:
    return lambda d: d["rules"]["tira_leva"]["effects"].append(effect)


# Each case: how to break the minimal world, and the words one single problem must contain
# (where the error is and what is wrong), so the author can find it.
BROKEN_WORLDS = {
    "unknown start room": (
        lambda d: d["game"].update(start_room="salone"),
        ["game.start_room", "salone"],
    ),
    "exit to unknown room": (
        lambda d: d["rooms"]["cella"]["exits"]["sud"].update(to="cantina"),
        ["rooms.cella.exits.sud.to", "cantina"],
    ),
    "item in unknown room": (
        lambda d: d["items"]["leva"].update(location="cantina"),
        ["items.leva.location", "cantina"],
    ),
    "room id reserved for the inventory": (
        lambda d: add_room(d, "inventory", {"nord": {"to": "atrio"}}),
        ["rooms.inventory", "reserved"],
    ),
    "trigger on unknown item": (
        lambda d: d["rules"]["usa_moneta"]["trigger"].update(target="specchio"),
        ["rules.usa_moneta.trigger.0.target", "specchio"],
    ),
    "trigger with unknown item": (
        lambda d: d["rules"]["usa_moneta"]["trigger"].update({"with": "specchio"}),
        ["rules.usa_moneta.trigger.0.with", "specchio"],
    ),
    "unknown item in the second trigger of a list": (
        lambda d: d["rules"]["tira_leva"].update(
            trigger=[{"verb": "tira", "target": "leva"}, {"verb": "spingi", "target": "leva", "with": "specchio"}]
        ),
        ["rules.tira_leva.trigger.1.with", "specchio"],
    ),
    "effect gives unknown item": (
        add_effect({"give": "spada"}),
        ["rules.tira_leva.effects.2.give", "spada"],
    ),
    "effect removes unknown item": (
        add_effect({"remove": "spada"}),
        ["rules.tira_leva.effects.2.remove", "spada"],
    ),
    "effect places unknown item": (
        add_effect({"place": {"item": "spada", "room": "cella"}}),
        ["rules.tira_leva.effects.2.place.item", "spada"],
    ),
    "effect places into unknown room": (
        add_effect({"place": {"item": "moneta", "room": "cantina"}}),
        ["rules.tira_leva.effects.2.place.room", "cantina"],
    ),
    "condition on unknown item": (
        lambda d: d["game"]["endings"][0].update(when={"has": "spada"}),
        ["game.endings.0.when", "spada"],
    ),
    "condition on unknown room": (
        lambda d: d["game"]["endings"][0].update(when={"player_in": "cantina"}),
        ["game.endings.0.when", "cantina"],
    ),
    "unknown item deep inside a condition": (
        lambda d: d["rules"]["tira_leva"].update(when={"not": {"any": [{"flag": "porta_aperta"}, {"has": "spada"}]}}),
        ["rules.tira_leva.when", "spada"],
    ),
    "room variant condition is checked": (
        lambda d: d["rooms"]["atrio"].update(variants=[{"when": {"has": "spada"}, "text": "Altro."}]),
        ["rooms.atrio.variants.0.when", "spada"],
    ),
    "closed exit variant condition is checked": (
        lambda d: d["rooms"]["atrio"]["exits"]["nord"].update(
            otherwise_variants=[{"when": {"has": "spada"}, "text": "Altro."}]
        ),
        ["rooms.atrio.exits.nord.otherwise_variants.0.when", "spada"],
    ),
    "item variant condition is checked": (
        lambda d: d["items"]["leva"].update(variants=[{"when": {"has": "spada"}, "text": "Altro."}]),
        ["items.leva.variants.0.when", "spada"],
    ),
    "item revealing an unknown item": (
        lambda d: d["items"]["leva"].update(reveals=["specchio"]),
        ["items.leva.reveals", "specchio"],
    ),
    "item in sight that nothing reveals": (
        lambda d: d["items"]["chiave"].update(visible_from={"room": "atrio"}),
        ["items.chiave.visible_from", "reveals"],
    ),
    "item visible from an unknown room": (
        lambda d: d["items"]["chiave"].update(visible_from={"room": "cantina"}),
        ["items.chiave.visible_from.room", "cantina"],
    ),
    "visibility condition is checked": (
        lambda d: d["items"]["chiave"].update(visible_from={"room": "atrio", "when": {"flag": "pozzo_vuoto"}}),
        ["items.chiave.visible_from.when", "pozzo_vuoto"],
    ),
    "flag read but never set (typo)": (
        lambda d: d["rooms"]["atrio"]["exits"]["nord"].update(when={"flag": "porta_apreta"}),
        ["rooms.atrio.exits.nord.when", "porta_apreta"],
    ),
    "out-of-play item never brought into play": (
        lambda d: d["rules"]["tira_leva"].update(effects=[{"set_flag": "porta_aperta"}]),
        ["items.chiave", "never"],
    ),
    "room unreachable from the start": (
        lambda d: add_room(d, "soffitta", {"giù": {"to": "atrio"}}),
        ["rooms.soffitta", "reachable"],
    ),
    "two items with the same name": (
        lambda d: d["items"]["chiave"].update(name="Moneta "),
        ["name", "moneta", "chiave"],
    ),
    # A name of articles and prepositions only would match every sentence of the player.
    "item alias with no significant word": (
        lambda d: d["items"]["moneta"].update(aliases=["soldo", "la"]),
        ["items.moneta.aliases.1", "'la'"],
    ),
    "room alias with no significant word": (
        lambda d: d["rooms"]["cella"].update(aliases=["su"]),
        ["rooms.cella.aliases.0", "'su'"],
    ),
    "rule otherwise variant is checked": (
        lambda d: d["rules"]["tira_leva"].update(
            otherwise_variants=[{"when": {"flag": "allarme"}, "text": "Suona un allarme."}]
        ),
        ["rules.tira_leva.otherwise_variants.0.when", "allarme"],
    ),
}


@pytest.mark.parametrize(("break_world", "expected_words"), BROKEN_WORLDS.values(), ids=BROKEN_WORLDS.keys())
def test_broken_world_is_reported(world_data, break_world, expected_words):
    break_world(world_data)

    problems = problems_for(world_data)

    assert any(all(word in problem for word in expected_words) for problem in problems), problems


def test_aliases_may_repeat_another_items_name(world_data):
    # "corda" must still work after the rope becomes "corda con gancio": the engine picks by scope.
    world_data["items"]["moneta"]["aliases"] = ["chiave"]

    assert problems_for(world_data) == []


def test_item_brought_into_play_by_place_is_fine(world_data):
    world_data["rules"]["tira_leva"]["effects"] = [
        {"set_flag": "porta_aperta"},
        {"place": {"item": "chiave", "room": "cella"}},
    ]

    assert problems_for(world_data) == []


def test_all_problems_are_reported_together(world_data):
    world_data["game"]["start_room"] = "salone"
    world_data["items"]["leva"]["location"] = "cantina"

    problems = problems_for(world_data)

    assert any("salone" in problem for problem in problems)
    assert any("cantina" in problem for problem in problems)


def keeper(d: dict) -> dict:
    return d["characters"]["custode"]


def topic(d: dict, topic_id: str) -> dict:
    return keeper(d)["topics"][topic_id]


BROKEN_KEEPERS = {
    "character in an unknown room": (
        lambda d: keeper(d).update(location="cantina"),
        ["characters.custode.location", "cantina"],
    ),
    "character with the id of an item": (
        lambda d: d["characters"].update(leva=d["characters"].pop("custode")),
        ["characters.leva", "item"],
    ),
    "character with the name of an item": (
        lambda d: keeper(d).update(name="Moneta"),
        ["characters.custode.name", "moneta"],
    ),
    "topic alias with no significant word": (
        lambda d: topic(d, "cella").update(aliases=["della"]),
        ["characters.custode.topics.cella.aliases.0", "'della'"],
    ),
    "two topics of a character with the same name": (
        lambda d: topic(d, "leva").update(name="Cella"),
        ["characters.custode.topics.leva.name", "cella"],
    ),
    "topic giving an unknown item": (
        lambda d: topic(d, "cella").update(effects=[{"give": "spada"}]),
        ["characters.custode.topics.cella.effects.0.give", "spada"],
    ),
    "topic known on a flag never set": (
        lambda d: topic(d, "cella").update(when={"flag": "amici"}),
        ["characters.custode.topics.cella.when", "amici"],
    ),
    "topic variant is checked": (
        lambda d: topic(d, "leva")["variants"][0].update(when={"has": "spada"}),
        ["characters.custode.topics.leva.variants.0.when", "spada"],
    ),
    "greeting variant is checked": (
        lambda d: keeper(d).update(greeting_variants=[{"when": {"flag": "amici"}, "text": "«Ciao, amico.»"}]),
        ["characters.custode.greeting_variants.0.when", "amici"],
    ),
    "character variant is checked": (
        lambda d: keeper(d)["variants"][0].update(when={"flag": "allarme"}),
        ["characters.custode.variants.0.when", "allarme"],
    ),
    "giving without the character who receives": (
        lambda d: d["rules"].update(dai_moneta={"trigger": {"verb": "dai", "target": "moneta"}, "text": "Grazie."}),
        ["rules.dai_moneta.trigger.0.with", "dai"],
    ),
    "giving to an item": (
        lambda d: d["rules"].update(
            dai_moneta={"trigger": {"verb": "dai", "target": "moneta", "with": "leva"}, "text": "Grazie."}
        ),
        ["rules.dai_moneta.trigger.0.with", "leva"],
    ),
    "giving a character": (
        lambda d: d["rules"].update(
            dai_custode={"trigger": {"verb": "dai", "target": "custode", "with": "custode"}, "text": "Grazie."}
        ),
        ["rules.dai_custode.trigger.0.target", "custode"],
    ),
    "another verb naming a character": (
        lambda d: d["rules"].update(
            usa_custode={"trigger": {"verb": "usa", "target": "moneta", "with": "custode"}, "text": "No."}
        ),
        ["rules.usa_custode.trigger.0.with", "custode"],
    ),
    "move to an unknown room": (
        lambda d: keeper(d).update(moves=[{"when": {"flag": "porta_aperta"}, "room": "cantina"}]),
        ["characters.custode.moves.0.room", "cantina"],
    ),
    "move on a flag never set": (
        lambda d: keeper(d).update(moves=[{"when": {"flag": "allarme"}, "room": "cella"}]),
        ["characters.custode.moves.0.when", "allarme"],
    ),
}


def test_a_world_with_a_character_has_no_problems(keeper_world):
    assert problems_for(keeper_world) == []


def test_a_rule_may_react_to_giving_an_item_to_a_character(keeper_world):
    keeper_world["rules"]["paga_custode"] = {
        "trigger": {"verb": "dai", "target": "moneta", "with": "custode"},
        "text": "«Grazie», dice il custode.",
    }
    keeper_world["characters"]["custode"]["refuses"] = "Il custode scuote la testa."

    assert problems_for(keeper_world) == []


@pytest.mark.parametrize(("break_world", "expected_words"), BROKEN_KEEPERS.values(), ids=BROKEN_KEEPERS.keys())
def test_broken_character_is_reported(keeper_world, break_world, expected_words):
    break_world(keeper_world)

    problems = problems_for(keeper_world)

    assert any(all(word in problem for word in expected_words) for problem in problems), problems


def test_a_flag_set_by_a_topic_may_be_read_elsewhere(keeper_world):
    keeper_world["rooms"]["atrio"]["variants"] = [{"when": {"flag": "forziere_noto"}, "text": "Un atrio."}]

    assert problems_for(keeper_world) == []


def test_an_item_given_by_a_topic_is_brought_into_play(keeper_world):
    keeper_world["items"]["mappa"] = {"name": "mappa", "gender": "f", "description": "Una mappa.", "location": None}
    topic(keeper_world, "cella")["effects"] = [{"give": "mappa"}]

    assert problems_for(keeper_world) == []


def test_an_item_in_sight_revealed_by_another_is_fine(world_data):
    world_data["items"]["chiave"]["visible_from"] = {"room": "atrio", "when": {"not": {"flag": "porta_aperta"}}}
    world_data["items"]["leva"]["reveals"] = ["chiave"]

    assert problems_for(world_data) == []
