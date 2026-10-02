"""La Stella di Valdimora, atti 1, 2 e 3 (il pianterreno, il piano nobile e la soffitta): the game played with typed commands through Game,
and the invariants that keep its puzzles honest.

Chain: the letter to Ettore -> the countess's envelope (the riddle) -> oil and medallion in the sundial
-> the sealed note for Livia, who wants Ettore's word -> the key of the great staircase -> end of act 1.
Optional: the grappa for the doctor -> his bag -> the medicine cabinet -> the register (proof 1).
"""

import pytest

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Give, Remove, SetFlag, World
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
    # Only Ettore's word for Livia and the key of the sideboard come from talking; Agnese's errands, in the
    # third act, only send her downstairs.
    effects = {
        (character.id, topic.id): topic.effects
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if topic.effects
    }

    assert set(effects) == {("ettore", "livia"), ("ettore", "credenza"), ("agnese", "petrolio"), ("agnese", "tisana")}
    assert [*effects["agnese", "petrolio"], *effects["agnese", "tisana"]] == [
        SetFlag(set_flag="agnese_in_rimessa"),
        SetFlag(set_flag="agnese_in_cucina"),
    ]


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
    # The service stairs open the third act: its state is kept, to go on from here after a death.
    assert "odore di polvere e di lavanda" in answers[-1]
    assert not game.finished and game.state.act == 2 and game.state.checkpoint is not None


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


@pytest.mark.parametrize("line", ["prendi il vaso", "spingi la balaustra", "salta dalla balaustra", "salta nella valle"])
def test_the_balcony_kills_and_the_game_goes_on_from_the_second_act(valdimora, line):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE)
    play(game, "su", "ovest", "sud")

    answer = game.turn(line)

    assert answer.endswith("Sei morta.")
    assert game.finished and game.state.lost and game.resumable == "secondo atto"
    assert game.turn("riprendi").startswith("Riprendi dall'inizio del secondo atto.")
    assert game.state.current_room == "atrio" and not game.finished
    assert game.turn("su").startswith("Loggia")  # the staircase is still open
    assert game.state.current_room == "loggia"


@pytest.mark.parametrize("line", ["tira il vaso", "spingi il vaso"])
def test_pulling_the_vase_by_hand_is_only_a_hint(valdimora, line):
    game = in_act_two(valdimora, "balcone")

    assert "qualcosa di lungo" in game.turn(line)
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
    answer = game.turn("chiedi ad Agnese del medaglione")
    assert "Me lo fate vedere" not in answer
    assert "disegnava dappertutto" in answer  # the clue stays


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


def test_the_cut_bell_cord_rings_nothing(valdimora):
    assert "tagliato di netto" in in_act_two(valdimora, "camera_contessa").turn("tira il cordone")


def test_even_asleep_the_doctor_knows_the_flask(valdimora):
    # Who had put him to sleep with the grappa never saw him recognise the flask.
    game = in_act_two(valdimora, "biliardo", "ferri_addormentato", carried=("flacone",))

    answer = game.turn("chiedi al dottore delle medicine")

    assert "L'avevo portata piena" in answer
    assert "russare" in answer
    assert "russa" in game.turn("parla con il dottore")
    assert "L'avevo portata piena" not in game.turn("chiedi al dottore delle medicine")  # once only


# --- Atto 3: la soffitta -------------------------------------------------------------------------------

# From the service landing, once its door is open: the photograph for Livia, Clara's room (the letters,
# the doll's house), the plank over the rotten floor, the lantern, the oil in the coach house and the
# matches in the kitchen, the cellar door.
TO_THE_CELLAR = [
    "su", "ovest", "sud", "dai la fotografia a Livia",
    "nord", "apri la porta con la chiave", "ovest",
    "apri il baule", "leggi le lettere", "usa il medaglione con la casa delle bambole",
    "est", "est", "nord", "prendi l'asse", "sud", "est", "usa l'asse con il pavimento",
    "nord", "prendi la lanterna", "sud", "ovest", "giù",
    "sud", "sud", "giù", "sud", "usa la tanica con la lanterna",
    "nord", "nord", "nord", "usa i fiammiferi con la lanterna",
    "apri la porta della cantina con la chiave",
]  # fmt: skip


def in_act_three(valdimora: World, room: str, *flags: str, carried: tuple[str, ...] = ()) -> Game:
    """A game already in the third act (its state kept), in `room`."""
    game = in_act_two(valdimora, room, "atto_tre", *flags, carried=carried)
    game.state.act = 2
    return game


