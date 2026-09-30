"""The LLM interpreter: player's sentence -> Action, with the model replaced by canned answers."""

from pathlib import Path

import pytest

from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Direction, Item, World
from app.llm.client import FakeLLMClient
from app.llm.interpreter import NotUnderstood, describe, interpret, interpreter_schema
from app.llm.prompts import interpreter_system


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world(WORLDS_DIR / "rocca")


@pytest.fixture
def in_reach(castle) -> list[Item]:
    return [castle.items[item_id] for item_id in ("pozzo", "porta_torre", "portone", "corda_con_gancio")]


def test_schema_limits_the_answer_to_known_verbs_items_in_reach_and_directions(in_reach):
    schema = interpreter_schema(in_reach)
    properties = schema["properties"]

    assert schema["required"] == ["verbo", "bersaglio", "con"]
    assert properties["verbo"]["enum"] == [
        "esamina", "prendi", "lascia", "usa", "apri", "chiudi", "spingi", "tira", "leggi", "dai", "salta",
        "parla", "chiedi", "vai", "guarda", "inventario", "altro",
    ]  # fmt: skip
    assert properties["bersaglio"]["enum"] == [
        "pozzo", "porta della torre", "portone", "corda con gancio",
        "nord", "sud", "est", "ovest", "su", "giù", "nessuno",
    ]  # fmt: skip
    assert properties["con"]["enum"] == ["pozzo", "porta della torre", "portone", "corda con gancio", "nessuno"]


def test_the_model_gets_a_fixed_system_prompt_then_items_exits_and_sentence(castle, in_reach):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}, {"verbo": "altro"}])
    rooms = castle.rooms

    exits = [(Direction.NORTH, rooms["torre"]), (Direction.EAST, rooms["scuderia"]), (Direction.WEST, rooms["cucina"])]
    interpret(fake, "cala il rampino nel pozzo", in_reach, exits)
    interpret(fake, "saluta", in_reach[:1], [(Direction.NORTH, None), (Direction.WEST, rooms["cucina"])])

    (first_system, first_user), (second_system, second_user) = fake.calls
    assert first_system == second_system  # the fixed part comes first, so Ollama can cache it
    assert first_user == (
        "Oggetti: pozzo (vera); porta della torre (porta, porta di ferro); portone; "
        "corda con gancio (corda, fune, gancio, uncino, rampino)\n"
        "Uscite: nord (Torre: scala, scale), est (Scuderia: scuderie, stalla, pellegrino), ovest (Cucina)\n"
        "Frase: cala il rampino nel pozzo"
    )
    assert second_user == "Oggetti: pozzo (vera)\nUscite: nord, ovest (Cucina)\nFrase: saluta"


def test_the_model_is_told_the_other_names_of_the_places_the_exits_lead_to(castle):
    # "vado dall'orso" at the brook went east: the model didn't know the bear lives in the den.
    den = castle.rooms["cucina"].model_copy(update={"name": "Tana", "aliases": ("orso", "grotta")})
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "vado dall'orso", [], [(Direction.EAST, castle.rooms["cucina"]), (Direction.WEST, den)])

    assert fake.calls[0][1].split("\n")[1] == "Uscite: est (Cucina), ovest (Tana: orso, grotta)"


def test_no_items_in_reach_and_no_exits(castle):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "salta", [])

    assert fake.calls[0][1] == "Oggetti: nessuno\nUscite: nessuna\nFrase: salta"


