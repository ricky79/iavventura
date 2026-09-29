"""A game turn: parser first, then the LLM interpreter, the engine and the fixed text."""

import pytest

from app.engine.engine import NO_EXIT, NOBODY_HERE, NOT_HERE, Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import World
from app.engine.models import Action
from app.game import ALL_RIGHT, ALREADY_HERE, HELP, NOBODY_TO_TALK_TO, NOT_A_GAME_ACTION, NOT_UNDERSTOOD, Game
from app.llm.client import FakeLLMClient
from app.llm.prompts import interpreter_system


@pytest.fixture(scope="module")
def castle() -> World:
    return load_world(WORLDS_DIR / "rocca")


def say(game: Game, line: str) -> str:
    return game.turn(line)


def test_a_free_sentence_goes_through_the_llm_interpreter(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "corda con gancio", "con": "pozzo"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"

    output = say(game, "cala il rampino giù nel pozzo")

    assert output.startswith("(usa la corda con gancio con il pozzo)\n")
    assert output.endswith(castle.rules["pesca_chiave"].text)
    assert game.state.item_locations["chiave_torre"] == "inventory"


def test_the_key_in_the_well_can_be_named_without_the_llm(castle):
    game = Game(Engine(castle))
    game.state.item_locations["corda_con_gancio"] = "inventory"

    assert say(game, "prendi la chiave") == "Non vedi niente del genere qui."
    say(game, "esamina il pozzo")
    assert say(game, "prendi la chiave") == "Non ci arrivi."
    assert say(game, "prendi la chiave con il rampino") == castle.rules["pesca_chiave"].text


@pytest.mark.parametrize("name", ["corda", "fune", "gancio", "uncino", "rampino", "corda con gancio"])
def test_the_grapple_answers_to_the_names_of_its_parts(castle, name):
    game = Game(Engine(castle))
    game.state.item_locations["corda_con_gancio"] = "inventory"

    assert say(game, f"usa {name} con il pozzo") == castle.rules["pesca_chiave"].text


def test_the_llm_can_choose_the_key_in_the_well(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "prendi", "bersaglio": "chiave di ferro", "con": "corda con gancio"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"
    say(game, "esamina il pozzo")

    output = say(game, "recupera la chiave dal pozzo con il rampino")

    assert "; chiave di ferro (chiave)\n" in llm.calls[0][1]
    assert "chiave di ferro" in llm.schemas[0]["properties"]["bersaglio"]["enum"]
    assert output == f"(prendi la chiave di ferro con la corda con gancio)\n{castle.rules['pesca_chiave'].text}"


def test_throwing_the_grapple_into_the_well_fishes_the_key(castle):
    # Found while playing: the game asked "Vuoi lasciare il pozzo con la corda con gancio?",
    # and after "sì" answered "Non ce l'hai.".
    llm = FakeLLMClient(json_replies=[{"verbo": "lascia", "bersaglio": "pozzo", "con": "corda con gancio"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"

    output = say(game, "butta il rampino nel pozzo")

    assert output == f"(usa il pozzo con la corda con gancio)\n{castle.rules['pesca_chiave'].text}"
    assert game.state.item_locations["chiave_torre"] == "inventory"


def test_opening_shows_intro_and_first_room(castle):
    opening = Game(Engine(castle)).opening()

    assert opening.startswith("La bufera ti ha sorpreso")
    assert opening.endswith("Uscite: nord, est, ovest.")


def test_simple_commands_never_reach_the_llm(castle):
    llm = FakeLLMClient()
    game = Game(Engine(castle), llm)

    assert say(game, "nord") == "La porta della torre è chiusa a chiave."
    assert say(game, "apri il portone").startswith("Spingi, tiri, dai una spallata")
    assert say(game, "aiuto") == HELP
    assert say(game, "   ") == ""
    assert llm.calls == []


def test_without_llm_a_free_sentence_is_not_understood(castle):
    assert say(Game(Engine(castle)), "cala il rampino giù nel pozzo") == NOT_UNDERSTOOD


def test_a_sentence_that_is_no_game_action_gets_a_fixed_answer(castle):
    game = Game(Engine(castle), FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}]))
    before = game.state.model_copy(deep=True)

    assert say(game, "che bella giornata") == NOT_A_GAME_ACTION
    assert game.state == before


def test_when_the_llm_cannot_interpret_the_sentence_is_not_understood(castle):
    game = Game(Engine(castle), FakeLLMClient())

    assert say(game, "che bella giornata") == NOT_UNDERSTOOD
    assert game.state.turns == 0


def test_ambiguous_names_get_a_question_without_asking_the_llm(world_data):
    world_data["items"]["moneta_antica"] = {
        "name": "moneta antica",
        "gender": "f",
        "aliases": ["moneta"],
        "description": "Una moneta antica.",
        "location": "atrio",
    }
    llm = FakeLLMClient()

    output = say(Game(Engine(World.model_validate(world_data)), llm), "esamina la moneta")

    assert output == "Quale intendi: la moneta o la moneta antica?"
    assert llm.calls == []


def test_an_interpreted_sentence_is_shown_before_the_answer(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "esamina", "bersaglio": "portone", "con": "nessuno"}])

    output = say(Game(Engine(castle), llm), "dai un'occhiata al portone")

    assert output == f"(esamina il portone)\n{castle.items['portone'].description}"


