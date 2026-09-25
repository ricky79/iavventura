"""Pydantic models for the game world.

The world is static data loaded from YAML and never changes during play:
everything that changes lives in GameState.
"""

from enum import StrEnum
from typing import Annotated, Any, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    StringConstraints,
    Tag,
    field_validator,
    model_validator,
)

Id = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Item location meaning "carried by the player"; it can never be a room id.
INVENTORY = "inventory"


class Direction(StrEnum):
    NORTH = "nord"
    SOUTH = "sud"
    EAST = "est"
    WEST = "ovest"
    UP = "su"
    DOWN = "giù"


class Verb(StrEnum):
    """Verbs on items: rules react to them, otherwise the engine applies a default behaviour."""

    EXAMINE = "esamina"
    TAKE = "prendi"
    DROP = "lascia"
    USE = "usa"
    OPEN = "apri"
    CLOSE = "chiudi"
    PUSH = "spingi"
    PULL = "tira"
    READ = "leggi"


class Command(StrEnum):
    """Verbs without items: the engine handles them itself and rules can't react to them."""

    GO = "vai"
    LOOK = "guarda"
    INVENTORY = "inventario"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_by_name=True, validate_by_alias=True)


# --- Conditions: each one is a mapping with exactly one key -------------------


class FlagSet(_Frozen):
    flag: Id


class Has(_Frozen):
    """The item is in the player's inventory."""

    has: Id


class PlayerIn(_Frozen):
    player_in: Id


class AllOf(_Frozen):
    all: tuple["Condition", ...]


class AnyOf(_Frozen):
    any: tuple["Condition", ...]


class Not(_Frozen):
    not_: "Condition" = Field(alias="not")


# --- Effects: each one is a mapping with exactly one key ----------------------


class Give(_Frozen):
    """Moves the item into the inventory, wherever it was."""

    give: Id


class Remove(_Frozen):
    """Takes the item out of play."""

    remove: Id


class Placement(_Frozen):
    item: Id
    room: Id


class Place(_Frozen):
    place: Placement


class SetFlag(_Frozen):
    set_flag: Id


class ClearFlag(_Frozen):
    clear_flag: Id


_TAG_OF_TYPE: dict[type[BaseModel], str] = {
    FlagSet: "flag",
    Has: "has",
    PlayerIn: "player_in",
    AllOf: "all",
    AnyOf: "any",
    Not: "not",
    Give: "give",
    Remove: "remove",
    Place: "place",
    SetFlag: "set_flag",
    ClearFlag: "clear_flag",
}


def _single_key(value: Any) -> str | None:
    if isinstance(value, dict):
        return next(iter(value)) if len(value) == 1 else None
    return _TAG_OF_TYPE.get(type(value))


def _list_means_all(value: Any) -> Any:
    return {"all": value} if isinstance(value, list) else value


Condition = Annotated[
    Union[
        Annotated[FlagSet, Tag("flag")],
        Annotated[Has, Tag("has")],
        Annotated[PlayerIn, Tag("player_in")],
        Annotated[AllOf, Tag("all")],
        Annotated[AnyOf, Tag("any")],
        Annotated[Not, Tag("not")],
    ],
    Discriminator(
        _single_key,
        custom_error_type="invalid_condition",
        custom_error_message="a condition needs exactly one of the keys: flag, has, player_in, all, any, not",
    ),
    BeforeValidator(_list_means_all),
]

Effect = Annotated[
    Union[
        Annotated[Give, Tag("give")],
        Annotated[Remove, Tag("remove")],
        Annotated[Place, Tag("place")],
        Annotated[SetFlag, Tag("set_flag")],
        Annotated[ClearFlag, Tag("clear_flag")],
    ],
    Discriminator(
        _single_key,
        custom_error_type="invalid_effect",
        custom_error_message="an effect needs exactly one of the keys: give, remove, place, set_flag, clear_flag",
    ),
]

AllOf.model_rebuild()
AnyOf.model_rebuild()
Not.model_rebuild()


# --- World --------------------------------------------------------------------


class TextVariant(_Frozen):
    """Replaces the description while its condition holds; the first match wins."""

    when: Condition
    text: Text


class Exit(_Frozen):
    to: Id
    when: Condition | None = None
    otherwise: Text | None = None