def test_the_third_act_can_be_played_to_its_end(valdimora):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE, *TO_THE_SERVICE_STAIRS)

    answers = play(game, *TO_THE_CELLAR)

    assert "Fui io a dire al conte" in answers[3]
    assert "chiusa dal 1897" in answers[5]
    assert "«A mia figlia Clara»" in answers[7]
    assert "La contessa di Valdimora era tua nonna." in answers[8]
    assert "Dove il vino dorme più vecchio" in answers[9]
    assert "Ora si passa" in answers[16]
    assert "finché non è pieno" in answers[26]
    assert "La lanterna è accesa" in answers[30]
    assert answers[-1].endswith("Fine del terzo atto. (Il quarto è in costruzione.)")
    assert game.finished and not game.state.lost


def test_in_the_third_act_the_characters_move(valdimora):
    # The doctor stays by his bag in the billiard room (spec, «Atto 3: decisioni»).
    game = in_act_three(valdimora, "pianerottolo_soffitta")

    rooms = {character.id: game.engine.character_room(character, game.state) for character in valdimora.characters.values()}

    assert rooms == {"ettore": "cucina", "livia": "camera_livia", "corrado": "archivio", "ferri": "biliardo",
                     "agnese": "corridoio_servitu"}  # fmt: skip


@pytest.mark.parametrize(("line", "room"), [("chiedi ad Agnese della tisana", "cucina"), ("chiedi ad Agnese del petrolio", "rimessa")])
def test_sent_downstairs_agnese_leaves_her_room_open(valdimora, line, room):
    game = in_act_three(valdimora, "corridoio_servitu")

    answer = game.turn(line)

    assert "Vi aspetto" in answer
    assert game.engine.character_room(valdimora.characters["agnese"], game.state) == room
    assert game.turn("nord").startswith("Camera di Agnese")


def test_downstairs_agnese_does_the_errand(valdimora):
    tea = in_act_three(valdimora, "cucina", "agnese_in_cucina")
    oil = in_act_three(valdimora, "rimessa", "agnese_in_rimessa")

    assert "bella calda" in tea.turn("chiedi ad Agnese della tisana")
    assert "Prendetela pure" in oil.turn("chiedi ad Agnese del petrolio")


def test_the_light_under_the_roof_was_agnese(valdimora):
    # Seen from the courtyard in the first act: fresh wax in the attic, the candle stub in her room.
    attic = in_act_three(valdimora, "soffittone")
    her_room = in_act_three(valdimora, "camera_agnese", "agnese_in_cucina")
    corridor = in_act_three(valdimora, "corridoio_servitu")

    assert "a lume di candela" in attic.turn("esamina le impronte")
    assert "La cera colata è la stessa" in her_room.turn("esamina il mozzicone")
    assert "Sarà stato un lampo" in corridor.turn("chiedi ad Agnese della luce")


def test_the_count_s_papers_of_1897(valdimora):
    assert "aumento di salario" in in_act_three(valdimora, "archivio").turn("leggi il faldone")


@pytest.mark.parametrize(
    ("room", "carried", "line", "hint"),
    [
        ("corridoio_servitu", (), "ovest", "«Clara»"),
        ("corridoio_servitu", (), "apri la porta", "chiusa a chiave"),
        ("corridoio_servitu", (), "nord", "Non c'è niente da vedere"),
        ("corridoio_servitu", (), "apri la porta di Agnese", "Non c'è niente da vedere"),
        ("camera_clara", (), "apri la casa delle bambole", "incavo a forma di stella"),
        ("cucina", ("lanterna",), "usa i fiammiferi con la lanterna", "Non prende"),
        ("cucina", ("chiave_cantina",), "apri la porta della cantina con la chiave", "buio pesto"),
        ("cucina", ("chiave_cantina", "lanterna"), "apri la porta della cantina con la chiave", "spenta"),
    ],
    ids=["Clara's room", "Clara's door", "Agnese's room", "Agnese's door", "doll's house without the medallion",
         "lantern without oil", "cellar without light", "cellar, lantern out"],
)  # fmt: skip
def test_act_three_in_the_wrong_order_gives_hints(valdimora, room, carried, line, hint):
    game = in_act_three(valdimora, room, carried=carried)
    before = game.state.model_dump(exclude={"turns", "asked", "last_speaker"})

    answer = game.turn(line)

    assert hint in answer
    assert game.state.model_dump(exclude={"turns", "asked", "last_speaker"}) == before


def test_before_the_third_act_livia_gives_the_photograph_back(valdimora):
    game = in_act_two(valdimora, "camera_contessa", carried=("fotografia",))

    assert "impallidisce" in game.turn("dai la fotografia a Livia")
    assert "livia_confessa" not in game.state.flags


