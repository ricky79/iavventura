"""The classic parser: turns simple Italian commands into an Action.

It is strict on purpose: a word it doesn't know makes the whole sentence not understood,
and freer sentences will go to the LLM interpreter. Items and characters are recognised by name
or alias, ignoring articles and prepositions, preferring those in reach and the longest name.
"""

import re
from collections.abc import Iterable, Sequence
from typing import NamedTuple

from app.engine.models import Action, Character, Command, Conversation, Direction, Item, Room, Topic, Verb, World
from app.engine.text import Named, plain

STOPWORDS = frozenset(
    """
    il lo la i gli le l un uno una
    di a ad da in con su per tra fra verso contro dentro
    del dello della dei degli delle dell al allo alla ai agli alle all
    dal dallo dalla dai dagli dalle dall nel nello nella nei negli nelle nell
    col coi sul sullo sulla sui sugli sulle sull
    """.split()
)

DIRECTIONS = {
    "nord": Direction.NORTH,
    "n": Direction.NORTH,
    "sud": Direction.SOUTH,
    "s": Direction.SOUTH,
    "est": Direction.EAST,
    "e": Direction.EAST,
    "ovest": Direction.WEST,
    "o": Direction.WEST,
    "su": Direction.UP,
    "sali": Direction.UP,
    "salgo": Direction.UP,
    "arrampicati": Direction.UP,
    "giu": Direction.DOWN,
    "scendi": Direction.DOWN,
    "scendo": Direction.DOWN,
}

GO_WORDS = frozenset({"vai", "va", "vado", "cammina", "torna", "torno", "ritorna", "ritorno", "entra", "entro"})
LOOK_WORDS = frozenset({"guarda", "g", "descrivi"})  # with an item they mean "esamina"
INVENTORY_WORDS = frozenset({"inventario", "inv", "i"})
TALK_WORDS = frozenset({"parla", "saluta"})
ASK_WORDS = frozenset({"chiedi", "domanda"})

ITEM_VERBS = {
    "esamina": Verb.EXAMINE,
    "x": Verb.EXAMINE,
    "osserva": Verb.EXAMINE,
    "ispeziona": Verb.EXAMINE,
    "prendi": Verb.TAKE,
    "raccogli": Verb.TAKE,
    "afferra": Verb.TAKE,
    "piglia": Verb.TAKE,
    "lascia": Verb.DROP,
    "posa": Verb.DROP,
    "molla": Verb.DROP,
    "usa": Verb.USE,
    "utilizza": Verb.USE,
    "adopera": Verb.USE,
    "apri": Verb.OPEN,
    "chiudi": Verb.CLOSE,
    "spingi": Verb.PUSH,
    "premi": Verb.PUSH,
    "tira": Verb.PULL,
    "leggi": Verb.READ,
    # "dai" is also "da" + "i" among the stopwords: only as the first word is it the verb.
    "dai": Verb.GIVE,
    "da": Verb.GIVE,  # "dà", without its accent
    "porgi": Verb.GIVE,
    "offri": Verb.GIVE,
    "regala": Verb.GIVE,
    "consegna": Verb.GIVE,
    "ecco": Verb.GIVE,  # "ecco le more": handing over. Not "tieni", which is also "hold".
    "salta": Verb.JUMP,
    "salto": Verb.JUMP,
    "tuffati": Verb.JUMP,
    "buttati": Verb.JUMP,  # not "butta": "butta la corda nel pozzo" is throwing it
    "gettati": Verb.JUMP,
    "lanciati": Verb.JUMP,
}


class Ambiguous(NamedTuple):
    """Several items or characters in reach answer to the same words: the player has to say which one."""

    candidates: tuple[Item | Character, ...]


