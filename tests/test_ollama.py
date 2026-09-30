"""The real model on the sample castle: skipped unless OLLAMA_TESTS=1 (needs Ollama running).

    $env:OLLAMA_TESTS=1; .venv\\Scripts\\python -m pytest tests/test_ollama.py -v -s

Each sentence is interpreted, then executed by the engine: the test checks the effect on the game,
so equivalent actions ("apri la porta con la chiave" / "usa la chiave con la porta") both pass.
With -s it also prints how long each call took.
"""

import os
import time

import pytest

from app.config import Settings, make_client
from app.engine.engine import NOBODY_HERE, NOT_HERE, NOTHING_HAPPENS, OUT_OF_REACH, Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, FlagSet, GameState, Item, World
from app.game import NOT_A_GAME_ACTION, NOT_UNDERSTOOD, Game
from app.llm.interpreter import NotUnderstood, interpret

pytestmark = pytest.mark.skipif(os.environ.get("OLLAMA_TESTS") != "1", reason="needs Ollama: set OLLAMA_TESTS=1")

CASTLE = load_world(WORLDS_DIR / "rocca")
RULE = {rule_id: rule.text for rule_id, rule in CASTLE.rules.items()}
PILGRIM = CASTLE.characters["pellegrino"]
ANSWER = {topic_id: topic.text for topic_id, topic in PILGRIM.topics.items()}


@pytest.fixture(scope="module")
def llm():
    client = make_client(Settings.from_env())
    if client is None or (reason := client.unavailable_reason()):
        pytest.skip(f"LLM not available: {reason if client else 'LLM=off'}")
    return client


def near(engine: Engine, state: GameState) -> list[Item]:
    """What the game passes to the interpreter: items in reach, then those in sight."""
    return engine.in_reach(state) + engine.visible(state)


def understood(llm, engine: Engine, state: GameState, sentence: str) -> Action | NotUnderstood:
    """The sentence interpreted as the game does it, with the time the call took."""
    start = time.perf_counter()
    action = interpret(
        llm, sentence, near(engine, state), engine.known_exits(state), engine.characters_here(state), engine.world.game.examples
    )
    print(f"\n  {time.perf_counter() - start:4.1f}s  {sentence!r} -> {action}")
    return action


def game_in(room: str, *carried: str) -> tuple[Engine, GameState]:
    engine = Engine(CASTLE)
    state, _ = engine.new_game()
    state.current_room = room
    for item_id in carried:
        state.item_locations[item_id] = "inventory"
    if "corda_con_gancio" in carried:
        state.item_locations["corda"] = state.item_locations["gancio"] = None
    return engine, state


CASES = [
    # (room, carried items, sentence, check on (outcome, state))
    ("cucina", (), "raccogli quel vecchio gancio", lambda o, s: s.item_locations["gancio"] == "inventory"),
    ("scuderia", ("gancio",), "lega la corda al gancio", lambda o, s: o.text == RULE["lega_gancio"]),
    ("cortile", ("corda_con_gancio",), "cala il rampino giù nel pozzo", lambda o, s: o.text == RULE["pesca_chiave"]),
    # Found while playing: "butta" and "getta" come back as "lascia" with both items.
    ("cortile", ("corda_con_gancio",), "butta il rampino nel pozzo", lambda o, s: o.text == RULE["pesca_chiave"]),
    ("cortile", ("corda_con_gancio",), "getta il rampino nel pozzo", lambda o, s: o.text == RULE["pesca_chiave"]),
    ("cortile", ("chiave_torre",), "provo ad aprire la porta usando la chiave", lambda o, s: o.text == RULE["apri_torre"]),
    ("cortile", (), "dai un'occhiata al pozzo", lambda o, s: o.text == CASTLE.items["pozzo"].description),
    ("cortile", (), "torna verso ovest", lambda o, s: s.current_room == "cucina"),
    ("cortile", ("corda",), "metti giù la corda", lambda o, s: s.item_locations["corda"] == "cortile"),
    ("cortile", ("corda",), "cosa ho con me?", lambda o, s: o.inventory == ("corda",)),
    ("cortile", (), "vado in cucina", lambda o, s: s.current_room == "cucina"),
    ("cortile", (), "torno di corsa nella scuderia", lambda o, s: s.current_room == "scuderia"),
]