def test_the_keys_of_the_third_act_come_only_from_livia_and_the_doll_s_house(valdimora):
    givers = {
        key: [rule.id for rule in valdimora.rules.values() if Give(give=key) in rule.effects]
        for key in ("chiave_clara", "chiave_cantina")
    }
    topics = [
        (character.id, topic.id)
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if Give(give="chiave_clara") in topic.effects or Give(give="chiave_cantina") in topic.effects
    ]

    assert givers == {"chiave_clara": ["livia_confessa"], "chiave_cantina": ["apri_casa_bambole"]}
    assert topics == []


def test_under_agnese_s_mattress_is_proof_three(valdimora):
    game = in_act_three(valdimora, "camera_agnese", "agnese_in_cucina", carried=("registro",))

    answers = play(game, "esamina il letto", "leggi la lettera di giugno", "esamina l'anello", "leggi il quaderno",
                   "esamina il letto")  # fmt: skip

    assert [game.state.item_locations[item] for item in ("lettera_giugno", "anello", "quaderno")] == ["inventory"] * 3
    assert "Qualcuno l'ha aperta" in answers[1]
    assert "«C. ad A.»" in answers[2]
    assert "Era Agnese" in answers[3]
    assert "non c'è più niente" in answers[4]


# From the attic landing: the clothesline, tied under the skylight, then the roof and the pigeon loft.
TO_THE_PIGEONS = [
    "nord", "prendi la corda", "sud", "est", "sud", "usa la corda con il lucernario", "su", "est",
    "prendi il tubetto", "leggi la lettera del notaio",
]  # fmt: skip


def test_the_notary_s_letter_is_on_the_roof(valdimora):
    game = in_act_three(valdimora, "pianerottolo_soffitta")

    answers = play(game, *TO_THE_PIGEONS)

    assert "qualcosa ti tiene" in answers[5]
    assert "studio notarile" in answers[8]
    assert "riconoscimento di vostra nipote" in answers[9]
    assert not game.finished


@pytest.mark.parametrize(
    "lines",
    [("su", "est", "nord"), ("su", "est", "salta nel buco"), ("su", "est", "sud", "su")],
    ids=["the attic without the plank", "into the hole", "the roof without the rope"],
)
def test_the_attic_kills_and_the_game_goes_on_from_the_third_act(valdimora, lines):
    game = new_game(valdimora)
    play(game, *TO_THE_STAIRCASE, *TO_THE_SERVICE_STAIRS)

    answer = play(game, *lines)[-1]

    assert answer.endswith("Sei morta.")
    assert game.finished and game.state.lost and game.resumable == "terzo atto"
    assert game.turn("riprendi").startswith("Riprendi dall'inizio del terzo atto.")
    assert game.state.current_room == "pianerottolo_servizio" and not game.finished
    assert game.turn("su").startswith("Pianerottolo della soffitta")


def test_with_the_plank_and_the_rope_the_attic_and_the_roof_are_safe(valdimora):
    game = in_act_three(valdimora, "soffittone", "asse_posata", "corda_legata")

    play(game, "nord", "sud", "sud", "su")

    assert game.state.current_room == "tetto" and not game.finished


@pytest.mark.parametrize(
    ("room", "flags", "carried", "line", "done"),
    [
        ("corridoio_servitu", (), ("chiave_clara",), "ovest", "usala"),
        ("corridoio_servitu", ("camera_clara_aperta",), (), "apri la porta", "già aperta"),
        ("camera_livia", ("livia_confessa",), ("fotografia",), "dai la fotografia a Livia", "L'ho guardata abbastanza"),
        ("cucina", (), ("chiave_cantina",), "apri la porta della cantina", "usala"),
        ("camera_clara", ("casa_aperta",), (), "usa il medaglione con la casa delle bambole", "non c'è altro"),
        ("camera_clara", ("lettere_lette",), ("lettere_clara",), "leggi le lettere", "Si chiama Irene"),
        ("stanza_orologio", ("corda_legata",), (), "esamina il lucernario", "legata la tua corda"),
    ],
)  # fmt: skip
def test_a_hint_of_the_third_act_knows_when_it_is_done(valdimora, room, flags, carried, line, done):
    assert done in in_act_three(valdimora, room, *flags, carried=carried).turn(line)