def parse(
    text: str,
    world: World,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Sequence[tuple[Character, Sequence[Topic]]] = (),
) -> Action | Ambiguous | None:
    """None when the sentence isn't a simple command made only of known words.

    `in_reach` also holds the items in sight (Engine.visible): the parser prefers them all alike.
    `exits` are the current room's exits with the destinations the player knows (Engine.known_exits):
    they let "vai in cucina" go through the exit that leads there.
    `characters` are those in the room, with the topics the player can ask about (Engine.characters_here).
    """
    words = words_of(text)
    if not words:
        return None
    first, rest = words[0], words[1:]

    if first in DIRECTIONS and not rest:
        return Action(verb=Command.GO, direction=DIRECTIONS[first])
    if first in GO_WORDS:
        # "su" is also a preposition, so directions are kept before dropping the stopwords.
        rest = [word for word in rest if word in DIRECTIONS or word not in STOPWORDS]
        if len(rest) == 1 and rest[0] in DIRECTIONS:
            return Action(verb=Command.GO, direction=DIRECTIONS[rest[0]])
        for direction, room in exits:
            if room is not None and tuple(rest) in {significant_words(name) for name in (room.name, *room.aliases)}:
                return Action(verb=Command.GO, direction=direction)
        return None
    if first in INVENTORY_WORDS:
        return Action(verb=Command.INVENTORY) if not rest else None
    if first in LOOK_WORDS and not rest:
        return Action(verb=Command.LOOK)
    if first in TALK_WORDS or first in ASK_WORDS:
        return _conversation(first in ASK_WORDS, [word for word in rest if word not in STOPWORDS], world, characters)

    verb = Verb.EXAMINE if first in LOOK_WORDS else ITEM_VERBS.get(first)
    if verb is None:
        return None
    people = [character for character, _ in characters]
    mentions = _mentions([word for word in rest if word not in STOPWORDS], world, [*in_reach, *people])
    if mentions is None or not 1 <= len(mentions) <= 2:
        return None
    for candidates in mentions:
        if len(candidates) > 1:
            return Ambiguous(candidates)
    ids = [candidates[0].id for candidates in mentions]
    if len(set(ids)) < len(ids):
        return None
    return Action(verb=verb, target=ids[0], with_=ids[1] if len(ids) == 2 else None)


def find_topic(words: Sequence[str], topics: Iterable[Topic]) -> Topic | None:
    """The topic whose name or an alias is exactly these significant words."""
    key = tuple(words)
    return next(
        (topic for topic in topics if any(significant_words(name) == key for name in (topic.name, *topic.aliases))),
        None,
    )


def _conversation(
    asking: bool, words: list[str], world: World, characters: Sequence[tuple[Character, Sequence[Topic]]]
) -> Action | Ambiguous | None:
    """"parla con X", "saluta X", "chiedi a X di Y"; without X, the only character here.
    A question about something that is no topic the player knows goes to the LLM."""
    people = [character for character, _ in characters]
    found = _longest(words, 0, _phrases(people)) if words else None
    if found is None and words:
        # A character elsewhere: any one will do, the engine answers that nobody like that is here.
        found = _longest(words, 0, _phrases(world.characters.values()))
        if found is not None:
            found = (found[0], found[1][:1])
    if found is not None:
        length, candidates = found
        if len(candidates) > 1:
            return Ambiguous(candidates)
        character, words = candidates[0], words[length:]
    elif len(people) == 1:
        character = people[0]
    else:
        return None
    if not asking:
        return Action(verb=Conversation.TALK, target=character.id) if not words else None
    topics = next((topics for person, topics in characters if person.id == character.id), ())
    topic = find_topic(words, topics) if words else None
    return Action(verb=Conversation.ASK, target=character.id, topic=topic.id) if topic else None


def words_of(text: str) -> list[str]:
    """Lowercase words without accents or punctuation; apostrophes split words (l'uncino)."""
    return re.findall(r"[a-z0-9]+", plain(text))


def significant_words(text: str) -> tuple[str, ...]:
    """The words without articles and prepositions: "la porta della torre" -> ("porta", "torre")."""
    return tuple(word for word in words_of(text) if word not in STOPWORDS)


