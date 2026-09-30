import pytest
from pydantic import ValidationError

from app.engine.models import (
    Action,
    AllOf,
    Command,
    Conversation,
    Direction,
    FlagSet,
    Gender,
    Gesture,
    Has,
    Not,
    SetFlag,
    Verb,
    World,
)


def error_locations(exc: ValidationError) -> list[str]:
    return [".".join(str(part) for part in err["loc"]) for err in exc.errors()]


def test_minimal_world_parses_with_ids_taken_from_keys(world_data):
    world = World.model_validate(world_data)

    assert world.rooms["atrio"].id == "atrio"
    assert world.items["chiave"].id == "chiave"
    assert world.rules["tira_leva"].id == "tira_leva"
    assert world.rooms["atrio"].exits[Direction.NORTH].to == "cella"
    [use_coin] = world.rules["usa_moneta"].triggers
    assert use_coin.verb is Verb.USE
    assert use_coin.with_ == "moneta"
    assert world.rules["tira_leva"].triggers[0].with_ is None
    assert world.items["chiave"].location is None
    assert world.items["leva"].scenery is True
    assert world.items["moneta"].scenery is False


def test_unknown_field_is_rejected(world_data):
    world_data["rooms"]["atrio"]["descripton"] = "refuso"

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "rooms.atrio.descripton" in error_locations(exc.value)


def test_room_key_must_be_a_valid_id(world_data):
    world_data["rooms"]["Sala grande"] = world_data["rooms"].pop("cella")

    with pytest.raises(ValidationError):
        World.model_validate(world_data)


def test_explicit_id_is_rejected_because_the_key_is_the_id(world_data):
    world_data["items"]["moneta"]["id"] = "soldo"

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "items.moneta" in str(exc.value)


def test_unknown_direction_is_rejected(world_data):
    world_data["rooms"]["cella"]["exits"] = {"nordest": {"to": "atrio"}}

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert any("rooms.cella.exits" in loc for loc in error_locations(exc.value))


def test_unknown_verb_is_rejected(world_data):
    world_data["rules"]["usa_moneta"]["trigger"]["verb"] = "mangia"

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "rules.usa_moneta.trigger.0.verb" in error_locations(exc.value)


def test_a_rule_may_have_several_equivalent_triggers(world_data):
    world_data["rules"]["tira_leva"]["trigger"] = [
        {"verb": "tira", "target": "leva"},
        {"verb": "spingi", "target": "leva", "with": "moneta"},
    ]

    triggers = World.model_validate(world_data).rules["tira_leva"].triggers

    assert [(trigger.verb, trigger.target, trigger.with_) for trigger in triggers] == [
        (Verb.PULL, "leva", None),
        (Verb.PUSH, "leva", "moneta"),
    ]


def test_a_rule_needs_at_least_one_trigger(world_data):
    world_data["rules"]["tira_leva"]["trigger"] = []

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "rules.tira_leva.trigger" in error_locations(exc.value)


def test_empty_text_is_rejected(world_data):
    world_data["rooms"]["atrio"]["description"] = "   "

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "rooms.atrio.description" in error_locations(exc.value)


def test_condition_with_two_keys_is_rejected(world_data):
    world_data["game"]["endings"][0]["when"] = {"flag": "porta_aperta", "has": "moneta"}

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert any(loc.startswith("game.endings.0.when") for loc in error_locations(exc.value))


def test_unknown_condition_key_is_rejected(world_data):
    world_data["game"]["endings"][0]["when"] = {"flagg": "porta_aperta"}

    with pytest.raises(ValidationError):
        World.model_validate(world_data)


def test_condition_list_is_shorthand_for_all(world_data):
    world_data["rooms"]["atrio"]["exits"]["nord"]["when"] = [
        {"flag": "porta_aperta"},
        {"not": [{"has": "moneta"}]},
    ]

    world = World.model_validate(world_data)

    assert world.rooms["atrio"].exits[Direction.NORTH].when == AllOf(
        all=[FlagSet(flag="porta_aperta"), Not(not_=AllOf(all=[Has(has="moneta")]))]
    )


def test_effects_are_parsed_by_their_key(world_data):
    world = World.model_validate(world_data)

    assert world.rules["tira_leva"].effects[0] == SetFlag(set_flag="porta_aperta")


def test_unknown_effect_is_rejected(world_data):
    world_data["rules"]["tira_leva"]["effects"].append({"teletrasporta": "cella"})

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert any(loc.startswith("rules.tira_leva.effects.2") for loc in error_locations(exc.value))


def test_world_is_immutable(world_data):
    world = World.model_validate(world_data)

    with pytest.raises(ValidationError):
        world.rooms["atrio"].name = "Altro"


def test_game_needs_at_least_one_ending(world_data):
    world_data["game"]["endings"] = []

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "game.endings" in error_locations(exc.value)