ACT_THREE_DESCRIBED = [
    ("pianerottolo_soffitta", "scala"), ("stenditoio", "finestrelle"),
    ("corridoio_servitu", "targhetta"), ("corridoio_servitu", "porta di Agnese"),
    ("camera_agnese", "crocifisso"), ("camera_agnese", "catino"), ("camera_agnese", "comodino"),
    ("camera_agnese", "mozzicone"), ("camera_agnese", "scarpe"), ("camera_agnese", "letto"),
    ("camera_livia", "letto"), ("camera_livia", "inginocchiatoio"), ("camera_livia", "armadio"),
    ("camera_livia", "vestiti"), ("camera_livia", "rosa"), ("camera_livia", "davanzale"),
    ("camera_clara", "letto"), ("camera_clara", "coperta"), ("camera_clara", "casa delle bambole"),
    ("camera_clara", "baule"), ("camera_clara", "carta da parati"),
    ("soffittone", "mobili"), ("soffittone", "teli"), ("soffittone", "travi"), ("soffittone", "impronte"),
    ("soffittone", "cera"), ("soffittone", "pavimento"), ("soffittone", "buco"), ("soffittone", "assi"),
    ("sottotetto", "tegola"), ("sottotetto", "spioventi"),
    ("archivio", "scaffali"), ("archivio", "faldoni"), ("archivio", "pergamene"), ("archivio", "faldone"),
    ("archivio", "tavolo"),
    ("stanza_orologio", "ingranaggi"), ("stanza_orologio", "pendolo"), ("stanza_orologio", "lucernario"),
    ("stanza_orologio", "trave"),
    ("tetto", "tegole"), ("tetto", "tempesta"), ("tetto", "colmo"),
    ("piccionaia", "piccioni"), ("piccionaia", "posatoi"), ("piccionaia", "tubetto"),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "thing"), ACT_THREE_DESCRIBED, ids=[f"{room}: {thing}" for room, thing in ACT_THREE_DESCRIBED]
)
def test_what_a_room_of_the_third_act_describes_can_be_examined(valdimora, room, thing):
    game = in_act_three(valdimora, room)

    answer = game.turn(f"esamina {thing}")

    assert answer not in ("Non vedi niente del genere qui.", "Non ho capito.")
    assert not answer.startswith("Quale intendi")


# --- Atto 3: i personaggi --------------------------------------------------------------------------------



def test_asked_about_the_photograph_livia_wants_it_but_tells_nothing(valdimora):
    game = in_act_three(valdimora, "camera_livia", carried=("fotografia",))
    before = game.state.model_dump(exclude={"turns", "asked", "last_speaker"})

    assert "Datemela" in game.turn("chiedi a Livia della fotografia")
    assert game.state.model_dump(exclude={"turns", "asked", "last_speaker"}) == before


@pytest.mark.parametrize(
    ("room", "flags", "line", "expected"),
    [
        ("corridoio_servitu", (), "parla con Agnese", "chiedete a me: scendo io"),
        ("camera_livia", (), "parla con Livia", "In camera mia non c'è niente per voi"),
        ("camera_livia", (), "chiedi a Livia di Clara", "Non conosco nessuna Clara"),
        ("camera_livia", ("livia_confessa",), "chiedi a Livia di Clara", "l'ho tradita"),
        ("archivio", (), "parla con Corrado", "Le carte di famiglia"),
        ("archivio", ("lettere_lette",), "parla con Corrado", "Allora siete voi. La nipotina."),
        ("archivio", ("lettere_lette",), "chiedi a Corrado di Clara", "cancellata da tutto"),
        ("cucina", (), "parla con Ettore", "Siete salita fin lassù"),
        ("cucina", ("lettere_lette",), "parla con Ettore", "Bentornata a casa"),
        ("cucina", (), "chiedi a Ettore della lanterna", "nel sottotetto"),
        ("cucina", (), "chiedi a Ettore della cantina", "senza un lume non si scende"),
        ("cucina", ("lettere_lette",), "chiedi a Ettore di Clara", "Era vostra nonna"),
    ],
)  # fmt: skip
def test_the_characters_have_something_to_say_in_the_third_act(valdimora, room, flags, line, expected):
    assert expected in in_act_three(valdimora, room, *flags).turn(line)


@pytest.mark.parametrize(
    ("room", "flags", "carried", "line", "done"),
    [
        ("camera_livia", ("livia_confessa",), (), "chiedi a Livia della camera di Clara", "La chiave ce l'avete"),
        ("cucina", (), ("chiave_cantina",), "chiedi a Ettore della cantina", "Siete sicura di avere tutto"),
        ("cucina", ("lanterna_accesa",), (), "chiedi a Ettore della lanterna", "ci vedrete"),
    ],
)  # fmt: skip
def test_what_the_characters_say_in_the_third_act_knows_when_it_is_done(valdimora, room, flags, carried, line, done):
    assert done in in_act_three(valdimora, room, *flags, carried=carried).turn(line)


