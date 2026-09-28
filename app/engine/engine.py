"""The game engine: the only code that changes a GameState.

It executes an Action against the world's rules and returns an Outcome, which app/engine/text.py
turns into text. Every check runs before the state is touched, so a refused action leaves it unchanged.
"""

from typing import Any

from pydantic import ValidationError

from app.engine.models import (
    INVENTORY,
    Action,
    AllOf,
    AnyOf,
    Character,
    ClearFlag,
    Command,
    Condition,
    Conversation,
    Direction,
    Effect,
    FlagSet,
    GameState,
    Gender,
    Give,
    Has,
    Item,
    Not,
    Outcome,
    Place,
    PlayerIn,
    Remove,
    Room,
    RoomView,
    Rule,
    SetFlag,
    TextVariant,
    Topic,
    Verb,
    World,
)
from app.engine.parser import significant_words, words_of

# Engine messages. They never name the item, so they need no article; a few agree with a plural
# item (_PLURAL below).
GAME_OVER = "La partita è finita."
NO_EXIT = "Non puoi andare da quella parte."
NOT_HERE = "Non vedi niente del genere qui."
NOBODY_HERE = "Non vedi nessuno del genere qui."
OUT_OF_REACH = "Non ci arrivi."
NOTHING_HAPPENS = "Non succede niente."
DONE = "Fatto."
CANT_TAKE = "Non si può prendere."
ALREADY_HAVE = "Ce l'hai già."
DONT_HAVE = "Non ce l'hai."
CANT_OPEN = "Non si può aprire."
CANT_CLOSE = "Non si può chiudere."
NOTHING_TO_READ = "Non c'è niente da leggere."
NOT_WANTED = "Non sa che farsene."
GIVE_TO_WHOM = "A chi?"
NOBODY_TO_GIVE_TO = "Qui non c'è nessuno."
CANT_GIVE = "Non si può dare."

_NOTHING_WITHOUT_A_RULE = {Verb.OPEN: CANT_OPEN, Verb.CLOSE: CANT_CLOSE, Verb.READ: NOTHING_TO_READ}

# The messages above for a plural item: "Ce le hai già." for the berries. By gender where the
# pronoun shows it.
_PLURAL = {
    ALREADY_HAVE: {Gender.MASCULINE: "Ce li hai già.", Gender.FEMININE: "Ce le hai già."},
    DONT_HAVE: {Gender.MASCULINE: "Non ce li hai.", Gender.FEMININE: "Non ce le hai."},
    CANT_TAKE: "Non si possono prendere.",
    CANT_OPEN: "Non si possono aprire.",
    CANT_CLOSE: "Non si possono chiudere.",
}


def _said_of(thing: Item | Character, message: str) -> str:
    """The engine's message, agreeing with a plural item or character."""
    plural = _PLURAL.get(message) if thing.plural else None
    if plural is None:
        return message
    return plural if isinstance(plural, str) else plural[thing.gender]


class StateError(Exception):
    """A saved state doesn't fit this world: the world changed, or the state was edited by hand."""


