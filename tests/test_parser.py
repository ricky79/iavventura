"""The classic parser: simple Italian commands -> Action, Ambiguous or None."""

import pytest

from app.engine.models import Action, Direction, World
from app.engine.parser import Ambiguous, ToWhom, gesture_said, is_named, parse, words_of


@pytest.fixture
def world(world_data) -> World:
    """Names with prepositions inside and aliases shared between items, as in the castle."""
    world_data["items"] = {
        "corda": {"name": "corda", "gender": "f", "aliases": ["fune"], "description": "-", "location": "atrio"},
        "gancio": {
            "name": "gancio da macellaio",
            "gender": "m",
            "aliases": ["gancio", "uncino"],
            "description": "-",
            "location": "atrio",
        },
        "corda_con_gancio": {
            "name": "corda con gancio",
            "gender": "f",
            "aliases": ["corda", "gancio", "rampino"],
            "description": "-",
            "location": None,
        },
        "pozzo": {"name": "pozzo", "gender": "m", "description": "-", "location": "atrio", "scenery": True},
        "porta": {
            "name": "porta della torre",
            "gender": "f",
            "aliases": ["porta", "porta di ferro"],
            "description": "-",
            "location": "atrio",
            "scenery": True,
        },
        "chiave": {"name": "chiave di ferro", "gender": "f", "aliases": ["chiave"], "description": "-", "location": None},
    }
    return World.model_validate(world_data)


def parse_with(world: World, text: str, *in_reach: str):
    return parse(text, world, [world.items[item_id] for item_id in in_reach])


# --- Commands without items ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("nord", Action(verb="vai", direction="nord")),
        ("n", Action(verb="vai", direction="nord")),
        ("s", Action(verb="vai", direction="sud")),
        ("e", Action(verb="vai", direction="est")),
        ("o", Action(verb="vai", direction="ovest")),
        ("vai a nord", Action(verb="vai", direction="nord")),
        ("va verso sud", Action(verb="vai", direction="sud")),
        ("vai su", Action(verb="vai", direction="su")),
        ("sali", Action(verb="vai", direction="su")),
        ("giù", Action(verb="vai", direction="giù")),
        ("giu", Action(verb="vai", direction="giù")),
        ("scendi", Action(verb="vai", direction="giù")),
        ("  Nord! ", Action(verb="vai", direction="nord")),
        ("guarda", Action(verb="guarda")),
        ("g", Action(verb="guarda")),
        ("descrivi", Action(verb="guarda")),
        ("inventario", Action(verb="inventario")),
        ("inv", Action(verb="inventario")),
        ("i", Action(verb="inventario")),
    ],
)
def test_commands_without_items(world, text, expected):
    assert parse_with(world, text) == expected


# --- Commands on items ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("prendi la corda", Action(verb="prendi", target="corda")),
        ("raccogli la fune", Action(verb="prendi", target="corda")),
        ("PRENDI LA CORDA.", Action(verb="prendi", target="corda")),
        ("prendi l'uncino", Action(verb="prendi", target="gancio")),
        ("prendi il gancio da macellaio", Action(verb="prendi", target="gancio")),
        ("lascia la corda", Action(verb="lascia", target="corda")),
        ("x pozzo", Action(verb="esamina", target="pozzo")),
        ("guarda nel pozzo", Action(verb="esamina", target="pozzo")),
        ("usa la corda con il gancio", Action(verb="usa", target="corda", with_="gancio")),
        ("usa il gancio sulla corda", Action(verb="usa", target="gancio", with_="corda")),
        ("spingi la porta", Action(verb="spingi", target="porta")),
        ("apri la porta di ferro", Action(verb="apri", target="porta")),
    ],
)
def test_commands_on_items_in_reach(world, text, expected):
    assert parse_with(world, text, "corda", "gancio", "pozzo", "porta") == expected


