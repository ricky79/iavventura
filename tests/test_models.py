import pytest
from pydantic import ValidationError

from app.engine.models import Action, AllOf, Command, Direction, FlagSet, Has, Not, SetFlag, Verb, World


def error_locations(exc: ValidationError) -> list[str]:
    return [".".join(str(part) for part in err["loc"]) for err in exc.errors()]


def test_minimal_world_parses_with_ids_taken_from_keys(world_data):
    world = World.model_validate(world_data)

    assert world.rooms["atrio"].id == "atrio"
    assert world.items["chiave"].id == "chiave"
    assert world.rules["tira_leva"].id == "tira_leva"
    assert world.rooms["atrio"].exits[Direction.NORTH].to == "cella"
    assert world.rules["usa_moneta"].trigger.verb is Verb.USE
    assert world.rules["usa_moneta"].trigger.with_ == "moneta"
    assert world.rules["tira_leva"].trigger.with_ is None
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

    assert "rules.usa_moneta.trigger.verb" in error_locations(exc.value)


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
    ],
)
def test_malformed_actions_are_rejected(fields):
    with pytest.raises(ValidationError):
        Action.model_validate(fields)


def test_action_verbs_are_parsed_into_their_enums():
    assert Action(verb="vai", direction="giù").verb is Command.GO
    assert Action(verb="leggi", target="libro").verb is Verb.READ