@pytest.mark.parametrize(("room", "carried", "sentence", "check"), CASES, ids=[case[2] for case in CASES])
def test_free_sentences_become_the_right_action(llm, room, carried, sentence, check):
    engine, state = game_in(room, *carried)

    action = understood(llm, engine, state, sentence)

    assert isinstance(action, Action)
    assert check(engine.execute(state, action), state)


# The bug found while playing: a sentence with a purpose. The player had examined the well,
# so the key was in sight at the bottom of it.
PURPOSE = [
    "usa il rampino per recuperare la chiave dal pozzo",
    "provo a ripescare la chiave nel pozzo col rampino",
    "recupera la chiave dal pozzo con il rampino",
]


@pytest.mark.parametrize("sentence", PURPOSE)
def test_the_grapple_fishes_the_key_seen_in_the_well(llm, sentence):
    engine, state = game_in("cortile", "corda_con_gancio")
    engine.execute(state, Action(verb="esamina", target="pozzo"))

    action = understood(llm, engine, state, sentence)

    assert isinstance(action, Action)
    assert engine.execute(state, action).text == RULE["pesca_chiave"]


@pytest.mark.parametrize("sentence", ["ciao, come stai?", "che tempo farà domani?"])
def test_small_talk_is_not_understood(llm, sentence):
    engine, state = game_in("cortile")

    result = understood(llm, engine, state, sentence)

    # With nobody around, "ciao" is no game action either (the model may answer "parla").
    assert isinstance(result, NotUnderstood)
    assert result.not_an_action


@pytest.mark.parametrize(
    ("room", "sentence"),
    [
        ("cortile", "vado nella cantina"),
        # Found while playing: the kitchen is past the courtyard, and the model answers "ovest".
        ("scuderia", "vai in cucina"),
    ],
)
def test_a_place_that_is_not_an_exit_does_not_move_the_player(llm, room, sentence):
    engine, state = game_in(room)
    game = Game(engine, llm, state=state)

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer!r}")

    assert state.current_room == room


# --- The pilgrim in the stable -------------------------------------------------------------------

DIALOGUE = [
    ("salve, pellegrino!", PILGRIM.greeting),
    ("pellegrino, cosa sai della torre?", ANSWER["torre"]),
    ("gli chiedo del pozzo", ANSWER["pozzo"]),
    ("chiedo al vecchio come si esce da qui", ANSWER["portone"]),
    ("gli chiedo se ha fame", PILGRIM.unknown),
]


@pytest.mark.parametrize(("sentence", "answer"), DIALOGUE, ids=[case[0] for case in DIALOGUE])
def test_the_pilgrim_answers_free_questions(llm, sentence, answer):
    engine, state = game_in("scuderia")

    action = understood(llm, engine, state, sentence)

    assert isinstance(action, Action)
    assert engine.execute(state, action).text == answer


GIFTS = ["offri la corda al vecchio", "do la corda al pellegrino", "regalo la corda al viandante"]


@pytest.mark.parametrize("sentence", GIFTS)
def test_the_pilgrim_refuses_what_he_is_given(llm, sentence):
    engine, state = game_in("scuderia", "corda")

    action = understood(llm, engine, state, sentence)

    assert isinstance(action, Action)
    assert engine.execute(state, action).text == PILGRIM.refuses
    assert state.item_locations["corda"] == "inventory"


# --- Dangers: jumping into the well kills ---------------------------------------------------------

DEATH = next(ending.text for ending in CASTLE.game.endings if ending.when == FlagSet(flag="caduto_nel_pozzo"))
# Sentences the parser leaves to the model ("salta nel pozzo" it knows by itself).
JUMPS = ["mi butto nel pozzo", "mi tuffo nel pozzo", "voglio saltare dentro il pozzo", "salto giù nel pozzo"]


@pytest.mark.parametrize("sentence", JUMPS)
def test_jumping_into_the_well_kills(llm, sentence):
    engine, state = game_in("cortile")
    game = Game(engine, llm, state=state)

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert answer.endswith(DEATH)
    assert game.finished


