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
    GIVE = "dai"  # to a character: in a rule, `with` is the character who receives the item
    JUMP = "salta"  # into something: "salta nel pozzo"


class Command(StrEnum):
    """Verbs without items: the engine handles them itself and rules can't react to them."""

    GO = "vai"
    LOOK = "guarda"
    INVENTORY = "inventario"


class Conversation(StrEnum):
    """Verbs on characters: the character answers with its author's texts; rules can't react to them."""

    TALK = "parla"
    ASK = "chiedi"


class Gesture(StrEnum):
    """What the player says to a character besides greeting it and asking about a topic."""

    FAREWELL = "congedo"
    THANKS = "grazie"
    APOLOGY = "scuse"
    HOW_ARE_YOU = "come_stai"
    WHO_ARE_YOU = "chi_sei"
    RUDENESS = "scortesia"


# The words for the gestures, as the interpreter's model and the authors say them; None is the greeting.
GESTURE_LABELS: dict[str, Gesture | None] = {
    "saluto": None,
    "congedo": Gesture.FAREWELL,
    "grazie": Gesture.THANKS,
    "scuse": Gesture.APOLOGY,
    "come stai": Gesture.HOW_ARE_YOU,
    "chi sei": Gesture.WHO_ARE_YOU,
    "scortesia": Gesture.RUDENESS,
}


class Gender(StrEnum):
    """Grammatical gender of a name: it chooses the article (la corda, il gancio)."""

    MASCULINE = "m"
    FEMININE = "f"


class Article(StrEnum):
    """How a name takes its article, when not like a common noun (il gancio, un gancio)."""

    DEFINITE = "definite"  # always the definite article: "il dottor Ferri", never "un dottor Ferri"
    NONE = "none"  # no article: a first name, "Ettore", "a Ettore", "di Livia"


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
    otherwise_variants: tuple[TextVariant, ...] = ()  # the first that holds replaces otherwise


class Room(_Frozen):
    id: Id
    name: Text
    # Other ways to name the place, also who or what is there: "vai dall'orso" for the den.
    aliases: tuple[Text, ...] = ()
    description: Text
    variants: tuple[TextVariant, ...] = ()
    exits: dict[Direction, Exit] = {}


class Visibility(_Frozen):
    """Where an item is seen without being within reach (the key at the bottom of the well)."""

    room: Id
    when: Condition | None = None


class Item(_Frozen):
    id: Id
    name: Text
    gender: Gender
    plural: bool = False
    article: Article | None = None  # a proper name or a title (Article); without it, like a common noun
    aliases: tuple[Text, ...] = ()
    description: Text
    # A room id, INVENTORY, or None when the item enters play only through an effect.
    location: Id | None
    # Scenery can't be taken and isn't listed: the room description already mentions it.
    scenery: bool = False
    variants: tuple[TextVariant, ...] = ()
    # Seen from a room while out of reach: the player can name it, only rules can act on it.
    # It has to be seen first: another item's description reveals it (the well shows the key).
    visible_from: Visibility | None = None
    # Items its description shows, when the player examines it: from then on they are seen.
    reveals: tuple[Id, ...] = ()


class Trigger(_Frozen):
    verb: Verb
    target: Id
    with_: Id | None = Field(default=None, alias="with")


def _one_means_a_list(value: Any) -> Any:
    return [value] if isinstance(value, dict) else value


class Rule(_Frozen):
    id: Id
    # Written `trigger` in YAML: one trigger, or a list of equivalent ways to solve the same puzzle.
    triggers: Annotated[tuple[Trigger, ...], BeforeValidator(_one_means_a_list)] = Field(alias="trigger", min_length=1)
    when: Condition | None = None
    otherwise: Text | None = None
    otherwise_variants: tuple[TextVariant, ...] = ()  # the first that holds replaces otherwise
    effects: tuple[Effect, ...] = ()
    text: Text


class Topic(_Frozen):
    """Something a character can be asked about. Name and gender make "chiedi al pellegrino della torre"."""

    id: Id
    name: Text
    gender: Gender
    plural: bool = False
    article: Article | None = None  # a proper name or a title (Article); without it, like a common noun
    aliases: tuple[Text, ...] = ()
    # While false the character doesn't know the topic: it answers `unknown`, and the LLM isn't told.
    when: Condition | None = None
    text: Text
    variants: tuple[TextVariant, ...] = ()
    again: Text | None = None  # the answer from the second time on, unless a variant holds
    effects: tuple[Effect, ...] = ()


class Move(_Frozen):
    """Where a character is while a condition holds: Agnese on the floor the player has just opened."""

    when: Condition
    room: Id


class Line(_Frozen):
    """A character's answer to a gesture: the text, variants that follow the game, the second time."""

    text: Text
    variants: tuple[TextVariant, ...] = ()
    again: Text | None = None