class Room(_Frozen):
    id: Id
    name: Text
    description: Text
    variants: tuple[TextVariant, ...] = ()
    exits: dict[Direction, Exit] = {}


class Item(_Frozen):
    id: Id
    name: Text
    aliases: tuple[Text, ...] = ()
    description: Text
    # A room id, INVENTORY, or None when the item enters play only through an effect.
    location: Id | None
    # Scenery can't be taken and isn't listed: the room description already mentions it.
    scenery: bool = False
    variants: tuple[TextVariant, ...] = ()


class Trigger(_Frozen):
    verb: Verb
    target: Id
    with_: Id | None = Field(default=None, alias="with")


class Rule(_Frozen):
    id: Id
    trigger: Trigger
    when: Condition | None = None
    otherwise: Text | None = None
    effects: tuple[Effect, ...] = ()
    text: Text


class Ending(_Frozen):
    when: Condition
    text: Text


class GameInfo(_Frozen):
    title: Text
    intro: Text
    start_room: Id
    endings: tuple[Ending, ...]

    @field_validator("endings")
    @classmethod
    def _at_least_one_ending(cls, endings: tuple[Ending, ...]) -> tuple[Ending, ...]:
        # An "after" validator, so a malformed ending doesn't also report "no endings".
        if not endings:
            raise ValueError("the game needs at least one ending")
        return endings


class World(_Frozen):
    game: GameInfo
    rooms: dict[Id, Room]
    items: dict[Id, Item] = {}
    rules: dict[Id, Rule] = {}

    @model_validator(mode="before")
    @classmethod
    def _ids_from_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for section in ("rooms", "items", "rules"):
            entries = data.get(section)
            if isinstance(entries, dict):
                data[section] = {key: _with_id(section, key, value) for key, value in entries.items()}
        return data


def _with_id(section: str, key: str, value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    if "id" in value:
        raise ValueError(f"{section}.{key}: don't write 'id', the key is already the id")
    return {**value, "id": key}


# --- Game state ---------------------------------------------------------------


class GameState(BaseModel):
    """Everything that changes during a game; the engine is its only writer."""

    model_config = ConfigDict(extra="forbid")

    current_room: Id
    # Every item of the world: a room id, INVENTORY, or None when out of play.
    item_locations: dict[Id, Id | None]
    flags: set[Id] = Field(default_factory=set)
    visited: set[Id] = Field(default_factory=set)
    turns: int = 0
    finished: bool = False

    @classmethod
    def new(cls, world: World) -> "GameState":
        return cls(
            current_room=world.game.start_room,
            item_locations={item.id: item.location for item in world.items.values()},
            visited={world.game.start_room},
        )


# --- Actions and outcomes -----------------------------------------------------


class Action(_Frozen):
    """What the player wants to do, with items already resolved to ids (by the parser or the LLM)."""

    verb: Verb | Command
    target: Id | None = None
    with_: Id | None = Field(default=None, alias="with")
    direction: Direction | None = None

    @model_validator(mode="after")
    def _fields_fit_the_verb(self) -> "Action":
        if self.verb is Command.GO:
            if self.direction is None or self.target is not None or self.with_ is not None:
                raise ValueError("'vai' needs a direction and no items")
        elif isinstance(self.verb, Command):
            if self.direction is not None or self.target is not None or self.with_ is not None:
                raise ValueError(f"'{self.verb}' takes neither items nor a direction")
        else:
            if self.target is None or self.direction is not None:
                raise ValueError(f"'{self.verb}' needs a target and no direction")
            if self.with_ == self.target:
                raise ValueError("target and with must be two different items")
        return self


class RoomView(_Frozen):
    """The room as the player sees it now: description variant chosen, only portable items listed."""

    id: Id
    name: Text
    description: Text
    items: tuple[Id, ...]
    exits: tuple[Direction, ...]
    first_visit: bool


class Outcome(_Frozen):
    """What an action produced, for the narrator: the engine has already applied it to the state."""

    # False when the engine refused the action or nothing reacted to it; the state is then unchanged.
    ok: bool
    # Rule text, item description or engine message.
    text: Text | None = None
    # Set when the player enters a room, looks around, or starts the game.
    room: RoomView | None = None
    inventory: tuple[Id, ...] | None = None
    # Set on the action that ends the game.
    ending: Text | None = None