# --- An interpreted action nothing in the world foresees: ask first --------------------------------


# The model understood the sentence, but nothing in the world foresees it.
THROW = "lancio il rampino contro il portone"


def misunderstood_grapple(castle: World) -> Game:
    """The model aims the grapple at the door: "usa il portone con la corda con gancio"."""
    llm = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "portone", "con": "corda con gancio"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"
    return game


def test_the_grapple_aimed_at_a_door_the_sentence_does_not_name_is_not_understood(castle):
    # The bug found while playing: the game asked "Vuoi usare la corda con gancio con il portone?".
    game = misunderstood_grapple(castle)
    say(game, "esamina il pozzo")  # the key is in sight, and the sentence names it

    assert say(game, "usa il rampino per recuperare la chiave dal pozzo") == NOT_UNDERSTOOD
    assert game.pending is None


def test_an_unexpected_interpreted_action_is_asked_before_doing_it(castle):
    game = misunderstood_grapple(castle)
    before = game.state.model_copy(deep=True)

    output = say(game, THROW)

    # The carried item comes first: "usare la corda con gancio con il portone".
    assert output == "Vuoi usare la corda con gancio con il portone?"
    assert game.pending == Action(verb="usa", target="corda_con_gancio", with_="portone")
    assert game.state == before


@pytest.mark.parametrize("answer", ["sì", "si", "Sì, certo", "ok"])
def test_yes_does_the_action_asked_about(castle, answer):
    game = misunderstood_grapple(castle)
    say(game, THROW)

    output = say(game, answer)

    assert output == "Non succede niente."
    assert game.state.turns == 1
    assert game.pending is None


@pytest.mark.parametrize("answer", ["no", "No, grazie"])
def test_no_drops_the_action_asked_about(castle, answer):
    game = misunderstood_grapple(castle)
    say(game, THROW)

    output = say(game, answer)

    assert output == ALL_RIGHT
    assert game.state.turns == 0
    assert game.pending is None


def test_any_other_line_after_the_question_is_a_new_command(castle):
    game = misunderstood_grapple(castle)
    say(game, THROW)

    output = say(game, "usa il rampino con il pozzo")

    assert output == castle.rules["pesca_chiave"].text
    assert game.pending is None


def test_s_and_n_after_the_question_are_still_directions(castle):
    game = misunderstood_grapple(castle)
    say(game, THROW)

    assert say(game, "n") == "La porta della torre è chiusa a chiave."
    assert game.pending is None


def test_what_the_player_typed_is_done_without_asking(castle):
    game = Game(Engine(castle), FakeLLMClient())
    game.state.item_locations["corda_con_gancio"] = "inventory"

    assert say(game, "usa il rampino con il portone") == "Non succede niente."
    assert game.pending is None