def test_longest_name_wins_even_when_it_contains_a_preposition(world):
    action = parse_with(world, "usa la corda con gancio nel pozzo", "corda_con_gancio", "pozzo")

    assert action == Action(verb="usa", target="corda_con_gancio", with_="pozzo")


def test_a_name_does_not_reach_across_con(world_data):
    # Valdimora: «usa la chiave con la credenza» was «usa la chiave della credenza», alone: «Non
    # succede niente». A name reaches across «con» only if it has it (the grapple, «corda con gancio»).
    world_data["items"]["credenza"] = {"name": "credenza", "gender": "f", "description": "-", "location": "atrio"}
    world_data["items"]["chiave_credenza"] = {
        "name": "chiave della credenza", "gender": "f", "aliases": ["chiave"], "description": "-", "location": "atrio",
    }  # fmt: skip
    world = World.model_validate(world_data)

    action = parse_with(world, "usa la chiave con la credenza", "credenza", "chiave_credenza")

    assert action == Action(verb="usa", target="chiave_credenza", with_="credenza")


def test_the_grapple_still_reaches_across_its_own_con(world):
    assert parse_with(world, "usa la corda con gancio con il pozzo", "corda_con_gancio", "pozzo") == Action(
        verb="usa", target="corda_con_gancio", with_="pozzo"
    )


def test_names_of_items_out_of_reach_do_not_hide_those_in_reach(world):
    # "corda con gancio" is the name of an item out of play: here the words mean two items.
    action = parse_with(world, "usa la corda con il gancio", "corda", "gancio")

    assert action == Action(verb="usa", target="corda", with_="gancio")


def test_names_with_prepositions_on_both_sides(world):
    action = parse_with(world, "apri la porta di ferro con la chiave di ferro", "porta", "chiave")

    assert action == Action(verb="apri", target="porta", with_="chiave")


def test_an_alias_is_resolved_among_items_in_reach(world):
    assert parse_with(world, "esamina il rampino", "corda_con_gancio") == Action(
        verb="esamina", target="corda_con_gancio"
    )
    assert parse_with(world, "prendi la corda", "corda_con_gancio") == Action(verb="prendi", target="corda_con_gancio")


def test_an_item_out_of_reach_still_reaches_the_engine(world):
    # The engine then answers "Non vedi niente del genere qui."
    assert parse_with(world, "prendi la chiave", "corda") == Action(verb="prendi", target="chiave")


def test_items_out_of_reach_are_never_ambiguous(world):
    # "gancio" is both the hook and the grapple: asking which one would reveal the grapple.
    assert parse_with(world, "prendi il gancio", "pozzo") == Action(verb="prendi", target="gancio")


def test_two_items_in_reach_with_the_same_name_are_ambiguous(world):
    result = parse_with(world, "prendi la corda", "corda", "corda_con_gancio")

    assert result == Ambiguous(candidates=(world.items["corda"], world.items["corda_con_gancio"]))


@pytest.mark.parametrize(
    "text",
    ["salta nel pozzo", "salto nel pozzo", "tuffati nel pozzo", "buttati nel pozzo", "gettati nel pozzo", "lanciati dentro il pozzo"],
)  # fmt: skip
def test_jumping_into_an_item(world, text):
    assert parse_with(world, text, "corda", "pozzo") == Action(verb="salta", target="pozzo")


@pytest.mark.parametrize("text", ["salta", "mi butto nel pozzo", "butta la corda nel pozzo", "salta giù nel pozzo"])
def test_other_ways_of_jumping_are_left_to_the_llm(world, text):
    assert parse_with(world, text, "corda", "pozzo") is None


# --- What the parser does not understand --------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "?!",
        "balla",
        "prendi",
        "prendi la",
        "prendi la vecchia corda",
        "prendi la corda e il gancio",
        "usa la corda con il gancio nel pozzo",
        "usa la corda con la fune",
        "vai",
        "vai in cucina",
        "nord sud",
        "inventario corda",
        "guarda nord",
    ],
)
def test_anything_else_is_not_understood(world, text):
    assert parse_with(world, text, "corda", "gancio", "pozzo") is None