@pytest.mark.parametrize(
    ("sentence", "reply", "expected"),
    [
        ("cala il rampino nel pozzo", {"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"},
         Action(verb="usa", target="corda_con_gancio", with_="pozzo")),
        ("dai una spinta al portone", {"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"},
         Action(verb="spingi", target="portone")),
        ("metti giù il rampino", {"verbo": "lascia", "bersaglio": "corda con gancio", "con": "nessuno"},
         Action(verb="lascia", target="corda_con_gancio")),
        ("raccogli la corda", {"verbo": "prendi", "bersaglio": "corda con gancio", "con": "corda con gancio"},
         Action(verb="prendi", target="corda_con_gancio")),
        ("torna a nord", {"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}, Action(verb="vai", direction="nord")),
        ("scendo di sotto", {"verbo": "vai", "bersaglio": "giù", "con": "nessuno"}, Action(verb="vai", direction="giù")),
        ("guardati intorno", {"verbo": "guarda", "bersaglio": "nessuno", "con": "nessuno"}, Action(verb="guarda")),
        ("guarda nel pozzo", {"verbo": "guarda", "bersaglio": "pozzo", "con": "nessuno"},
         Action(verb="esamina", target="pozzo")),
        ("cosa ho con me?", {"verbo": "inventario", "bersaglio": "nessuno", "con": "nessuno"},
         Action(verb="inventario")),
    ],
)  # fmt: skip
def test_replies_become_actions_on_item_ids(in_reach, sentence, reply, expected):
    assert interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach) == expected


def test_the_model_may_say_the_sentence_is_not_a_game_action(in_reach):
    reply = {"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}

    result = interpret(FakeLLMClient(json_replies=[reply]), "che ore sono?", in_reach)

    assert result == NotUnderstood("la frase non è un'azione di gioco", not_an_action=True)


@pytest.mark.parametrize(
    "reply",
    [
        {"verbo": "prendi", "bersaglio": "nessuno", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "nord", "con": "nessuno"},
        {"verbo": "prendi", "bersaglio": "chiave di ferro", "con": "nessuno"},
        {"verbo": "vai", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": "vola", "bersaglio": "pozzo", "con": "nessuno"},
        {"verbo": ["usa"], "bersaglio": {"x": 1}, "con": None},
        {},
    ],
    ids=["no target", "direction as target", "item out of reach", "go to an item",
         "unknown verb", "wrong types", "empty"],
)  # fmt: skip
def test_replies_that_make_no_sense_are_not_understood(in_reach, reply):
    result = interpret(FakeLLMClient(json_replies=[reply]), "frase", in_reach)

    assert isinstance(result, NotUnderstood)
    assert not result.not_an_action


def test_a_broken_model_means_not_understood(in_reach):
    result = interpret(FakeLLMClient(), "frase", in_reach)

    assert result == NotUnderstood("il modello non ha dato una risposta valida")


# --- Log of how the answer was understood ---------------------------------------------------------


@pytest.mark.parametrize(
    ("reply", "logged"),
    [
        ({"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"},
         "=== azione: usa corda_con_gancio con pozzo"),
        ({"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}, "=== azione: spingi portone"),
        ({"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}, "=== azione: vai nord"),
        ({"verbo": "apri", "bersaglio": "porta della torre", "con": "nessuno"},
         "=== non capito: la frase non nomina 'porta della torre'"),
        ({"verbo": "inventario", "bersaglio": "nessuno", "con": "nessuno"}, "=== azione: inventario"),
        ({"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"},
         "=== non capito: la frase non è un'azione di gioco"),
        ({"verbo": "vola", "bersaglio": "pozzo", "con": "nessuno"}, "=== non capito: verbo sconosciuto 'vola'"),
        ({"verbo": "vai", "bersaglio": "pozzo", "con": "nessuno"}, "=== non capito: direzione non valida 'pozzo'"),
        ({"verbo": "prendi", "bersaglio": "nessuno", "con": "nessuno"},
         "=== non capito: bersaglio non a portata 'nessuno'"),
    ],
)  # fmt: skip
def test_how_the_answer_was_understood_is_logged(in_reach, caplog, reply, logged):
    sentence = "vai a nord e spingi il portone, poi cala il rampino nel pozzo"

    with caplog.at_level("INFO", logger="app.llm"):
        interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach)

    assert caplog.records[-1].getMessage() == logged


def test_a_broken_model_is_logged_as_not_understood(in_reach, caplog):
    with caplog.at_level("INFO", logger="app.llm"):
        interpret(FakeLLMClient(), "frase", in_reach)

    assert caplog.records[-1].getMessage() == "=== non capito: il modello non ha dato una risposta valida"


# --- The sentence with a purpose (bug found while playing) ------------------------------------------


def test_the_prompt_shows_a_sentence_with_a_purpose(castle):
    # Without this example qwen2.5:3b aimed the grapple at the door: "per recuperare la chiave" confused it.
    assert (
        "Frase: usa il rampino per recuperare la chiave dal pozzo\n"
        '{"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}\n'
    ) in interpreter_system(castle.game.examples)


def test_the_grapple_sentence_becomes_fishing_in_the_well(castle, in_reach):
    near = [*in_reach, castle.items["chiave_torre"]]
    fake = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}])

    action = interpret(fake, "usa il rampino per recuperare la chiave dal pozzo", near)

    assert action == Action(verb="usa", target="pozzo", with_="corda_con_gancio")
    assert fake.calls[0][1].startswith("Oggetti: pozzo (vera); porta della torre (porta, porta di ferro); portone; ")
    assert "; chiave di ferro (chiave)\n" in fake.calls[0][1]


# --- Throwing one thing into another (bug found while playing) -------------------------------------


def test_dropping_one_thing_into_another_is_using_them_together(in_reach):
    # "butta il rampino nel pozzo": qwen2.5:3b answers "lascia" with both items, even with "buttare"
    # moved under "usa" in the glossary. Dropping needs no second item: the two go together.
    fake = FakeLLMClient(json_replies=[{"verbo": "lascia", "bersaglio": "pozzo", "con": "corda con gancio"}])

    action = interpret(fake, "butta il rampino nel pozzo", in_reach)

    assert action == Action(verb="usa", target="pozzo", with_="corda_con_gancio")


# --- Jumping -----------------------------------------------------------------------------------------


def test_the_prompt_explains_jumping():
    assert "- salta: saltare, tuffarsi o buttarsi dentro qualcosa\n" in interpreter_system()


@pytest.mark.parametrize("sentence", ["mi butto nel pozzo", "voglio saltare giù nel pozzo"])
def test_jumping_into_an_item(in_reach, sentence):
    fake = FakeLLMClient(json_replies=[{"verbo": "salta", "bersaglio": "pozzo", "con": "nessuno"}])

    assert interpret(fake, sentence, in_reach) == Action(verb="salta", target="pozzo")


@pytest.mark.parametrize(
    ("sentence", "tool"),
    [("butta il rampino nel pozzo", "corda con gancio"), ("lancio il rampino nel pozzo", "nessuno")],
    ids=["the model gives the other item", "the sentence names it"],
)
def test_jumping_with_another_item_is_using_them_together(in_reach, sentence, tool):
    # Jumping may kill: throwing the grapple into the well must never become a jump.
    fake = FakeLLMClient(json_replies=[{"verbo": "salta", "bersaglio": "pozzo", "con": tool}])

    assert interpret(fake, sentence, in_reach) == Action(verb="usa", target="pozzo", with_="corda_con_gancio")


@pytest.mark.parametrize(
    ("sentence", "direction"), [("salgo sulla vera del pozzo", "su"), ("scendo nel pozzo", "giù")]
)
def test_climbing_is_no_jump(castle, in_reach, sentence, direction):
    # "salgo sul sasso" in the glade: with "salta" in the prompt the model heard a jump.
    fake = FakeLLMClient(json_replies=[{"verbo": "salta", "bersaglio": "pozzo", "con": "nessuno"}])

    action = interpret(fake, sentence, in_reach, [(Direction.NORTH, castle.rooms["torre"])])

    assert action == Action(verb="vai", direction=direction)


# --- What the sentence names wins over what the model picked (found playing Valdimora) --------------


@pytest.fixture(scope="module")
def valdimora() -> World:
    return load_world(WORLDS_DIR / "valdimora")


def valdimora_items(world: World, *item_ids: str) -> list[Item]:
    return [world.items[item_id] for item_id in item_ids]


def test_reading_has_no_tool_so_the_one_named_is_read(valdimora):
    # «leggo il biglietto della contessa»: the model read the letter, with the envelope as a tool.
    reply = {"verbo": "leggi", "bersaglio": "lettera della contessa", "con": "busta della contessa"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "busta")

    action = interpret(FakeLLMClient(json_replies=[reply]), "leggo il biglietto della contessa", in_reach)

    assert action == Action(verb="leggi", target="busta")


def test_the_only_other_item_named_is_only_a_guess_for_the_tool(valdimora):
    # «infilo il medaglione nell'incavo»: the model picked the letter as the tool; «incavo» is the
    # sundial. A guess, not an action: the game asks first (a question may name things too).
    reply = {"verbo": "usa", "bersaglio": "medaglione", "con": "lettera della contessa"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "meridiana")

    result = interpret(FakeLLMClient(json_replies=[reply]), "infilo il medaglione nell'incavo", in_reach)

    assert isinstance(result, NotUnderstood)
    assert result.guess == Action(verb="usa", target="medaglione", with_="meridiana")


def test_with_two_other_items_named_the_tool_is_not_guessed(valdimora):
    reply = {"verbo": "usa", "bersaglio": "medaglione", "con": "lettera della contessa"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "meridiana", "oliatore")

    result = interpret(FakeLLMClient(json_replies=[reply]), "infilo il medaglione nell'incavo con l'olio", in_reach)

    assert isinstance(result, NotUnderstood)
    assert result.guess is None


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [("frugo nella borsa del dottore", Action(verb="esamina", target="borsa")), ("cosa ho con me?", Action(verb="inventario"))],
    ids=["an item named: examining it", "no item named: the inventory"],
)  # fmt: skip
def test_the_inventory_of_an_item_the_sentence_names_is_examining_it(valdimora, sentence, expected):
    # «frugo nella borsa del dottore»: the model answered «inventario», with the bag as its target.
    reply = {"verbo": "inventario", "bersaglio": "borsa del dottore", "con": "nessuno"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "borsa")

    assert interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach) == expected


def test_an_item_the_model_calls_by_another_name_is_found(valdimora):
    # «offro la grappa al dottore»: the model answered «grappa», an alias, not «bottiglia di grappa».
    reply = {"verbo": "dai", "bersaglio": "dottor Ferri", "con": "grappa"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "grappa")
    characters = [(valdimora.characters["ferri"], [])]

    action = interpret(FakeLLMClient(json_replies=[reply]), "offro la grappa al dottore", in_reach, (), characters)

    assert action == Action(verb="dai", target="ferri", with_="grappa")


def test_nobody_can_be_jumped_into(keeper):
    items, characters = near_keeper(keeper)
    fake = FakeLLMClient(json_replies=[{"verbo": "salta", "bersaglio": "custode", "con": "nessuno"}])

    result = interpret(fake, "salto addosso al custode", items, (), characters)

    assert isinstance(result, NotUnderstood)


# --- Characters ----------------------------------------------------------------------------------


@pytest.fixture
def keeper(keeper_world) -> World:
    return World.model_validate(keeper_world)


def near_keeper(world: World) -> tuple[list[Item], list]:
    """The atrium of the test world: the lever and the coin, and the custode with two topics."""
    custode = world.characters["custode"]
    return [world.items["leva"], world.items["moneta"]], [(custode, [custode.topics["cella"], custode.topics["leva"]])]


def test_the_schema_adds_the_characters_here_and_their_topics(keeper):
    items, characters = near_keeper(keeper)

    properties = interpreter_schema(items, characters)["properties"]

    assert properties["bersaglio"]["enum"] == [
        "leva", "moneta", "custode", "nord", "sud", "est", "ovest", "su", "giù", "nessuno",
    ]  # fmt: skip
    # "leva" is both an item and a topic: it is offered once. With someone here, the gestures too.
    assert properties["con"]["enum"] == [
        "leva", "moneta", "custode", "cella", "saluto", "congedo", "grazie", "scuse", "come stai", "chi sei", "scortesia",
        "nessuno",
    ]  # fmt: skip


def test_the_gestures_are_offered_only_with_someone_here(keeper):
    items, _ = near_keeper(keeper)

    assert interpreter_schema(items)["properties"]["con"]["enum"] == ["leva", "moneta", "nessuno"]


@pytest.mark.parametrize(
    ("verb", "tool", "gesture"),
    [("parla", "grazie", "grazie"), ("parla", "come stai", "come_stai"), ("parla", "saluto", None),
     ("parla", "nessuno", None), ("chiedi", "grazie", "grazie")],
    ids=["thanks", "how are you", "greeting", "nothing is the greeting", "a gesture asked is said"],
)  # fmt: skip
def test_talking_comes_back_with_its_gesture(keeper, verb, tool, gesture):
    items, characters = near_keeper(keeper)
    reply = {"verbo": verb, "bersaglio": "custode", "con": tool}

    action = interpret(FakeLLMClient(json_replies=[reply]), "vi sono grata, custode", items, (), characters)

    assert action == Action(verb="parla", target="custode", gesture=gesture)


def test_with_two_here_nobody_named_is_the_last_one_spoken_to(keeper_world):
    keeper_world["characters"]["cuoca"] = {
        "name": "cuoca", "gender": "f", "description": "-", "location": "atrio",
        "greeting": "«Ciao.»", "unknown": "«Boh.»",
    }  # fmt: skip
    world = World.model_validate(keeper_world)
    characters = [(world.characters["custode"], []), (world.characters["cuoca"], [])]
    reply = {"verbo": "parla", "bersaglio": "nessuno", "con": "grazie"}

    def heard(last_speaker):
        return interpret(FakeLLMClient(json_replies=[reply]), "vi sono grata", [], (), characters, last_speaker=last_speaker)

    assert heard("cuoca") == Action(verb="parla", target="cuoca", gesture="grazie")
    assert isinstance(heard(None), NotUnderstood)
    assert isinstance(heard("pellegrino"), NotUnderstood)


def test_a_gesture_is_logged_with_the_action():
    assert describe(Action(verb="parla", target="custode", gesture="come_stai")) == "parla custode: come_stai"
    assert describe(Action(verb="parla", target="custode")) == "parla custode"


def test_the_prompt_explains_the_gestures():
    system = interpreter_system()

    assert "- parla: rivolgersi a un personaggio:" in system
    assert 'con "parla", il gesto' in system
    assert '{"verbo": "parla", "bersaglio": "cuoca", "con": "grazie"}' in system


def test_the_model_is_told_about_the_characters_only_when_someone_is_here(keeper):
    items, characters = near_keeper(keeper)
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}, {"verbo": "altro"}])

    interpret(fake, "salve", items, [(Direction.NORTH, None)], characters)
    interpret(fake, "salve", items, [(Direction.NORTH, None)])

    assert fake.calls[0][1] == (
        "Oggetti: leva; moneta (soldo)\n"
        "Personaggi: custode (guardiano, vecchio)\n"
        "Argomenti: cella (prigione); leva\n"
        "Uscite: nord\n"
        "Frase: salve"
    )
    assert fake.calls[1][1] == "Oggetti: leva; moneta (soldo)\nUscite: nord\nFrase: salve"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"verbo": "parla", "bersaglio": "custode", "con": "nessuno"}, Action(verb="parla", target="custode")),
        ({"verbo": "chiedi", "bersaglio": "custode", "con": "cella"},
         Action(verb="chiedi", target="custode", topic="cella")),
        ({"verbo": "chiedi", "bersaglio": "custode", "con": "leva"},
         Action(verb="chiedi", target="custode", topic="leva")),
        ({"verbo": "chiedi", "bersaglio": "custode", "con": "nessuno"}, Action(verb="chiedi", target="custode")),
        ({"verbo": "chiedi", "bersaglio": "custode", "con": "moneta"}, Action(verb="chiedi", target="custode")),
        ({"verbo": "chiedi", "bersaglio": "nessuno", "con": "cella"},
         Action(verb="chiedi", target="custode", topic="cella")),
        ({"verbo": "parla", "bersaglio": "nessuno", "con": "nessuno"}, Action(verb="parla", target="custode")),
        ({"verbo": "esamina", "bersaglio": "custode", "con": "nessuno"}, Action(verb="esamina", target="custode")),
        ({"verbo": "usa", "bersaglio": "moneta", "con": "custode"},
         Action(verb="usa", target="moneta", with_="custode")),
    ],
    ids=["talk", "ask", "ask about a topic named like an item", "ask about nothing known",
         "ask about an item that is no topic", "ask the only one here", "talk to the only one here",
         "examine", "use an item with"],
)  # fmt: skip
def test_replies_about_characters_become_actions(keeper, reply, expected):
    items, characters = near_keeper(keeper)
    sentence = "guardo il custode e gli do la moneta"

    assert interpret(FakeLLMClient(json_replies=[reply]), sentence, items, (), characters) == expected


