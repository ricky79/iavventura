"""Fixed Italian text for the player: articles, lists and the rendering of an Outcome.

Every answer the player reads comes from here or from the world's authors: the LLM never writes it.
"""

import unicodedata
from collections.abc import Iterable

from app.engine.models import (
    Action,
    Character,
    Conversation,
    Direction,
    Gender,
    Item,
    Outcome,
    RoomView,
    Topic,
    Verb,
    World,
)

# Everything with a name and a gender: items, characters and the topics they talk about.
Named = Item | Character | Topic

_VOWELS = frozenset("aeiou")
_INFINITIVES = {
    Verb.EXAMINE: "esaminare",
    Verb.TAKE: "prendere",
    Verb.DROP: "lasciare",
    Verb.USE: "usare",
    Verb.OPEN: "aprire",
    Verb.CLOSE: "chiudere",
    Verb.PUSH: "spingere",
    Verb.PULL: "tirare",
    Verb.READ: "leggere",
    Conversation.TALK: "parlare",
    Conversation.ASK: "chiedere",
}
# A preposition and the definite article become one word: a + il = al, di + la = della.
_ARTICULATED = {
    "a": {"il ": "al ", "lo ": "allo ", "l'": "all'", "la ": "alla ", "i ": "ai ", "gli ": "agli ", "le ": "alle "},
    "di": {"il ": "del ", "lo ": "dello ", "l'": "dell'", "la ": "della ", "i ": "dei ", "gli ": "degli ", "le ": "delle "},
}  # fmt: skip


def definite(item: Named) -> str:
    """The name with its definite article: il gancio, lo specchio, l'uncino, la corda, gli attrezzi."""
    return _definite_article(item) + item.name


def articulated(preposition: str, item: Named) -> str:
    """The name after "a" or "di", joined to its article: al pellegrino, della torre, dell'uncino."""
    return _ARTICULATED[preposition][_definite_article(item)] + item.name


def indefinite(item: Named) -> str:
    """The name with its indefinite article (partitive in the plural): un gancio, un'ascia, dei sassi."""
    feminine = item.gender is Gender.FEMININE
    if item.plural:
        if feminine:
            article = "delle "
        else:
            article = "degli " if _takes_lo(item.name) or _starts_with_vowel(item.name) else "dei "
    elif feminine:
        article = "un'" if _starts_with_vowel(item.name) and not _takes_lo(item.name) else "una "
    else:
        article = "uno " if _takes_lo(item.name) else "un "
    return article + item.name


def join(words: Iterable[str], conjunction: str = "e") -> str:
    """a, b e c"""
    words = list(words)
    if len(words) <= 1:
        return "".join(words)
    return f"{', '.join(words[:-1])} {conjunction} {words[-1]}"


def which_one(candidates: Iterable[Named]) -> str:
    return f"Quale intendi: {join((definite(item) for item in candidates), 'o')}?"


def action_text(action: Action, world: World) -> str:
    """The action as a command: "usa la corda con il gancio", "vai a nord", "chiedi al pellegrino della torre"."""
    if action.direction is not None:
        return f"vai {_to(action.direction)}"
    return " ".join([action.verb, *_complements(action, world)])


def confirmation(action: Action, world: World) -> str:
    """The question before an interpreted action the world doesn't foresee:
    "Vuoi usare la corda con il gancio?", "Vuoi andare a ovest?"."""
    if action.direction is not None:
        return f"Vuoi andare {_to(action.direction)}?"
    return " ".join(["Vuoi", _INFINITIVES[action.verb], *_complements(action, world)]) + "?"


def render(outcome: Outcome, world: World) -> str:
    """The outcome as fixed text: one paragraph each for text, room, inventory and ending."""
    paragraphs = []
    if outcome.text:
        paragraphs.append(outcome.text)
    if outcome.room is not None:
        paragraphs.append(_room(outcome.room, world))
    if outcome.inventory is not None:
        paragraphs.append(_inventory(outcome.inventory, world))
    if outcome.ending:
        paragraphs.append(outcome.ending)
    return "\n\n".join(paragraphs)


def plain(text: str) -> str:
    """Lowercase and without accents, for comparing words: "Giù" -> "giu"."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _complements(action: Action, world: World) -> list[str]:
    """What follows the verb: "la corda con il gancio", "con il pellegrino", "al pellegrino della torre"."""
    if action.verb is Conversation.TALK:
        return ["con", definite(world.thing(action.target))]
    if action.verb is Conversation.ASK:
        character = world.characters[action.target]
        words = [articulated("a", character)]
        if action.topic is not None:
            words.append(articulated("di", character.topics[action.topic]))
        return words
    words = []
    if action.target is not None:
        words.append(definite(world.thing(action.target)))
    if action.with_ is not None:
        words += ["con", definite(world.thing(action.with_))]
    return words


def _to(direction: Direction) -> str:
    """"a nord", but "su" and "giù" alone."""
    return str(direction) if direction in (Direction.UP, Direction.DOWN) else f"a {direction}"


def _room(room: RoomView, world: World) -> str:
    lines = [room.name, room.description]
    if room.characters:
        people = [world.characters[character_id] for character_id in room.characters]
        there = "Qui c'è" if len(people) == 1 and not people[0].plural else "Qui ci sono"
        lines.append(f"{there} {join(indefinite(person) for person in people)}.")
    if room.items:
        lines.append(f"Qui vedi {join(indefinite(world.items[item_id]) for item_id in room.items)}.")
    if room.exits:
        exits = sorted(room.exits, key=list(Direction).index)
        label = "Uscita" if len(exits) == 1 else "Uscite"
        lines.append(f"{label}: {', '.join(exits)}.")
    return "\n".join(lines)


def _inventory(item_ids: tuple[str, ...], world: World) -> str:
    if not item_ids:
        return "Non hai niente con te."
    return f"Hai con te {join(indefinite(world.items[item_id]) for item_id in item_ids)}."


def _definite_article(item: Named) -> str:
    feminine = item.gender is Gender.FEMININE
    if item.plural:
        return "le " if feminine else ("gli " if _takes_lo(item.name) or _starts_with_vowel(item.name) else "i ")
    if _takes_lo(item.name):
        return "la " if feminine else "lo "
    if _starts_with_vowel(item.name):
        return "l'"
    return "la " if feminine else "il "


def _starts_with_vowel(name: str) -> bool:
    return plain(name)[:1] in _VOWELS


def _takes_lo(name: str) -> bool:
    """s + consonant, z, x, y, gn, ps, pn, i + vowel: lo specchio, lo zaino, lo gnomo, lo iodio."""
    word = plain(name)
    first, second = word[:1], word[1:2]
    return (
        first in ("z", "x", "y")
        or word[:2] in ("gn", "ps", "pn")
        or (first == "s" and second != "" and second not in _VOWELS)
        or (first == "i" and second in _VOWELS)
    )