# Jumping into the well kills: the model alone must not decide it.
JUMP = {"verbo": "salta", "bersaglio": "pozzo", "con": "nessuno"}


@pytest.mark.parametrize("sentence", ["mi butto nel pozzo", "voglio saltarci dentro, nel pozzo"])
def test_an_interpreted_jump_the_sentence_asks_for_is_done(castle, sentence):
    game = Game(Engine(castle), FakeLLMClient(json_replies=[JUMP]))

    output = say(game, sentence)

    assert output.startswith(f"(salta nel pozzo)\n{castle.rules['salto_nel_pozzo'].text}")
    assert game.finished


@pytest.mark.parametrize("sentence", ["entro nel pozzo", "mi calo nel pozzo"])
def test_an_interpreted_jump_without_a_word_for_jumping_is_asked(castle, sentence):
    game = Game(Engine(castle), FakeLLMClient(json_replies=[JUMP]))

    assert say(game, sentence) == "Vuoi saltare nel pozzo?"
    assert not game.finished
    say(game, "sì")
    assert game.finished


def test_a_game_can_go_on_with_the_question_still_open(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    state.item_locations["corda_con_gancio"] = "inventory"
    pending = Action(verb="usa", target="corda_con_gancio", with_="pozzo")

    output = say(Game(engine, state=state, pending=pending), "sì")

    assert output == castle.rules["pesca_chiave"].text


def test_going_to_a_named_room_needs_no_llm(castle):
    llm = FakeLLMClient()
    game = Game(Engine(castle), llm)

    output = say(game, "vai in cucina")

    assert output.startswith("Cucina\n")
    assert game.state.current_room == "cucina"
    assert llm.calls == []


@pytest.mark.parametrize(
    ("sentence", "direction"),
    [
        ("torno di corsa verso ovest", "ovest"),
        ("torno di corsa nella cucina", "ovest"),
        ("scendo giù per le scale", "giù"),
    ],
)
def test_an_interpreted_move_that_names_the_way_is_done(castle, sentence, direction):
    llm = FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": direction, "con": "nessuno"}])
    game = Game(Engine(castle), llm)
    game.state.visited.add("cucina")

    output = say(game, sentence)

    assert output.startswith(f"(vai {'a ' if direction == 'ovest' else ''}{direction})\n")
    assert game.pending is None


def test_an_interpreted_move_that_names_neither_direction_nor_room_is_asked(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": "ovest", "con": "nessuno"}])
    game = Game(Engine(castle), llm)

    output = say(game, "vado nella cantina")

    assert output == "Vuoi andare a ovest?"
    assert game.state.current_room == "cortile"
    assert game.pending == Action(verb="vai", direction="ovest")


def going_east(world: World) -> Game:
    return Game(Engine(world), FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": "est", "con": "nessuno"}]))


def test_an_interpreted_move_to_a_room_named_nearly_is_done(castle):
    # Found while playing: "vai alle scuderie" was asked about, three times (now the parser knows
    # "scuderie"). A typo is fine too.
    output = say(going_east(castle), "corri alla scudria")

    assert output.startswith("(vai a est)\nScuderia\n")


def test_an_interpreted_move_to_a_room_named_by_an_alias_is_done(castle):
    output = say(going_east(castle), "corro di nuovo dal pellegrino")

    assert output.startswith("(vai a est)\nScuderia\n")


def test_a_single_letter_is_no_direction_in_a_free_sentence(castle):
    # "e" is also "and": the move is asked about.
    assert say(going_east(castle), "prendi fiato e scappa") == "Vuoi andare a est?"


def test_the_llm_is_told_where_the_exits_lead(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": "est", "con": "nessuno"}])
    game = Game(Engine(castle), llm)

    output = say(game, "torno di corsa nella scuderia")

    exits = "Uscite: nord (Torre: scala, scale), est (Scuderia: scuderie, stalla, pellegrino), ovest (Cucina)"
    assert f"\n{exits}\n" in llm.calls[0][1]
    assert output.startswith("(vai a est)\nScuderia\n")


def test_a_game_can_go_on_from_a_saved_state(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()
    state.current_room = "cucina"
    state.visited.add("cucina")

    game = Game(engine, state=state)

    assert say(game, "est").startswith("Cortile\n")
    assert game.state is state


def test_only_a_new_game_has_an_opening(castle):
    engine = Engine(castle)
    state, _ = engine.new_game()

    with pytest.raises(ValueError):
        Game(engine, state=state).opening()



# --- The pilgrim in the stable -------------------------------------------------------------------


def in_the_stable(castle: World, llm: FakeLLMClient | None = None) -> Game:
    game = Game(Engine(castle), llm)
    game.state.current_room = "scuderia"
    return game


def test_the_stable_shows_the_pilgrim(castle):
    assert "\nQui c'è un pellegrino.\n" in say(in_the_stable(castle), "guarda")


def test_talking_to_the_pilgrim_needs_no_llm(castle):
    llm = FakeLLMClient()
    game = in_the_stable(castle, llm)
    pilgrim = castle.characters["pellegrino"]

    assert say(game, "parla con il pellegrino") == pilgrim.greeting
    assert say(game, "chiedi al vecchio della torre") == pilgrim.topics["torre"].text
    assert llm.calls == []


def test_a_question_in_free_words_goes_through_the_llm(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "chiedi", "bersaglio": "pellegrino", "con": "torre"}])
    game = in_the_stable(castle, llm)

    output = say(game, "pellegrino, come si sale sulla torre?")

    assert "\nPersonaggi: pellegrino (" in llm.calls[0][1]
    assert "\nArgomenti: " in llm.calls[0][1]
    assert output == f"(chiedi al pellegrino della torre)\n{castle.characters['pellegrino'].topics['torre'].text}"


def test_a_question_about_something_the_pilgrim_does_not_know_is_logged(castle, caplog):
    llm = FakeLLMClient(json_replies=[{"verbo": "chiedi", "bersaglio": "pellegrino", "con": "nessuno"}])
    game = in_the_stable(castle, llm)

    [entry] = logged(caplog, game, "gli chiedo se ha fame")

    assert entry["azione"] == "chiedi pellegrino"
    assert entry["esito"] == "fallita"
    assert entry["dettaglio"] == castle.characters["pellegrino"].unknown


# --- Log of the commands that went wrong ---------------------------------------------------------


def logged(caplog, game: Game, *lines: str) -> list[dict]:
    with caplog.at_level("INFO", logger="app.commands"):
        for line in lines:
            say(game, line)
    return [record.command for record in caplog.records if record.name == "app.commands"]


def test_a_sentence_that_is_no_game_action_is_logged(castle, caplog):
    game = Game(Engine(castle), FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}]))

    assert logged(caplog, game, "che bella giornata") == [
        {
            "stanza": "cortile",
            "frase": "che bella giornata",
            "da": "llm",
            "azione": None,
            "esito": "altro",
            "dettaglio": "la frase non è un'azione di gioco",
        }
    ]