@pytest.mark.parametrize(
    "reply",
    [
        {"verbo": "parla", "bersaglio": "moneta", "con": "nessuno"},
        {"verbo": "chiedi", "bersaglio": "leva", "con": "cella"},
    ],
    ids=["talk to an item", "ask an item"],
)
def test_only_characters_can_be_talked_to(keeper, reply):
    items, characters = near_keeper(keeper)

    assert isinstance(interpret(FakeLLMClient(json_replies=[reply]), "frase", items, (), characters), NotUnderstood)


def test_with_nobody_here_talking_is_no_game_action(keeper):
    # "ciao, come stai?" with nobody around: qwen2.5:3b answers "parla", the game says it isn't an action.
    items, _ = near_keeper(keeper)
    reply = {"verbo": "parla", "bersaglio": "nessuno", "con": "nessuno"}

    result = interpret(FakeLLMClient(json_replies=[reply]), "ciao, come stai?", items)

    assert result == NotUnderstood("non c'è nessuno con cui parlare", not_an_action=True, talking=True)


def test_a_question_is_logged_with_its_topic(keeper, caplog):
    items, characters = near_keeper(keeper)
    reply = {"verbo": "chiedi", "bersaglio": "custode", "con": "cella"}

    with caplog.at_level("INFO", logger="app.llm"):
        interpret(FakeLLMClient(json_replies=[reply]), "frase", items, (), characters)

    assert caplog.records[-1].getMessage() == "=== azione: chiedi custode di cella"