# --- Found by the final review of act 3 ------------------------------------------------------------------


def test_the_rope_is_tied_to_the_beam_under_the_skylight(valdimora):
    # The skylight's description invites it: «Sotto, una trave robusta, a cui si potrebbe legare qualcosa».
    game = in_act_three(valdimora, "stanza_orologio", carried=("corda",))

    assert "trave robusta" in game.turn("esamina la trave")
    assert "qualcosa ti tiene" in game.turn("usa la corda con la trave")
    assert "corda_legata" in game.state.flags


def test_in_the_third_act_livia_has_no_keys_at_her_belt(valdimora):
    game = in_act_three(valdimora, "camera_livia")

    assert "Senza il mazzo di chiavi" in game.turn("parla con Livia")
    assert "con un mazzo di chiavi alla cintura" not in game.turn("esamina Livia")


@pytest.mark.parametrize(
    ("flags", "expected"),
    [(("agnese_in_cucina",), "qui con noi"), (("agnese_in_rimessa",), "in rimessa"), ((), "corridoio della servitù")],
)  # fmt: skip
def test_ettore_knows_where_agnese_is_in_the_third_act(valdimora, flags, expected):
    assert expected in in_act_three(valdimora, "cucina", *flags).turn("chiedi a Ettore di Agnese")


@pytest.mark.parametrize(
    ("flags", "carried", "expected"),
    [((), ("lanterna",), "L'avete trovata"), (("lanterna_piena",), ("lanterna",), "accendetela"),
     (("lanterna_piena", "lanterna_accesa"), ("lanterna",), "ci vedrete")],
)  # fmt: skip
def test_ettore_s_hint_on_the_lantern_follows_it(valdimora, flags, carried, expected):
    answer = in_act_three(valdimora, "cucina", *flags, carried=carried).turn("chiedi a Ettore della lanterna")

    assert expected in answer
    assert "nel sottotetto" not in answer


# --- The minors of act 3 ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("room", "flags", "thing", "expected"),
    [
        ("stanza_orologio", (), "il tetto", "Dal lucernario vedi il tetto"),
        ("stanza_orologio", (), "la pioggia", "Dal lucernario vedi il tetto"),
        ("stanza_orologio", (), "il vento", "Dal lucernario vedi il tetto"),
        ("soffittone", (), "il tetto", "Travi di castagno"),
        ("sottotetto", ("asse_posata",), "il tetto", "Una tegola spezzata"),
        ("tetto", ("corda_legata",), "il tetto", "Pioggia e vento"),
        ("camera_clara", (), "il tetto", "incavo a forma di stella"),
    ],
)  # fmt: skip
def test_the_roof_can_be_examined_where_it_is_described(valdimora, room, flags, thing, expected):
    # «fuori, il tetto è lucido di pioggia»: «esamina il tetto» wasn't understood, the rain was elsewhere.
    assert expected in in_act_three(valdimora, room, *flags).turn(f"esamina {thing}")


def test_jumping_on_the_roof_from_the_clock_room_is_a_hint(valdimora):
    game = in_act_three(valdimora, "stanza_orologio")
    tied = in_act_three(valdimora, "stanza_orologio", "corda_legata")

    assert "Ci si sale dal lucernario" in game.turn("salta sul tetto")
    assert not game.state.finished and game.state.current_room == "stanza_orologio"
    assert "La tua corda pende fin lassù" in tied.turn("esamina il tetto")
    assert "Sali, e tieniti a lei" in tied.turn("salta sul tetto")


def test_the_medallion_fits_the_star_slot_of_the_doll_s_house(valdimora):
    # «c'è un incavo a forma di stella»: «incavo» named only the sundial and the portrait, elsewhere.
    game = in_act_three(valdimora, "camera_clara", "camera_clara_aperta")

    assert "Con uno scatto il tetto si solleva" in game.turn("usa il medaglione con l'incavo")
    assert game.state.item_locations["chiave_cantina"] == "inventory"


@pytest.mark.parametrize(
    ("room", "flags", "expected"),
    [
        ("rimessa", ("valigia_aperta",), "solo i tuoi vestiti"),
        ("camera_clara", ("baule_aperto",), "vestiti da ragazza"),
        ("camera_livia", (), "Tre vestiti grigi"),
    ],
)  # fmt: skip
def test_the_clothes_are_examined_where_they_are(valdimora, room, flags, expected):
    # In the coach house and in Clara's room «esamina i vestiti» found only Livia's wardrobe, upstairs.
    assert expected in in_act_three(valdimora, room, *flags).turn("esamina i vestiti")
