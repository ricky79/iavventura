"""The classic parser: turns simple Italian commands into an Action.

It is strict on purpose: a word it doesn't know makes the whole sentence not understood,
and freer sentences will go to the LLM interpreter. Items and characters are recognised by name
or alias, ignoring articles and prepositions, preferring those in reach and the longest name.
"""

import re
from collections.abc import Iterable, Sequence
from typing import NamedTuple

from app.engine.models import (
    Action,
    Character,
    Command,
    Conversation,
    Direction,
    Gesture,
    Item,
    Room,
    Topic,
    Verb,
    World,
)
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

# Words of everyday speech, never a typo for a name ("ho sete" is no "seta", "metto" no "motto"): they
# name only a thing called just so. Not here: words that name by another ending ("esco" is "esce").
COMMON_WORDS = frozenset(
    """
    sono siete siamo sara stato stata avete abbiamo hanno avevo aveva
    faccio fate fatto fatta vado andate andiamo andare andato andata vengo vieni viene venite venuto venuta
    stai state stanno dico dici dite detto detta dimmi ditemi vedo vedi vede vedete visto vista
    sapete sapevo voglio vuoi vuole volete posso puoi potete devo devi deve dovete
    metto metti mette messo messa letto letta preso presa seguo segui segue spegni spengo spento spenta
    cerco cerca cercate morto torno torna tornate salgo sali scendo scendi
    tocco tocca tocchi provo prova sento senti sente aspetto aspetta parlo parla dammi datemi
    nostro nostra nostri nostre vostro vostra vostri vostre questo questa questi queste quello quella quelli
    molto molta molti molte poco tanto tanta troppo tutto tutta tutti tutte altro altra altri altre
    ancora sempre adesso subito prima dopo forse quasi proprio anche mezzo
    bene male strano strana strani strane bello bella brutto brutta vecchia nuovo nuova grande piccolo piccola
    vero sete fame freddo caldo paura sonno sera seria basta vale pena mille pieno soli certi certe
    porto porti fermo fermi figlio corre crede parti sogni
    perche quando quanto quale come dove cosa niente nulla
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

# "usa X con Y": between the item and the tool, a mark no name reaches across unless it has it.
TOOL_WORDS = frozenset({"con", "col", "coi"})
TOOL_MARK = "|"

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

# Short social formulas, as significant words (articles and prepositions dropped): a gesture to the
# character named at the start or at the end, the only one here, or the one spoken to last. None is the
# greeting. Longer or freer sentences go to the LLM.
GESTURE_FORMULAS: dict[tuple[str, ...], Gesture | None] = {
    **dict.fromkeys([("ciao",), ("buongiorno",), ("buonasera",), ("salve",)], None),
    **dict.fromkeys(
        [("grazie",), ("grazie", "mille"), ("grazie", "tante"), ("molte", "grazie"), ("grazie", "tutto"),
         ("vi", "ringrazio"), ("ti", "ringrazio")],
        Gesture.THANKS,
    ),
    **dict.fromkeys(
        [("arrivederci",), ("addio",), ("dopo",), ("presto",), ("buonanotte",), ("buona", "notte"), ("ci", "vediamo")],
        Gesture.FAREWELL,
    ),
    **dict.fromkeys(
        [("scusate",), ("scusa",), ("scusami",), ("scusatemi",), ("perdonatemi",), ("perdonami",), ("mi", "dispiace"),
         ("chiedo", "scusa")],
        Gesture.APOLOGY,
    ),
    **dict.fromkeys(
        [("come", "state"), ("come", "stai"), ("come", "va"), ("tutto", "bene"), ("state", "bene"), ("stai", "bene")],
        Gesture.HOW_ARE_YOU,
    ),
    **dict.fromkeys(
        [("chi", "siete"), ("chi", "sei"), ("come", "vi", "chiamate"), ("come", "ti", "chiami")], Gesture.WHO_ARE_YOU
    ),
    **dict.fromkeys(
        [("stupido",), ("stupida",), ("idiota",), ("cretino",), ("cretina",), ("antipatico",), ("antipatica",),
         ("maleducato",), ("maleducata",), ("andate", "diavolo"), ("vai", "diavolo"), ("va", "diavolo")],
        Gesture.RUDENESS,
    ),
}  # fmt: skip

# The words that say a gesture in a free sentence, to check the LLM's answer: with "parla" the model
# answers "saluto" for almost any of them. Words, beginnings of words (every ending: "perdonatemi",
# "stupida") and pairs of words. Not the greeting, which the model says when it knows no better; not
# «diavolo» either, which is also an exclamation.
_GESTURE_WORDS = {
    "grazie": Gesture.THANKS,
    "dispiace": Gesture.APOLOGY,
    **dict.fromkeys(["arrivederci", "addio", "buonanotte"], Gesture.FAREWELL),
}
_GESTURE_STEMS = {
    "ringrazi": Gesture.THANKS,
    **dict.fromkeys(["scus", "perdon"], Gesture.APOLOGY),
    **dict.fromkeys(
        ["stupid", "idiot", "cretin", "scem", "imbecill", "antipatic", "maleducat", "streg", "meger", "brontolon",
         "cattiv", "scioc"],
        Gesture.RUDENESS,
    ),
}  # fmt: skip
_GESTURE_PAIRS = {
    **dict.fromkeys([("ci", "vediamo"), ("a", "presto"), ("a", "dopo")], Gesture.FAREWELL),
    **dict.fromkeys(
        [("come", "stai"), ("come", "state"), ("come", "va"), ("ti", "senti"), ("vi", "sentite"), ("tutto", "bene")],
        Gesture.HOW_ARE_YOU,
    ),
    # «chiamate il dottore» is no «chi sei»: only with «ti» or «vi».
    **dict.fromkeys(
        [("chi", "sei"), ("chi", "siete"), ("ti", "chiami"), ("vi", "chiamate"), ("tuo", "nome"), ("vostro", "nome"),
         ("suo", "nome")],
        Gesture.WHO_ARE_YOU,
    ),
}  # fmt: skip
_YOU_ARE = frozenset({"sei", "siete", "sii", "siate"})


class Ambiguous(NamedTuple):
    """Several items or characters in reach answer to the same words: the player has to say which one."""

    candidates: tuple[Item | Character, ...]


class ToWhom(NamedTuple):
    """A gesture or a question without a name, with several characters here and none of them spoken to
    last: the player has to say to whom («A chi?»). Without anyone, a formula said to nobody («grazie»
    in an empty room)."""

    people: tuple[Character, ...]


def parse(
    text: str,
    world: World,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Sequence[tuple[Character, Sequence[Topic]]] = (),
    last_speaker: str | None = None,
) -> Action | Ambiguous | ToWhom | None:
    """None when the sentence isn't a simple command made only of known words.

    `in_reach` also holds the items in sight (Engine.visible): the parser prefers them all alike.
    `exits` are the current room's exits with the destinations the player knows (Engine.known_exits):
    they let "vai in cucina" go through the exit that leads there.
    `characters` are those in the room, with the topics the player can ask about (Engine.characters_here).
    `last_speaker` receives gestures and questions without a name when several are here.
    """
    words = words_of(text)
    if not words:
        return None
    gesture = _gesture(words, characters, last_speaker)
    if gesture is not None:
        return gesture
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
        return _conversation(
            first in ASK_WORDS, [word for word in rest if word not in STOPWORDS], world, characters, last_speaker
        )

    verb = Verb.EXAMINE if first in LOOK_WORDS else ITEM_VERBS.get(first)
    if verb is None:
        return None
    people = [character for character, _ in characters]
    kept = [TOOL_MARK if word in TOOL_WORDS else word for word in rest if word in TOOL_WORDS or word not in STOPWORDS]
    mentions = _mentions(kept, world, [*in_reach, *people])
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
    asking: bool,
    words: list[str],
    world: World,
    characters: Sequence[tuple[Character, Sequence[Topic]]],
    last_speaker: str | None,
) -> Action | Ambiguous | ToWhom | None:
    """"parla con X", "saluta X", "chiedi a X di Y"; without X, the only character here or the one spoken
    to last.
    A question that names none of X's topics, not even nearly, is the gesture it says («chiedi scusa»),
    or about an item or another character of the world it gets X's `unknown`; anything else that is no
    topic the player knows goes to the LLM."""
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
    elif (addressee := _addressee(characters, last_speaker)) is not None:
        character = addressee[0]
    else:
        return ToWhom(tuple(people)) if len(people) > 1 else None
    if not asking:
        return Action(verb=Conversation.TALK, target=character.id) if not words else None
    topics = next((topics for person, topics in characters if person.id == character.id), ())
    topic = find_topic(words, topics) if words else None
    if topic is not None:
        return Action(verb=Conversation.ASK, target=character.id, topic=topic.id)
    named = topics_named(character, topics, words) if words else []
    if words and not named and (gesture := gesture_said(words)) is not None:
        # «chiedi al pellegrino del suo nome», «chiedi scusa al custode»: no topic, a gesture.
        return Action(verb=Conversation.TALK, target=character.id, gesture=gesture)
    others = [person for person in world.characters.values() if person.id != character.id]
    if words and not named and tuple(words) in _phrases([*world.items.values(), *others]):
        # «chiedi a Livia della meridiana»: something of the game she has no topic about. «della
        # chiave», nearly her «chiavi», is left to the LLM.
        return Action(verb=Conversation.ASK, target=character.id)
    return None


def _addressee(
    characters: Sequence[tuple[Character, Sequence[Topic]]], last_speaker: str | None
) -> tuple[Character, Sequence[Topic]] | None:
    """Who a sentence without a name is for: the only one here, or the one spoken to last if here."""
    if len(characters) == 1:
        return characters[0]
    return next((pair for pair in characters if pair[0].id == last_speaker), None)


def _gesture(
    words: list[str], characters: Sequence[tuple[Character, Sequence[Topic]]], last_speaker: str | None
) -> Action | ToWhom | None:
    """«grazie», «arrivederci, Livia», «Livia, come state?»: a gesture, if the words are a formula with
    at most the name of someone here at the start or at the end; «A chi?» if nobody is named and several
    could be meant; said to nobody if nobody is here."""
    said = tuple(word for word in words if word not in STOPWORDS)
    for person, topics in characters:
        for phrase in {significant_words(name) for name in (person.name, *person.aliases)} - {()}:
            size = len(phrase)
            for rest in (said[size:] if said[:size] == phrase else None, said[:-size] if said[-size:] == phrase else None):
                if rest is not None and rest in GESTURE_FORMULAS:
                    return _said_to(person, topics, rest)
    if said not in GESTURE_FORMULAS:
        return None
    if (addressee := _addressee(characters, last_speaker)) is None:
        return ToWhom(tuple(person for person, _ in characters))
    return _said_to(*addressee, said)


def _said_to(person: Character, topics: Sequence[Topic], formula: tuple[str, ...]) -> Action:
    """The gesture of a formula; the question, if the formula is the name of one of the character's
    topics (the pilgrim's «chi sei»)."""
    topic = find_topic(formula, topics)
    if topic is not None:
        return Action(verb=Conversation.ASK, target=person.id, topic=topic.id)
    return Action(verb=Conversation.TALK, target=person.id, gesture=GESTURE_FORMULAS[formula])


def gesture_said(words: Sequence[str]) -> Gesture | None:
    """The gesture a free sentence says, by its words ("perdonatemi se vi disturbo": an apology); the
    last one said if several ("grazie e arrivederci"). An unkind word is rude only said to someone ("sei
    un drago cattivo", "che antipatica!"), not in "i draghi cattivi sputano fuoco?". None for anything
    else, the greeting too."""
    to_someone = bool(_YOU_ARE.intersection(words)) or len([word for word in words if word not in STOPWORDS]) <= 2
    said = None
    for position, word in enumerate(words):
        gesture = _GESTURE_PAIRS.get(tuple(words[position - 1 : position + 1])) if position else None
        gesture = gesture or _GESTURE_WORDS.get(word)
        gesture = gesture or next((g for stem, g in _GESTURE_STEMS.items() if word.startswith(stem)), None)
        if gesture is Gesture.RUDENESS and not to_someone:
            gesture = None
        said = gesture or said
    return said


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


def names_of(thing: Named | Room) -> tuple[str, ...]:
    """The name and the aliases of the thing, also those the model isn't shown (Item.hidden_aliases)."""
    return (thing.name, *thing.aliases, *(thing.hidden_aliases if isinstance(thing, Item) else ()))


def names_said(thing: Named | Room, words: Sequence[str]) -> list[tuple[str, ...]]:
    """The names and aliases of the thing that the words say (see is_named), as significant words."""
    names = dict.fromkeys(significant_words(name) for name in names_of(thing))
    return [name for name in names if all(any(_nearly(word, name_word) for word in words) for name_word in name)]


def words_saying(name: tuple[str, ...], words: Sequence[str]) -> set[str]:
    """The words that say a name of names_said."""
    return {word for word in words if any(_nearly(word, name_word) for name_word in name)}


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
    "gancio"). `word` is the player's: a common word is no typo (COMMON_WORDS)."""
    if word == other:
        return True
    if word in COMMON_WORDS:
        return False
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
        if words[position] == TOOL_MARK:
            position += 1
            continue
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
        for name in names_of(item):
            for key in {significant_words(name), _marked_words(name)}:
                if item not in phrases.setdefault(key, []):
                    phrases[key].append(item)
    return phrases


def _marked_words(name: str) -> tuple[str, ...]:
    """The significant words of a name with «con» kept as a mark: "corda con gancio" reaches across the
    «con» of a sentence, "chiave della credenza" doesn't ("usa la chiave con la credenza")."""
    return tuple(TOOL_MARK if word in TOOL_WORDS else word for word in words_of(name) if word in TOOL_WORDS or word not in STOPWORDS)


def _longest(words: list[str], position: int, phrases: _Phrases) -> tuple[int, tuple[Named, ...]] | None:
    for length in range(len(words) - position, 0, -1):
        candidates = phrases.get(tuple(words[position : position + length]))
        if candidates:
            return length, tuple(candidates)
    return None