def test_the_prompt_shows_how_to_talk_to_a_character(castle):
    for system in (interpreter_system(), interpreter_system(castle.game.examples)):
        assert "- parla: " in system
        assert "- chiedi: " in system
        # Last, after the grapple: anywhere before it, "getta il rampino nel pozzo" went to the door.
        assert system.endswith('{"verbo": "chiedi", "bersaglio": "cuoca", "con": "nessuno"}')


# --- The examples of each world ---------------------------------------------------------------------

ROCCA_PROMPT = Path(__file__).parent / "prompt_rocca.txt"
TRUNK = 'Oggetti: baule\nUscite: nessuna\nFrase: apri il baule\n{"verbo": "apri", "bersaglio": "baule", "con": "nessuno"}'


def test_the_castle_prompt_is_the_one_checked_on_the_real_model(castle):
    # Any change to the prompt has to pass the whole tests/test_ollama.py first; then update the file.
    assert interpreter_system(castle.game.examples) == ROCCA_PROMPT.read_text(encoding="utf-8")


def test_the_examples_of_a_world_come_after_the_generic_ones_and_before_the_dialogue():
    system = interpreter_system(TRUNK)

    generic = system.index("Frase: buongiorno, che ore sono?")
    own = system.index("Frase: apri il baule")
    dialogue = system.index("Oggetti: mestolo")
    assert generic < own < dialogue


