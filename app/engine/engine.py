"""The game engine: the only code that changes a GameState.

It executes an Action against the world's rules and returns an Outcome, which app/engine/text.py
turns into text. Every check runs before the state is touched, so a refused action leaves it unchanged.
"""

from app.engine.models import (
    INVENTORY,
    Action,
    AllOf,
    AnyOf,
    ClearFlag,
    Command,
    Condition,
    Direction,
    Effect,
    FlagSet,
    GameState,
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
    Verb,
    World,
)
from app.engine.parser import significant_words, words_of

# Engine messages. They never name the item, so they need no article or gender.
GAME_OVER = "La partita è finita."
NO_EXIT = "Non puoi andare da quella parte."
NOT_HERE = "Non vedi niente del genere qui."
NOTHING_HAPPENS = "Non succede niente."
DONE = "Fatto."
CANT_TAKE = "Non si può prendere."
ALREADY_HAVE = "Ce l'hai già."
DONT_HAVE = "Non ce l'hai."
CANT_OPEN = "Non si può aprire."
CANT_CLOSE = "Non si può chiudere."
NOTHING_TO_READ = "Non c'è niente da leggere."

_NOTHING_WITHOUT_A_RULE = {Verb.OPEN: CANT_OPEN, Verb.CLOSE: CANT_CLOSE, Verb.READ: NOTHING_TO_READ}


class Engine:
    def __init__(self, world: World) -> None:
        self.world = world

    def new_game(self) -> tuple[GameState, Outcome]:
        state = GameState.new(self.world)
        return state, Outcome(ok=True, text=self.world.game.intro, room=self._room_view(state, first_visit=True))

    def in_reach(self, state: GameState) -> list[Item]:
        """Items the player can act on: those in the current room (scenery included) and those carried."""
        return self._items_in(state, state.current_room, INVENTORY)

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

    def _act_on_items(self, state: GameState, action: Action) -> Outcome:
        in_reach = {item.id for item in self.in_reach(state)}
        if action.target not in in_reach or (action.with_ is not None and action.with_ not in in_reach):
            return Outcome(ok=False, text=NOT_HERE)
        rule = self._find_rule(action)
        if rule is None:
            return self._default(state, action.verb, self.world.items[action.target])
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
                return Outcome(ok=True, text=_description(item, state))
            case Verb.TAKE if item.scenery:
                return Outcome(ok=False, text=CANT_TAKE)
            case Verb.TAKE if location == INVENTORY:
                return Outcome(ok=False, text=ALREADY_HAVE)
            case Verb.TAKE:
                state.item_locations[item.id] = INVENTORY
                return Outcome(ok=True, text=DONE)
            case Verb.DROP if location != INVENTORY:
                return Outcome(ok=False, text=DONT_HAVE)
            case Verb.DROP:
                state.item_locations[item.id] = state.current_room
                return Outcome(ok=True, text=DONE)
        return Outcome(ok=False, text=_NOTHING_WITHOUT_A_RULE.get(verb, NOTHING_HAPPENS))

    def _find_rule(self, action: Action) -> Rule | None:
        """The first rule for this verb on exactly these items, in either order.

        "usa X con Y" is what players write for anything: without a rule of its own,
        it takes the first rule of any verb on the same two items (apri porta con chiave).
        """
        items = {action.target, action.with_} - {None}
        same_items = [
            rule for rule in self.world.rules.values() if {rule.trigger.target, rule.trigger.with_} - {None} == items
        ]
        for rule in same_items:
            if rule.trigger.verb == action.verb:
                return rule
        if action.verb is Verb.USE and action.with_ is not None and same_items:
            return same_items[0]
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


def _description(thing: Room | Item, state: GameState) -> str:
    """The first variant whose condition holds, otherwise the plain description."""
    for variant in thing.variants:
        if holds(variant.when, state):
            return variant.text
    return thing.description