# --- Going to a room by its name ----------------------------------------------------------------


def exits_to(world: World, *pairs: tuple[str, str | None]):
    return [(Direction(direction), world.rooms[room] if room else None) for direction, room in pairs]


@pytest.mark.parametrize("text", ["vai nella cella", "vai in cella", "va alla cella", "cammina verso la Cella"])
def test_going_to_a_known_room_by_name(world, text):
    exits = exits_to(world, ("sud", None), ("ovest", "cella"))

    assert parse(text, world, [], exits) == Action(verb="vai", direction="ovest")


def test_directions_still_work_when_rooms_are_known(world):
    assert parse("vai a sud", world, [], exits_to(world, ("ovest", "cella"))) == Action(verb="vai", direction="sud")


def test_a_room_the_player_does_not_know_is_not_understood(world):
    assert parse("vai nella cella", world, [], exits_to(world, ("ovest", None))) is None


def test_a_room_that_is_not_through_an_exit_is_not_understood(world):
    assert parse("vai nell'atrio", world, [], exits_to(world, ("ovest", "cella"))) is None


def test_every_significant_word_of_the_room_name_is_needed(world_data):
    world_data["rooms"]["cella"]["name"] = "Cella del conte"
    world = World.model_validate(world_data)
    exits = exits_to(world, ("ovest", "cella"))

    assert parse("vai nella cella del conte", world, [], exits) == Action(verb="vai", direction="ovest")
    assert parse("vai nella cella", world, [], exits) is None


@pytest.mark.parametrize("text", ["vai dal prigioniero", "torna alla prigione", "vado in prigione"])
def test_going_to_a_known_room_by_an_alias(world_data, text):
    # "vado dall'orso" at the brook went east: the model didn't know the bear lives in the den.
    world_data["rooms"]["cella"]["aliases"] = ["prigione", "prigioniero"]
    world = World.model_validate(world_data)

    assert parse(text, world, [], exits_to(world, ("ovest", "cella"))) == Action(verb="vai", direction="ovest")


@pytest.mark.parametrize(
    ("text", "direction"),
    [
        ("torna a sud", "sud"),
        ("torno verso est", "est"),
        ("ritorna a nord", "nord"),
        ("ritorno giù", "giù"),
        ("vado a ovest", "ovest"),
        ("entra nella cella", "ovest"),
        ("entro in cella", "ovest"),
        ("salgo", "su"),
        ("scendo", "giù"),
        ("arrampicati", "su"),
    ],
)
def test_more_words_for_going(world, text, direction):
    exits = exits_to(world, ("ovest", "cella"))

    assert parse(text, world, [], exits) == Action(verb="vai", direction=direction)


# --- Talking to characters -----------------------------------------------------------------------


@pytest.fixture
def keeper(keeper_world) -> World:
    return World.model_validate(keeper_world)


def parse_near_keeper(world: World, text: str, topics: tuple[str, ...] = ("cella", "leva")):
    """The custode is here, and the player can ask about `topics`."""
    custode = world.characters["custode"]
    return parse(text, world, [], (), [(custode, [custode.topics[topic_id] for topic_id in topics])])


@pytest.mark.parametrize(
    "text", ["parla con il custode", "parla al guardiano", "saluta il vecchio", "parla", "saluta"]
)
def test_talking_to_a_character(keeper, text):
    assert parse_near_keeper(keeper, text) == Action(verb="parla", target="custode")


@pytest.mark.parametrize(
    ("text", "topic"),
    [
        ("chiedi al custode della cella", "cella"),
        ("domanda al guardiano della prigione", "cella"),
        ("chiedi al vecchio della leva", "leva"),
        ("chiedi della cella", "cella"),  # to the only character here
    ],
)
def test_asking_a_character_about_a_topic(keeper, text, topic):
    assert parse_near_keeper(keeper, text) == Action(verb="chiedi", target="custode", topic=topic)