# Nobody dies without asking for it: at worst the game asks "Vuoi saltare nel pozzo?".
NOT_JUMPS = [
    ((), "guardo giù nel pozzo"),
    ((), "mi affaccio al pozzo"),
    ((), "entro nel pozzo"),
    (("corda_con_gancio",), "lancio il rampino nel pozzo"),
]


@pytest.mark.parametrize(("carried", "sentence"), NOT_JUMPS, ids=[case[1] for case in NOT_JUMPS])
def test_only_asking_for_it_jumps_into_the_well(llm, carried, sentence):
    engine, state = game_in("cortile", *carried)
    game = Game(engine, llm, state=state)

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert not game.finished


# --- Il draghetto raffreddato: frasi da bambino --------------------------------------------------

DRAGON = load_world(WORLDS_DIR / "draghetto")
DRAGON_RULE = {rule_id: rule.text for rule_id, rule in DRAGON.rules.items()}
DRAGONET = DRAGON.characters["draghetto"]
# Everything the dragon may answer: a question the model maps to any topic is fine.
DRAGON_SAYS = {
    DRAGONET.greeting,
    DRAGONET.unknown,
    *(topic.text for topic in DRAGONET.topics.values()),
    *(variant.text for topic in DRAGONET.topics.values() for variant in topic.variants),
}
CLIMB = DRAGON.rooms["quercia"].exits["su"].otherwise


def dragon_in(room: str, *carried: str, flags: tuple[str, ...] = (), seen: tuple[str, ...] = ()):
    engine = Engine(DRAGON)
    state, _ = engine.new_game()
    state.current_room = room
    for item_id in carried:
        state.item_locations[item_id] = "inventory"
    state.flags.update(flags)
    state.seen.update(seen)
    return engine, state


DRAGON_CASES = [
    # (room, carried items, flags, items seen, sentence, check on (outcome, state))
    ("radura", (), (), (), "ciao draghetto", lambda o, s: o.text == DRAGONET.greeting),
    ("radura", (), (), (), "come posso aiutarti?", lambda o, s: o.text in DRAGON_SAYS),
    # The saying must stay a look, with the dragon right there (found by the review of piece 2).
    ("radura", (), (), (), "dai un'occhiata al draghetto", lambda o, s: o.text == DRAGONET.description),
    ("roveto", (), (), (), "raccolgo le more", lambda o, s: s.item_locations["more"] == "inventory"),
    ("tana", ("more",), (), (), "do le more all'orso", lambda o, s: o.text == DRAGON_RULE["scambia_more"]),
    ("quercia", ("ramo",), (), (), "salgo sull'albero", lambda o, s: o.text == CLIMB),
    ("quercia", ("ramo",), (), ("piuma",), "stacco la piuma col bastone",
     lambda o, s: o.text == DRAGON_RULE["stacca_piuma"]),
    ("radura", ("vasetto_miele",), (), (), "gli do il miele", lambda o, s: o.text == DRAGON_RULE["miele_al_drago"]),
    ("radura", ("piuma",), ("gola_guarita",), (), "faccio il solletico al drago con la piuma",
     lambda o, s: o.text == DRAGON_RULE["solletico"]),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "seen", "sentence", "check"), DRAGON_CASES, ids=[case[4] for case in DRAGON_CASES]
)
def test_kids_sentences_in_the_dragon_adventure(llm, room, carried, flags, seen, sentence, check):
    engine, state = dragon_in(room, *carried, flags=flags, seen=seen)

    action = understood(llm, engine, state, sentence)

    assert isinstance(action, Action)
    assert check(engine.execute(state, action), state)


# --- Sentences found while playing both adventures (2026-09-28) ----------------------------------
# Through the whole turn, as the player gets it: the model's answer, the checks on it, the engine
# and the fixed text. The check is on what the player sees, or on the game not doing what the
# sentence doesn't ask for.

TOPIC = {topic_id: topic.text for topic_id, topic in DRAGONET.topics.items()}
BEAR = DRAGON.characters["orso"]


def playing(llm, world: World, room: str, carried=(), flags=(), seen=()) -> Game:
    game = Game(Engine(world), llm)
    state = game.state
    state.current_room = room
    state.visited.add(room)
    for item_id in carried:
        state.item_locations[item_id] = "inventory"
    if "corda_con_gancio" in carried:
        state.item_locations["corda"] = state.item_locations["gancio"] = None
    state.flags.update(flags)
    state.seen.update(seen)
    return game