class Character(_Frozen):
    """Someone the player can talk to: it greets, and answers about its topics with fixed texts."""

    id: Id
    name: Text
    gender: Gender
    plural: bool = False
    article: Article | None = None  # a proper name or a title (Article); without it, like a common noun
    aliases: tuple[Text, ...] = ()
    description: Text
    variants: tuple[TextVariant, ...] = ()
    location: Id  # a room: where the character is while none of its moves holds
    moves: tuple[Move, ...] = ()  # the first whose condition holds says where the character is now
    greeting: Text  # "parla con X"
    greeting_variants: tuple[TextVariant, ...] = ()  # the first that holds replaces the greeting
    greeting_again: Text | None = None  # the greeting from the second time on, unless a variant holds
    unknown: Text  # the answer about anything else
    refuses: Text | None = None  # "dai X" that no rule wants; without it, the engine's own answer
    gestures: dict[Gesture, Line] = {}  # without one, a plain answer with the character's name
    topics: dict[Id, Topic] = {}

    @model_validator(mode="before")
    @classmethod
    def _topic_ids_from_keys(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("topics"), dict):
            data = {**data, "topics": {key: _with_id("topics", key, value) for key, value in data["topics"].items()}}
        return data


class Ending(_Frozen):
    when: Condition
    text: Text
    death: bool = False  # the player dies: the game can go on from the beginning of the last act


class Act(_Frozen):
    """A part of the game (a floor of Valdimora). When its condition first holds the state is kept:
    after a death the game goes on from there."""

    name: Text  # read after "dall'inizio del": "secondo atto"
    when: Condition


class GameInfo(_Frozen):
    title: Text
    summary: Text  # one or two lines for the menu of the adventures
    # Examples for the LLM interpreter, in the prompt's format (app/llm/prompts.py): they go between
    # the generic ones and the dialogue.
    examples: Text | None = None
    intro: Text
    start_room: Id
    acts: tuple[Act, ...] = ()  # in order: each begins after the one before
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
    characters: dict[Id, Character] = {}

    @model_validator(mode="before")
    @classmethod
    def _ids_from_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for section in ("rooms", "items", "rules", "characters"):
            entries = data.get(section)
            if isinstance(entries, dict):
                data[section] = {key: _with_id(section, key, value) for key, value in entries.items()}
        return data

    def thing(self, thing_id: str) -> Item | Character:
        """An item or a character: actions name both by id (esamina il pellegrino)."""
        return self.items.get(thing_id) or self.characters[thing_id]


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
    # Items out of reach the player has seen (Item.reveals): only these can be named from afar.
    seen: set[Id] = Field(default_factory=set)
    # What the player has already said to whom: "livia:topic:contessa", "livia:gesture:grazie".
    asked: set[str] = Field(default_factory=set)
    # The character spoken to, asked or given something last: gestures and questions without a name go
    # to them, if they are here.
    last_speaker: Id | None = None
    turns: int = 0
    finished: bool = False
    # The game ended with a death (Ending.death): it can go on from the last act begun, if any.
    lost: bool = False
    # How many acts of the world have begun (GameInfo.acts), and the state when the last one began,
    # without its own checkpoint: after a death the game goes on from there.
    act: int = 0
    checkpoint: "GameState | None" = None

    @classmethod
    def new(cls, world: World) -> "GameState":
        return cls(
            current_room=world.game.start_room,
            item_locations={item.id: item.location for item in world.items.values()},
            visited={world.game.start_room},
        )


# --- Actions and outcomes -----------------------------------------------------


class Action(_Frozen):
    """What the player wants to do, with items and characters already resolved to ids (by the parser
    or the LLM). "chiedi" has the character as target and a topic of its own, None if it doesn't know it."""

    verb: Verb | Command | Conversation
    target: Id | None = None
    with_: Id | None = Field(default=None, alias="with")
    direction: Direction | None = None
    topic: Id | None = None
    gesture: Gesture | None = None  # only with "parla"; None is the greeting

    @model_validator(mode="after")
    def _fields_fit_the_verb(self) -> "Action":
        if self.topic is not None and self.verb is not Conversation.ASK:
            raise ValueError("only 'chiedi' has a topic")
        if self.gesture is not None and self.verb is not Conversation.TALK:
            raise ValueError("only 'parla' has a gesture")
        if isinstance(self.verb, Conversation):
            if self.target is None or self.with_ is not None or self.direction is not None:
                raise ValueError(f"'{self.verb}' needs a character and nothing else")
        elif self.verb is Command.GO:
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
    characters: tuple[Id, ...] = ()


class Outcome(_Frozen):
    """What an action produced: the engine has already applied it to the state."""

    # False when the engine refused the action or nothing reacted to it; the state is then unchanged.
    ok: bool
    # Rule text, item description or engine message.
    text: Text | None = None
    # Set when the player enters a room, looks around, or starts the game.
    room: RoomView | None = None
    inventory: tuple[Id, ...] | None = None
    # Set on the action that ends the game.
    ending: Text | None = None
