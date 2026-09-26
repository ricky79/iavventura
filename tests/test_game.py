"""A game turn: parser first, then the LLM interpreter, the engine and the fixed text."""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import World
from app.engine.models import Action
from app.game import ALL_RIGHT, HELP, NOT_A_GAME_ACTION, NOT_UNDERSTOOD, Game
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


def misunderstood_grapple(castle: World) -> Game:
    """The bug found while playing: the model aims the grapple at the door instead of the well."""
    llm = FakeLLMClient(json_replies=[{"verbo": "usa", "bersaglio": "portone", "con": "corda con gancio"}])
    game = Game(Engine(castle), llm)
    game.state.item_locations["corda_con_gancio"] = "inventory"
    return game


def test_an_unexpected_interpreted_action_is_asked_before_doing_it(castle):
    game = misunderstood_grapple(castle)
    before = game.state.model_copy(deep=True)

    output = say(game, "usa il rampino per recuperare la chiave dal pozzo")

    # The carried item comes first: "usare la corda con gancio con il portone".
    assert output == "Vuoi usare la corda con gancio con il portone?"
    assert game.pending == Action(verb="usa", target="corda_con_gancio", with_="portone")
    assert game.state == before


@pytest.mark.parametrize("answer", ["sì", "si", "Sì, certo", "ok"])
def test_yes_does_the_action_asked_about(castle, answer):
    game = misunderstood_grapple(castle)
    say(game, "usa il rampino per recuperare la chiave dal pozzo")

    output = say(game, answer)

    assert output == "Non succede niente."
    assert game.state.turns == 1
    assert game.pending is None


@pytest.mark.parametrize("answer", ["no", "No, grazie"])
def test_no_drops_the_action_asked_about(castle, answer):
    game = misunderstood_grapple(castle)
    say(game, "usa il rampino per recuperare la chiave dal pozzo")

    output = say(game, answer)

    assert output == ALL_RIGHT
    assert game.state.turns == 0
    assert game.pending is None


def test_any_other_line_after_the_question_is_a_new_command(castle):
    game = misunderstood_grapple(castle)
    say(game, "usa il rampino per recuperare la chiave dal pozzo")

    output = say(game, "usa il rampino con il pozzo")

    assert output == castle.rules["pesca_chiave"].text
    assert game.pending is None


def test_s_and_n_after_the_question_are_still_directions(castle):
    game = misunderstood_grapple(castle)
    say(game, "usa il rampino per recuperare la chiave dal pozzo")

    assert say(game, "n") == "La porta della torre è chiusa a chiave."
    assert game.pending is None


def test_what_the_player_typed_is_done_without_asking(castle):
    game = Game(Engine(castle), FakeLLMClient())
    game.state.item_locations["corda_con_gancio"] = "inventory"

    assert say(game, "usa il rampino con il portone") == "Non succede niente."
    assert game.pending is None


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
    [("torna verso ovest", "ovest"), ("torno di corsa nella cucina", "ovest"), ("scendo giù per le scale", "giù")],
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


def test_the_llm_is_told_where_the_exits_lead(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "vai", "bersaglio": "est", "con": "nessuno"}])
    game = Game(Engine(castle), llm)

    output = say(game, "torno di corsa nella scuderia")

    assert "\nUscite: nord (Torre), est (Scuderia), ovest (Cucina)\n" in llm.calls[0][1]
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
    [entry] = logged(caplog, misunderstood_grapple(castle), "usa il rampino per recuperare la chiave dal pozzo")

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