def says(*texts: str):
    """The answer has one of the texts (after "(…)" for an interpreted action, before an ending)."""
    return lambda answer, game: any(text in answer for text in texts)


def stays_in(room: str):
    """Nothing done and nothing asked: the sentence is no move ("attento alle spine")."""
    return lambda answer, game: game.state.current_room == room and game.pending is None


def goes_to(room: str):
    return lambda answer, game: game.state.current_room == room


NOTHING_DONE = (NOT_UNDERSTOOD, NOT_A_GAME_ACTION)

PLAYED = [
    # (world, room, carried, flags, seen, sentence, check on (answer, game))
    # A question became an action: this one tied the hook to the rope, puzzle solved.
    (CASTLE, "scuderia", ("gancio",), (), (), "a cosa mi serve questa corda?",
     lambda a, g: g.state.item_locations["corda_con_gancio"] is None and g.pending is None),
    (CASTLE, "scuderia", (), (), (), "come si fa a usire",
     says(ANSWER["portone"], PILGRIM.unknown, PILGRIM.greeting, *NOTHING_DONE)),
    (CASTLE, "scuderia", (), (), (), "chi sei?", says(PILGRIM.gestures["chi_sei"].text)),
    (CASTLE, "scuderia", (), (), (), "vecchio, come ti chiami?", says(PILGRIM.gestures["chi_sei"].text)),
    (CASTLE, "cortile", (), (), (), "ma non c'è la chiave nel pozzo",
     says(CASTLE.items["pozzo"].description, NOT_HERE, *NOTHING_DONE)),
    # With the gestures in the prompt the model says "esamina il pellegrino" (2026-09-30): the question
    # names the castellano, and the game asks about the rocca.
    (CASTLE, "scuderia", (), (), (), "chi era il castellano?", says(ANSWER["rocca"])),
    (CASTLE, "scuderia", (), (), (), "grazie mille", says(PILGRIM.gestures["grazie"].text)),
    (CASTLE, "scuderia", (), (), (), "arrivederci", says(PILGRIM.gestures["congedo"].text)),
    # Something that isn't here: the model picked anything ("apri il pellegrino").
    (CASTLE, "scuderia", (), (), (), "apro la porta di ferro", says(NOT_HERE)),
    (CASTLE, "cortile", (), (), (), "scavalco le mura", stays_in("cortile")),
    (CASTLE, "cortile", (), (), (), "busso alla porta della torre", stays_in("cortile")),
    (CASTLE, "cortile", (), (), (), "sfondo la porta a calci",
     says(RULE["apri_torre_senza_chiave"], NOTHING_HAPPENS)),
    (CASTLE, "cortile", ("corda_con_gancio",), (), (), "aggancia la corda alla vera di pietra",
     says(RULE["pesca_chiave"])),
    (CASTLE, "cortile", ("corda",), (), (),
     "bene ora utilizza la corda che hai preso nella scuderia e legala alla vera del pozzo", says(RULE["cala_corda"])),
    (CASTLE, "cortile", ("corda_con_gancio",), (), ("chiave_torre",), "afferra la ciave nel pozzo",
     says(RULE["pesca_chiave"], OUT_OF_REACH)),
    (CASTLE, "cortile", (), (), (), "sali la scala", says(CASTLE.rooms["cortile"].exits["nord"].otherwise)),
    # Il draghetto, played as a kid.
    (DRAGON, "radura", (), (), (), "perche hai il naso rosso", says(*DRAGON_SAYS)),
    (DRAGON, "radura", (), (), (), "cosa ti è successo?", says(TOPIC["raffreddore"], DRAGONET.greeting)),
    (DRAGON, "radura", (), (), (), "cosa ti serve?", says(TOPIC["raffreddore"], DRAGONET.greeting)),
    (DRAGON, "radura", (), (), (), "aiuta il draghetto", stays_in("radura")),
    (DRAGON, "quercia", ("ramo",), (), (), "quanto è lungo il ramo?", says(DRAGON.items["ramo"].description)),
    (DRAGON, "roveto", (), (), (), "attento alle spine", stays_in("roveto")),
    (DRAGON, "ruscello", ("more",), (), (), "vuoi delle more?", stays_in("ruscello")),
    (DRAGON, "radura", (), (), (), "mangio una mora", says(NOT_HERE)),
    (DRAGON, "quercia", (), (), (), "prendi una scala", says(*NOTHING_DONE)),
    (DRAGON, "ruscello", ("more",), (), (), "bevo un po' d'acqua",
     lambda a, g: g.pending is None and g.state.item_locations["more"] == "inventory"),
    (DRAGON, "tana", ("more",), (), (), "ecco le more", says(DRAGON_RULE["scambia_more"])),
    (DRAGON, "tana", ("more",), (), (), "mi dai il tuo miele?", says(BEAR.topics["miele"].text)),
    (DRAGON, "radura", ("more",), (), (), "mi dai il miele?", says(TOPIC["miele"])),
    (DRAGON, "radura", ("ramo", "piuma"), ("gola_guarita",), (), "ti faccio il solletico sul naso con la piuma",
     says(DRAGON_RULE["solletico"])),
    (DRAGON, "quercia", ("ramo",), (), (), "guardo su nell'albero",
     says(DRAGON.items["quercia"].description, DRAGON.items["nido"].description)),
    (DRAGON, "ruscello", (), (), (), "attraverso il ponte", goes_to("tana")),
    (DRAGON, "radura", (), (), (), "torno dal draghetto", stays_in("radura")),
    (DRAGON, "quercia", (), (), (), "vai a casa",
     lambda a, g: CLIMB not in a and g.pending != Action(verb="vai", direction="su")),
    (DRAGON, "radura", (), (), (), "ciao orso", says(NOBODY_HERE)),
    (DRAGON, "ruscello", (), (), (), "ciao orso", says(NOBODY_HERE)),
    (DRAGON, "quercia", (), (), (), "mi arrampico sulla quercia", says(CLIMB)),
    (DRAGON, "radura", (), (), (), "vado a prendere le more", lambda a, g: g.state.current_room == "roveto" or a == NOT_HERE),
    # From the kid's game: the den is past the brook, so west is asked about, never another way.
    (DRAGON, "radura", (), (), (), "vai dall orso",
     lambda a, g: g.state.current_room in ("radura", "ruscello") and g.pending in (None, Action(verb="vai", direction="ovest"))),
    # Found by the review: a gift or a question naming someone who isn't here.
    (DRAGON, "tana", ("more",), (), (), "do le more al drago", lambda a, g: g.state.item_locations["more"] == "inventory"),
    (DRAGON, "radura", ("vasetto_miele",), (), (), "porto il miele all'orso",
     lambda a, g: "gola_guarita" not in g.state.flags and g.state.item_locations["vasetto_miele"] == "inventory"),
    (DRAGON, "radura", (), (), (), "conosci l'orso?", says(TOPIC["orso"])),
    (DRAGON, "radura", (), (), (), "hai visto l'orso?", says(TOPIC["orso"])),
    (DRAGON, "radura", (), (), (), "salgo sul sasso", stays_in("radura")),
    (DRAGON, "ruscello", (), (), (), "scendo nel ruscello", stays_in("ruscello")),
]  # fmt: skip