class Engine:
    def __init__(self, world: World) -> None:
        self.world = world

    def new_game(self) -> tuple[GameState, Outcome]:
        state = GameState.new(self.world)
        return state, Outcome(ok=True, text=self.world.game.intro, room=self._room_view(state, first_visit=True))

    def restore(self, data: Any) -> GameState:
        """A state saved elsewhere (the browser keeps it), checked against this world.

        Texts may have changed since it was saved; rooms and items must still be the same.
        """
        try:
            state = GameState.model_validate(data)
        except ValidationError as exc:
            raise StateError(f"not a game state: {exc}") from None
        rooms, items = self.world.rooms, self.world.items
        problems = []
        if state.current_room not in rooms:
            problems.append(f"unknown room '{state.current_room}'")
        problems += [f"item '{item_id}' is missing" for item_id in items if item_id not in state.item_locations]
        for item_id, location in state.item_locations.items():
            if item_id not in items:
                problems.append(f"unknown item '{item_id}'")
            elif location not in (None, INVENTORY) and location not in rooms:
                problems.append(f"item '{item_id}' in unknown room '{location}'")
        problems += [f"unknown visited room '{room_id}'" for room_id in sorted(state.visited) if room_id not in rooms]
        problems += [f"unknown seen item '{item_id}'" for item_id in sorted(state.seen) if item_id not in items]
        if problems:
            raise StateError("; ".join(problems))
        return state

    def in_reach(self, state: GameState) -> list[Item]:
        """Items the player can act on: those in the current room (scenery included) and those carried."""
        return self._items_in(state, state.current_room, INVENTORY)

    def visible(self, state: GameState) -> list[Item]:
        """Items in sight from the current room but out of reach (`visible_from`), once the player
        has seen them: they can be named, and only rules can act on them."""
        in_reach = {item.id for item in self.in_reach(state)}
        return [
            item
            for item in self.world.items.values()
            if item.visible_from is not None
            and item.id in state.seen
            and item.visible_from.room == state.current_room
            and item.id not in in_reach
            and (item.visible_from.when is None or holds(item.visible_from.when, state))
        ]

    def known_exits(self, state: GameState) -> list[tuple[Direction, Room | None]]:
        """The exits of the current room in compass order, each with its destination if the player
        knows it: already visited, or named in the description they are reading now. So "vai in
        cucina" works for a kitchen the courtyard mentions, and doesn't reveal rooms never seen."""
        room = self.world.rooms[state.current_room]
        described = set(words_of(_description(room, state)))
        exits = []
        for direction in sorted(room.exits, key=list(Direction).index):
            destination = self.world.rooms[room.exits[direction].to]
            named = set(significant_words(destination.name)) <= described
            exits.append((direction, destination if destination.id in state.visited or named else None))
        return exits

    def characters_here(self, state: GameState) -> list[tuple[Character, list[Topic]]]:
        """The characters in the current room, each with the topics the player can ask about now."""
        return [
            (character, [topic for topic in character.topics.values() if topic.when is None or holds(topic.when, state)])
            for character in self.world.characters.values()
            if character.location == state.current_room
        ]

    def expects(self, action: Action) -> bool:
        """Whether the world foresees the action: a command, talking, a rule that reacts to it, a verb
        that does something by itself (esamina, prendi, lascia) with no tool it would ignore, or giving,
        which at worst is refused."""
        if isinstance(action.verb, Command | Conversation) or action.verb is Verb.GIVE:
            return True
        if self._find_rule(action) is not None:
            return True
        return action.with_ is None and action.verb in (Verb.EXAMINE, Verb.TAKE, Verb.DROP)

    def execute(self, state: GameState, action: Action) -> Outcome:
        """Applies the action to `state` and tells what happened; the first ending that holds closes the game."""
        if state.finished:
            return Outcome(ok=False, text=GAME_OVER)
        outcome = self._perform(state, action)
        state.turns += 1
        ending = next((ending for ending in self.world.game.endings if holds(ending.when, state)), None)
        if ending is not None:
            state.finished = True
            outcome = outcome.model_copy(update={"ending": ending.text})
        return outcome

    def _perform(self, state: GameState, action: Action) -> Outcome:
        match action.verb:
            case Command.GO:
                return self._go(state, action.direction)
            case Command.LOOK:
                return Outcome(ok=True, room=self._room_view(state, first_visit=False))
            case Command.INVENTORY:
                return Outcome(ok=True, inventory=tuple(item.id for item in self._items_in(state, INVENTORY)))
            case Conversation.TALK | Conversation.ASK:
                return self._talk(state, action)
            case Verb.GIVE:
                return self._give(state, action)
        return self._act_on_items(state, action)

    def _go(self, state: GameState, direction: Direction) -> Outcome:
        exit_ = self.world.rooms[state.current_room].exits.get(direction)
        if exit_ is None:
            return Outcome(ok=False, text=NO_EXIT)
        if exit_.when is not None and not holds(exit_.when, state):
            return Outcome(ok=False, text=exit_.otherwise or NO_EXIT)
        first_visit = exit_.to not in state.visited
        state.current_room = exit_.to
        state.visited.add(exit_.to)
        return Outcome(ok=True, room=self._room_view(state, first_visit))

    def _talk(self, state: GameState, action: Action) -> Outcome:
        """The greeting, or the answer about a topic the character knows; about anything else, `unknown`."""
        here = next((pair for pair in self.characters_here(state) if pair[0].id == action.target), None)
        if here is None:
            return Outcome(ok=False, text=NOBODY_HERE)
        character, topics = here
        if action.verb is Conversation.TALK:
            return Outcome(ok=True, text=_first_variant(character.greeting_variants, character.greeting, state))
        topic = next((topic for topic in topics if topic.id == action.topic), None)
        if topic is None:
            return Outcome(ok=False, text=character.unknown)
        for effect in topic.effects:
            _apply(effect, state)
        return Outcome(ok=True, text=_first_variant(topic.variants, topic.text, state))

    def _act_on_items(self, state: GameState, action: Action) -> Outcome:
        in_reach = {item.id for item in self.in_reach(state)} | {person.id for person, _ in self.characters_here(state)}
        in_sight = {item.id for item in self.visible(state)}
        items = {action.target, action.with_} - {None}
        if not items <= in_reach | in_sight:
            return Outcome(ok=False, text=NOT_HERE)
        rule = self._find_rule(action)
        if rule is None:
            if items & in_sight:
                return Outcome(ok=False, text=OUT_OF_REACH)
            if action.target in self.world.characters:
                return self._default_on_character(state, action.verb, self.world.characters[action.target])
            return self._default(state, action.verb, self.world.items[action.target])
        if items & self.world.characters.keys():
            # Only "dai" rules name characters: "usa X con il personaggio" gives, with the same checks.
            return self._give(state, action)
        return self._apply_rule(state, rule)

    def _give(self, state: GameState, action: Action) -> Outcome:
        """"dai X a Y": a character here receives an item the player carries. The two may come in
        either order ("dai al pellegrino la corda"); without a character, the only one here takes it.
        With no rule for it the character refuses (`refuses`), and nothing changes."""
        named = [thing_id for thing_id in (action.target, action.with_) if thing_id is not None]
        people = [thing_id for thing_id in named if thing_id in self.world.characters]
        items = [thing_id for thing_id in named if thing_id in self.world.items]
        if len(items) != 1 or len(people) > 1:
            return Outcome(ok=False, text=CANT_GIVE)
        here = [character.id for character, _ in self.characters_here(state)]
        if not people:
            if len(here) != 1:
                return Outcome(ok=False, text=GIVE_TO_WHOM if here else NOBODY_TO_GIVE_TO)
            people = here
        if people[0] not in here:
            return Outcome(ok=False, text=NOBODY_HERE)
        if state.item_locations[items[0]] != INVENTORY:
            return Outcome(ok=False, text=_said_of(self.world.items[items[0]], DONT_HAVE))
        rule = self._find_rule(Action(verb=Verb.GIVE, target=items[0], with_=people[0]))
        if rule is None:
            return Outcome(ok=False, text=self.world.characters[people[0]].refuses or NOT_WANTED)
        return self._apply_rule(state, rule)

    def _apply_rule(self, state: GameState, rule: Rule) -> Outcome:
        """The rule's text and effects, or `otherwise` when its condition doesn't hold."""
        if rule.when is not None and not holds(rule.when, state):
            return Outcome(ok=False, text=rule.otherwise or NOTHING_HAPPENS)
        for effect in rule.effects:
            _apply(effect, state)
        return Outcome(ok=True, text=rule.text)

    def _default(self, state: GameState, verb: Verb, item: Item) -> Outcome:
        """What a verb does when no rule reacts to it; a tool, if any, is ignored."""
        location = state.item_locations[item.id]
        match verb:
            case Verb.EXAMINE:
                state.seen.update(item.reveals)
                return Outcome(ok=True, text=_description(item, state))
            case Verb.TAKE if item.scenery:
                return Outcome(ok=False, text=_said_of(item, CANT_TAKE))
            case Verb.TAKE if location == INVENTORY:
                return Outcome(ok=False, text=_said_of(item, ALREADY_HAVE))
            case Verb.TAKE:
                state.item_locations[item.id] = INVENTORY
                return Outcome(ok=True, text=DONE)
            case Verb.DROP if location != INVENTORY:
                return Outcome(ok=False, text=_said_of(item, DONT_HAVE))
            case Verb.DROP:
                state.item_locations[item.id] = state.current_room
                return Outcome(ok=True, text=DONE)
        return Outcome(ok=False, text=_said_of(item, _NOTHING_WITHOUT_A_RULE.get(verb, NOTHING_HAPPENS)))

    def _default_on_character(self, state: GameState, verb: Verb, character: Character) -> Outcome:
        """Characters can be looked at; the other verbs on them do nothing (rules never name them)."""
        match verb:
            case Verb.EXAMINE:
                return Outcome(ok=True, text=_description(character, state))
            case Verb.TAKE:
                return Outcome(ok=False, text=_said_of(character, CANT_TAKE))
            case Verb.DROP:
                return Outcome(ok=False, text=_said_of(character, DONT_HAVE))
        return Outcome(ok=False, text=_said_of(character, _NOTHING_WITHOUT_A_RULE.get(verb, NOTHING_HAPPENS)))

    def _find_rule(self, action: Action) -> Rule | None:
        """The first rule with a trigger for this verb on exactly these items, in either order.

        "usa X con Y" is what players write for anything: without a rule of its own,
        it takes the first rule of any verb on the same two items (apri porta con chiave).
        """
        items = {action.target, action.with_} - {None}
        same_items = [
            (rule, trigger)
            for rule in self.world.rules.values()
            for trigger in rule.triggers
            if {trigger.target, trigger.with_} - {None} == items
        ]
        for rule, trigger in same_items:
            if trigger.verb == action.verb:
                return rule
        if action.verb is Verb.USE and action.with_ is not None and same_items:
            return same_items[0][0]
        return None

    def _room_view(self, state: GameState, first_visit: bool) -> RoomView:
        room = self.world.rooms[state.current_room]
        return RoomView(
            id=room.id,
            name=room.name,
            description=_description(room, state),
            items=tuple(item.id for item in self._items_in(state, room.id) if not item.scenery),
            exits=tuple(room.exits),
            first_visit=first_visit,
            characters=tuple(character.id for character, _ in self.characters_here(state)),
        )

    def _items_in(self, state: GameState, *places: str) -> list[Item]:
        """Items now in any of the places (room ids or INVENTORY), in the order of the world."""
        return [item for item in self.world.items.values() if state.item_locations[item.id] in places]