def test_a_world_without_examples_gets_the_generic_ones_and_the_dialogue():
    system = interpreter_system()

    assert "rampino" not in system
    assert '{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}\nOggetti: mestolo\n' in system


def test_the_system_prompt_carries_the_examples_it_is_given(in_reach):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "apri il baule", in_reach, examples=TRUNK)

    assert fake.calls[0][0] == interpreter_system(TRUNK)


# --- Giving ------------------------------------------------------------------------------------------


def test_the_prompt_explains_giving():
    assert '- dai: dare, porgere, offrire un oggetto a un personaggio (anche "ecco", "tieni")\n' in interpreter_system()


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"verbo": "dai", "bersaglio": "corda con gancio", "con": "pellegrino"},
         Action(verb="dai", target="corda_con_gancio", with_="pellegrino")),
        ({"verbo": "dai", "bersaglio": "pellegrino", "con": "corda con gancio"},
         Action(verb="dai", target="pellegrino", with_="corda_con_gancio")),
    ],
    ids=["item then character", "character then item"],
)  # fmt: skip
def test_giving_comes_back_with_both_names(castle, in_reach, reply, expected):
    characters = [(castle.characters["pellegrino"], [])]

    sentence = "offro il rampino al pellegrino"

    assert interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach, (), characters) == expected


