"""The classic parser: turns simple Italian commands into an Action.

It is strict on purpose: a word it doesn't know makes the whole sentence not understood,
and freer sentences will go to the LLM interpreter. Items are recognised by name or alias,
ignoring articles and prepositions, preferring the items in reach and the longest name.
"""

import re
from collections.abc import Iterable, Sequence
from typing import NamedTuple

from app.engine.models import Action, Command, Direction, Item, Room, Verb, World
from app.engine.text import plain

STOPWORDS = frozenset(
    """
    il lo la i gli le l un uno una
    di a da in con su per tra fra verso contro dentro
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
    "giu": Direction.DOWN,
    "scendi": Direction.DOWN,
}

GO_WORDS = frozenset({"vai", "va", "cammina"})
LOOK_WORDS = frozenset({"guarda", "g", "descrivi"})  # with an item they mean "esamina"
INVENTORY_WORDS = frozenset({"inventario", "inv", "i"})

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
}


class Ambiguous(NamedTuple):
    """Several items in reach answer to the same words: the player has to say which one."""

    candidates: tuple[Item, ...]


def parse(
    text: str, world: World, in_reach: Sequence[Item], exits: Sequence[tuple[Direction, Room | None]] = ()
) -> Action | Ambiguous | None:
    """None when the sentence isn't a simple command made only of known words.

    `in_reach` also holds the items in sight (Engine.visible): the parser prefers them all alike.
    `exits` are the current room's exits with the destinations the player knows (Engine.known_exits):
    they let "vai in cucina" go through the exit that leads there.
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
            if room is not None and significant_words(room.name) == tuple(rest):
                return Action(verb=Command.GO, direction=direction)
        return None
    if first in INVENTORY_WORDS:
        return Action(verb=Command.INVENTORY) if not rest else None
    if first in LOOK_WORDS and not rest:
        return Action(verb=Command.LOOK)

    verb = Verb.EXAMINE if first in LOOK_WORDS else ITEM_VERBS.get(first)
    if verb is None:
        return None
    mentions = _mentions([word for word in rest if word not in STOPWORDS], world, in_reach)
    if mentions is None or not 1 <= len(mentions) <= 2:
        return None
    for candidates in mentions:
        if len(candidates) > 1:
            return Ambiguous(candidates)
    ids = [candidates[0].id for candidates in mentions]
    if len(set(ids)) < len(ids):
        return None
    return Action(verb=verb, target=ids[0], with_=ids[1] if len(ids) == 2 else None)


def words_of(text: str) -> list[str]:
    """Lowercase words without accents or punctuation; apostrophes split words (l'uncino)."""
    return re.findall(r"[a-z0-9]+", plain(text))


def significant_words(text: str) -> tuple[str, ...]:
    """The words without articles and prepositions: "la porta della torre" -> ("porta", "torre")."""
    return tuple(word for word in words_of(text) if word not in STOPWORDS)


_Phrases = dict[tuple[str, ...], list[Item]]


def _mentions(words: list[str], world: World, in_reach: Sequence[Item]) -> list[tuple[Item, ...]] | None:
    """The items the words refer to, in order; None if some words match no item at all."""
    near = _phrases(in_reach)
    anywhere = _phrases(world.items.values())
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


def _phrases(items: Iterable[Item]) -> _Phrases:
    """Each name and alias as its significant words -> the items it may refer to."""
    phrases: _Phrases = {}
    for item in items:
        for name in (item.name, *item.aliases):
            key = significant_words(name)
            if item not in phrases.setdefault(key, []):
                phrases[key].append(item)
    return phrases


def _longest(words: list[str], position: int, phrases: _Phrases) -> tuple[int, tuple[Item, ...]] | None:
    for length in range(len(words) - position, 0, -1):
        candidates = phrases.get(tuple(words[position : position + length]))
        if candidates:
            return length, tuple(candidates)
    return None