@pytest.mark.parametrize(
    "text",
    [
        "chiedi al custode del tempo",  # the LLM decides: unknown topic, or a way of naming a known one
        "chiedi al custode",
        "parla con il custode della cella",
    ],
)
def test_questions_without_a_known_topic_are_left_to_the_llm(keeper, text):
    assert parse_near_keeper(keeper, text) is None


@pytest.mark.parametrize("text", ["chiedi al custode della chiave", "chiedi al custode della moneta"])
def test_a_question_about_something_the_character_has_no_topic_for(keeper, text):
    # «chiedi a Livia di Corrado»: something of the game, but no topic of hers (the key not yet).
    assert parse_near_keeper(keeper, text) == Action(verb="chiedi", target="custode")


def test_a_topic_named_nearly_is_left_to_the_llm(keeper_world):
    # «chiedi a Livia della chiave»: the key is an item, but «chiave» nearly names her topic «chiavi».
    keeper_world["characters"]["custode"]["topics"]["monete"] = {
        "name": "monete", "gender": "f", "plural": True, "text": "«Ne ho viste tante.»",
    }  # fmt: skip
    keeper = World.model_validate(keeper_world)

    assert parse_near_keeper(keeper, "chiedi al custode della moneta", ("cella", "leva", "monete")) is None


def test_with_nobody_here_there_is_no_one_to_talk_to(keeper):
    assert parse("parla", keeper, [], (), []) is None
    assert parse("chiedi della cella", keeper, [], (), []) is None


def test_a_character_in_another_room_still_reaches_the_engine(keeper):
    assert parse("parla con il custode", keeper, [], (), []) == Action(verb="parla", target="custode")


def test_a_character_can_be_examined(keeper):
    assert parse_near_keeper(keeper, "esamina il custode") == Action(verb="esamina", target="custode")
    assert parse_near_keeper(keeper, "guarda il vecchio") == Action(verb="esamina", target="custode")


def test_two_characters_with_the_same_name_are_ambiguous(keeper_world):
    keeper_world["characters"]["eremita"] = {
        "name": "eremita",
        "gender": "m",
        "aliases": ["vecchio"],
        "description": "Un eremita.",
        "location": "atrio",
        "greeting": "«Pace.»",
        "unknown": "«Chissà.»",
    }
    world = World.model_validate(keeper_world)
    here = [(character, []) for character in world.characters.values()]

    parsed = parse("parla con il vecchio", world, [], (), here)

    assert parsed == Ambiguous((world.characters["custode"], world.characters["eremita"]))


# --- Giving ----------------------------------------------------------------------------------------


def parse_giving(world: World, text: str):
    """The custode is here and the player carries the coin."""
    return parse(text, world, [world.items["moneta"]], (), [(world.characters["custode"], [])])


@pytest.mark.parametrize(
    "text",
    [
        "dai la moneta al custode",
        "dà la moneta al guardiano",
        "porgi la moneta al vecchio",
        "offri il soldo al custode",
        "regala la moneta al custode",
        "consegna la moneta al custode",
        "dai la moneta ad un custode",  # «ad» before a vowel, as in «dai il medaglione ad Agnese»
    ],
)
def test_giving_an_item_to_a_character(keeper, text):
    assert parse_giving(keeper, text) == Action(verb="dai", target="moneta", with_="custode")


def test_the_character_may_come_first(keeper):
    assert parse_giving(keeper, "dai al custode la moneta") == Action(verb="dai", target="custode", with_="moneta")


def test_giving_without_naming_the_character_reaches_the_engine(keeper):
    assert parse_giving(keeper, "dai la moneta") == Action(verb="dai", target="moneta")