# --- The answer is checked against the sentence (found while playing, 2026-09-28) ------------------


@pytest.mark.parametrize(
    ("sentence", "reply"),
    [
        # With nothing like it in the list, qwen2.5:3b picks any item: "prendi il sasso" for a blackberry.
        ("prendi una scala", {"verbo": "prendi", "bersaglio": "portone", "con": "nessuno"}),
        ("aggancia il rampino alla vera",
         {"verbo": "usa", "bersaglio": "porta della torre", "con": "corda con gancio"}),
        ("bevo un po' d'acqua dal pozzo", {"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}),
        ("a cosa serve il pozzo?", {"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"}),
    ],
    ids=["target", "target with a tool", "tool", "a question on one of the two"],
)
def test_an_item_the_sentence_does_not_name_is_not_understood(in_reach, sentence, reply):
    result = interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach)

    assert isinstance(result, NotUnderstood)
    assert not result.not_an_action


def test_an_item_may_be_named_nearly(in_reach):
    reply = {"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}

    action = interpret(FakeLLMClient(json_replies=[reply]), "cala le corde nel pozo", in_reach)

    assert action == Action(verb="usa", target="pozzo", with_="corda_con_gancio")


@pytest.mark.parametrize(
    ("sentence", "reply", "expected"),
    [
        ("tieni, è tua", {"verbo": "dai", "bersaglio": "moneta", "con": "custode"}, None),
        ("gli do la moneta", {"verbo": "dai", "bersaglio": "moneta", "con": "custode"},
         Action(verb="dai", target="moneta", with_="custode")),
        ("ti passo il soldo", {"verbo": "usa", "bersaglio": "custode", "con": "moneta"},
         Action(verb="usa", target="custode", with_="moneta")),
        ("aiuta il custode", {"verbo": "usa", "bersaglio": "custode", "con": "nessuno"}, None),
        ("fagli un regalo", {"verbo": "dai", "bersaglio": "custode", "con": "nessuno"}, None),
        ("apro la porta", {"verbo": "apri", "bersaglio": "custode", "con": "nessuno"}, None),
        ("osservo il guardiano", {"verbo": "esamina", "bersaglio": "custode", "con": "nessuno"},
         Action(verb="esamina", target="custode")),
    ],
    ids=["an item not named", "the character by a pronoun", "the character by a pronoun, with usa",
         "a character alone with usa", "a character alone with dai", "a character not named",
         "a character named by an alias"],
)  # fmt: skip
def test_a_character_here_needs_no_name_only_to_give_something(keeper, sentence, reply, expected):
    items, characters = near_keeper(keeper)

    result = interpret(FakeLLMClient(json_replies=[reply]), sentence, items, (), characters)

    if expected is None:
        assert isinstance(result, NotUnderstood)
    else:
        assert result == expected


@pytest.mark.parametrize(
    ("sentence", "reply", "topic"),
    [
        ("chi era il castellano?", {"verbo": "chiedi", "bersaglio": "pellegrino", "con": "torre"}, "rocca"),
        ("pellegrino, cosa sai della torre?", {"verbo": "chiedi", "bersaglio": "pellegrino", "con": "nessuno"},
         "torre"),
        ("vecchio, parlami del pozzo e della chiave",
         {"verbo": "chiedi", "bersaglio": "pellegrino", "con": "chiave"}, "chiave"),
        ("come si esce da qui?", {"verbo": "chiedi", "bersaglio": "pellegrino", "con": "portone"}, "portone"),
    ],
    ids=["a topic named by an alias", "the character's own name is no topic", "the model's among those named",
         "nothing named: the model's"],
)  # fmt: skip
def test_a_topic_named_in_the_sentence_wins(castle, sentence, reply, topic):
    pilgrim = castle.characters["pellegrino"]
    characters = [(pilgrim, list(pilgrim.topics.values()))]

    action = interpret(FakeLLMClient(json_replies=[reply]), sentence, [], (), characters)

    assert action == Action(verb="chiedi", target="pellegrino", topic=topic)


@pytest.mark.parametrize(
    "sentence",
    ["torno indietro", "a nord!", "verso la torre", "salgo le scale", "scappa"],
)
def test_a_move_needs_a_direction_a_known_place_or_a_verb_of_motion(castle, in_reach, sentence):
    reply = {"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}
    exits = [(Direction.NORTH, castle.rooms["torre"])]

    action = interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach, exits)

    assert action == Action(verb="vai", direction="nord")


@pytest.mark.parametrize("sentence", ["attento alle spine", "busso alla porta", "vuoi delle more?"])
def test_a_move_the_sentence_does_not_ask_for_is_not_understood(in_reach, sentence, caplog):
    # qwen2.5:3b answered "vai" to all of them, and the game asked "Vuoi andare a est?".
    reply = {"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}

    with caplog.at_level("INFO", logger="app.llm"):
        result = interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach, [(Direction.NORTH, None)])

    assert result == NotUnderstood("la frase non chiede di spostarsi")
    assert caplog.records[-1].getMessage() == "=== non capito: la frase non chiede di spostarsi"


def test_a_move_goes_the_only_way_the_sentence_names(castle):
    # "attraverso il ponte" at the brook: the model went east, the bridge is west.
    den = castle.rooms["cucina"].model_copy(update={"name": "Tana", "aliases": ("orso", "ponte")})
    reply = {"verbo": "vai", "bersaglio": "est", "con": "nessuno"}
    exits = [(Direction.EAST, castle.rooms["cucina"]), (Direction.WEST, den)]

    action = interpret(FakeLLMClient(json_replies=[reply]), "attraverso il ponte", [], exits)

    assert action == Action(verb="vai", direction="ovest")


def test_a_direction_the_sentence_says_wins_over_the_model(castle):
    # "salgo sul sasso" in the glade: the model went north, and the game answered "Sei già qui.".
    reply = {"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}

    exits = [(Direction.NORTH, castle.rooms["torre"])]

    action = interpret(FakeLLMClient(json_replies=[reply]), "salgo sul sasso", [], exits)

    assert action == Action(verb="vai", direction="su")


@pytest.mark.parametrize(
    ("sentence", "name", "alias"), [("mangio una mora", "Roveto", "more"), ("parlo con l'orso", "Tana", "orso")]
)
def test_naming_what_is_in_a_place_is_no_move(castle, sentence, name, alias):
    # Only a verb of motion, a direction or the place's own name ask for a move: not what is there.
    place = castle.rooms["cucina"].model_copy(update={"name": name, "aliases": (alias,)})
    reply = {"verbo": "vai", "bersaglio": "ovest", "con": "nessuno"}

    result = interpret(FakeLLMClient(json_replies=[reply]), sentence, [], [(Direction.WEST, place)])

    assert result == NotUnderstood("la frase non chiede di spostarsi")