# --- Action -------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {"verb": "vai", "direction": "nord"},
        {"verb": "guarda"},
        {"verb": "inventario"},
        {"verb": "prendi", "target": "moneta"},
        {"verb": "usa", "target": "moneta", "with": "leva"},
        {"verb": "parla", "target": "custode"},
        {"verb": "chiedi", "target": "custode", "topic": "cella"},
        {"verb": "chiedi", "target": "custode"},  # about something the character doesn't know
    ],
)
def test_well_formed_actions_are_accepted(fields):
    Action.model_validate(fields)


@pytest.mark.parametrize(
    "fields",
    [
        {"verb": "vai"},
        {"verb": "vai", "direction": "nord", "target": "moneta"},
        {"verb": "guarda", "target": "leva"},
        {"verb": "inventario", "direction": "sud"},
        {"verb": "prendi"},
        {"verb": "prendi", "with": "moneta"},
        {"verb": "esamina", "target": "leva", "direction": "nord"},
        {"verb": "usa", "target": "moneta", "with": "moneta"},
        {"verb": "salta"},
        {"verb": "parla"},
        {"verb": "parla", "target": "custode", "topic": "cella"},
        {"verb": "chiedi", "target": "custode", "with": "moneta"},
        {"verb": "chiedi", "target": "custode", "direction": "nord"},
        {"verb": "esamina", "target": "leva", "topic": "cella"},
        {"verb": "guarda", "topic": "cella"},
    ],
)
def test_malformed_actions_are_rejected(fields):
    with pytest.raises(ValidationError):
        Action.model_validate(fields)


def test_action_verbs_are_parsed_into_their_enums():
    assert Action(verb="vai", direction="giù").verb is Command.GO
    assert Action(verb="leggi", target="libro").verb is Verb.READ
    assert Action(verb="chiedi", target="custode").verb is Conversation.ASK


def test_only_talking_has_a_gesture():
    assert Action(verb="parla", target="custode", gesture="grazie").gesture is Gesture.THANKS
    with pytest.raises(ValidationError):
        Action(verb="chiedi", target="custode", gesture="grazie")


# --- Characters -------------------------------------------------------------------


def test_characters_and_their_topics_take_their_ids_from_the_keys(keeper_world):
    keeper = World.model_validate(keeper_world).characters["custode"]

    assert keeper.id == "custode"
    assert keeper.location == "atrio"
    assert keeper.aliases == ("guardiano", "vecchio")
    assert list(keeper.topics) == ["cella", "leva", "chiave"]
    assert keeper.topics["cella"].id == "cella"
    assert keeper.topics["chiave"].effects == (SetFlag(set_flag="forziere_noto"),)


@pytest.mark.parametrize("field", ["greeting", "unknown", "location", "gender"])
def test_a_character_needs_its_texts_a_room_and_a_gender(keeper_world, field):
    del keeper_world["characters"]["custode"][field]

    with pytest.raises(ValidationError) as caught:
        World.model_validate(keeper_world)

    assert error_locations(caught.value) == [f"characters.custode.{field}"]


def test_a_topic_needs_a_name_and_a_gender_for_its_article(keeper_world):
    del keeper_world["characters"]["custode"]["topics"]["cella"]["gender"]

    with pytest.raises(ValidationError) as caught:
        World.model_validate(keeper_world)

    assert error_locations(caught.value) == ["characters.custode.topics.cella.gender"]


def test_a_world_without_characters_is_fine(world_data):
    assert World.model_validate(world_data).characters == {}


# --- Gender and number of items -------------------------------------------------


def test_items_declare_gender_and_are_singular_by_default(world_data):
    world = World.model_validate(world_data)

    assert world.items["moneta"].gender is Gender.FEMININE
    assert world.items["moneta"].plural is False


def test_item_without_gender_is_rejected(world_data):
    del world_data["items"]["leva"]["gender"]

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "items.leva.gender" in error_locations(exc.value)


def test_unknown_gender_is_rejected(world_data):
    world_data["items"]["leva"]["gender"] = "n"

    with pytest.raises(ValidationError) as exc:
        World.model_validate(world_data)

    assert "items.leva.gender" in error_locations(exc.value)


def test_an_item_may_be_visible_from_a_room_while_a_condition_holds(world_data):
    world_data["items"]["chiave"]["visible_from"] = {"room": "cella", "when": {"not": {"flag": "porta_aperta"}}}
    world_data["items"]["moneta"]["visible_from"] = {"room": "atrio"}

    world = World.model_validate(world_data)

    assert world.items["chiave"].visible_from.room == "cella"
    assert world.items["chiave"].visible_from.when == Not(not_=FlagSet(flag="porta_aperta"))
    assert world.items["moneta"].visible_from.when is None
    assert world.items["leva"].visible_from is None