@pytest.mark.parametrize("text", ["dai un'occhiata alla leva", "dai una spinta alla moneta"])
def test_sayings_with_dai_are_left_to_the_llm(keeper, text):
    assert parse_giving(keeper, text) is None


# --- Gestures -----------------------------------------------------------------------------------------


@pytest.fixture
def with_cook(keeper_world) -> World:
    keeper_world["characters"]["cuoca"] = {
        "name": "cuoca", "gender": "f", "description": "-", "location": "atrio",
        "greeting": "«Ciao.»", "unknown": "«Boh.»",
    }  # fmt: skip
    return World.model_validate(keeper_world)


def two_here(world: World, last_speaker: str | None = None, text: str = "grazie"):
    """The custode, who can be asked about the cell, and the cook in the atrium."""
    custode = world.characters["custode"]
    return parse(text, world, [], (), [(custode, [custode.topics["cella"]]), (world.characters["cuoca"], [])], last_speaker)


@pytest.mark.parametrize(
    ("text", "gesture"),
    [
        ("grazie", "grazie"), ("grazie mille!", "grazie"), ("vi ringrazio", "grazie"), ("grazie, custode", "grazie"),
        ("custode, grazie", "grazie"), ("arrivederci", "congedo"), ("a dopo", "congedo"), ("buonanotte", "congedo"),
        ("scusate", "scuse"), ("perdonatemi", "scuse"), ("mi dispiace", "scuse"), ("come state?", "come_stai"),
        ("tutto bene?", "come_stai"), ("chi siete?", "chi_sei"), ("come vi chiamate?", "chi_sei"),
        ("stupido!", "scortesia"), ("andate al diavolo", "scortesia"), ("vai al diavolo", "scortesia"),
        ("ciao", None), ("buongiorno, custode", None), ("salve", None),
    ],
)  # fmt: skip
def test_social_formulas_are_gestures(keeper, text, gesture):
    assert parse_near_keeper(keeper, text) == Action(verb="parla", target="custode", gesture=gesture)


def test_a_formula_that_is_a_topic_is_a_question(keeper_world):
    # The pilgrim's «chi sei» was a topic: a topic the formula names wins over the gesture.
    keeper_world["characters"]["custode"]["topics"]["leva"]["aliases"] = ["come va"]
    keeper = World.model_validate(keeper_world)

    assert parse_near_keeper(keeper, "come va?") == Action(verb="chiedi", target="custode", topic="leva")
    assert parse_near_keeper(keeper, "grazie per la leva") is None  # no formula: the LLM decides


def test_social_formulas_do_not_steal_commands(keeper):
    assert parse_near_keeper(keeper, "vai a nord") == Action(verb="vai", direction="nord")
    assert parse_near_keeper(keeper, "parla con il custode") == Action(verb="parla", target="custode")
    assert parse("vai al diavolo", keeper, [], (), []) == ToWhom(())  # with nobody here, no move either


def test_with_nobody_here_a_formula_is_said_to_nobody(keeper):
    # The game answers «Qui non c'è nessuno con cui parlare.» without asking the LLM.
    assert parse("grazie", keeper, [], (), []) == ToWhom(())


def test_a_gesture_without_a_name_goes_to_the_last_one_spoken_to(with_cook):
    both = ToWhom((with_cook.characters["custode"], with_cook.characters["cuoca"]))

    assert two_here(with_cook) == both  # «A chi?»
    assert two_here(with_cook, "cuoca") == Action(verb="parla", target="cuoca", gesture="grazie")
    assert two_here(with_cook, "pellegrino") == both  # the last one spoken to isn't here
    assert two_here(with_cook, "cuoca", "grazie, custode") == Action(verb="parla", target="custode", gesture="grazie")