# Still wrong with qwen2.5:3b (2026-09-28). None of them changes the game: at worst the game asks,
# says "Non ho capito." or does something harmless ("lascia" the door: "Non ce l'hai.").
KNOWN_LIMITS = {
    "busso alla porta della torre": "no verb for knocking: the model says 'tira' and the game asks",
    "sfondo la porta a calci": "the model says 'lascia' the door: 'Non ce l'hai.'",
    "aggancia la corda alla vera di pietra": "unstable: right in some runs, 'Non ho capito.' in others",
    "afferra la ciave nel pozzo": "the well comes back as the tool: 'Vuoi prendere la chiave di ferro con il pozzo?'",
    "ti faccio il solletico sul naso con la piuma": "with 'ti' the model loses the dragon: 'Vuoi usare la piuma?'",
    "guardo su nell'albero": "'guarda su' is looking around, not at the oak",
    # Found with the dialogues (2026-09-30).
    "siete una vecchia strega": "'vecchia' is nearly 'vecchio', Ettore's alias: 'Non vedi nessuno del genere qui.'",
}


@pytest.mark.parametrize(
    ("world", "room", "carried", "flags", "seen", "sentence", "check"),
    [
        pytest.param(
            *case,
            id=f"{case[1]}: {case[5]}",
            marks=pytest.mark.xfail(reason=KNOWN_LIMITS[case[5]], strict=False) if case[5] in KNOWN_LIMITS else (),
        )
        for case in PLAYED
    ],
)
def test_sentences_found_while_playing(llm, world, room, carried, flags, seen, sentence, check):
    game = playing(llm, world, room, carried, flags, seen)

    start = time.perf_counter()
    answer = game.turn(sentence)
    print(f"\n  {time.perf_counter() - start:4.1f}s  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert check(answer, game)


# --- La Stella di Valdimora, atto 1 ------------------------------------------------------------------

VALDIMORA = load_world(WORLDS_DIR / "valdimora")
VALDIMORA_RULE = {rule_id: rule.text for rule_id, rule in VALDIMORA.rules.items()}
ETTORE = VALDIMORA.characters["ettore"]

VALDIMORA_CASES = [
    # (room, carried, flags, sentence, check on (answer, game))
    ("atrio", (), (), "leggo l'annuncio funebre", says(VALDIMORA_RULE["leggi_annuncio"])),
    ("rimessa", (), (), "apro la mia valigia", lambda a, g: g.state.item_locations["fotografia"] == "inventory"),
    ("rimessa", (), (), "prendo l'olio", lambda a, g: g.state.item_locations["oliatore"] == "inventory"),
    # As below: taken for asking about the letter, Ettore asks to see it, a fair hint.
    ("stanza_maggiordomo", (), (), "mostro la lettera al maggiordomo",
     lambda a, g: g.state.item_locations["busta"] == "inventory" or ETTORE.topics["lettera"].text in a),
    # The model may take it for asking about the letter: Ettore then asks to see it, a fair hint.
    ("stanza_maggiordomo", (), (), "faccio vedere la lettera a Ettore",
     lambda a, g: g.state.item_locations["busta"] == "inventory" or ETTORE.topics["lettera"].text in a),
    ("stanza_maggiordomo", ("busta",), ("busta_data",), "leggo il biglietto della contessa",
     says(VALDIMORA_RULE["leggi_busta"])),
    ("cortile", (), ("busta_letta",), "guardo bene sotto la meridiana",
     says(VALDIMORA.items["meridiana"].variants[1].text)),
    ("cortile", ("oliatore",), ("busta_letta",), "metto un po' d'olio sulla meridiana",
     lambda a, g: "meridiana_oliata" in g.state.flags),
    # Done, or asked first when the model picked another tool and «incavo» is only a guess.
    ("cortile", (), ("busta_letta", "meridiana_oliata"), "infilo il medaglione nell'incavo",
     lambda a, g: g.state.item_locations["biglietto_livia"] == "inventory"
     or g.pending == Action(verb="usa", target="medaglione", with_="meridiana")),
    ("stanza_maggiordomo", (), ("busta_data",), "chiedo a Ettore di mettere una buona parola con Livia",
     lambda a, g: "ettore_garantisce" in g.state.flags),
    ("ufficio_governante", ("biglietto_livia",), ("ettore_garantisce",), "consegno il biglietto a Livia",
     lambda a, g: g.state.item_locations["chiave_scalone"] == "inventory"),
    ("atrio", ("chiave_scalone",), (), "salgo lo scalone",
     says(VALDIMORA.rooms["atrio"].exits["su"].otherwise)),
    ("stanza_maggiordomo", (), ("busta_data",), "gli chiedo di mia madre",
     says(ETTORE.topics["clara"].text)),
    ("biliardo", ("grappa",), (), "offro la grappa al dottore", lambda a, g: "ferri_addormentato" in g.state.flags),
    ("biliardo", (), ("ferri_addormentato",), "frugo nella borsa del dottore",
     lambda a, g: g.state.item_locations["chiavetta"] == "inventory" or "nessuno ti impedirebbe" in a),
    ("dispensa", ("chiavetta",), (), "apro l'armadietto dei medicinali con la chiavetta",
     lambda a, g: g.state.item_locations["registro"] == "inventory"),
    # «chi sei?» to Agnese: her own answer; no action may start.
    ("cappella", (), (), "chi sei?", says(VALDIMORA.characters["agnese"].gestures["chi_sei"].text)),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "sentence", "check"),
    [pytest.param(*case, id=f"{case[0]}: {case[3]}") for case in VALDIMORA_CASES],
)
def test_valdimora_free_sentences(llm, room, carried, flags, sentence, check):
    game = playing(llm, VALDIMORA, room, carried, flags, ())

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert check(answer, game)