def test_a_sentence_not_understood_is_logged_with_the_reason(castle, caplog):
    [with_llm] = logged(caplog, Game(Engine(castle), FakeLLMClient()), "che bella giornata")
    caplog.clear()
    [without_llm] = logged(caplog, Game(Engine(castle)), "che bella giornata")

    assert (with_llm["esito"], with_llm["dettaglio"]) == ("non capito", "il modello non ha dato una risposta valida")
    assert (without_llm["da"], without_llm["esito"]) == ("parser", "non capito")
    assert without_llm["dettaglio"] == "il parser non la capisce e l'LLM è spento"


def test_a_failed_action_is_logged_with_the_answer(castle, caplog):
    assert logged(caplog, Game(Engine(castle)), "nord") == [
        {
            "stanza": "cortile",
            "frase": "nord",
            "da": "parser",
            "azione": "vai nord",
            "esito": "fallita",
            "dettaglio": "La porta della torre è chiusa a chiave.",
        }
    ]


def test_a_question_before_an_unexpected_action_is_logged(castle, caplog):
    [entry] = logged(caplog, misunderstood_grapple(castle), THROW)

    assert entry["da"] == "llm"
    assert entry["azione"] == "usa corda_con_gancio con portone"
    assert entry["esito"] == "conferma"
    assert entry["dettaglio"] == "Vuoi usare la corda con gancio con il portone?"


