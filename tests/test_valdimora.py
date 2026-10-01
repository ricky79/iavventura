"""La Stella di Valdimora, atti 1 e 2 (il pianterreno e il piano nobile): the game played with typed commands through Game,
and the invariants that keep its puzzles honest.

Chain: the letter to Ettore -> the countess's envelope (the riddle) -> oil and medallion in the sundial
-> the sealed note for Livia, who wants Ettore's word -> the key of the great staircase -> end of act 1.
Optional: the grappa for the doctor -> his bag -> the medicine cabinet -> the register (proof 1).
"""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Give, Remove, World
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
    # The staircase opens the second act: its state is kept, to go on from here after a death.
    assert "la lasci nella toppa" in answers[-1]
    assert not game.finished and game.state.act == 1 and game.state.checkpoint is not None


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
         "leggi la busta", "sud", "est")  # fmt: skip

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


# From the atrium: Ettore gives the key of the sideboard, the grappa puts the doctor to sleep,
# his bag has the key of the medicine cabinet, and the cabinet the register.
TO_THE_REGISTER = [
    "ovest", "nord", "nord", "dai la lettera a Ettore", "chiedi a Ettore della credenza",
    "sud", "apri la credenza con la chiave della credenza",
    "est", "sud", "est",
    "dai la grappa al dottore", "prendi la borsa",
    "nord", "nord", "ovest",
    "apri l'armadietto con la chiavetta", "leggi il registro",
]  # fmt: skip


def test_the_register_can_be_found(valdimora):
    game = new_game(valdimora)

    answers = play(game, *TO_THE_REGISTER)

    assert "Ecco la chiave" in answers[4]
    assert "bottiglia di grappa" in answers[6]
    assert "comincia a russare" in answers[10]
    assert "chiavetta d'ottone" in answers[11]
    assert "le gocce diventano venti" in answers[-1]
    assert game.state.item_locations["registro"] == "inventory"


def test_the_optional_thread_in_the_wrong_order(valdimora):
    game = new_game(valdimora)

    sideboard = play(game, "ovest", "nord", "apri la credenza")[-1]
    bag = play(game, "sud", "est", "est", "prendi la borsa")[-1]
    cabinet = play(game, "nord", "nord", "ovest", "apri l'armadietto")[-1]

    assert "chiusa a chiave" in sideboard
    assert "Giù le mani" in bag
    assert "chiuso a chiave" in cabinet
    assert game.state.item_locations["chiavetta"] is None