def test_a_question_without_a_name_goes_to_the_last_one_spoken_to(with_cook):
    both = ToWhom((with_cook.characters["custode"], with_cook.characters["cuoca"]))

    assert two_here(with_cook, None, "chiedi della cella") == both
    assert two_here(with_cook, None, "parla") == both
    assert two_here(with_cook, "custode", "chiedi della cella") == Action(verb="chiedi", target="custode", topic="cella")


@pytest.mark.parametrize(
    ("text", "gesture"),
    [
        ("vi ringrazio tanto, signora", "grazie"), ("mille grazie davvero", "grazie"), ("chiedo scusa", "scuse"),
        ("mi dispiace tanto", "scuse"), ("ci vediamo più tardi", "congedo"), ("a presto, amico", "congedo"),
        ("come ti senti?", "come_stai"), ("tutto bene, vecchio?", "come_stai"), ("e tu come ti chiami?", "chi_sei"),
        ("e voi come vi chiamate?", "chi_sei"),
        ("sei un drago cattivo", "scortesia"), ("siete una strega", "scortesia"), ("che antipatica!", "scortesia"),
        ("stupido!", "scortesia"), ("grazie e addio", "congedo"),  # the last one said
    ],
)  # fmt: skip
def test_the_words_of_a_gesture_in_a_free_sentence(text, gesture):
    assert gesture_said(words_of(text)) == gesture


@pytest.mark.parametrize(
    "text",
    ["ciao", "come si esce da qui?", "chi era il castellano?", "come sta la contessa?", "che graziosa stanza",
     "che diavolo è questo?", "vado a nord",
     # Found by the final review: an unkind word said to nobody is no rudeness.
     "i draghi cattivi sputano fuoco?", "che tempo cattivo stasera, eh?", "streghe e fantasmi esistono?",
     "questa storia è scioccante",
     "chiamate il dottore", "lo chiamano Tobia"],  # «chiamare» is no «chi sei» without «ti»/«vi»
)  # fmt: skip
def test_no_gesture_in_other_sentences(text):
    # Not the greeting: the model already answers it when it knows no better.
    assert gesture_said(words_of(text)) is None


# --- Whether a sentence names a thing (to check the LLM's answers) ------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "busso alla porta della torre",
        "sfondo la porta a calci",
        "provo la porta di ferro",
        "afferra la ciave nel pozzo",  # a typo: one letter less
        "prendo le chiavi",  # another ending
    ],
)
def test_a_sentence_names_a_thing_by_its_name_or_an_alias_nearly(world, text):
    door, key = world.items["porta"], world.items["chiave"]

    assert is_named(door, words_of(text)) or is_named(key, words_of(text))


@pytest.mark.parametrize(
    ("text", "item_id"),
    [
        ("apri la torre", "porta"),  # every significant word of a name is needed: "porta della torre"
        ("prendo il ferro", "chiave"),
        ("cala la fine nel pozzo", "corda"),  # four letters: only the ending may change
        ("prendi una scala", "pozzo"),
        ("lancio la fune", "gancio"),  # a typo keeps the first letter
    ],
)
def test_a_sentence_that_does_not_name_a_thing(world, text, item_id):
    assert not is_named(world.items[item_id], words_of(text))


def test_rooms_are_named_like_items(world_data):
    world_data["rooms"]["atrio"]["name"] = "Scuderia"
    room = World.model_validate(world_data).rooms["atrio"]

    assert is_named(room, words_of("vai alle scuderie"))
    assert not is_named(room, words_of("vai in cucina"))


@pytest.mark.parametrize("text", ["ecco la moneta", "ecco il soldo"])
def test_handing_over_an_item_is_giving_it(keeper, text):
    # "ecco le more" to the bear: the model answered "guarda", or nothing at all.
    assert parse_giving(keeper, text) == Action(verb="dai", target="moneta")


def test_holding_an_item_is_left_to_the_llm(keeper):
    # "tieni la corda" may be "take it" or "hold it".
    assert parse_giving(keeper, "tieni la moneta") is None