def test_what_works_is_not_logged(castle, caplog):
    assert logged(caplog, Game(Engine(castle)), "ovest", "prendi il gancio", "guarda") == []


def test_the_llm_is_not_told_about_the_key_before_the_well_is_examined(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}])
    game = Game(Engine(castle), llm)

    say(game, "recupera la chiave dal pozzo")

    assert "chiave" not in llm.calls[0][1].split("\n")[0]


def test_the_llm_gets_the_examples_of_the_world(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}])

    Game(Engine(castle), llm).turn("che bella giornata")

    assert llm.calls[0][0] == interpreter_system(castle.game.examples)
    assert "usa il rampino per recuperare la chiave dal pozzo" in llm.calls[0][0]


def test_the_log_names_the_adventure_when_the_game_knows_it(castle, caplog):
    [entry] = logged(caplog, Game(Engine(castle), adventure="rocca"), "nord")

    assert list(entry)[:2] == ["avventura", "stanza"]
    assert entry["avventura"] == "rocca"


def test_giving_is_never_asked_about(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "dai", "bersaglio": "corda", "con": "pellegrino"}])
    game = Game(Engine(castle), llm)
    game.state.current_room = "scuderia"
    game.state.item_locations["corda"] = "inventory"

    output = game.turn("offro la corda al vecchio")

    assert output == f"(dai la corda al pellegrino)\n{castle.characters['pellegrino'].refuses}"
    assert game.pending is None


# --- Someone or something that isn't here (found while playing, 2026-09-28) ------------------------


@pytest.fixture(scope="module")
def dragon() -> World:
    return load_world(WORLDS_DIR / "draghetto")


def talking(reply: dict) -> FakeLLMClient:
    return FakeLLMClient(json_replies=[reply])


def test_talking_with_nobody_around_says_so(castle):
    game = Game(Engine(castle), talking({"verbo": "parla", "bersaglio": "nessuno", "con": "nessuno"}))

    assert say(game, "ciao, come va?") == NOBODY_TO_TALK_TO


def test_greeting_a_character_who_is_elsewhere_says_nobody_like_that_is_here(dragon):
    # "ciao orso" at the brook: the game answered "Non sembra un'azione del gioco."
    game = Game(Engine(dragon), talking({"verbo": "parla", "bersaglio": "nessuno", "con": "nessuno"}))
    game.state.current_room = "ruscello"

    assert say(game, "ciao orso") == NOBODY_HERE


def test_greeting_a_character_who_is_elsewhere_does_not_greet_the_one_here(dragon):
    # "ciao orso" in the glade: the dragon answered.
    game = Game(Engine(dragon), talking({"verbo": "parla", "bersaglio": "draghetto", "con": "nessuno"}))

    assert say(game, "ciao orso") == NOBODY_HERE


def test_greeting_the_one_here_may_name_someone_else(dragon):
    # The bear is elsewhere, but the dragon is named: it answers about the bear, one of its topics.
    game = Game(Engine(dragon), talking({"verbo": "parla", "bersaglio": "draghetto", "con": "nessuno"}))

    assert say(game, "ciao draghetto, sai dov'è l'orso?").endswith(dragon.characters["draghetto"].topics["orso"].text)


@pytest.mark.parametrize(
    "reply",
    [
        {"verbo": "prendi", "bersaglio": "sasso", "con": "nessuno"},
        {"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"},
    ],
    ids=["the model picks something else", "the model says it is no game action"],
)
def test_an_item_that_is_elsewhere_is_not_here(dragon, reply):
    # "mangio una mora" in the glade: the model took the stone. The berries are also a topic of the
    # dragon, but this is no question about them.
    game = Game(Engine(dragon), talking(reply))

    assert say(game, "mangio una mora") == NOT_HERE
    assert game.state.turns == 0