def test_two_keys_ask_which_one(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "sala_da_pranzo"
    for key in ("chiave_scalone", "chiave_credenza"):
        game.state.item_locations[key] = "inventory"

    question = game.turn("apri la credenza con la chiave")
    opened = game.turn("apri la credenza con la chiave della credenza")

    assert question == "Quale intendi: la chiave dello scalone o la chiave della credenza?"
    assert "bottiglia di grappa" in opened


def test_wrong_gifts_are_refused_and_kept(valdimora):
    game = new_game(valdimora)
    game.state.item_locations["grappa"] = "inventory"
    game.state.current_room = "biliardo"

    to_corrado = game.turn("dai la grappa a Corrado")
    game.state.current_room = "ufficio_governante"
    to_livia = game.turn("dai la lettera a Livia")
    game.state.current_room = "cappella"
    to_agnese = game.turn("dai il medaglione ad Agnese")

    assert to_corrado == "«Non accetto regali dagli estranei.»"
    assert to_livia == "«Tenete le vostre cose, signorina.»"
    assert "Che strana stella" in to_agnese
    assert all(game.state.item_locations[item] == "inventory" for item in ("grappa", "lettera", "medaglione"))


def test_the_sleeping_doctor_only_snores(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "biliardo"
    game.state.flags.add("ferri_addormentato")

    answers = play(game, "parla con il dottore", "chiedi al dottore della contessa", "guarda")

    assert answers[0] == "Il dottor Ferri russa. Non c'è verso di svegliarlo."
    assert answers[1] == "Il dottore russa."
    assert "Qui ci sono Corrado e il dottor Ferri." in answers[2]


def test_no_character_gives_a_shortcut(valdimora):
    # Only Ettore's word for Livia and the key of the sideboard come from talking.
    effects = {
        (character.id, topic.id): topic.effects
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if topic.effects
    }

    assert set(effects) == {("ettore", "livia"), ("ettore", "credenza")}


# Everything a room describes can be examined: (room, what the player types).
DESCRIBED = [
    ("atrio", "portone"), ("atrio", "annuncio"),
    ("rimessa", "calesse"), ("rimessa", "scaffali"), ("rimessa", "frana"),
    ("salotto", "poltrone"), ("salotto", "pianoforte"), ("salotto", "specchi"),
    ("serra", "rosaio"), ("serra", "limoni"),
    ("sala_da_pranzo", "tavola"), ("sala_da_pranzo", "lampadario"), ("sala_da_pranzo", "credenza"),
    ("stanza_maggiordomo", "argenteria"), ("stanza_maggiordomo", "campanelli"),
    ("cucina", "focolare"), ("cucina", "pentole"), ("cucina", "porta della cantina"),
    ("lavanderia", "vasche"), ("lavanderia", "lenzuola"), ("lavanderia", "stufa"),
    ("dispensa", "conserve"), ("dispensa", "armadietto"),
    ("ufficio_governante", "quadro delle chiavi"), ("ufficio_governante", "calendario"),
    ("ufficio_governante", "libri contabili"),
    ("cappella", "bara"), ("cappella", "candele"), ("cappella", "gigli"),
    ("biliardo", "tavolo da biliardo"), ("biliardo", "stecche"), ("biliardo", "carrello"),
    ("biliardo", "borsa"),
    ("cortile", "meridiana"), ("cortile", "finestre"),
]  # fmt: skip


@pytest.mark.parametrize(("room", "thing"), DESCRIBED, ids=[f"{room}: {thing}" for room, thing in DESCRIBED])
def test_what_a_room_describes_can_be_examined(valdimora, room, thing):
    game = new_game(valdimora)
    game.state.current_room = room

    answer = game.turn(f"esamina {thing}")

    assert answer not in ("Non vedi niente del genere qui.", "Non ho capito.")


def test_things_for_the_next_acts_are_already_here(valdimora):
    items = valdimora.items

    assert (items["forbici"].location, items["tanica"].location, items["fiammiferi"].location) == (
        "rimessa", "rimessa", "cucina",
    )
    assert items["rosaio"].scenery and items["porta_cantina"].scenery


def test_the_mourning_notice_tells_the_countess_is_dead(valdimora):
    game = new_game(valdimora)

    notice = game.turn("leggi l'annuncio")
    door = game.turn("apri il portone")

    assert "14 ottobre 1927" in notice
    assert "frana" in door


# --- Found by the final review --------------------------------------------------------------------


def test_the_sundial_waits_for_the_countess_riddle(valdimora):
    # Oil and medallion opened the sundial before meeting Ettore: the letter, the riddle and the act's
    # revelation were skipped, and the oil went «nell'incavo» before anyone had seen it.
    game = new_game(valdimora)

    oil, medallion = play(game, "sud", "prendi l'oliatore", "nord", "nord",
                          "usa l'oliatore con la meridiana", "usa il medaglione con la meridiana")[-2:]  # fmt: skip

    assert "incavo" not in oil and "incavo" not in medallion
    assert "meridiana_oliata" not in game.state.flags
    assert game.state.item_locations["biglietto_livia"] is None


def test_the_sleeping_doctor_neither_refuses_nor_answers_awake(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "biliardo"
    game.state.flags.add("ferri_addormentato")

    refused = game.turn("dai la lettera al dottore")
    unknown = game.engine.execute(game.state, Action(verb="chiedi", target="ferri")).text

    assert refused == "Il dottore non ne vuole sapere."
    assert unknown == "Dal dottore, su questo, non cavi niente."


@pytest.mark.parametrize(
    ("room", "key", "line", "answer"),
    [
        ("atrio", "chiave_scalone", "apri la porta dello scalone", "Hai la chiave dello scalone: usala."),
        ("sala_da_pranzo", "chiave_credenza", "apri la credenza", "Hai la chiave della credenza: usala."),
        ("dispensa", "chiavetta", "apri l'armadietto", "Hai la chiavetta dell'armadietto: usala."),
    ],
    ids=["staircase", "sideboard", "medicine cabinet"],
)
def test_holding_the_key_the_hint_says_to_use_it(valdimora, room, key, line, answer):
    game = new_game(valdimora)
    game.state.current_room = room
    game.state.item_locations[key] = "inventory"

    assert game.turn(line) == answer


@pytest.mark.parametrize(
    ("room", "key", "line"),
    [
        ("sala_da_pranzo", "chiave_scalone", "apri la credenza con la chiave"),
        ("dispensa", "chiave_credenza", "apri l'armadietto con la chiave"),
        ("atrio", "chiavetta", "apri la porta con la chiavetta"),
        ("cucina", "chiave_scalone", "apri la porta della cantina con la chiave"),
    ],
    ids=["sideboard", "medicine cabinet", "staircase", "cellar"],
)
def test_a_wrong_key_does_not_fit(valdimora, room, key, line):
    game = new_game(valdimora)
    game.state.current_room = room
    game.state.item_locations[key] = "inventory"

    assert game.turn(line) == "La chiave non entra nella serratura."


def test_the_key_board_agrees_with_the_cellar_door(valdimora):
    # The board had a «Cantina» key hanging, the cellar door said its hook was empty.
    board = valdimora.items["quadro_chiavi"].description

    assert "Due ganci sono vuoti" in board and "«Cantina»" in board


def test_the_sundial_motto_can_be_read(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "cortile"

    assert "Horas non numero nisi serenas" in game.turn("leggi il motto")


def test_the_countess_note_for_livia_is_asked_about(valdimora):
    # «dai il biglietto della contessa a Livia» gave her the envelope, and she refused it.
    game = new_game(valdimora)
    game.state.current_room = "ufficio_governante"
    for item in ("busta", "biglietto_livia"):
        game.state.item_locations[item] = "inventory"

    answer = game.turn("dai il biglietto della contessa a Livia")

    assert answer == "Quale intendi: la busta della contessa o il biglietto sigillato?"


MORE_DESCRIBED = [
    ("ufficio_governante", "quadro"), ("stanza_maggiordomo", "tavolo"), ("stanza_maggiordomo", "sedia"),
    ("stanza_maggiordomo", "porta"), ("atrio", "vetrata"), ("atrio", "pavimento"),
    ("lavanderia", "ferro da stiro"), ("biliardo", "tavolino"), ("biliardo", "poltrona"),
    ("biliardo", "bottiglie"), ("salotto", "spartito"), ("salotto", "porta a vetri"),
]  # fmt: skip


@pytest.mark.parametrize(("room", "thing"), MORE_DESCRIBED, ids=[f"{room}: {thing}" for room, thing in MORE_DESCRIBED])
def test_more_of_what_a_room_describes_can_be_examined(valdimora, room, thing):
    game = new_game(valdimora)
    game.state.current_room = room

    answer = game.turn(f"esamina {thing}")

    assert answer not in ("Non vedi niente del genere qui.", "Non ho capito.")


# --- The dialogues -------------------------------------------------------------------------------------


def test_livia_has_something_to_say_about_corrado(valdimora):
    # The first feedback: «chiedi a Livia di Corrado» answered about Ettore.
    game = new_game(valdimora)
    game.state.current_room = "ufficio_governante"

    assert "avvoltoio" in game.turn("chiedi a Livia di Corrado")


def test_asked_again_livia_does_not_repeat_herself(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "ufficio_governante"

    first, second = game.turn("chiedi a Livia della contessa"), game.turn("chiedi a Livia della contessa")

    assert "Trent'anni" in first and second == "«Ho detto che non ne parlo.»"


def test_agnese_and_corrado_defend_each_other(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "cappella"
    agnese = game.turn("chiedi ad Agnese di Corrado")
    game.state.current_room = "biliardo"
    corrado = game.turn("chiedi a Corrado di Agnese")

    assert "Tutti lo giudicano male" in agnese
    assert "Parliamo d'altro" in corrado


def test_the_sleeping_doctor_only_snores_at_gestures_too(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "biliardo"
    game.state.flags.add("ferri_addormentato")

    answers = play(game, "grazie, dottore", "dottore, come state?", "chiedi al dottore di Agnese")

    assert all("russa" in answer for answer in answers)


def test_how_are_you_goes_to_the_last_one_spoken_to(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "biliardo"

    play(game, "parla con Corrado")

    assert game.turn("come state?").startswith("«Come uno che aspetta un'eredità")


def test_the_doctor_wants_the_grappa_he_sees(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "biliardo"
    game.state.item_locations["grappa"] = "inventory"

    assert "non fatemi soffrire" in game.turn("chiedi al dottore della grappa")


# --- Atto 2: i ritocchi al pianterreno ---------------------------------------------------------------


def test_a_key_once_used_stays_in_its_lock(valdimora):
    # Fewer keys in the pocket, fewer «Quale intendi»: the staircase, the sideboard, the cabinet.
    upstairs, register = new_game(valdimora), new_game(valdimora)

    play(upstairs, *TO_THE_STAIRCASE)
    play(register, *TO_THE_REGISTER)

    assert upstairs.state.item_locations["chiave_scalone"] is None
    assert (register.state.item_locations["chiave_credenza"], register.state.item_locations["chiavetta"]) == (None, None)


def test_the_photograph_of_my_mother(valdimora):
    # A deferred defect of act 1: the parser didn't know «fotografia di mia madre».
    game = new_game(valdimora)
    game.state.current_room = "stanza_maggiordomo"
    game.state.item_locations["fotografia"] = "inventory"

    assert game.turn("dai la fotografia di mia madre a Ettore") == valdimora.characters["ettore"].refuses


# --- Atto 2: il piano nobile -----------------------------------------------------------------------

# From the atrium, once the staircase is open: the portrait, the rose for Livia (the shears are in the
# coach house, the rose bush in the greenhouse), the jewel box, the music box, the service stairs.
TO_THE_SERVICE_STAIRS = [
    "su", "nord", "prendi il drappo", "esamina il ritratto", "usa il medaglione con il ritratto",
    "sud", "ovest", "nord", "nord", "chiedi a Livia della rosa",
    "sud", "sud", "est", "giù", "sud", "prendi le forbici", "nord", "ovest", "ovest",
    "usa le forbici con il rosaio",
    "est", "est", "su", "ovest", "nord", "nord", "dai la rosa a Livia",
    "ovest", "apri il portagioie", "est", "sud", "est", "sud", "est",
    "usa il cilindro con il carillon", "usa la chiavetta con il carillon",
    "ovest", "nord", "nord", "apri la porta della scala di servizio con la chiave",
]  # fmt: skip


def in_act_two(valdimora: World, room: str, *flags: str, carried: tuple[str, ...] = ()) -> Game:
    """A game already in the second act (its state kept), in `room`."""
    game = new_game(valdimora)
    game.state.flags.update({"atto_due", "busta_data", *flags})
    game.state.act = 1
    game.state.current_room = room
    for item_id in carried:
        game.state.item_locations[item_id] = "inventory"
    return game


def test_the_second_act_can_be_played_to_its_end(valdimora):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE)

    answers = play(game, *TO_THE_SERVICE_STAIRS)

    assert "Da sotto, una ragazza" in answers[2]
    assert "È tua madre" in answers[3]
    assert "Suonala per me" in answers[4]
    assert "Profuma di pioggia" in answers[19]
    assert "Lei avrebbe voluto così" in answers[26]
    assert "testa a farfalla" in answers[28]
    assert "ninna nanna" in answers[35]
    assert answers[-1].endswith("Fine del secondo atto. (Il terzo è in costruzione.)")
    assert game.finished and not game.state.lost


def test_in_the_second_act_the_characters_are_upstairs(valdimora):
    # The doctor stays by his bag in the billiard room (spec, «Atto 2: decisioni»).
    game = in_act_two(valdimora, "loggia")

    rooms = {character.id: game.engine.character_room(character, game.state) for character in valdimora.characters.values()}

    assert rooms == {"ettore": "galleria", "livia": "camera_contessa", "corrado": "studio_conte", "ferri": "biliardo",
                     "agnese": "loggia"}  # fmt: skip


def test_going_up_the_staircase_by_name(valdimora):
    game = in_act_two(valdimora, "atrio")

    game.turn("vai sullo scalone")

    assert game.state.current_room == "loggia"


@pytest.mark.parametrize(
    ("room", "carried", "line", "hint"),
    [
        ("galleria", (), "usa il medaglione con il ritratto", "coperto dal drappo"),
        ("salone_musica", ("chiavetta_carica",), "usa la chiavetta con il carillon", "gira a vuoto"),
        ("camera_contessa", (), "ovest", "Il boudoir no"),
        ("camera_contessa", (), "apri la porta del boudoir", "Il boudoir no"),
        ("pianerottolo_servizio", (), "apri la porta", "chiusa a chiave"),
        ("pianerottolo_servizio", (), "su", "chiusa a chiave"),
        ("serra", (), "prendi la rosa", "spine"),
    ],
    ids=["frame before the drape", "key before the cylinder", "boudoir", "boudoir door", "service door",
         "service stairs", "rose without shears"],
)  # fmt: skip
def test_act_two_in_the_wrong_order_gives_hints(valdimora, room, carried, line, hint):
    game = in_act_two(valdimora, room, carried=carried)
    before = game.state.model_dump(exclude={"turns", "asked", "last_speaker"})

    answer = game.turn(line)

    assert hint in answer
    assert game.state.model_dump(exclude={"turns", "asked", "last_speaker"}) == before


def test_livia_takes_the_rose_only_upstairs(valdimora):
    game = new_game(valdimora)
    game.state.current_room = "ufficio_governante"
    game.state.item_locations["rosa_bianca"] = "inventory"

    assert "Tenetela voi" in game.turn("dai la rosa a Livia")
    assert game.state.item_locations["rosa_bianca"] == "inventory"


def test_two_things_with_the_same_name_in_reach_ask_which_one(valdimora):
    greenhouse = in_act_two(valdimora, "serra", carried=("rosa_bianca",))
    music_room = in_act_two(valdimora, "salone_musica", "cilindro_messo", carried=("chiavetta", "chiavetta_carica"))

    assert greenhouse.turn("prendi la rosa") == "Quale intendi: la rosa bianca o il rosaio?"
    assert music_room.turn("usa la chiavetta con il carillon") == (
        "Quale intendi: la chiavetta di carica o la chiavetta dell'armadietto?"
    )
    assert "ninna nanna" in music_room.turn("usa la chiavetta di carica con il carillon")


def test_the_key_of_the_service_stairs_comes_only_from_the_music_box(valdimora):
    givers = [rule.id for rule in valdimora.rules.values() if Give(give="chiave_servizio") in rule.effects]
    topics = [
        (character.id, topic.id)
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if Give(give="chiave_servizio") in topic.effects
    ]

    assert givers == ["carica_carillon"]
    assert topics == []


# Everything a room of the second act describes can be examined: (room, what the player types).
ACT_TWO_DESCRIBED = [
    ("loggia", "scalone"), ("loggia", "colonnato"), ("loggia", "pavimento"), ("loggia", "candelabri"),
    ("salone_feste", "lampadari"), ("salone_feste", "sedie"), ("salone_feste", "portafinestra"),
    ("balcone", "balaustra"), ("balcone", "vaso"), ("balcone", "valle"),
    ("salottino_verde", "solitario"), ("salottino_verde", "tappezzeria"), ("salottino_verde", "tavolino"),
    ("camera_contessa", "letto"), ("camera_contessa", "comodino"), ("camera_contessa", "cordone"),
    ("camera_contessa", "porta del boudoir"), ("boudoir", "toeletta"), ("boudoir", "portagioie"),
    ("guardaroba", "armadi"), ("guardaroba", "porticina"),
    ("galleria", "ritratti"), ("galleria", "drappo"), ("galleria", "ritratto"),
    ("pianerottolo_servizio", "porta"), ("pianerottolo_servizio", "pareti"),
    ("salone_musica", "arpa"), ("salone_musica", "poltroncine"), ("salone_musica", "carillon"),
    ("biblioteca", "scaffali"), ("biblioteca", "libro"),
    ("studio_conte", "scrivania"), ("studio_conte", "trofei"), ("studio_conte", "rastrelliera"),
    ("camera_corrado", "letto"), ("camera_corrado", "cambiali"), ("camera_corrado", "bottiglie"),
]  # fmt: skip


@pytest.mark.parametrize(("room", "thing"), ACT_TWO_DESCRIBED, ids=[f"{room}: {thing}" for room, thing in ACT_TWO_DESCRIBED])
def test_what_a_room_of_the_second_act_describes_can_be_examined(valdimora, room, thing):
    game = new_game(valdimora)
    game.state.current_room = room

    answer = game.turn(f"esamina {thing}")

    assert answer not in ("Non vedi niente del genere qui.", "Non ho capito.")
    assert not answer.startswith("Quale intendi")


# From the atrium, once the staircase is open: the count's walking stick, then the balcony.
TO_THE_FLASK = [
    "su", "est", "nord", "nord", "prendi il bastone", "sud", "sud", "ovest", "ovest", "sud",
    "usa il bastone con il vaso",
]  # fmt: skip


def test_the_flask_can_be_found(valdimora):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE)

    answers = play(game, *TO_THE_FLASK, "prendi il vaso", "esamina il flacone")

    assert "boccetta di vetro scuro" in answers[10]
    assert game.state.item_locations["flacone"] == "inventory"
    assert "al sicuro" in answers[11] and not game.finished  # once hooked, the vase is harmless
    assert "Digitale" in answers[12]


@pytest.mark.parametrize("line", ["prendi il vaso", "spingi la balaustra", "salta dalla balaustra"])
def test_the_balcony_kills_and_the_game_goes_on_from_the_second_act(valdimora, line):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE)
    play(game, "su", "ovest", "sud")

    answer = game.turn(line)

    assert answer.endswith("Sei morta.")
    assert game.finished and game.state.lost and game.resumable == "secondo atto"
    assert game.turn("riprendi").startswith("Riprendi dall'inizio del secondo atto.")
    assert game.state.current_room == "atrio" and not game.finished


def test_pulling_the_vase_by_hand_is_only_a_hint(valdimora):
    game = in_act_two(valdimora, "balcone")

    assert "qualcosa di lungo" in game.turn("tira il vaso")
    assert not game.finished


def test_the_doctor_knows_the_flask(valdimora):
    game = in_act_two(valdimora, "biliardo", carried=("flacone",))

    assert "L'avevo portata piena" in game.turn("chiedi al dottore delle medicine")


@pytest.mark.parametrize(
    ("room", "flags", "line", "expected"),
    [
        ("loggia", (), "parla con Agnese", "Posso vedere il vostro medaglione"),
        ("loggia", (), "chiedi ad Agnese del medaglione", "Che bella stella"),
        ("loggia", (), "dai il medaglione ad Agnese", "Che strana stella"),
        ("studio_conte", (), "parla con Corrado", "Prendete pure quello che volete"),
        ("studio_conte", (), "chiedi a Corrado del bastone", "Prendetelo pure"),
        ("camera_contessa", (), "parla con Livia", "Siete salita"),
        ("camera_contessa", (), "chiedi a Livia della rosa", "Ogni mattina"),
        ("camera_contessa", (), "chiedi a Livia del cordone", "Non me n'ero accorta"),
        ("camera_contessa", (), "chiedi a Livia della scala di servizio", "la teneva la contessa"),
        ("galleria", (), "parla con Ettore", "Sapevo"),
        ("galleria", (), "chiedi a Ettore del ritratto", "coperto dal 1897"),
        ("galleria", ("ritratto_scoperto",), "chiedi a Ettore del ritratto", "La signorina Clara"),
        ("galleria", ("ritratto_scoperto",), "chiedi a Ettore del carillon", "ninna nanna"),
    ],
)  # fmt: skip
def test_the_characters_have_something_to_say_upstairs(valdimora, room, flags, line, expected):
    assert expected in in_act_two(valdimora, room, *flags).turn(line)


def test_agnese_no_longer_goes_back_to_the_coffin(valdimora):
    answer = in_act_two(valdimora, "loggia").turn("arrivederci, Agnese")

    assert "Io resto qui ad aspettarvi" in answer
    assert "bara" not in answer


# --- Found by the final review of act 2 --------------------------------------------------------------


def test_with_the_stick_in_hand_taking_the_vase_is_only_a_hint(valdimora):
    # The model dropped the stick («recupero il vaso usando il bastone» became «prendi il vaso»), and the
    # player who had done the right thing fell from the balcony.
    game = in_act_two(valdimora, "balcone", carried=("bastone",))

    answer = game.turn("prendi il vaso")

    assert "bastone" in answer
    assert not game.finished


def test_upstairs_ettore_knows_where_agnese_is(valdimora):
    answer = in_act_two(valdimora, "galleria").turn("chiedi a Ettore di Agnese")

    assert "loggia" in answer
    assert "cappella" not in answer


def test_the_rose_can_be_put_in_the_vase_by_hand(valdimora):
    # Livia and the room point at the silver vase on the bedside table.
    game = in_act_two(valdimora, "camera_contessa", carried=("rosa_bianca",))

    answer = game.turn("usa la rosa con il comodino")

    assert "Lei avrebbe voluto così" in answer
    assert "livia_permette" in game.state.flags


# --- Minors left by the final review of act 2 --------------------------------------------------------


@pytest.mark.parametrize(
    ("room", "flags", "name", "first"),
    [
        ("loggia", (), "Agnese", "Ce l'avete fatta"),
        ("studio_conte", (), "Corrado", "Siete arrivata fin quassù"),
        ("camera_contessa", (), "Livia", "Siete salita"),
        ("camera_contessa", ("livia_permette",), "Livia", "«Grazie», dice soltanto"),
        ("galleria", (), "Ettore", "Sapevo"),
        ("galleria", ("ritratto_scoperto",), "Ettore", "Ora avete visto"),
    ],
)  # fmt: skip
def test_upstairs_a_greeting_is_not_said_twice(valdimora, room, flags, name, first):
    # The variants won over greeting_again: Agnese said «Ce l'avete fatta!» at every greeting.
    game = in_act_two(valdimora, room, *flags)

    assert first in game.turn(f"parla con {name}")
    assert first not in game.turn(f"parla con {name}")


@pytest.mark.parametrize(
    ("room", "flag", "name", "first"),
    [
        ("stanza_maggiordomo", "busta_data", "Ettore", "Quello che so, è vostro"),
        ("ufficio_governante", "livia_chiave", "Livia", "Avete la chiave"),
    ],
)  # fmt: skip
def test_downstairs_a_greeting_is_not_said_twice(valdimora, room, flag, name, first):
    game = new_game(valdimora)
    game.state.flags.add(flag)
    game.state.current_room = room

    assert first in game.turn(f"parla con {name}")
    assert first not in game.turn(f"parla con {name}")


def test_once_shown_the_medallion_agnese_no_longer_asks_for_it(valdimora):
    game = in_act_two(valdimora, "loggia", carried=("medaglione",))

    game.turn("dai il medaglione ad Agnese")

    assert "medaglione" not in game.turn("parla con Agnese")
    assert "Me lo fate vedere" not in game.turn("chiedi ad Agnese del medaglione")


@pytest.mark.parametrize(
    ("room", "flags", "carried", "line", "done"),
    [
        ("studio_conte", (), ("bastone",), "chiedi a Corrado del bastone", "L'avete già in mano"),
        ("camera_contessa", (), ("chiave_servizio",), "chiedi a Livia della scala di servizio", "l'avete trovata"),
        ("camera_contessa", ("livia_chiave",), (), "chiedi a Livia dello scalone", "Ormai siete salita"),
        ("galleria", ("ritratto_scoperto", "carillon_suonato"), (), "chiedi a Ettore del carillon", "L'avete fatto suonare"),
        ("pianerottolo_servizio", (), ("chiave_servizio",), "su", "usala"),
    ],
)  # fmt: skip
def test_a_hint_knows_when_it_is_done(valdimora, room, flags, carried, line, done):
    # A hint that sends the player to do something has a variant for when it is done.
    assert done in in_act_two(valdimora, room, *flags, carried=carried).turn(line)