def is_named(thing: Named | Room, words: Sequence[str]) -> bool:
    """Whether the words name the thing: every significant word of its name or of an alias is there,
    at least nearly ("scuderie" for "Scuderia", "ciave" for "chiave"). To check the LLM's answers,
    not by the parser, which wants the exact words."""
    return bool(names_said(thing, words))


def names_said(thing: Named | Room, words: Sequence[str]) -> list[tuple[str, ...]]:
    """The names and aliases of the thing that the words say (see is_named), as significant words."""
    names = dict.fromkeys(significant_words(name) for name in (thing.name, *thing.aliases))
    return [name for name in names if all(any(_nearly(word, name_word) for word in words) for name_word in name)]


def topics_named(character: Character, topics: Iterable[Topic], words: Sequence[str]) -> list[Topic]:
    """The topics the words name, the last named first ("cosa serve per prendere la piuma?" is about
    the feather); the character's own name is no topic ("pellegrino, cosa sai della torre?")."""
    words = [word for word in words if not is_named(character, [word])]
    named = [(position, topic) for topic in topics if (position := _last_mention(topic, words)) is not None]
    return [topic for _, topic in sorted(named, key=lambda pair: -pair[0])]


def _last_mention(thing: Named, words: Sequence[str]) -> int | None:
    """Where the words last name the thing, if they do."""
    said = [name_word for name in names_said(thing, words) for name_word in name]
    return max((index for index, word in enumerate(words) if any(_nearly(word, other) for other in said)), default=None)


def names_the_way(direction: Direction, words: Sequence[str], exits: Sequence[tuple[Direction, Room | None]]) -> bool:
    """Whether a free sentence names the way out: the direction (not by a single letter: "e" is also
    "and"), or the known room it leads to, by its name or an alias, at least nearly."""
    if any(len(word) > 1 and DIRECTIONS.get(word) == direction for word in words):
        return True
    room = dict(exits).get(direction)
    return room is not None and is_named(room, words)


def _nearly(word: str, other: str) -> bool:
    """The same word; between words of four letters another ending ("more", "mora"); with a longer one,
    one letter more, less or different (a typo: "pozo", "ciave"), but never the first ("lancio" is no
    "gancio")."""
    if word == other:
        return True
    shorter, longer = sorted((word, other), key=len)
    if len(shorter) < 4 or len(longer) - len(shorter) > 1 or word[0] != other[0]:
        return False
    if len(longer) == 4:
        return word[:-1] == other[:-1]
    if len(shorter) == len(longer):
        return sum(a != b for a, b in zip(word, other)) == 1
    return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))


_Phrases = dict[tuple[str, ...], list[Named]]


def _mentions(words: list[str], world: World, in_reach: Sequence[Named]) -> list[tuple[Named, ...]] | None:
    """The items (or characters) the words refer to, in order; None if some words match nothing at all."""
    near = _phrases(in_reach)
    anywhere = _phrases([*world.items.values(), *world.characters.values()])
    mentions = []
    position = 0
    while position < len(words):
        found = _longest(words, position, near)
        if found is None:
            # An item out of reach: any one will do, the engine answers that it isn't here.
            found = _longest(words, position, anywhere)
            if found is None:
                return None
            found = (found[0], found[1][:1])
        length, candidates = found
        mentions.append(candidates)
        position += length
    return mentions


def _phrases(items: Iterable[Named]) -> _Phrases:
    """Each name and alias as its significant words -> the items it may refer to."""
    phrases: _Phrases = {}
    for item in items:
        for name in (item.name, *item.aliases):
            key = significant_words(name)
            if item not in phrases.setdefault(key, []):
                phrases[key].append(item)
    return phrases


def _longest(words: list[str], position: int, phrases: _Phrases) -> tuple[int, tuple[Named, ...]] | None:
    for length in range(len(words) - position, 0, -1):
        candidates = phrases.get(tuple(words[position : position + length]))
        if candidates:
            return length, tuple(candidates)
    return None
