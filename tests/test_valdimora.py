"""La Stella di Valdimora, atto 1 (il pianterreno): the game played with typed commands through Game,
and the invariants that keep its puzzles honest.

Chain: the letter to Ettore -> the countess's envelope (the riddle) -> oil and medallion in the sundial
-> the sealed note for Livia, who wants Ettore's word -> the key of the great staircase -> end of act 1.
Optional: the grappa for the doctor -> his bag -> the medicine cabinet -> the register (proof 1).
"""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Give, Remove, World
from app.game import Game


@pytest.fixture(scope="module")
def valdimora() -> World:
    return load_world(WORLDS_DIR / "valdimora")


def new_game(world: World) -> Game:
    return Game(Engine(world))


def play(game: Game, *lines: str) -> list[str]:
    return [game.turn(line) for line in lines]


# From the atrium: the suitcase and the oil can in the coach house, the letter to Ettore, the riddle,
# the sundial, then Livia, and back to the staircase.
TO_THE_STAIRCASE = [
    "sud", "apri la valigia", "prendi l'oliatore", "nord",
    "ovest", "nord", "nord",
    "dai la lettera a Ettore", "leggi la busta", "chiedi a Ettore di Livia",
    "sud", "est",
    "esamina la meridiana", "usa l'oliatore con la meridiana", "usa il medaglione con la meridiana",
    "leggi il foglietto",
    "est", "nord",
    "dai il biglietto sigillato a Livia",
    "sud", "sud", "ovest",
    "apri la porta dello scalone con la chiave",
]  # fmt: skip


def test_the_first_act_can_be_played_to_its_end(valdimora):
    game = new_game(valdimora)

    answers = play(game, *TO_THE_STAIRCASE)

    assert "Avete gli occhi di vostra madre" in answers[7]
    assert "quando piove, cercami più in basso" in answers[8]
    assert "incavo a forma di stella" in answers[12]
    assert "Per Livia" in answers[14]
    assert "cerca chi ti somiglia" in answers[15]
    assert "Non fatemene pentire" in answers[18]
    assert answers[-1].endswith("Fine del primo atto. (Il secondo è in costruzione.)")
    assert game.finished and not game.state.lost


def test_the_game_opens_in_the_atrium_with_the_letter_and_the_medallion(valdimora):
    game = new_game(valdimora)

    opening = game.opening()
    inventory = game.turn("inventario")

    assert opening.startswith("Genova, ottobre 1927.")
    assert "\n\nAtrio\n" in opening
    assert inventory == "Hai con te una lettera della contessa e un medaglione."


def test_ettore_and_livia_are_called_by_their_names(valdimora):
    game = new_game(valdimora)

    butler = play(game, "ovest", "nord", "nord")[-1]
    play(game, "sud", "est", "est", "nord")
    governess = game.turn("guarda")

    assert "Qui c'è Ettore." in butler
    assert "Qui c'è Livia." in governess


def test_things_done_in_the_wrong_order_give_a_hint(valdimora):
    game = new_game(valdimora)
    play(game, "sud", "prendi l'oliatore", "nord", "ovest", "nord", "nord", "dai la lettera a Ettore",
         "sud", "est")  # fmt: skip

    rusty = game.turn("usa il medaglione con la meridiana")
    play(game, "usa l'oliatore con la meridiana", "usa il medaglione con la meridiana")
    empty = game.turn("usa il medaglione con la meridiana")
    play(game, "est", "nord")
    doubt = game.turn("dai il biglietto sigillato a Livia")
    locked = play(game, "sud", "sud", "ovest", "apri la porta dello scalone")[-1]

    assert "bloccato dalla ruggine" in rusty
    assert empty == "Lo scomparto è aperto, e dentro non c'è altro."
    assert "Chi garantisce per voi?" in doubt
    assert game.state.item_locations["biglietto_livia"] == "inventory"
    assert "chiusa a chiave" in locked
    assert not game.finished


def test_the_medallion_never_leaves_irene(valdimora):
    game = new_game(valdimora)

    answer = game.turn("lascia il medaglione")

    assert answer == "No: è tutto ciò che ti resta di tua madre."
    assert game.state.item_locations["medaglione"] == "inventory"
    assert not any(
        Remove(remove="medaglione") in rule.effects for rule in valdimora.rules.values()
    )


def test_the_key_of_the_staircase_comes_only_from_livia(valdimora):
    givers = [rule.id for rule in valdimora.rules.values() if Give(give="chiave_scalone") in rule.effects]
    topics = [
        topic.id
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if Give(give="chiave_scalone") in topic.effects
    ]

    assert (givers, topics) == (["dai_biglietto_livia"], [])