def test_going_where_the_player_already_is(dragon):
    # "torno dal draghetto" in the glade: the game asked "Vuoi andare a est?".
    game = Game(Engine(dragon), talking({"verbo": "vai", "bersaglio": "est", "con": "nessuno"}))

    assert say(game, "torno dal draghetto") == ALREADY_HERE
    assert game.pending is None


def test_going_to_a_place_that_is_no_exit_is_not_understood(dragon):
    # "vai a casa" at the oak: the game asked "Vuoi andare su?".
    game = Game(Engine(dragon), talking({"verbo": "vai", "bersaglio": "su", "con": "nessuno"}))
    game.state.current_room = "quercia"

    assert say(game, "vai a casa") == NOT_UNDERSTOOD
    assert game.pending is None


def test_a_name_shared_with_something_here_is_not_elsewhere(castle):
    # "corda" is the plain rope (out of play) and the grapple (carried).
    game = Game(Engine(castle), talking({"verbo": "usa", "bersaglio": "portone", "con": "corda con gancio"}))
    game.state.item_locations.update({"corda_con_gancio": "inventory", "corda": None, "gancio": None})

    assert say(game, "aggancia la corda alla vera") == NOT_UNDERSTOOD


def test_a_name_within_one_said_of_something_here_is_not_elsewhere():
    # Valdimora: «biglietto» is the sealed note (elsewhere), but also part of «biglietto della
    # contessa», the envelope carried: the game answered «Non vedi niente del genere qui.».
    valdimora = load_world(WORLDS_DIR / "valdimora")
    game = Game(Engine(valdimora), talking({"verbo": "leggi", "bersaglio": "medaglione", "con": "nessuno"}))
    game.state.item_locations["busta"] = "inventory"

    assert say(game, "leggo il biglietto della contessa") == NOT_UNDERSTOOD