# --- Dialogues: gestures said freely -------------------------------------------------------------

LIVIA = VALDIMORA.characters["livia"]
AGNESE = VALDIMORA.characters["agnese"]


def gesture_of(character, gesture: str):
    return says(character.gestures[gesture].text)


GESTURE_CASES = [
    # (world, room, sentence, check on (answer, game)). None of them is a formula of the parser: they go to the model.
    (VALDIMORA, "ufficio_governante", "vi ringrazio tanto, signora", gesture_of(LIVIA, "grazie")),
    (VALDIMORA, "ufficio_governante", "come vi sentite, oggi?", gesture_of(LIVIA, "come_stai")),
    (VALDIMORA, "ufficio_governante", "e voi chi siete, di preciso?", gesture_of(LIVIA, "chi_sei")),
    (VALDIMORA, "ufficio_governante", "siete una vecchia strega", gesture_of(LIVIA, "scortesia")),
    (VALDIMORA, "ufficio_governante", "chiedo a Livia di Corrado", says(LIVIA.topics["corrado"].text)),
    (VALDIMORA, "ufficio_governante", "chiedo a Livia della meridiana", says(LIVIA.unknown)),
    (VALDIMORA, "cappella", "perdonatemi se vi disturbo", gesture_of(AGNESE, "scuse")),
    (VALDIMORA, "cappella", "mi dispiace tanto per la contessa", says(AGNESE.topics["contessa"].text, AGNESE.gestures["scuse"].text)),
    (VALDIMORA, "cappella", "adesso vado, ci vediamo più tardi", gesture_of(AGNESE, "congedo")),
    (CASTLE, "scuderia", "grazie mille, buon uomo", gesture_of(PILGRIM, "grazie")),
    (CASTLE, "scuderia", "come ti senti, vecchio?", gesture_of(PILGRIM, "come_stai")),
    (CASTLE, "scuderia", "sei proprio un vecchio brontolone", gesture_of(PILGRIM, "scortesia")),
    (CASTLE, "scuderia", "addio, e buona fortuna", gesture_of(PILGRIM, "congedo")),
    (DRAGON, "radura", "ti ringrazio tanto, draghetto", gesture_of(DRAGONET, "grazie")),
    (DRAGON, "radura", "come stai oggi?", gesture_of(DRAGONET, "come_stai")),
    (DRAGON, "radura", "sei un drago cattivo", gesture_of(DRAGONET, "scortesia")),
    (DRAGON, "tana", "chi sei tu?", gesture_of(BEAR, "chi_sei")),
    (DRAGON, "tana", "scusami tanto, orso", gesture_of(BEAR, "scuse")),
    # Found by the final review: a question behind the words of a gesture is still the question.
    (VALDIMORA, "stanza_maggiordomo", "scusate, cosa sapete della contessa?", says(ETTORE.topics["contessa"].text)),
    (DRAGON, "radura", "i draghi cattivi sputano fuoco?", says(*DRAGON_SAYS)),
]  # fmt: skip


@pytest.mark.parametrize(
    ("world", "room", "sentence", "check"),
    [
        pytest.param(
            *case,
            id=f"{case[1]}: {case[2]}",
            marks=pytest.mark.xfail(reason=KNOWN_LIMITS[case[2]], strict=False) if case[2] in KNOWN_LIMITS else (),
        )
        for case in GESTURE_CASES
    ],
)
def test_gestures_said_freely(llm, world, room, sentence, check):
    game = playing(llm, world, room)

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert check(answer, game)
