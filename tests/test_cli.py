"""The game in the terminal: the menu of the adventures, then typed commands in, fixed text out."""

import pytest

from app.cli import GOODBYE, PLAY_AGAIN, RESUME, WHICH_ADVENTURE, choose, menu, pick, run, session
from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import World
from app.game import HELP, Game


def play(*commands: str, world: World | None = None) -> str:
    """Runs a whole session (on the sample castle by default) and returns everything it printed."""
    output: list[str] = []
    lines = iter(commands)

    def read_line() -> str:
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    run(Game(Engine(world or load_world(WORLDS_DIR / "rocca"))), read_line, output.append)
    return "\n".join(output)


def test_session_opens_with_the_intro_and_the_first_room():
    output = play()

    assert output.startswith("La bufera ti ha sorpreso sul passo")
    assert "\n\nCortile\nUn cortile lastricato" in output
    assert output.endswith("Uscite: nord, est, ovest.")


def test_a_sentence_the_parser_does_not_know_is_not_understood():
    assert play("balla la tarantella").endswith("Non ho capito.")


def test_empty_lines_are_ignored():
    assert play("", "   ") == play()


def test_items_are_listed_with_their_articles():
    assert "Qui vedi un gancio da macellaio." in play("ovest")


def test_ambiguous_names_get_a_question(world_data):
    world_data["items"]["moneta_antica"] = {
        "name": "moneta antica",
        "gender": "f",
        "aliases": ["moneta"],
        "description": "Una moneta antica.",
        "location": "atrio",
    }

    output = play("esamina la moneta", world=World.model_validate(world_data))

    assert output.endswith("Quale intendi: la moneta o la moneta antica?")


def test_help_lists_the_commands():
    assert play("aiuto").endswith(HELP)


def test_quitting_asks_for_confirmation():
    output = play("fine", "s", "guarda")

    assert "Vuoi davvero terminare la partita? (s/n)" in output
    assert output.count("Cortile") == 1


def test_not_confirming_goes_on_with_the_game():
    output = play("esci", "no", "guarda")

    assert output.count("Cortile") == 2


def test_the_castle_can_be_finished_by_typing_commands():
    output = play(
        "nord",
        "vai a ovest",
        "prendi il gancio",
        "e",
        "usa il gancio nel pozzo",
        "est",
        "raccogli la corda",
        "usa la corda con il gancio",
        "o",
        "usa il rampino sul pozzo",
        "apri la porta di ferro con la chiave",
        "n",
        "guarda",
    )

    assert "La porta della torre è chiusa a chiave." in output
    assert "Il gancio da solo non arriva nemmeno a metà del pozzo." in output
    assert "Ora hai un rampino improvvisato." in output
    assert output.endswith("da lì una scala di pietra scende fino al sentiero. Sei libero.")


# --- The menu of the adventures ----------------------------------------------------------------------


@pytest.fixture
def worlds(world_data) -> dict[str, World]:
    return {"rocca": load_world(WORLDS_DIR / "rocca"), "prova": World.model_validate(world_data)}


def test_the_menu_numbers_the_adventures_with_their_summaries(worlds):
    assert menu(worlds) == (
        "Scegli la tua avventura:\n\n"
        " 1. La Rocca di Serravento\n"
        "    Un castello abbandonato, una bufera, un portone che non si riapre.\n\n"
        " 2. Prova\n"
        "    Un mondo di prova."
    )


@pytest.mark.parametrize(
    "line, expected",
    [
        ("1", "rocca"),
        (" 2. ", "prova"),
        ("rocca", "rocca"),
        ("la Rocca di Serravento", "rocca"),
        ("PROVA", "prova"),
        ("3", None),
        ("0", None),
        ("", None),
        ("castello", None),
        ("rocca o prova", None),
    ],
)
def test_an_adventure_is_picked_by_its_number_or_by_a_word_of_its_title(worlds, line, expected):
    assert pick(worlds, line) == expected


def test_an_answer_that_fits_no_adventure_is_asked_again(worlds):
    output: list[str] = []
    answers = iter(["7", "prova"])

    assert choose(worlds, lambda: next(answers), output.append) == "prova"
    assert output == [menu(worlds), WHICH_ADVENTURE]


# --- Playing again -----------------------------------------------------------------------------------


def play_session(worlds: dict[str, World], *lines: str) -> list[str]:
    """Menu, games and the question at the end of each, as main() runs them."""
    output: list[str] = []
    answers = iter(lines)

    def read_line() -> str:
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    session(worlds, lambda adventure_id: Game(Engine(worlds[adventure_id])), read_line, output.append)
    return output


# In the test world the lever opens the cell, and entering it ends the game.
TO_THE_END = ["2", "tira la leva", "nord"]


def test_a_game_that_ends_asks_whether_to_play_again(worlds):
    output = play_session(worlds, *TO_THE_END, "sì", "2")

    # menu, opening, the lever, the cell with the ending; then the question, the menu, a new opening
    assert len(output) == 7
    assert output[3].endswith("Fine.")
    assert output[4:6] == [PLAY_AGAIN, menu(worlds)]
    assert output[6].startswith("Inizio.")


def test_not_playing_again_says_goodbye(worlds):
    output = play_session(worlds, *TO_THE_END, "no", "2")

    assert output[-2:] == [PLAY_AGAIN, GOODBYE]


def test_quitting_does_not_ask_to_play_again(worlds):
    output = play_session(worlds, "2", "fine", "s")

    assert PLAY_AGAIN not in output
    assert output[-1] == GOODBYE


# --- After a death -----------------------------------------------------------------------------------

GO_ON = RESUME.format(act="secondo atto")


def test_after_a_death_the_terminal_offers_to_go_on_from_the_last_act(acts_world):
    output = play_session(
        {"prova": World.model_validate(acts_world)}, "1", "tira la leva", "salta sulla leva", "sì", "nord", "no"
    )

    after_the_question = output[output.index(GO_ON) + 1]
    assert after_the_question.startswith("Riprendi dall'inizio del secondo atto.")
    assert output[-3].endswith("Fine.")
    assert output[-2:] == [PLAY_AGAIN, GOODBYE]


def test_not_going_on_after_a_death_asks_whether_to_play_again(acts_world):
    output = play_session(
        {"prova": World.model_validate(acts_world)}, "1", "tira la leva", "salta sulla leva", "no", "no"
    )

    assert output[-3:] == [GO_ON, PLAY_AGAIN, GOODBYE]


def test_a_death_before_any_act_only_asks_whether_to_play_again(acts_world):
    output = play_session({"prova": World.model_validate(acts_world)}, "1", "salta sulla leva", "no")

    assert GO_ON not in output
    assert output[-2:] == [PLAY_AGAIN, GOODBYE]


def test_riprendi_is_a_yes_to_the_terminal_question(acts_world):
    # «Vuoi riprendere…?» → «riprendi»: counted as no, it ended the game and lost it (found by the review).
    output = play_session(
        {"prova": World.model_validate(acts_world)}, "1", "tira la leva", "salta sulla leva", "riprendi", "nord", "no"
    )

    assert output[output.index(GO_ON) + 1].startswith("Riprendi dall'inizio del secondo atto.")