@pytest.mark.parametrize(
    ("room", "sentence", "character", "topic"),
    [("radura", "mi dai il miele?", "draghetto", "miele"), ("tana", "mi dai il tuo miele?", "orso", "miele")],
)
def test_a_question_the_model_misses_is_asked_about_the_topic_it_names(dragon, room, sentence, character, topic):
    # The model answered "dai le more": the kid was asking for the honey.
    game = Game(Engine(dragon), talking({"verbo": "dai", "bersaglio": "more", "con": "nessuno"}))
    game.state.current_room = room
    game.state.item_locations["more"] = "inventory"

    output = say(game, sentence)

    assert output.endswith(dragon.characters[character].topics[topic].text)
    assert output.startswith(f"(chiedi {'al draghetto' if character == 'draghetto' else "all'orso"} del miele)\n")
    assert game.state.item_locations["more"] == "inventory"


@pytest.mark.parametrize("sentence", ["perche hai il naso rosso", "come mai hai il naso rosso"])
def test_a_question_without_its_question_mark_is_asked_too(dragon, sentence):
    # Kids leave out the "?": a sentence starting with perché, cosa, come... is a question.
    game = Game(Engine(dragon), talking({"verbo": "prendi", "bersaglio": "sasso", "con": "nessuno"}))

    output = say(game, sentence)

    assert output == f"(chiedi al draghetto del solletico)\n{dragon.characters['draghetto'].topics['solletico'].text}"


@pytest.mark.parametrize(
    ("sentence", "topic"),
    [("chi sei?", "pellegrino"), ("vecchio, come ti chiami?", "pellegrino"), ("com'è andato il viaggio?", "pellegrino")],
)
def test_talking_about_a_topic_is_asking_about_it(castle, sentence, topic):
    # "chi sei?": the model answered "parla", and the pilgrim only greeted.
    game = in_the_stable(castle, talking({"verbo": "parla", "bersaglio": "pellegrino", "con": "nessuno"}))

    output = say(game, sentence)

    assert output == f"(chiedi al pellegrino del pellegrino)\n{castle.characters['pellegrino'].topics[topic].text}"


@pytest.mark.parametrize(
    "sentence", ["chiedo al vecchio come si esce da qui", "come faccio a uscire?", "come si fa a usire"]
)
def test_asking_how_to_get_out_is_asking_about_the_door(castle, sentence):
    # With "salta" in the prompt the model lost the topic: "come si esce" names it by itself.
    game = in_the_stable(castle, talking({"verbo": "chiedi", "bersaglio": "pellegrino", "con": "nessuno"}))

    output = say(game, sentence)

    assert output == f"(chiedi al pellegrino del portone)\n{castle.characters['pellegrino'].topics['portone'].text}"


def test_greeting_the_character_by_name_is_still_greeting(castle):
    game = in_the_stable(castle, talking({"verbo": "parla", "bersaglio": "pellegrino", "con": "nessuno"}))

    assert say(game, "salve, pellegrino!").endswith(castle.characters["pellegrino"].greeting)


@pytest.mark.parametrize(
    ("sentence", "reply", "topic"),
    [
        ("cosa ti serve?", {"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}, "raffreddore"),
        ("cosa ti è successo?", {"verbo": "chiedi", "bersaglio": "draghetto", "con": "quercia"}, "raffreddore"),
    ],
)
def test_the_dragon_answers_what_it_needs(dragon, sentence, reply, topic):
    output = say(Game(Engine(dragon), talking(reply)), sentence)

    assert output.endswith(dragon.characters["draghetto"].topics[topic].text)


def test_an_item_elsewhere_comes_before_nobody_to_talk_to(castle):
    # "ma non c'è la chiave nel pozzo": the model heard talking, the game said nobody is here.
    game = Game(Engine(castle), talking({"verbo": "parla", "bersaglio": "nessuno", "con": "nessuno"}))

    assert say(game, "ma non c'è la chiave nel pozzo") == NOT_HERE


def test_going_to_a_place_farther_on_is_asked_when_the_way_leads_there(dragon):
    # "vai dall orso" in the glade: the den is past the brook, and west is the way.
    game = Game(Engine(dragon), talking({"verbo": "vai", "bersaglio": "ovest", "con": "nessuno"}))

    assert say(game, "vai dall orso") == "Vuoi andare a ovest?"
    assert game.pending == Action(verb="vai", direction="ovest")


# --- Found by the review: someone elsewhere, for any action on a character --------------------------


@pytest.mark.parametrize(
    ("room", "carried", "sentence", "reply"),
    [
        ("tana", "more", "do le more al drago", {"verbo": "dai", "bersaglio": "more", "con": "orso"}),
        # "dai le more" to nobody goes to the only one here: the bear again.
        ("tana", "more", "do le more al drago", {"verbo": "dai", "bersaglio": "more", "con": "nessuno"}),
        ("radura", "vasetto_miele", "porto il miele all'orso",
         {"verbo": "dai", "bersaglio": "vasetto di miele", "con": "draghetto"}),
    ],
)  # fmt: skip
def test_giving_to_someone_elsewhere_gives_nothing_to_the_one_here(dragon, room, carried, sentence, reply):
    # The model gave to the one here: the bear's trade, or the honey used up on the dragon.
    game = Game(Engine(dragon), talking(reply))
    game.state.current_room = room
    game.state.item_locations[carried] = "inventory"
    before = game.state.model_copy(deep=True)

    assert say(game, sentence) == NOBODY_HERE
    assert game.state == before


@pytest.mark.parametrize("sentence", ["conosci l'orso?", "hai visto l'orso?"])
def test_asking_the_one_here_about_someone_elsewhere(dragon, sentence):
    game = Game(Engine(dragon), talking({"verbo": "parla", "bersaglio": "draghetto", "con": "nessuno"}))

    assert say(game, sentence).endswith(dragon.characters["draghetto"].topics["orso"].text)


def test_a_question_for_someone_elsewhere_about_nothing_known(keeper_world):
    # A prisoner in the cell, who is no topic of the keeper in the atrium.
    keeper_world["characters"]["prigioniero"] = {
        "name": "prigioniero", "gender": "m", "description": "-", "location": "cella",
        "greeting": "-", "unknown": "-", "topics": {},
    }  # fmt: skip
    world = World.model_validate(keeper_world)
    game = Game(Engine(world), talking({"verbo": "chiedi", "bersaglio": "custode", "con": "nessuno"}))

    assert say(game, "chiedi al prigioniero se ha fame") == NOBODY_HERE


@pytest.mark.parametrize(
    ("room", "sentence"), [("radura", "salgo sul sasso"), ("ruscello", "scendo nel ruscello")]
)
def test_climbing_on_something_here_is_no_way_out(dragon, room, sentence):
    # The game answered "Sei già qui.": the stone and the brook are also names of the places.
    game = Game(Engine(dragon), talking({"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}))
    game.state.current_room = room

    assert say(game, sentence).endswith(NO_EXIT)
    assert game.state.current_room == room


def test_of_two_topics_named_the_last_one_wins(dragon):
    # "serve" names the cold, "piuma" the tickle: the question is about the feather.
    game = Game(Engine(dragon), talking({"verbo": "chiedi", "bersaglio": "draghetto", "con": "nessuno"}))

    assert say(game, "cosa serve per prendere la piuma?").endswith(dragon.characters["draghetto"].topics["solletico"].text)


@pytest.mark.parametrize(
    ("sentence", "reply", "answer"),
    [
        ("mangio una mora", {"verbo": "prendi", "bersaglio": "sasso", "con": "nessuno"}, NOT_HERE),
        ("mi dai il miele?", {"verbo": "prendi", "bersaglio": "sasso", "con": "nessuno"},
         "(chiedi al draghetto del miele)"),
    ],
)  # fmt: skip
def test_the_log_says_what_the_game_answered_instead(dragon, caplog, sentence, reply, answer):
    [entry] = logged(caplog, Game(Engine(dragon), talking(reply)), sentence)

    assert entry["esito"] == "non capito"
    assert entry["dettaglio"] == f"la frase non nomina 'sasso'; risposta: {answer}"


# --- After a death: «riprendi» -------------------------------------------------------------------


@pytest.fixture
def two_acts(acts_world) -> Game:
    """The test world in two acts; the LLM would answer "not understood" to anything."""
    return Game(Engine(World.model_validate(acts_world)), FakeLLMClient())


def test_after_a_death_riprendi_goes_on_from_the_last_act(two_acts):
    say(two_acts, "tira la leva")
    death = say(two_acts, "salta sulla leva")

    act = two_acts.resumable
    output = say(two_acts, "riprendi")

    assert death.endswith("Sei morta.")
    assert act == "secondo atto"
    assert output.startswith("Riprendi dall'inizio del secondo atto.\n\nAtrio\n")
    assert not two_acts.finished
    assert say(two_acts, "nord").endswith("Fine.")


def test_one_can_die_and_go_on_again(two_acts):
    say(two_acts, "tira la leva")
    for _ in range(2):
        say(two_acts, "salta sulla leva")
        assert say(two_acts, "riprendi").startswith("Riprendi dall'inizio del secondo atto.")

    assert not two_acts.finished


def test_a_finished_game_answers_without_the_llm(two_acts):
    say(two_acts, "salta sulla leva")  # dead before any act began: nothing to go on from

    assert say(two_acts, "riprendi") == "La partita è finita."
    assert say(two_acts, "provo a scappare dalla finestra") == "La partita è finita."
    assert two_acts.llm.calls == []


def test_riprendi_means_nothing_while_playing_or_after_winning(two_acts):
    playing = say(two_acts, "riprendi")
    say(two_acts, "tira la leva")
    say(two_acts, "nord")
    won = say(two_acts, "riprendi")

    assert playing == NOT_UNDERSTOOD  # the fake LLM understands nothing
    assert won == "La partita è finita."
    assert two_acts.state.current_room == "cella"
