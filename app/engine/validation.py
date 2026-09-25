"""Cross-reference checks on a structurally valid World.

Pydantic validates each piece on its own; these checks look at how the pieces
refer to each other. Every problem is collected, so the author sees them all at once.
"""

from collections.abc import Iterator

from app.engine.models import (
    INVENTORY,
    AllOf,
    AnyOf,
    Condition,
    FlagSet,
    Give,
    Has,
    Not,
    Place,
    PlayerIn,
    Remove,
    SetFlag,
    World,
)


def find_problems(world: World) -> list[str]:
    """Returns one "path: message" line per problem; an empty list means the world is consistent."""
    problems: list[str] = []

    def report(path: str, message: str) -> None:
        problems.append(f"{path}: {message}")

    def check_room(path: str, room_id: str) -> None:
        if room_id not in world.rooms:
            report(path, f"unknown room '{room_id}'")

    def check_item(path: str, item_id: str) -> None:
        if item_id not in world.items:
            report(path, f"unknown item '{item_id}'")

    check_room("game.start_room", world.game.start_room)
    if INVENTORY in world.rooms:
        report(f"rooms.{INVENTORY}", f"'{INVENTORY}' is reserved for the player's inventory")

    for room in world.rooms.values():
        for direction, exit_ in room.exits.items():
            check_room(f"rooms.{room.id}.exits.{direction}.to", exit_.to)

    for item in world.items.values():
        if item.location not in (None, INVENTORY):
            check_room(f"items.{item.id}.location", item.location)
        if item.visible_from is not None:
            check_room(f"items.{item.id}.visible_from.room", item.visible_from.room)
        for index, item_id in enumerate(item.reveals):
            check_item(f"items.{item.id}.reveals.{index}", item_id)

    revealed = {item_id for item in world.items.values() for item_id in item.reveals}
    for item in world.items.values():
        if item.visible_from is not None and item.id not in revealed:
            report(f"items.{item.id}.visible_from", "no item reveals it (reveals), so it is never seen")

    for rule in world.rules.values():
        for index, trigger in enumerate(rule.triggers):
            check_item(f"rules.{rule.id}.trigger.{index}.target", trigger.target)
            if trigger.with_ is not None:
                check_item(f"rules.{rule.id}.trigger.{index}.with", trigger.with_)
        for index, effect in enumerate(rule.effects):
            path = f"rules.{rule.id}.effects.{index}"
            match effect:
                case Give(give=item_id):
                    check_item(f"{path}.give", item_id)
                case Remove(remove=item_id):
                    check_item(f"{path}.remove", item_id)
                case Place(place=placement):
                    check_item(f"{path}.place.item", placement.item)
                    check_room(f"{path}.place.room", placement.room)

    flags_ever_set = {effect.set_flag for effect in _effects(world) if isinstance(effect, SetFlag)}
    for path, condition in _conditions(world):
        for atom in _atoms(condition):
            match atom:
                case FlagSet(flag=flag) if flag not in flags_ever_set:
                    report(path, f"flag '{flag}' is never set by any effect")
                case Has(has=item_id):
                    check_item(path, item_id)
                case PlayerIn(player_in=room_id):
                    check_room(path, room_id)

    brought_into_play = {effect.give for effect in _effects(world) if isinstance(effect, Give)} | {
        effect.place.item for effect in _effects(world) if isinstance(effect, Place)
    }
    for item in world.items.values():
        if item.location is None and item.id not in brought_into_play:
            report(f"items.{item.id}", "starts out of play (location: null) and is never brought in by any effect")

    if world.game.start_room in world.rooms:
        reachable = _reachable_rooms(world)
        for room_id in world.rooms:
            if room_id not in reachable:
                report(f"rooms.{room_id}", f"not reachable from the start room '{world.game.start_room}'")

    owner_of_name: dict[str, str] = {}
    for item in world.items.values():
        key = item.name.casefold()
        if key in owner_of_name:
            report(f"items.{item.id}.name", f"name '{item.name}' is already used by item '{owner_of_name[key]}'")
        else:
            owner_of_name[key] = item.id

    return problems


def _effects(world: World) -> Iterator:
    for rule in world.rules.values():
        yield from rule.effects


def _conditions(world: World) -> Iterator[tuple[str, Condition]]:
    for room in world.rooms.values():
        for direction, exit_ in room.exits.items():
            if exit_.when is not None:
                yield f"rooms.{room.id}.exits.{direction}.when", exit_.when
        for index, variant in enumerate(room.variants):
            yield f"rooms.{room.id}.variants.{index}.when", variant.when
    for item in world.items.values():
        for index, variant in enumerate(item.variants):
            yield f"items.{item.id}.variants.{index}.when", variant.when
        if item.visible_from is not None and item.visible_from.when is not None:
            yield f"items.{item.id}.visible_from.when", item.visible_from.when
    for rule in world.rules.values():
        if rule.when is not None:
            yield f"rules.{rule.id}.when", rule.when
    for index, ending in enumerate(world.game.endings):
        yield f"game.endings.{index}.when", ending.when


def _atoms(condition: Condition) -> Iterator[Condition]:
    match condition:
        case AllOf(all=parts) | AnyOf(any=parts):
            for part in parts:
                yield from _atoms(part)
        case Not(not_=inner):
            yield from _atoms(inner)
        case _:
            yield condition


def _reachable_rooms(world: World) -> set[str]:
    reachable = {world.game.start_room}
    to_visit = [world.game.start_room]
    while to_visit:
        room = world.rooms.get(to_visit.pop())
        if room is None:
            continue
        for exit_ in room.exits.values():
            if exit_.to not in reachable:
                reachable.add(exit_.to)
                to_visit.append(exit_.to)
    return reachable
