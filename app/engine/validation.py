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
    Effect,
    FlagSet,
    Give,
    Has,
    Not,
    Place,
    PlayerIn,
    Remove,
    SetFlag,
    Verb,
    World,
)
from app.engine.parser import significant_words


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
            path = f"rules.{rule.id}.trigger.{index}"
            check_item(f"{path}.target", trigger.target)
            if trigger.verb is Verb.GIVE:
                # "dai X a Y": the item, then the character who receives it
                if trigger.with_ is None:
                    report(f"{path}.with", "'dai' needs the character who receives the item")
                elif trigger.with_ not in world.characters:
                    report(f"{path}.with", f"unknown character '{trigger.with_}'")
            elif trigger.with_ is not None:
                check_item(f"{path}.with", trigger.with_)

    for character in world.characters.values():
        check_room(f"characters.{character.id}.location", character.location)
        for index, move in enumerate(character.moves):
            check_room(f"characters.{character.id}.moves.{index}.room", move.room)
        if character.id in world.items:
            report(f"characters.{character.id}", f"id '{character.id}' is already used by an item")

    for path, effect in _effects(world):
        match effect:
            case Give(give=item_id):
                check_item(f"{path}.give", item_id)
            case Remove(remove=item_id):
                check_item(f"{path}.remove", item_id)
            case Place(place=placement):
                check_item(f"{path}.place.item", placement.item)
                check_room(f"{path}.place.room", placement.room)

    effects = [effect for _, effect in _effects(world)]
    flags_ever_set = {effect.set_flag for effect in effects if isinstance(effect, SetFlag)}
    for path, condition in _conditions(world):
        for atom in _atoms(condition):
            match atom:
                case FlagSet(flag=flag) if flag not in flags_ever_set:
                    report(path, f"flag '{flag}' is never set by any effect")
                case Has(has=item_id):
                    check_item(path, item_id)
                case PlayerIn(player_in=room_id):
                    check_room(path, room_id)

    brought_into_play = {effect.give for effect in effects if isinstance(effect, Give)} | {
        effect.place.item for effect in effects if isinstance(effect, Place)
    }
    for item in world.items.values():
        if item.location is None and item.id not in brought_into_play:
            report(f"items.{item.id}", "starts out of play (location: null) and is never brought in by any effect")

    if world.game.start_room in world.rooms:
        reachable = _reachable_rooms(world)
        for room_id in world.rooms:
            if room_id not in reachable:
                report(f"rooms.{room_id}", f"not reachable from the start room '{world.game.start_room}'")

    # Items and characters are named in the same commands (esamina X), so their names can't repeat.
    owner_of_name: dict[str, str] = {}
    for section, things in (("items", world.items), ("characters", world.characters)):
        for thing in things.values():
            key = thing.name.casefold()
            if key in owner_of_name:
                report(f"{section}.{thing.id}.name", f"name '{thing.name}' is already used by {owner_of_name[key]}")
            else:
                owner_of_name[key] = f"{section[:-1]} '{thing.id}'"

    # A name made only of articles and prepositions ("su", "la") would match every sentence.
    for path, name in _names(world):
        if not significant_words(name):
            report(path, f"'{name}' has only articles and prepositions: it names nothing")

    for character in world.characters.values():
        topic_of_name: dict[str, str] = {}
        for topic in character.topics.values():
            key = topic.name.casefold()
            if key in topic_of_name:
                report(
                    f"characters.{character.id}.topics.{topic.id}.name",
                    f"name '{topic.name}' is already used by topic '{topic_of_name[key]}'",
                )
            else:
                topic_of_name[key] = topic.id

    return problems


def _names(world: World) -> Iterator[tuple[str, str]]:
    """Every name and alias the player can use, with its path."""
    named = [
        *((f"rooms.{room.id}", room) for room in world.rooms.values()),
        *((f"items.{item.id}", item) for item in world.items.values()),
        *((f"characters.{character.id}", character) for character in world.characters.values()),
        *(
            (f"characters.{character.id}.topics.{topic.id}", topic)
            for character in world.characters.values()
            for topic in character.topics.values()
        ),
    ]
    for path, thing in named:
        yield f"{path}.name", thing.name
        for index, alias in enumerate(thing.aliases):
            yield f"{path}.aliases.{index}", alias


def _effects(world: World) -> Iterator[tuple[str, Effect]]:
    """Every effect with its path: those of rules, and those of the topics characters answer about."""
    for rule in world.rules.values():
        for index, effect in enumerate(rule.effects):
            yield f"rules.{rule.id}.effects.{index}", effect
    for character in world.characters.values():
        for topic in character.topics.values():
            for index, effect in enumerate(topic.effects):
                yield f"characters.{character.id}.topics.{topic.id}.effects.{index}", effect


def _conditions(world: World) -> Iterator[tuple[str, Condition]]:
    for room in world.rooms.values():
        for direction, exit_ in room.exits.items():
            if exit_.when is not None:
                yield f"rooms.{room.id}.exits.{direction}.when", exit_.when
            for index, variant in enumerate(exit_.otherwise_variants):
                yield f"rooms.{room.id}.exits.{direction}.otherwise_variants.{index}.when", variant.when
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
        for index, variant in enumerate(rule.otherwise_variants):
            yield f"rules.{rule.id}.otherwise_variants.{index}.when", variant.when
    for character in world.characters.values():
        path = f"characters.{character.id}"
        for index, variant in enumerate(character.variants):
            yield f"{path}.variants.{index}.when", variant.when
        for index, variant in enumerate(character.greeting_variants):
            yield f"{path}.greeting_variants.{index}.when", variant.when
        for index, move in enumerate(character.moves):
            yield f"{path}.moves.{index}.when", move.when
        for topic in character.topics.values():
            if topic.when is not None:
                yield f"{path}.topics.{topic.id}.when", topic.when
            for index, variant in enumerate(topic.variants):
                yield f"{path}.topics.{topic.id}.variants.{index}.when", variant.when
    for index, ending in enumerate(world.game.endings):
        yield f"game.endings.{index}.when", ending.when
    for index, act in enumerate(world.game.acts):
        yield f"game.acts.{index}.when", act.when


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
