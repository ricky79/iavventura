"""Fixed Italian text for the player: articles, lists and the rendering of an Outcome.

Every answer the player reads comes from here or from the world's authors: the LLM never writes it.
"""

import unicodedata
from collections.abc import Iterable

from app.engine.models import (
    Action,
    Article,
    Character,
    Conversation,
    Direction,
    Gender,
    Gesture,
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
    Verb.GIVE: "dare",
    Verb.JUMP: "saltare",
    Conversation.TALK: "parlare",
    Conversation.ASK: "chiedere",
}
# A preposition and the definite article become one word: a + il = al, di + la = della.
_ARTICULATED = {
    "a": {"il ": "al ", "lo ": "allo ", "l'": "all'", "la ": "alla ", "i ": "ai ", "gli ": "agli ", "le ": "alle "},
    "di": {"il ": "del ", "lo ": "dello ", "l'": "dell'", "la ": "della ", "i ": "dei ", "gli ": "degli ", "le ": "delle "},
    "in": {"il ": "nel ", "lo ": "nello ", "l'": "nell'", "la ": "nella ", "i ": "nei ", "gli ": "negli ", "le ": "nelle "},
    "da": {"il ": "dal ", "lo ": "dallo ", "l'": "dall'", "la ": "dalla ", "i ": "dai ", "gli ": "dagli ", "le ": "dalle "},
}  # fmt: skip
# A gesture as a command and as what the player wants ("ringrazia Livia", "ringraziare Livia"); {the}
# is the character with its article, {to} and {from_} the same after «a» and «da».
_GESTURES = {
    None: ("parla con {the}", "parlare con {the}"),
    Gesture.FAREWELL: ("congedati {from_}", "congedarti {from_}"),
    Gesture.THANKS: ("ringrazia {the}", "ringraziare {the}"),
    Gesture.APOLOGY: ("scusati con {the}", "scusarti con {the}"),
    Gesture.HOW_ARE_YOU: ("chiedi {to} come sta", "chiedere {to} come sta"),
    Gesture.WHO_ARE_YOU: ("chiedi {to} chi è", "chiedere {to} chi è"),
    Gesture.RUDENESS: ("sii scortese con {the}", "essere scortese con {the}"),
}


def definite(item: Named) -> str:
    """The name with its definite article: il gancio, lo specchio, l'uncino, la corda, gli attrezzi;
    a first name without one: Ettore."""
    if item.article is Article.NONE:
        return item.name
    return _definite_article(item) + item.name


def articulated(preposition: str, item: Named) -> str:
    """The name after "a", "di", "in" or "da", joined to its article: al pellegrino, della torre, nel
    pozzo; a first name keeps the preposition apart: a Ettore, di Livia, ad Agnese."""
    if item.article is Article.NONE:
        # «ad Agnese»: «a» before a name starting with «a» takes a «d».
        joined = "ad" if preposition == "a" and plain(item.name).startswith("a") else preposition
        return f"{joined} {item.name}"
    return _ARTICULATED[preposition][_definite_article(item)] + item.name


def indefinite(item: Named) -> str:
    """The name with its indefinite article (partitive in the plural): un gancio, un'ascia, dei sassi;
    a proper name or a title keeps its own: Ettore, il dottor Ferri."""
    if item.article is not None:
        # Someone or something already known by name: "Qui c'è Ettore", "Qui c'è il dottor Ferri".
        return definite(item)
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
    if action.verb is Conversation.TALK:
        return _gesture(action, world, infinitive=False)
    return " ".join([action.verb, *_complements(action, world)])


def confirmation(action: Action, world: World) -> str:
    """The question before an interpreted action the world doesn't foresee:
    "Vuoi usare la corda con il gancio?", "Vuoi andare a ovest?"."""
    if action.direction is not None:
        return f"Vuoi andare {_to(action.direction)}?"
    if action.verb is Conversation.TALK:
        return f"Vuoi {_gesture(action, world, infinitive=True)}?"
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
    """What follows the verb: "la corda con il gancio", "al pellegrino della torre", "la moneta al
    custode", "nel pozzo"."""
    if action.verb is Conversation.ASK:
        character = world.characters[action.target]
        words = [articulated("a", character)]
        if action.topic is not None:
            words.append(articulated("di", character.topics[action.topic]))
        return words
    if action.verb is Verb.GIVE:
        # "la moneta al custode", in whatever order the action has them
        things = [world.thing(thing_id) for thing_id in (action.target, action.with_) if thing_id is not None]
        people = [thing for thing in things if isinstance(thing, Character)]
        return [definite(thing) for thing in things if thing not in people] + [
            articulated("a", person) for person in people
        ]
    words = []
    if action.target is not None:
        thing = world.thing(action.target)
        words.append(articulated("in", thing) if action.verb is Verb.JUMP else definite(thing))
    if action.with_ is not None:
        words += ["con", definite(world.thing(action.with_))]
    return words


def _gesture(action: Action, world: World, infinitive: bool) -> str:
    character = world.characters[action.target]
    words = _GESTURES[action.gesture][1 if infinitive else 0]
    return words.format(the=definite(character), to=articulated("a", character), from_=articulated("da", character))


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