def holds(condition: Condition, state: GameState) -> bool:
    match condition:
        case FlagSet(flag=flag):
            return flag in state.flags
        case Has(has=item_id):
            return state.item_locations.get(item_id) == INVENTORY
        case PlayerIn(player_in=room_id):
            return state.current_room == room_id
        case AllOf(all=parts):
            return all(holds(part, state) for part in parts)
        case AnyOf(any=parts):
            return any(holds(part, state) for part in parts)
        case Not(not_=inner):
            return not holds(inner, state)
    raise TypeError(f"unknown condition: {condition!r}")


def _apply(effect: Effect, state: GameState) -> None:
    match effect:
        case Give(give=item_id):
            state.item_locations[item_id] = INVENTORY
        case Remove(remove=item_id):
            state.item_locations[item_id] = None
        case Place(place=placement):
            state.item_locations[placement.item] = placement.room
        case SetFlag(set_flag=flag):
            state.flags.add(flag)
        case ClearFlag(clear_flag=flag):
            state.flags.discard(flag)


def _description(thing: Room | Item | Character, state: GameState) -> str:
    """The first variant whose condition holds, otherwise the plain description."""
    return _first_variant(thing.variants, thing.description, state)


def _first_variant(variants: tuple[TextVariant, ...], text: str, state: GameState) -> str:
    return next((variant.text for variant in variants if holds(variant.when, state)), text)
