# La Stella di Valdimora, atto 3: la soffitta — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dal pianerottolo di servizio si sale in soffitta e il terzo atto si gioca fino alla porta della cantina, con la confessione di Livia, le lettere «a mia figlia Clara» (rivelazione 3), la casa delle bambole, l'asse sul pavimento marcio, la lanterna da riempire e accendere di sotto, i fili facoltativi (la camera di Agnese con la prova 3, il tetto con la lettera del notaio), tre morti con la ripresa dall'inizio dell'atto, i personaggi spostati coi loro testi nuovi, e un finale provvisorio «Fine del terzo atto».

**Architecture:** quasi tutto è dati: un file nuovo, `data/worlds/valdimora/soffitta.yaml` (12 stanze, gli oggetti e le regole del terzo atto, compresa la porta della cantina), e ritocchi a `gioco.yaml` (il secondo `acts`, le morti, il finale provvisorio), `piano-nobile.yaml` (via la stanza provvisoria), `pianterreno.yaml` e `personaggi.yaml` (`moves`, varianti, argomenti). Il motore non cambia. Il modello vero ha mostrato quattro difetti generali dell'interprete, corretti nel codice senza toccare il prompt.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, pytest; Ollama con qwen2.5:3b per i test col modello vero.

**Spec:** `docs/superpowers/specs/2026-09-29-valdimora-design.md` — sezioni 2 (atti e personaggi), 3 (piantina: secondo piano), 4 (enigmi: atto 3, con le «decisioni prese al momento di costruirlo») e 6 (costruzione e prove).

## Global Constraints

- Branch: `feature/valdimora-atto-3` (già creato da `main`; contiene la spec aggiornata e, in un commit a parte, questo piano).
- Nessuna dipendenza nuova. Comandi con `.venv/Scripts/python` (Git Bash).
- Codice e identificatori in inglese; testi, commit e documentazione in italiano.
- **Il prompt dell'LLM non cambia**, e Valdimora non ha `game.examples`.
- **Testi**: Irene al femminile («sei salita»); i domestici, il dottore, Corrado e Agnese le danno del **voi** («signorina»); la contessa, nelle lettere, dà del **tu**. Registro del 1927. Ogni descrizione di stanza nomina le stanze vicine col loro nome; ogni cosa nominata in una descrizione di stanza è un arredo esaminabile; un indizio che manda a fare qualcosa ha una variante per quando è fatto. Gli atti restano veri dopo il loro inizio: le varianti dell'atto 3 vengono prima di quelle dell'atto 2.
- I testi scritti in questo piano sono quelli da usare, già provati su una copia del mondo (vedi «Come è stato verificato»): l'utente li rilegge qui e nella PR.
- **YAML**: un testo su una riga con «: » va tra virgolette doppie; anche un alias fatto di cifre («"1897"»), che YAML leggerebbe come numero.
- Mai nei commit: `run.bat`, `run_log.bat`, `test_llm.txt`. Aggiungere i file uno per uno.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Le modifiche ai file esistenti si fanno con Edit, sostituendo esattamente il blocco indicato; i file nuovi con Write. Nessun testo di questo piano contiene backslash.

## Decisioni prese nel piano (la spec non le copriva)

1. **Il terzo atto è il secondo `acts`** («terzo atto», su `atto_tre`): aprire la scala di servizio salva la partita, e dopo una morte «riprendi» riporta al pianerottolo di servizio con la porta aperta. Il testo del finale provvisorio dell'atto 2 (la scala che sale, l'odore di lavanda) passa alla regola che apre la porta.
2. **Le chiavi usate restano nella serratura**, come nell'atto 2: la chiave della camera di Clara e quella della cantina. Così in tasca c'è sempre una sola «chiave».
3. **Le morti entrando**: il gioco mostra la stanza, poi il finale, e i testi lo seguono («Le assi marce che hai appena attraversato…»). Saltare nel buco del pavimento («salta nel buco») è la terza morte, come il pozzo e la valle.
4. **L'asse e la corda, una volta messe, diventano arredi** (`asse_stesa`, `corda_legata`, effetto `place`): non si riprendono, così il ponte e la corda non spariscono.
5. **Le commissioni di Agnese** stanno nel Task 1 insieme alla soffitta, perché la sua camera si apre coi loro flag. Le varianti dei due argomenti dipendono dalla stanza di Irene (`player_in`), perché gli effetti di un argomento valgono prima che il testo sia scelto: chiesto nel corridoio, Agnese parte; chiesto in cucina, offre la tisana.
6. **Le prove nella camera di Agnese**: esaminare il letto (anche «guardo sotto il materasso») le trova; è una regola su `esamina` con effetti, come cercare. Il quaderno, col registro in mano, ha la stessa «A.» del registro: è la risposta alle lenzuola «A. V.» del primo atto.
7. **La porta di Agnese è un oggetto senza l'alias «porta»**, così «apri la porta» nel corridoio è quella di Clara, e non chiede «Quale intendi».
8. **La lettera della contessa** (quella di Irene, che Ettore le rende nel primo atto) resta in tasca: con la lettera di giugno o quella del notaio «leggi la lettera» chiede quale. Le lettere per Clara hanno l'alias «lettere della contessa».
9. **Quattro correzioni generali all'interprete** (Task 3), trovate col modello vero, il prompt non cambia: «lego»/«annodo» non è leggere; esaminare qualcosa che la frase non nomina diventa esaminare l'unica cosa che nomina; per leggere ed esaminare vince l'oggetto nominato con le parole esatte su quello nominato solo con un'altra desinenza; un salto senza parola da salto che nomina una stanza tra le uscite è uno spostamento (e se lì si muore, il gioco chiede prima).
10. **Corrado affronta Irene nel saluto** («Allora siete voi. La nipotina.»), dopo le lettere; la descrizione dell'archivio non cambia, perché chi c'è nella stanza lo dice già il motore («Qui c'è Corrado.»).
11. **Le partite salvate nel browser durante il secondo atto ricominciano una volta** («Il mondo è cambiato»): ci sono oggetti nuovi. Succedeva anche con gli atti 1 e 2.

## Come è stato verificato, prima di scriverlo

Tutte le modifiche di questo piano sono state applicate a copie del repository, task per task, e generate da lì: per ogni task i test nuovi falliscono sul codice di prima (Task 1: 76; Task 2: 16; Task 3: 4) e passano dopo, con tutta la suite verde (1304, poi 1320, poi 1326). Sulla copia sono stati giocati la soluzione dei tre atti, i fili facoltativi, le morti con la ripresa, gli ordini sbagliati, i dialoghi e l'esame di ogni arredo. Col modello vero le 23 frasi libere del terzo atto: 18 al primo giro, poi 23 con le correzioni del Task 3; tutto `tests/test_ollama.py` sulla copia: 171 passati e 7 limiti noti, nessun caso di prima rotto.

## Review Focus

1. **Le morti entrando nella stanza**: il parser uccide subito («nord» dal soffittone senza l'asse, «su» dalla stanza dell'orologio senza la corda), come deciso; una frase libera chiede prima — test nel Task 1 (morti e ripresa) e nel Task 3 («attraverso il pavimento marcio», «esco dal lucernario sul tetto» col modello vero).
2. **La camera di Agnese**: si entra solo mentre lei è di sotto, e una volta mandata ci resta; la prova non si perde — test nel Task 1.
3. **Gli atti precedenti restano veri**: nessun testo dell'atto 2 nel terzo (la loggia, il quadro, la camera della contessa) — test dei saluti e degli argomenti nel Task 2.
4. **Le correzioni dell'interprete non cambiano le frasi di prima**: tutto `tests/test_ollama.py` col modello vero nel Task 3; i casi di guardia («ciave» resta la chiave, «salto dal lucernario» resta un salto) nel Task 3.
5. **La ripresa dopo una morte nel terzo atto** riporta al pianerottolo di servizio con la porta aperta, e da lì si risale — test nel Task 1.

---

### Task 1: La soffitta, il filo principale, i pericoli e le commissioni di Agnese

**Files:**
- Create: `data/worlds/valdimora/soffitta.yaml`
- Modify: `data/worlds/valdimora/gioco.yaml` (commento, `summary`, `acts`, morti, finale provvisorio), `data/worlds/valdimora/piano-nobile.yaml` (via la stanza provvisoria; varianti del pianerottolo di servizio e della sua porta; testo della regola che la apre), `data/worlds/valdimora/pianterreno.yaml` (refuso delle lenzuola, chiave sbagliata, porta della cantina), `data/worlds/valdimora/personaggi.yaml` (commento, `moves`, gli argomenti di Agnese)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: la chiave della scala di servizio che resta nella serratura e `atto_tre` (atto 2); gli aiuti dei test `new_game`, `play`, `in_act_two`, `TO_THE_STAIRCASE`, `TO_THE_SERVICE_STAIRS`.
- Produces: stanze `pianerottolo_soffitta`, `stenditoio`, `corridoio_servitu`, `camera_agnese`, `camera_livia`, `camera_clara`, `soffittone`, `sottotetto`, `archivio`, `stanza_orologio`, `tetto`, `piccionaia`; oggetti `asse`, `corda`, `chiave_clara`, `lettere_clara`, `casa_bambole`, `chiave_cantina`, `lanterna`, `lettera_giugno`, `anello`, `quaderno`, `lettera_notaio` e gli arredi; flag `livia_confessa`, `camera_clara_aperta`, `baule_aperto`, `lettere_lette`, `casa_aperta`, `asse_posata`, `lanterna_piena`, `lanterna_accesa`, `materasso_frugato`, `corda_legata`, `tubetto_aperto`, `agnese_in_rimessa`, `agnese_in_cucina`, `caduta_in_soffitta`, `atto_quattro`; gli argomenti di Agnese `aiuto` (variante), `petrolio` e `tisana` (con effetti: la mandano di sotto), `camera`, `luce`. Nei test, le costanti `TO_THE_CELLAR`, `TO_THE_PIGEONS` e l'aiuto `in_act_three(valdimora, room, *flags, carried=())`.

- [ ] **Step 1: Test che falliscono**

- In `tests/test_valdimora.py`, il blocco
```python
"""La Stella di Valdimora, atti 1 e 2 (il pianterreno e il piano nobile): the game played with typed commands through Game,
```
diventa
```python
"""La Stella di Valdimora, atti 1, 2 e 3 (il pianterreno, il piano nobile e la soffitta): the game played with typed commands through Game,
```
- In `tests/test_valdimora.py`, il blocco
```python
    assert "ninna nanna" in answers[35]
    assert answers[-1].endswith("Fine del secondo atto. (Il terzo è in costruzione.)")
    assert game.finished and not game.state.lost
```
diventa
```python
    assert "ninna nanna" in answers[35]
    # The service stairs open the third act: its state is kept, to go on from here after a death.
    assert "odore di polvere e di lavanda" in answers[-1]
    assert not game.finished and game.state.act == 2 and game.state.checkpoint is not None
```
- In `tests/test_valdimora.py`, il blocco
```python
def test_no_character_gives_a_shortcut(valdimora):
    # Only Ettore's word for Livia and the key of the sideboard come from talking.
    effects = {
        (character.id, topic.id): topic.effects
        for character in valdimora.characters.values()
        for topic in character.topics.values()
        if topic.effects
    }

    assert set(effects) == {("ettore", "livia"), ("ettore", "credenza")}
```
diventa
```python
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
```
- In `tests/test_valdimora.py`, il blocco
```python
from app.engine.models import Action, Give, Remove, World
```
diventa
```python
from app.engine.models import Action, Give, Remove, SetFlag, World
```
- In fondo a `tests/test_valdimora.py`:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 76 test (il secondo atto non finisce più con un finale; le stanze, gli oggetti, le regole e gli argomenti del terzo atto non ci sono).

- [ ] **Step 3: Implementazione**

Con Write, `data/worlds/valdimora/soffitta.yaml`:
```yaml
# La soffitta di Valdimora (secondo piano): stanze, oggetti e regole del terzo atto.
# Spec: docs/superpowers/specs/2026-09-29-valdimora-design.md, sezioni 3 e 4 (atto 3).
# Il petrolio è nella rimessa e i fiammiferi in cucina; la porta della cantina, in cucina, chiude
# il terzo atto (finale provvisorio: lo toglie l'atto 4).

rooms:
  pianerottolo_soffitta:
    name: Pianerottolo della soffitta
    aliases: [soffitta]
    description: >
      In cima alla scala di servizio, un pianerottolo stretto e buio che sa di polvere e di lavanda.
      Quassù dorme la servitù. A ovest il corridoio della servitù, a est il soffittone, a nord lo
      stenditoio; la scala scende al piano nobile.
    exits:
      giù: {to: pianerottolo_servizio}
      ovest: {to: corridoio_servitu}
      est: {to: soffittone}
      nord: {to: stenditoio}

  stenditoio:
    name: Stenditoio
    description: >
      Una stanza lunga e vuota sotto il tetto, con le finestrelle aperte al vento perché il bucato
      asciughi. Non c'è un panno steso. A sud il pianerottolo.
    exits:
      sud: {to: pianerottolo_soffitta}

  corridoio_servitu:
    name: Corridoio della servitù
    aliases: [corridoio]
    description: >
      Un corridoio basso e stretto, dove un uomo alto dovrebbe chinarsi. A nord la camera di Agnese, a
      sud quella di Livia; in fondo, a ovest, una porta chiusa con una targhetta d'ottone. A est si
      torna sul pianerottolo.
    variants:
      - when: {flag: camera_clara_aperta}
        text: >
          Un corridoio basso e stretto, dove un uomo alto dovrebbe chinarsi. A nord la camera di
          Agnese, a sud quella di Livia; in fondo, a ovest, la porta della camera di Clara è aperta. A
          est si torna sul pianerottolo.
    exits:
      est: {to: pianerottolo_soffitta}
      sud: {to: camera_livia}
      nord:
        to: camera_agnese
        when: {any: [{flag: agnese_in_rimessa}, {flag: agnese_in_cucina}]}
        otherwise: >
          Agnese si mette davanti alla porta della sua camera, con un sorriso. «Lì è tutto in
          disordine, signorina. Non c'è niente da vedere, ve lo assicuro.»
      ovest:
        to: camera_clara
        when: {flag: camera_clara_aperta}
        otherwise: >
          La porta in fondo al corridoio è chiusa a chiave. Sulla targhetta d'ottone, quasi
          cancellata, una parola sola: «Clara».
        otherwise_variants:
          - when: {has: chiave_clara}
            text: "La porta della camera di Clara è chiusa a chiave. Hai la chiave della camera di Clara: usala."

  camera_agnese:
    name: Camera di Agnese
    description: >
      Una cameretta ordinata fino alla pignoleria: un letto stretto rifatto a regola d'arte, un
      crocifisso, un catino sul comodino. Accanto al catino, un mozzicone di candela consumato fino in
      fondo; sotto il letto, un paio di scarpe grigie di polvere. A sud il corridoio.
    exits:
      sud: {to: corridoio_servitu}

  camera_livia:
    name: Camera di Livia
    description: >
      Una camera spoglia come una cella: un letto stretto, un inginocchiatoio, un armadio con tre
      vestiti grigi tutti uguali. Sul davanzale, in un vasetto da poco, una rosa bianca secca da anni.
      A nord il corridoio.
    exits:
      nord: {to: corridoio_servitu}

  camera_clara:
    name: Camera di Clara
    description: >
      La camera di una ragazza, rimasta com'era trent'anni fa sotto un velo di polvere: un letto
      stretto con la coperta ricamata, una casa delle bambole alta quasi quanto te, un baule ai piedi
      del letto. La carta da parati è a stelline d'argento. A est il corridoio.
    exits:
      est: {to: corridoio_servitu}

  soffittone:
    name: Soffittone
    description: >
      Un soffittone immenso sotto le travi del tetto, ingombro di mobili coperti da teli. Nella
      polvere del pavimento ci sono impronte fresche, e qua e là gocce di cera: qualcuno è salito qui
      con una candela, e non molti giorni fa. A nord, verso il sottotetto, il pavimento è marcio: le
      assi sono nere di umido, e in mezzo c'è un buco da cui si vede il piano di sotto. Metterci il
      piede sarebbe una follia. A ovest il pianerottolo, a est l'archivio di famiglia, a sud la stanza
      dell'orologio.
    variants:
      - when: {flag: asse_posata}
        text: >
          Un soffittone immenso sotto le travi del tetto, ingombro di mobili coperti da teli. Nella
          polvere del pavimento ci sono impronte fresche, e qua e là gocce di cera: qualcuno è salito
          qui con una candela, e non molti giorni fa. A nord, sul pavimento marcio, hai steso l'asse
          lunga: un ponte stretto verso il sottotetto. A ovest il pianerottolo, a est l'archivio di
          famiglia, a sud la stanza dell'orologio.
    exits:
      ovest: {to: pianerottolo_soffitta}
      nord: {to: sottotetto}
      est: {to: archivio}
      sud: {to: stanza_orologio}

  sottotetto:
    name: Sottotetto
    description: >
      Uno spazio basso sotto gli spioventi, dove si sta solo chinati. Da una tegola rotta entra la
      pioggia. A sud il soffittone.
    exits:
      sud: {to: soffittone}

  archivio:
    name: Archivio di famiglia
    aliases: [archivio]
    description: >
      Una stanza stretta, foderata di scaffali: faldoni, pergamene arrotolate, trecento anni di carte
      dei Valdimora. Su un tavolo, un faldone aperto con la data «1897». A ovest il soffittone.
    exits:
      ovest: {to: soffittone}

  stanza_orologio:
    name: Stanza dell'orologio
    aliases: [torretta]
    description: >
      La stanza del grande orologio della torretta: ingranaggi di ferro grandi come ruote di carro, e
      un pendolo fermo. In alto, il lucernario sbatte nel vento; fuori, il tetto è lucido di pioggia e
      ripido come uno scivolo. Uscirci senza niente a cui tenersi sarebbe una follia. A nord il
      soffittone.
    variants:
      - when: {flag: corda_legata}
        text: >
          La stanza del grande orologio della torretta: ingranaggi di ferro grandi come ruote di
          carro, e un pendolo fermo. In alto, il lucernario sbatte nel vento; dalla trave sotto il
          lucernario pende la corda che hai legato: con quella, lassù, ti puoi tenere. A nord il
          soffittone.
    exits:
      nord: {to: soffittone}
      su: {to: tetto}

  tetto:
    name: Tetto
    description: >
      Sei sul tetto, nel mezzo della tempesta. Le tegole sono lucide di pioggia, e il vento ti strappa
      il fiato. A est, lungo il colmo, la piccionaia; giù, la stanza dell'orologio.
    exits:
      giù: {to: stanza_orologio}
      est: {to: piccionaia}

  piccionaia:
    name: Piccionaia
    description: >
      Una piccionaia di legno, che sa di piume bagnate. Sui posatoi, una dozzina di piccioni tubano al
      riparo; uno ha un tubetto di latta legato alla zampa. A ovest si torna sul tetto.
    exits:
      ovest: {to: tetto}

items:
  # --- Il pianerottolo e lo stenditoio: l'asse e la corda ---
  scala_soffitta:
    name: scala di legno
    gender: f
    aliases: [scala, scala di servizio, gradini]
    description: Una scala di legno stretta e ripida, consumata al centro dei gradini. Scende al piano nobile.
    location: pianerottolo_soffitta
    scenery: true

  finestrelle:
    name: finestrelle
    gender: f
    plural: true
    aliases: [finestrella, finestre]
    description: Finestrelle basse, aperte sul vento e sulla pioggia. Giù, tre piani più in basso, il cortile.
    location: stenditoio
    scenery: true

  asse:
    name: asse lunga
    gender: f
    aliases: [asse, asse da stiro]
    description: Un'asse di legno lunga e stretta, da stiro. È pesante, ma la porti.
    location: stenditoio

  corda:
    name: corda da bucato
    gender: f
    aliases: [corda, fune]
    description: Una corda da bucato, lunga e robusta.
    location: stenditoio

  # --- Il corridoio, la camera di Agnese (prova 3) e quella di Livia ---
  porta_clara:
    name: porta della camera di Clara
    gender: f
    aliases: [porta, porta di Clara, camera di Clara, targhetta, porta in fondo]
    description: >
      Una porta di legno chiaro, chiusa a chiave. Sulla targhetta d'ottone, quasi cancellata, una
      parola sola: «Clara».
    location: corridoio_servitu
    scenery: true
    variants:
      - when: {flag: camera_clara_aperta}
        text: La porta della camera di Clara, aperta. La chiave è rimasta nella serratura.

  porta_agnese:
    name: porta della camera di Agnese
    gender: f
    aliases: [porta di Agnese]
    description: Una porta di legno scuro, senza serratura.
    location: corridoio_servitu
    scenery: true

  letto_agnese:
    name: letto di Agnese
    gender: m
    aliases: [letto, materasso, letto stretto]
    description: >
      Un letto stretto, rifatto con cura. Il materasso, però, è gonfio da una parte, come se sotto ci
      fosse qualcosa.
    location: camera_agnese
    scenery: true
    variants:
      - when: {flag: materasso_frugato}
        text: Un letto stretto, rifatto con cura. Sotto il materasso non c'è più niente.

  crocifisso:
    name: crocifisso
    gender: m
    aliases: [croce]
    description: Un crocifisso di legno scuro, appeso sopra il letto.
    location: camera_agnese
    scenery: true

  catino:
    name: catino
    gender: m
    aliases: [comodino, brocca]
    description: Un catino di ceramica bianca, con la sua brocca, su un comodino di legno grezzo.
    location: camera_agnese
    scenery: true

  mozzicone:
    name: mozzicone di candela
    gender: m
    aliases: [mozzicone, candela]
    description: >
      Un mozzicone di candela bianca, consumato fino in fondo. La cera colata è la stessa delle gocce
      nel soffittone.
    location: camera_agnese
    scenery: true

  scarpe:
    name: scarpe grigie
    gender: f
    plural: true
    aliases: [scarpe]
    description: Un paio di scarpe di panno nero, grigie della stessa polvere del soffittone.
    location: camera_agnese
    scenery: true

  lettera_giugno:
    name: lettera di giugno
    gender: f
    aliases: [lettera, lettera intercettata]
    description: >
      Una lettera della contessa, datata giugno 1927, indirizzata a te, a Genova. Il francobollo c'è,
      il timbro postale no: non è mai partita. È stata aperta, e richiusa con cura.
    location: null

  anello:
    name: anello
    gender: m
    aliases: [anellino]
    description: Un anellino d'oro sottile. All'interno, inciso, «C. ad A.».
    location: null

  quaderno:
    name: quaderno di Agnese
    gender: m
    aliases: [quaderno, appunti, calligrafia]
    description: >
      Un quaderno di appunti: la spesa, i romanzi da leggere alla contessa, le ore delle gocce. Ogni
      pagina è siglata con una «A.» tutta svolazzi.
    location: null
    variants:
      - when: {has: registro}
        text: >
          Un quaderno di appunti: la spesa, i romanzi da leggere alla contessa, le ore delle gocce.
          Ogni pagina è siglata con una «A.» tutta svolazzi. La confronti col registro delle medicine:
          è la stessa mano. Non era la contessa a firmare le dosi. Era Agnese.

  letto_livia:
    name: letto di Livia
    gender: m
    aliases: [letto, letto stretto]
    description: Un letto stretto, con una coperta grigia tirata senza una piega.
    location: camera_livia
    scenery: true

  inginocchiatoio:
    name: inginocchiatoio
    gender: m
    aliases: [rosario]
    description: Un inginocchiatoio di legno, col velluto consumato dalle ginocchia. Sopra, un rosario.
    location: camera_livia
    scenery: true

  armadio_livia:
    name: armadio di Livia
    gender: m
    aliases: [armadio, vestiti, vestiti grigi]
    description: Tre vestiti grigi tutti uguali, un grembiule, un cappotto. Nient'altro.
    location: camera_livia
    scenery: true

  rosa_secca:
    name: rosa secca
    gender: f
    aliases: [rosa, vasetto, davanzale]
    description: Una rosa bianca della serra, secca da anni, in un vasetto da poco. Livia non l'ha mai buttata.
    location: camera_livia
    scenery: true

  chiave_clara:
    name: chiave della camera di Clara
    gender: f
    aliases: [chiave, chiave di Clara, chiave piccola]
    description: Una chiave piccola e lucida, legata a un cordino. Livia l'ha portata al collo per trent'anni.
    location: null

  # --- La camera di Clara: le lettere (rivelazione 3) e la casa delle bambole ---
  letto_clara:
    name: letto di Clara
    gender: m
    aliases: [letto, coperta, coperta ricamata]
    description: Un letto stretto, con una coperta ricamata a mano. Le stelle del ricamo sono uguali a quella del tuo medaglione.
    location: camera_clara
    scenery: true

  carta_parati:
    name: carta da parati
    gender: f
    aliases: [stelline, pareti]
    description: Carta da parati azzurra, a stelline d'argento. In un angolo, a matita, segni di altezza e date, dal 1882 al 1895.
    location: camera_clara
    scenery: true

  baule:
    name: baule
    gender: m
    aliases: [baule di Clara, coperchio]
    description: Un baule da corredo, col coperchio intarsiato. Non è chiuso a chiave.
    location: camera_clara
    scenery: true
    variants:
      - when: {flag: baule_aperto}
        text: Il baule aperto. Dentro, vestiti da ragazza ripiegati con cura, e nient'altro.

  lettere_clara:
    name: lettere per Clara
    gender: f
    plural: true
    aliases: [lettere, lettere della contessa, pacco, pacco di lettere, nastro nero]
    description: >
      Un pacco di lettere legato con un nastro nero, tutte della contessa, tutte «a mia figlia
      Clara». Nessuna ha il francobollo: non sono mai partite.
    location: null

  casa_bambole:
    name: casa delle bambole
    gender: f
    aliases: [casa, casetta, bambole, comignolo]
    description: >
      Una casa delle bambole di legno dipinto, a tre piani, con le finestre vere e le tendine di
      pizzo. Sul tetto, al posto del comignolo, c'è un incavo a forma di stella.
    location: camera_clara
    scenery: true
    variants:
      - when: {flag: casa_aperta}
        text: La casa delle bambole, col tetto sollevato come un coperchio. Le stanzette in miniatura sono vuote.

  chiave_cantina:
    name: chiave della cantina
    gender: f
    aliases: [chiave, chiave lunga, cartellino]
    description: >
      Una chiave lunga e scura, un po' arrugginita. Sul cartellino, la grafia della contessa: «Dove il
      vino dorme più vecchio. Quando scenderai, porta con te tutto ciò che hai scoperto.»
    location: null

  # --- Il soffittone, il sottotetto (pericolo) e la lanterna ---
  mobili_coperti:
    name: mobili coperti
    gender: m
    plural: true
    aliases: [mobili, teli, bauli, cassapanche]
    description: >
      Bauli, cassapanche, una culla, un manichino da sarta: generazioni di cose messe da parte e
      coperte da teli bianchi. Qualcuno ha sollevato i teli, uno dopo l'altro, e li ha rimessi in
      fretta.
    location: soffittone
    scenery: true

  travi:
    name: travi
    gender: f
    plural: true
    aliases: [trave]
    description: Travi di castagno annerite dal tempo. Ci piove dentro da più di un punto.
    location: soffittone
    scenery: true

  impronte:
    name: impronte
    gender: f
    plural: true
    aliases: [polvere, gocce di cera, cera, gocce, orme]
    description: >
      Impronte di scarpe piccole, da donna, che girano tra i mobili coperti e tornano alla scala. E
      gocce di cera bianca, fresche: qualcuno ha cercato qualcosa, quassù, a lume di candela.
    location: soffittone
    scenery: true

  pavimento_marcio:
    name: pavimento marcio
    gender: m
    aliases: [pavimento, buco, assi, assi marce]
    description: >
      Le assi del pavimento, verso il sottotetto, sono nere di umido e piene di buchi; una non c'è più
      del tutto, e sotto si vede il buio del piano nobile. Ti servirebbe qualcosa di lungo da
      stenderci sopra, per passare.
    location: soffittone
    scenery: true
    variants:
      - when: {flag: asse_posata}
        text: Sul pavimento marcio hai steso l'asse lunga, da una trave sana all'altra. Regge.

  asse_stesa:
    name: asse stesa
    gender: f
    aliases: [asse, ponte]
    description: L'asse lunga, stesa sul pavimento marcio da una trave sana all'altra. Regge il tuo peso.
    location: null
    scenery: true

  tegola:
    name: tegola rotta
    gender: f
    aliases: [tegola, spioventi, pioggia]
    description: Una tegola spezzata. Ci piove dentro, goccia dopo goccia.
    location: sottotetto
    scenery: true

  lanterna:
    name: lanterna
    gender: f
    aliases: [lume, lanterna a petrolio, stoppino, serbatoio]
    description: Una vecchia lanterna a petrolio, col vetro annerito. Il serbatoio è vuoto, e senza petrolio non si accende.
    location: sottotetto
    variants:
      - when: {flag: lanterna_accesa}
        text: La lanterna accesa. Dietro il vetro annerito la fiamma trema, ma tiene.
      - when: {flag: lanterna_piena}
        text: La lanterna, col serbatoio pieno di petrolio. Manca solo da accenderla.

  # --- L'archivio di famiglia ---
  faldoni:
    name: faldoni
    gender: m
    plural: true
    aliases: [scaffali, pergamene, contratti]
    description: Faldoni di cartone e pergamene coi sigilli di cera rossa. Nessuno li riordina da anni.
    location: archivio
    scenery: true

  faldone_1897:
    name: faldone del 1897
    gender: m
    aliases: [faldone, "1897", carte del conte, carte, tavolo]
    description: >
      Il faldone del 1897, aperto sul tavolo: le carte del conte Ruggero. Conti della tenuta, una
      lettera al parroco, il libro paga della servitù.
    location: archivio
    scenery: true

  # --- La stanza dell'orologio, il tetto (pericolo) e la piccionaia ---
  meccanismo:
    name: meccanismo dell'orologio
    gender: m
    aliases: [meccanismo, ingranaggi, pendolo, orologio]
    description: >
      Ingranaggi di ferro, catene, un pendolo lungo quanto un uomo. L'orologio si è fermato alle tre e
      un quarto, e nessuno l'ha più caricato.
    location: stanza_orologio
    scenery: true

  lucernario:
    name: lucernario
    gender: m
    aliases: [botola]
    description: >
      Un lucernario di vetro e ferro, aperto, che sbatte nel vento. Sotto, una trave robusta, a cui si
      potrebbe legare qualcosa; fuori, il tetto.
    location: stanza_orologio
    scenery: true
    variants:
      - when: {flag: corda_legata}
        text: Il lucernario aperto, che sbatte nel vento. Alla trave sotto è legata la tua corda, che pende fuori, sul tetto.

  corda_legata:
    name: corda legata
    gender: f
    aliases: [corda, nodo]
    description: La corda da bucato, legata alla trave sotto il lucernario con un nodo da marinaio. Pende fuori, sul tetto.
    location: null
    scenery: true

  tempesta:
    name: tempesta
    gender: f
    aliases: [tegole, colmo, vento, pioggia]
    description: Pioggia e vento, e sotto di te le tegole lucide che scendono ripide verso il vuoto.
    location: tetto
    scenery: true

  piccioni:
    name: piccioni
    gender: m
    plural: true
    aliases: [piccione, posatoi, piume, piccionaia]
    description: >
      Piccioni viaggiatori, grigi e bagnati. La contessa li teneva per scrivere al notaio in città,
      quando la strada era chiusa.
    location: piccionaia
    scenery: true

  tubetto:
    name: tubetto di latta
    gender: m
    aliases: [tubetto, latta, zampa]
    description: Un tubetto di latta legato alla zampa di un piccione. Dentro c'è qualcosa di arrotolato.
    location: piccionaia
    scenery: true
    variants:
      - when: {flag: tubetto_aperto}
        text: Il tubetto di latta, vuoto. Il piccione ti guarda, offeso.

  lettera_notaio:
    name: lettera del notaio
    gender: f
    aliases: [lettera, carta intestata]
    description: Una lettera su carta intestata, «Studio notarile Bertola, Torino», datata 15 ottobre 1927.
    location: null

rules:
  # --- Il pianerottolo e lo stenditoio ---
  prendi_asse:
    trigger: {verb: prendi, target: asse_stesa}
    text: Se la togli, nel sottotetto non ci arrivi più. Lasciala dov'è.

  # --- La camera di Livia: la confessione ---
  livia_confessa:
    trigger: {verb: dai, target: fotografia, with: livia}
    when: {all: [{flag: atto_tre}, {not: {flag: livia_confessa}}]}
    otherwise: Livia guarda la fotografia, e per un attimo impallidisce. Poi te la rende senza una parola.
    otherwise_variants:
      - when: {flag: livia_confessa}
        text: Livia scuote la testa. «L'ho guardata abbastanza, signorina. Tenetela voi.»
    effects:
      - give: chiave_clara
      - set_flag: livia_confessa
    text: >
      Livia prende la fotografia e la guarda a lungo. Le tremano le mani. «Clara», dice piano.
      «Avevo diciotto anni, ed ero la sua cameriera. Fui io a dire al conte che aspettava un bambino:
      credevo di fare il mio dovere. La cacciò quella notte stessa, sotto la pioggia, e la contessa
      non me l'ha mai perdonato, anche se non me l'ha mai detto.» Ti rende la fotografia, poi si sfila
      dal collo una chiave piccola, legata a un cordino. «La camera di Clara. È chiusa da trent'anni,
      e la chiave l'ho sempre tenuta io. Andate, signorina. Voi ne avete il diritto.»

  # --- Il corridoio: la camera di Clara e quella di Agnese ---
  apri_camera_clara:
    trigger: {verb: apri, target: porta_clara, with: chiave_clara}
    when: {not: {flag: camera_clara_aperta}}
    otherwise: La porta della camera di Clara è già aperta.
    effects:
      - remove: chiave_clara
      - set_flag: camera_clara_aperta
    text: >
      La chiave gira dopo trent'anni con un lamento di ferro. La lasci nella serratura e spingi la
      porta: dentro, la polvere e il silenzio di una stanza chiusa dal 1897.

  apri_camera_clara_senza_chiave:
    trigger: {verb: apri, target: porta_clara}
    when: {all: [{not: {flag: camera_clara_aperta}}, {not: {has: chiave_clara}}]}
    otherwise: "Hai la chiave della camera di Clara: usala."
    otherwise_variants:
      - when: {flag: camera_clara_aperta}
        text: La porta della camera di Clara è già aperta.
    text: È chiusa a chiave. Eppure la serratura è lucida, come se qualcuno l'avesse tenuta in ordine per tutti questi anni.

  apri_porta_agnese:
    trigger: {verb: apri, target: porta_agnese}
    when: {any: [{flag: agnese_in_rimessa}, {flag: agnese_in_cucina}]}
    otherwise: >
      Agnese si mette davanti alla porta, con un sorriso. «Lì è tutto in disordine, signorina. Non
      c'è niente da vedere, ve lo assicuro.»
    text: Non è chiusa a chiave. Basta entrare.

  # --- La camera di Agnese: la prova 3 ---
  fruga_materasso:
    trigger:
      - {verb: esamina, target: letto_agnese}
      - {verb: prendi, target: letto_agnese}
      - {verb: tira, target: letto_agnese}
      - {verb: spingi, target: letto_agnese}
      - {verb: apri, target: letto_agnese}
    when: {not: {flag: materasso_frugato}}
    otherwise: Un letto stretto, rifatto con cura. Sotto il materasso non c'è più niente.
    effects:
      - give: lettera_giugno
      - give: anello
      - give: quaderno
      - set_flag: materasso_frugato
    text: >
      Il materasso è gonfio da una parte. Lo sollevi: sotto, ben nascosti, una lettera, un anellino
      d'oro e un quaderno. Li prendi, e rimetti il materasso com'era.

  leggi_lettera_giugno:
    trigger: {verb: leggi, target: lettera_giugno}
    text: >
      «Cara Irene, non mi conosci, ma io so chi sei. Ti scrivo per la terza volta, e ancora non mi
      rispondi: forse le mie lettere non ti arrivano. Vieni a Valdimora. C'è una cosa che appartiene a
      te e a tua madre, e il tempo che mi resta è poco. Adelaide di Valdimora.» Non è mai partita.
      Qualcuno l'ha aperta, l'ha letta, e l'ha tenuta.

  leggi_quaderno:
    trigger: {verb: leggi, target: quaderno}
    when: {has: registro}
    otherwise: >
      La spesa, i romanzi da leggere alla contessa, le ore delle gocce. Ogni pagina è siglata con una
      «A.» tutta svolazzi.
    text: >
      La spesa, i romanzi da leggere alla contessa, le ore delle gocce. Ogni pagina è siglata con una
      «A.» tutta svolazzi. La confronti col registro delle medicine: è la stessa mano. Non era la
      contessa a firmare le dosi. Era Agnese.

  # --- La camera di Clara: le lettere e la casa delle bambole ---
  apri_baule:
    trigger: {verb: apri, target: baule}
    when: {not: {flag: baule_aperto}}
    otherwise: Il baule è aperto, e dentro restano solo i vestiti.
    effects:
      - give: lettere_clara
      - set_flag: baule_aperto
    text: >
      Sollevi il coperchio. Dentro, vestiti da ragazza ripiegati con cura e, sopra tutto, un pacco di
      lettere legato con un nastro nero. Sulla prima, la grafia della contessa: «A mia figlia Clara».
      Lo prendi.

  prendi_baule:
    trigger: {verb: prendi, target: baule}
    text: È un baule da corredo, pesante come un armadio. Ma il coperchio non è chiuso a chiave.

  leggi_lettere:
    trigger: {verb: leggi, target: lettere_clara}
    when: {not: {flag: lettere_lette}}
    otherwise: L'ultima lettera la sai quasi a memoria. «Ma hai una figlia. Si chiama Irene.»
    effects:
      - set_flag: lettere_lette
    text: >
      Sciogli il nastro e leggi. La prima è del novembre 1897: «Clara, figlia mia, tuo padre mi ha
      proibito di cercarti, e io ho obbedito. Che Dio mi perdoni.» Poi una ogni anno, il giorno del
      compleanno di Clara, mai spedita. L'ultima è di questa primavera, e la mano trema: «Ettore mi ha
      detto tutto. Sei morta nove anni fa, e io non l'ho saputo. Ma hai una figlia. Si chiama Irene, e
      fa la sarta a Genova, come te. Le ho scritto.» Abbassi il foglio. La contessa di Valdimora era
      tua nonna.

  apri_casa_bambole:
    trigger:
      - {verb: usa, target: medaglione, with: casa_bambole}
    when: {not: {flag: casa_aperta}}
    otherwise: La casa delle bambole è aperta, e dentro non c'è altro.
    effects:
      - give: chiave_cantina
      - set_flag: casa_aperta
    text: >
      Appoggi il medaglione nell'incavo sul tetto della casetta, e lo giri. Con uno scatto il tetto si
      solleva come un coperchio. Nella stanzetta più alta, sul letto di una bambola, c'è una chiave
      lunga e scura, con un cartellino: «Dove il vino dorme più vecchio. Quando scenderai, porta con
      te tutto ciò che hai scoperto.» Prendi la chiave, e ti rimetti il medaglione al collo.

  apri_casa_senza_medaglione:
    trigger:
      - {verb: apri, target: casa_bambole}
      - {verb: tira, target: casa_bambole}
    when: {not: {flag: casa_aperta}}
    otherwise: La casa delle bambole è aperta, e dentro non c'è altro.
    text: Il tetto della casetta non si solleva. Al posto del comignolo c'è un incavo a forma di stella.

  prendi_casa_bambole:
    trigger: {verb: prendi, target: casa_bambole}
    text: È alta quasi quanto te. La lasci dov'è.

  leggi_chiave_cantina:
    trigger: {verb: leggi, target: chiave_cantina}
    text: "Sul cartellino, la grafia della contessa: «Dove il vino dorme più vecchio. Quando scenderai, porta con te tutto ciò che hai scoperto.»"

  # --- Il soffittone e il sottotetto (pericolo) ---
  stendi_asse:
    trigger: {verb: usa, target: asse, with: pavimento_marcio}
    effects:
      - remove: asse
      - place: {item: asse_stesa, room: soffittone}
      - set_flag: asse_posata
    text: >
      Stendi l'asse sul pavimento marcio, da una trave sana all'altra, e la provi con un piede.
      Scricchiola, ma regge. Ora si passa.

  salta_nel_buco:
    trigger: {verb: salta, target: pavimento_marcio}
    effects:
      - set_flag: caduta_in_soffitta
    text: Fai un passo sulle assi marce.

  # --- La lanterna: il petrolio (rimessa) e i fiammiferi (cucina) ---
  riempi_lanterna:
    trigger: {verb: usa, target: tanica, with: lanterna}
    when: {not: {flag: lanterna_piena}}
    otherwise: La lanterna è già piena di petrolio.
    effects:
      - set_flag: lanterna_piena
    text: Sviti il tappo della tanica e versi il petrolio nel serbatoio della lanterna, finché non è pieno.

  accendi_lanterna:
    trigger: {verb: usa, target: fiammiferi, with: lanterna}
    when: {all: [{flag: lanterna_piena}, {not: {flag: lanterna_accesa}}]}
    otherwise: La lanterna è già accesa.
    otherwise_variants:
      - when: {not: {flag: lanterna_piena}}
        text: Sfreghi un fiammifero, ma lo stoppino è secco e il serbatoio vuoto. Non prende.
    effects:
      - set_flag: lanterna_accesa
    text: >
      Sfreghi un fiammifero e lo avvicini allo stoppino. La fiamma prende, trema, poi si alza dritta
      dietro il vetro. La lanterna è accesa.

  # --- L'archivio di famiglia ---
  leggi_faldone:
    trigger: {verb: leggi, target: faldone_1897}
    text: >
      Una lettera del conte al parroco, del novembre 1897: «Mia figlia è partita, e non tornerà. Il
      suo nome non sia più pronunciato in questa casa.» E nel libro paga della servitù, in un
      inchiostro diverso, una riga sola: «Livia, cameriera: aumento di salario, novembre 1897.»

  # --- La stanza dell'orologio, il tetto (pericolo) e la piccionaia ---
  lega_corda:
    trigger:
      - {verb: usa, target: corda, with: lucernario}
      - {verb: usa, target: corda, with: meccanismo}
    effects:
      - remove: corda
      - place: {item: corda_legata, room: stanza_orologio}
      - set_flag: corda_legata
    text: >
      Leghi un capo della corda alla trave sotto il lucernario, con un nodo da marinaio, e lasci
      pendere l'altro fuori, sul tetto. Ora, lassù, qualcosa ti tiene.

  prendi_corda_legata:
    trigger: {verb: prendi, target: corda_legata}
    text: È legata alla trave, e lassù è lei che ti tiene. La lasci dov'è.

  prendi_tubetto:
    trigger:
      - {verb: prendi, target: tubetto}
      - {verb: apri, target: tubetto}
      - {verb: prendi, target: piccioni}
    when: {not: {flag: tubetto_aperto}}
    otherwise: Il tubetto è vuoto. Il piccione ti guarda, offeso.
    effects:
      - give: lettera_notaio
      - set_flag: tubetto_aperto
    text: >
      Il piccione si lascia prendere senza un battito d'ali. Sfili il tubetto dalla zampa e lo apri:
      dentro, arrotolata stretta, una lettera su carta intestata di uno studio notarile di Torino. Era
      per la contessa, ed è arrivata dopo di lei.

  leggi_lettera_notaio:
    trigger: {verb: leggi, target: lettera_notaio}
    text: >
      «Gentilissima contessa, confermo l'appuntamento: sarò a Valdimora il 20 ottobre, coi testimoni,
      per il riconoscimento di vostra nipote, la signorina Irene, figlia della defunta Clara di
      Valdimora, come vostra erede. I documenti che mi avete descritto saranno sufficienti. Con
      ossequio, avv. Bertola.» Chi sapeva del 20 ottobre, sapeva che cosa avrebbe perso.

  # --- La porta della cantina, in cucina: si scende solo con la lanterna accesa ---
  apri_cantina:
    trigger: {verb: apri, target: porta_cantina, with: chiave_cantina}
    when: {all: [{flag: lanterna_accesa}, {has: lanterna}]}
    otherwise: >
      La chiave gira, e la porta si apre su una scala di pietra che sprofonda nel buio pesto. Senza
      una luce non scendi di un passo: richiudi.
    otherwise_variants:
      - when: {has: lanterna}
        text: >
          La chiave gira, e la porta si apre su una scala di pietra che sprofonda nel buio pesto. La
          tua lanterna è spenta, e senza una luce non scendi di un passo: richiudi.
    effects:
      - remove: chiave_cantina
      - set_flag: atto_quattro
    text: >
      La chiave gira con fatica, e la lasci nella serratura. La porta si apre su una scala di pietra
      che scende nel buio; da sotto sale un'aria fredda, che sa di muffa e di vino.
```

- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
# Il secondo atto finisce aprendo la porta della scala di servizio (finale provvisorio: lo toglie
# l'atto 3). Dopo una morte si riprende dall'inizio del secondo atto.
```
diventa
```yaml
# Il terzo atto finisce aprendo la porta della cantina con la lanterna accesa (finale provvisorio:
# lo toglie l'atto 4). Dopo una morte si riprende dall'inizio dell'ultimo atto cominciato.
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
    (In costruzione: per ora i primi due atti.)
```
diventa
```yaml
    (In costruzione: per ora i primi tre atti.)
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
  acts:
    - name: secondo atto
      when: {flag: atto_due}
```
diventa
```yaml
  acts:
    - name: secondo atto
      when: {flag: atto_due}
    - name: terzo atto
      when: {flag: atto_tre}
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
    - when: {flag: atto_tre}
      text: >
        La porta si apre su una scala di legno stretta e ripida, che sale nel buio verso la soffitta.
        Da lassù scende un odore di polvere e di lavanda. «Dove lei dormiva bambina.» Fine del
        secondo atto. (Il terzo è in costruzione.)
```
diventa
```yaml
    - when: {flag: caduta_in_soffitta}
      death: true
      text: >
        Le assi marce cedono con uno schianto. Precipiti tra travi e calcinacci, e il pavimento del
        piano nobile ti viene incontro. Sei morta.
    - when: {all: [{player_in: sottotetto}, {not: {flag: asse_posata}}]}
      death: true
      text: >
        Le assi marce che hai appena attraversato scricchiolano sotto i tuoi piedi, poi cedono con uno
        schianto. Precipiti tra travi e calcinacci, giù fino al piano nobile. Sei morta.
    - when: {all: [{player_in: tetto}, {not: {flag: corda_legata}}]}
      death: true
      text: >
        Fai un passo sulle tegole bagnate, e ti scivolano via da sotto i piedi. Non c'è niente a cui
        aggrapparti. Sei morta.
    - when: {flag: atto_quattro}
      text: >
        Alle tue spalle, Ettore si schiarisce la voce. «Siete sicura di avere tutto, signorina?» Alzi
        la lanterna, e cominci a scendere. Fine del terzo atto. (Il quarto è in costruzione.)
```
- In `data/worlds/valdimora/piano-nobile.yaml`, il blocco
```yaml
      Un pianerottolo spoglio, per la servitù: pareti imbiancate a calce e un odore di cera. Una
      porta stretta chiude la scala di servizio, che sale verso la soffitta. A sud si torna nella
      galleria dei ritratti, a ovest nel guardaroba.
    exits:
```
diventa
```yaml
      Un pianerottolo spoglio, per la servitù: pareti imbiancate a calce e un odore di cera. Una
      porta stretta chiude la scala di servizio, che sale verso la soffitta. A sud si torna nella
      galleria dei ritratti, a ovest nel guardaroba.
    variants:
      - when: {flag: atto_tre}
        text: >
          Un pianerottolo spoglio, per la servitù: pareti imbiancate a calce e un odore di cera. La
          porta della scala di servizio è aperta, e la scala sale verso la soffitta. A sud si torna
          nella galleria dei ritratti, a ovest nel guardaroba.
    exits:
```
- In `data/worlds/valdimora/piano-nobile.yaml`, togliere il blocco
```yaml
  # Provvisoria: nessuno ci entra, perché aprire la scala di servizio chiude il secondo atto. La
  # riscrive l'atto 3, nel file della soffitta.
  pianerottolo_soffitta:
    name: Pianerottolo della soffitta
    description: In cima alla scala di servizio, la soffitta è buia e silenziosa.
    exits:
      giù: {to: pianerottolo_servizio}

```
- In `data/worlds/valdimora/piano-nobile.yaml`, il blocco
```yaml
    description: Una porta stretta di legno grezzo, chiusa a chiave. Dietro, una scala sale verso la soffitta.
    location: pianerottolo_servizio
    scenery: true
```
diventa
```yaml
    description: Una porta stretta di legno grezzo, chiusa a chiave. Dietro, una scala sale verso la soffitta.
    location: pianerottolo_servizio
    scenery: true
    variants:
      - when: {flag: atto_tre}
        text: La porta della scala di servizio, aperta. La chiave è rimasta nella serratura.
```
- In `data/worlds/valdimora/piano-nobile.yaml`, il blocco
```yaml
    text: La chiave gira dura, poi scatta. La lasci nella serratura, e spingi la porta.
```
diventa
```yaml
    text: >
      La chiave gira dura, poi scatta. La lasci nella serratura e spingi la porta: una scala di legno
      stretta e ripida sale nel buio verso la soffitta. Da lassù scende un odore di polvere e di
      lavanda.
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
Lenzuola di lino stese ad asciugare. Una porta ricamate le iniziali «A. V.».
```
diventa
```yaml
Lenzuola di lino stese ad asciugare. Ognuna porta ricamate le iniziali «A. V.».
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
      - {verb: apri, target: porta_cantina, with: chiavetta_carica}
```
diventa
```yaml
      - {verb: apri, target: porta_cantina, with: chiavetta_carica}
      - {verb: apri, target: porta_cantina, with: chiave_clara}
      - {verb: apri, target: porta_clara, with: chiave_cantina}
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
  apri_porta_cantina:
    trigger: {verb: apri, target: porta_cantina}
    text: È sbarrata e chiusa a chiave. Sul quadro delle chiavi di Livia, il gancio «Cantina» è vuoto.
```
diventa
```yaml
  apri_porta_cantina:
    trigger: {verb: apri, target: porta_cantina}
    when: {not: {has: chiave_cantina}}
    otherwise: "Hai la chiave della cantina: usala."
    text: È sbarrata e chiusa a chiave. Sul quadro delle chiavi di Livia, il gancio «Cantina» è vuoto.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
# I personaggi di Valdimora. Dove stanno nel primo atto: spec, sezione 2 (tabella dei personaggi);
# gli spostamenti (moves) arrivano con gli atti successivi.
```
diventa
```yaml
# I personaggi di Valdimora. Dove stanno atto per atto: spec, sezione 2 (tabella dei personaggi), e
# le decisioni di ogni atto (Ferri resta nel biliardo). Gli atti restano veri dopo il loro inizio,
# quindi le varianti di un atto vengono prima di quelle degli atti precedenti.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    location: stanza_maggiordomo
    moves:
      - when: {flag: atto_due}
        room: galleria
```
diventa
```yaml
    location: stanza_maggiordomo
    moves:
      - when: {flag: atto_tre}
        room: cucina
      - when: {flag: atto_due}
        room: galleria
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    location: ufficio_governante
    moves:
      - when: {flag: atto_due}
        room: camera_contessa
```
diventa
```yaml
    location: ufficio_governante
    moves:
      - when: {flag: atto_tre}
        room: camera_livia
      - when: {flag: atto_due}
        room: camera_contessa
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    location: biliardo
    moves:
      - when: {flag: atto_due}
        room: studio_conte
```
diventa
```yaml
    location: biliardo
    moves:
      - when: {flag: atto_tre}
        room: archivio
      - when: {flag: atto_due}
        room: studio_conte
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    location: cappella
    moves:
      - when: {flag: atto_due}
        room: loggia
```
diventa
```yaml
    location: cappella
    moves:
      # Le commissioni del terzo atto: mandata di sotto, ci resta (spec, «Atto 3: decisioni»).
      - when: {flag: agnese_in_cucina}
        room: cucina
      - when: {flag: agnese_in_rimessa}
        room: rimessa
      - when: {flag: atto_tre}
        room: corridoio_servitu
      - when: {flag: atto_due}
        room: loggia
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        text: «Qualunque cosa. La contessa avrebbe voluto così.»
        again: «Qualunque cosa, ve l'ho detto.»
```
diventa
```yaml
        text: «Qualunque cosa. La contessa avrebbe voluto così.»
        variants:
          - when: {flag: atto_tre}
            text: >
              «Se vi serve qualcosa di sotto, chiedete a me: il petrolio per una lanterna, una tisana
              calda… Le scale le conosco a occhi chiusi.»
        again: «Qualunque cosa, ve l'ho detto.»
      petrolio:
        name: petrolio
        gender: m
        aliases: [tanica, tanica di petrolio]
        when: {all: [{flag: atto_tre}, {not: {has: tanica}}, {not: {flag: agnese_in_cucina}}]}
        effects:
          - set_flag: agnese_in_rimessa
        text: >
          «Il petrolio? Ce n'è una tanica in rimessa. Vado io, signorina: voi siete stanca. Vi aspetto
          laggiù.» E scende di corsa le scale.
        variants:
          - when: {player_in: rimessa}
            text: «La tanica è lì, signorina, accanto al muro. Prendetela pure, per me è troppo pesante.»
      tisana:
        name: tisana
        gender: f
        aliases: [camomilla, infuso, qualcosa di caldo, tazza]
        when: {flag: atto_tre}
        effects:
          - set_flag: agnese_in_cucina
        text: >
          «Una tisana? Ma certo, signorina: vado in cucina e ve la preparo. Vi aspetto là, al caldo.»
          Agnese prende la candela e scende.
        variants:
          - when: {player_in: cucina}
            text: >
              «Eccola, bella calda.» Agnese ti porge una tazza fumante, e tu la bevi a piccoli sorsi.
              Sa di camomilla e di miele. «Vi aspetto qui, se vi serve altro.»
      camera:
        name: camera
        gender: f
        aliases: [camera di Agnese, cameretta, porta della camera di Agnese]
        when: {flag: atto_tre}
        text: «La mia cameretta? È tutta in disordine, signorina. Non c'è niente da vedere.»
        again: «Niente da vedere, davvero.»
      luce:
        name: luce
        gender: f
        aliases: [candela, impronte, cera, soffittone]
        when: {flag: atto_tre}
        text: «Una luce in soffitta?» Agnese ride, ma troppo in fretta. «Sarà stato un lampo, signorina. Con questo tempo…»
        again: «Un lampo, ve l'ho detto.»
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1304 passati, 155 saltati).

```bash
git add data/worlds/valdimora/soffitta.yaml data/worlds/valdimora/gioco.yaml data/worlds/valdimora/piano-nobile.yaml data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 3: la soffitta, il filo principale e i pericoli" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: I personaggi nel terzo atto

**Files:**
- Modify: `data/worlds/valdimora/personaggi.yaml` (saluti con le varianti dell'atto 3, argomenti nuovi di Ettore, Livia e Corrado)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: `in_act_three` e i flag del Task 1.
- Produces: argomenti `ettore.lanterna`, `ettore.cantina`, `livia.fotografia`, `livia.clara`, `livia.camera_clara`, `corrado.archivio`, `corrado.clara`; le varianti su `atto_tre`, `lettere_lette`, `livia_confessa`.

- [ ] **Step 1: Test che falliscono**

- In fondo a `tests/test_valdimora.py`:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 16 test (i saluti e gli argomenti del terzo atto non ci sono).

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: ritratto_scoperto}
        text: Ettore guarda il ritratto, poi guarda te. «Ora avete visto», dice soltanto.
```
diventa
```yaml
    greeting_variants:
      - when: {flag: lettere_lette}
        text: >
          Ettore posa l'argenteria e ti guarda a lungo. «Avete letto le sue lettere. Ve lo leggo in
          faccia.» Gli tremano le labbra. «Bentornata a casa, signorina.»
        again: «Signorina.» Ettore ti sorride, e torna alla sua argenteria.
      - when: {flag: atto_tre}
        text: >
          Ettore è in cucina, accanto al focolare, e lucida l'argenteria per tenere occupate le mani.
          «Signorina. Siete salita fin lassù, allora.»
        again: «Signorina.» Ettore non alza gli occhi dall'argenteria.
      - when: {flag: ritratto_scoperto}
        text: Ettore guarda il ritratto, poi guarda te. «Ora avete visto», dice soltanto.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        when: {flag: busta_data}
        text: >
          Ettore distoglie lo sguardo. «Non qui, signorina. Non ancora. La contessa ha voluto che le
          cose le trovaste da voi.»
        variants:
          - when: {flag: ritratto_scoperto}
```
diventa
```yaml
        when: {flag: busta_data}
        text: >
          Ettore distoglie lo sguardo. «Non qui, signorina. Non ancora. La contessa ha voluto che le
          cose le trovaste da voi.»
        variants:
          - when: {flag: lettere_lette}
            text: >
              «Ora sapete. Era vostra nonna, signorina, e vi voleva qui.» Ettore abbassa gli occhi.
              «Perdonatemi se non ve l'ho detto io: le avevo dato la mia parola.»
          - when: {flag: ritratto_scoperto}
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        variants:
          - when: {flag: atto_due}
            text: >
              «La dama di compagnia della contessa. Le leggeva i romanzi, le dava le medicine. Ora sta
              nella loggia, in cima allo scalone: dice che vi aspetta, se avete bisogno.»
```
diventa
```yaml
        variants:
          - when: {flag: atto_tre}
            text: >
              «La dama di compagnia della contessa. Ora sta di sopra, nel corridoio della servitù, e
              si offre di fare commissioni a tutti. Una ragazza servizievole.»
          - when: {flag: atto_due}
            text: >
              «La dama di compagnia della contessa. Le leggeva i romanzi, le dava le medicine. Ora sta
              nella loggia, in cima allo scalone: dice che vi aspetta, se avete bisogno.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        text: >
          «Finché non liberano la strada, qui non arriva nessuno. Nemmeno il notaio, che Livia
          aspettava per il 20.»
        again: «Ci vorranno giorni, signorina. Siamo tutti chiusi qui.»
```
diventa
```yaml
        text: >
          «Finché non liberano la strada, qui non arriva nessuno. Nemmeno il notaio, che Livia
          aspettava per il 20.»
        again: «Ci vorranno giorni, signorina. Siamo tutti chiusi qui.»
      lanterna:
        name: lanterna
        gender: f
        aliases: [lume, petrolio, fiammiferi]
        when: {flag: atto_tre}
        text: >
          «Una lanterna? Ce n'è una vecchia in soffitta, nel sottotetto, se il pavimento regge
          ancora. Il petrolio lo trovate in rimessa, e i fiammiferi qui in cucina.»
        variants:
          - when: {flag: lanterna_accesa}
            text: «Bene. Con quella, laggiù, ci vedrete.»
        again: «Il petrolio in rimessa, signorina, i fiammiferi qui in cucina.»
      cantina:
        name: cantina
        gender: f
        aliases: [porta della cantina, chiave della cantina, vino]
        when: {flag: atto_tre}
        text: >
          «La cantina è chiusa da quest'estate. La chiave la teneva la contessa, e non so dove l'abbia
          messa. Laggiù è buio pesto, signorina: senza un lume non si scende.»
        variants:
          - when: {has: chiave_cantina}
            text: >
              «Quella è la chiave della cantina.» Ettore la guarda, poi guarda te. «Laggiù è buio, e
              si scende più facilmente di quanto si risalga. Siete sicura di avere tutto, signorina?»
        again: «Senza un lume, laggiù, non si scende.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: livia_permette}
        text: Livia è seduta accanto al letto, e guarda la rosa sul comodino. «Grazie», dice soltanto.
```
diventa
```yaml
    greeting_variants:
      - when: {flag: livia_confessa}
        text: >
          Livia è seduta sul letto, con le mani in grembo e gli occhi rossi. «Vi ho detto tutto,
          signorina. Ora lasciatemi sola.»
      - when: {flag: atto_tre}
        text: >
          Livia è seduta sul letto della sua camera, le mani in grembo. Senza il mazzo di chiavi alla
          cintura sembra più piccola. «Anche qui, signorina? In camera mia non c'è niente per voi.»
        again: «Ancora voi.» Livia non si alza dal letto.
      - when: {flag: livia_permette}
        text: Livia è seduta accanto al letto, e guarda la rosa sul comodino. «Grazie», dice soltanto.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        text: «La chiave della scala di servizio la teneva la contessa, non io. Chissà dove l'ha messa.»
        variants:
          - when: {has: chiave_servizio}
```
diventa
```yaml
        text: «La chiave della scala di servizio la teneva la contessa, non io. Chissà dove l'ha messa.»
        variants:
          - when: {flag: atto_tre}
            text: «Siete salita anche quassù. Non vi ferma niente, eh, signorina?»
          - when: {has: chiave_servizio}
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        again: "«Ve l'ho detto: la teneva lei.»"
```
diventa
```yaml
        again: "«Ve l'ho detto: la teneva lei.»"
      fotografia:
        name: fotografia
        gender: f
        aliases: [foto, fotografia di mia madre]
        when: {all: [{flag: atto_tre}, {has: fotografia}]}
        text: «Che cosa tenete in mano?» Livia tende la mano, e la mano trema. «Datemela. Fatemela vedere da vicino.»
        variants:
          - when: {flag: livia_confessa}
            text: «Avete i suoi occhi. Avrei dovuto capirlo il primo giorno.»
        again: «Datemela, vi ho detto.»
      clara:
        name: Clara
        article: none
        gender: f
        aliases: [madre, mamma, mia madre]
        when: {flag: atto_tre}
        text: «Non conosco nessuna Clara.» Ma le mani, in grembo, le tremano.
        variants:
          - when: {flag: livia_confessa}
            text: «Era la ragazza più buona di questa casa. E io l'ho tradita.»
        again: «Vi ho detto che non la conosco.»
      camera_clara:
        name: camera di Clara
        gender: f
        aliases: [camera chiusa, porta in fondo, targhetta, chiave della camera di Clara]
        when: {flag: atto_tre}
        text: «Quella porta è chiusa dal 1897, signorina. Non si apre. Non per voi.»
        variants:
          - when: {flag: camera_clara_aperta}
            text: «L'avete aperta, allora. Trent'anni…» Livia si fa il segno della croce.
          - when: {flag: livia_confessa}
            text: «La chiave ce l'avete. Andate.»
        again: «Non si apre, vi ho detto.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: atto_due}
        text: >
          Corrado è seduto alla scrivania del conte, coi piedi sul piano di mogano.
```
diventa
```yaml
    greeting_variants:
      - when: {flag: lettere_lette}
        text: >
          Corrado ti aspetta sulla soglia dell'archivio, con un foglio ingiallito in mano. «Clara di
          Valdimora, nata nel 1878», legge ad alta voce. «La figlia di cui nessuno parlava.» Ti guarda
          il medaglione, poi la faccia, e non ride più. «Allora siete voi. La nipotina. Godetevela
          finché dura: il notaio non è ancora arrivato, e la strada è lunga.»
        again: «Ancora qui, nipotina? Godetevela, finché dura.»
      - when: {flag: atto_tre}
        text: >
          Corrado è chino su un faldone aperto, in una nuvola di polvere e di fumo. «Le carte di
          famiglia», dice senza alzare gli occhi. «Voglio essere sicuro che il notaio non trovi
          sorprese.»
        again: «Ancora voi? Sto lavorando, signorina.»
      - when: {flag: atto_due}
        text: >
          Corrado è seduto alla scrivania del conte, coi piedi sul piano di mogano.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        again: «Il notaio li pagherà. Parliamo d'altro.»
```
diventa
```yaml
        again: «Il notaio li pagherà. Parliamo d'altro.»
      archivio:
        name: archivio
        gender: m
        aliases: [carte, faldone, faldoni, carte di famiglia, "1897"]
        when: {flag: atto_tre}
        text: >
          «Trecento anni di carte. Cerco quello che non c'è: un altro erede. E finora, niente.» Soffia
          via la polvere da un faldone.
        variants:
          - when: {flag: lettere_lette}
            text: «Ho trovato quello che cercavo. Purtroppo per voi, e per me.»
        again: «Sto cercando, signorina. Lasciatemi lavorare.»
      clara:
        name: Clara
        article: none
        gender: f
        aliases: [madre, mia madre]
        when: {flag: lettere_lette}
        text: >
          «Clara di Valdimora. Una zia che nessuno ha mai nominato, cancellata da tutto, tranne che da
          questo faldone.» Corrado lo chiude di colpo. «E da voi, a quanto pare.»
        again: «Non ne voglio parlare.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {all: [{flag: atto_due}, {flag: medaglione_mostrato}]}
```
diventa
```yaml
    greeting_variants:
      - when: {flag: agnese_in_cucina}
        text: >
          Agnese è in cucina, davanti al focolare, e versa l'acqua bollente in una tazza. «Eccovi,
          signorina. La tisana è quasi pronta.»
        again: «Vi aspetto qui, signorina, se vi serve altro.»
      - when: {all: [{flag: agnese_in_rimessa}, {has: tanica}]}
        text: «Avete la tanica? Bene.» Agnese si pulisce le mani nel grembiule. «Io resto qui ancora un po', signorina.»
      - when: {flag: agnese_in_rimessa}
        text: >
          Agnese è nella rimessa, accanto alla tanica del petrolio. «Eccola, signorina: prendetela
          pure, per me è troppo pesante.»
      - when: {flag: atto_tre}
        text: >
          Agnese è nel corridoio della servitù, davanti alla porta della sua camera, con la candela in
          mano. «Siete salita fin quassù? Qui dormiamo noi della servitù.» Ti sorride. «Se vi serve
          qualcosa di sotto, chiedete a me: scendo io.»
        again: «Eccovi. Se vi serve qualcosa di sotto, chiedete pure.»
      - when: {all: [{flag: atto_due}, {flag: medaglione_mostrato}]}
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1320 passati, 155 saltati).

```bash
git add data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 3: i personaggi" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Il terzo atto col modello vero

**Files:**
- Modify: `app/llm/interpreter.py` (`_TIE_WORDS`, `_places_named`, `_read_what_is_named`, `_named_word_for_word`, `_words_naming`; il salto verso una stanza nominata)
- Test: `tests/test_interpreter.py`, `tests/test_ollama.py`

**Interfaces:**
- Consumes: il mondo dei Task 1 e 2; `parser.names_said`, `parser.words_saying`.
- Produces: nessuna interfaccia pubblica nuova; i casi del terzo atto in `VALDIMORA_CASES` e la costante `ACT_THREE` in `tests/test_ollama.py`.

- [ ] **Step 1: Test che falliscono**

- In `tests/test_ollama.py`, il blocco
```python
    ("balcone", (), ("atto_due",), "lancio uno sguardo verso la valle", lambda a, g: not g.finished),
]  # fmt: skip
```
diventa
```python
    ("balcone", (), ("atto_due",), "lancio uno sguardo verso la valle", lambda a, g: not g.finished),
    # The third act (2026-10-01).
    # Showing the photograph may be asking about it (Livia asks for it) or giving it (she confesses).
    ("camera_livia", ("fotografia",), ACT_THREE, "mostro la fotografia di mia madre a Livia",
     lambda a, g: g.state.item_locations["chiave_clara"] == "inventory" or LIVIA.topics["fotografia"].text in a),
    ("camera_livia", ("fotografia",), ACT_THREE, "porgo la foto alla governante",
     lambda a, g: g.state.item_locations["chiave_clara"] == "inventory"),
    ("camera_livia", (), ACT_THREE, "chi era Clara?", says(LIVIA.topics["clara"].text)),
    ("corridoio_servitu", ("chiave_clara",), ACT_THREE, "apro la camera di Clara con la chiave",
     lambda a, g: "camera_clara_aperta" in g.state.flags),
    ("camera_clara", (), (*ACT_THREE, "camera_clara_aperta"), "frugo nel baule",
     lambda a, g: g.state.item_locations["lettere_clara"] == "inventory" or "Non è chiuso a chiave" in a),
    ("camera_clara", ("lettere_clara",), (*ACT_THREE, "camera_clara_aperta"), "leggo le lettere della contessa",
     lambda a, g: "lettere_lette" in g.state.flags),
    ("camera_clara", (), (*ACT_THREE, "camera_clara_aperta"), "infilo il medaglione nel tetto della casa delle bambole",
     lambda a, g: g.state.item_locations["chiave_cantina"] == "inventory"
     or g.pending == Action(verb="usa", target="medaglione", with_="casa_bambole")),
    ("soffittone", ("asse",), ACT_THREE, "stendo l'asse sopra il pavimento marcio",
     lambda a, g: "asse_posata" in g.state.flags),
    # Nobody dies without asking for it.
    ("soffittone", (), ACT_THREE, "attraverso il pavimento marcio", lambda a, g: not g.finished),
    ("soffittone", (), ACT_THREE, "seguo le impronte nella polvere", lambda a, g: not g.finished and "Non vedi" not in a),
    ("stanza_orologio", (), ACT_THREE, "esco dal lucernario sul tetto", lambda a, g: not g.finished),
    ("sottotetto", (), (*ACT_THREE, "asse_posata"), "prendo la vecchia lanterna",
     lambda a, g: g.state.item_locations["lanterna"] == "inventory"),
    ("rimessa", ("lanterna",), ACT_THREE, "verso il petrolio nella lanterna", lambda a, g: "lanterna_piena" in g.state.flags),
    # Lit, or asked first when the model picked the hearth and the matches are only a guess.
    ("cucina", ("lanterna",), (*ACT_THREE, "lanterna_piena"), "accendo la lanterna con un fiammifero",
     lambda a, g: "lanterna_accesa" in g.state.flags
     or g.pending == Action(verb="usa", target="lanterna", with_="fiammiferi")),
    ("cucina", ("lanterna", "chiave_cantina"), (*ACT_THREE, "lanterna_piena", "lanterna_accesa"),
     "uso la chiave della cantina sulla porta", lambda a, g: "atto_quattro" in g.state.flags),
    ("corridoio_servitu", (), ACT_THREE, "Agnese, mi faresti una camomilla?", lambda a, g: "agnese_in_cucina" in g.state.flags),
    ("corridoio_servitu", (), ACT_THREE, "potresti andare a prendermi del petrolio?",
     lambda a, g: "agnese_in_rimessa" in g.state.flags),
    ("camera_agnese", (), (*ACT_THREE, "agnese_in_cucina"), "guardo sotto il materasso",
     lambda a, g: g.state.item_locations["lettera_giugno"] == "inventory"),
    # Tied, or asked first when the model picked the clockwork and the skylight is only a guess.
    ("stanza_orologio", ("corda",), ACT_THREE, "lego la corda alla trave del lucernario",
     lambda a, g: "corda_legata" in g.state.flags
     or g.pending == Action(verb="usa", target="corda", with_="lucernario")),
    ("piccionaia", (), (*ACT_THREE, "corda_legata"), "sfilo il tubetto dalla zampa del piccione",
     lambda a, g: g.state.item_locations["lettera_notaio"] == "inventory"),
    ("archivio", (), ACT_THREE, "sfoglio le carte del 1897",
     says(VALDIMORA_RULE["leggi_faldone"], VALDIMORA.items["faldone_1897"].description)),
    ("cucina", (), ACT_THREE, "Ettore, dove trovo una lanterna?", says(ETTORE.topics["lanterna"].text)),
    ("archivio", (), (*ACT_THREE, "lettere_lette"), "che cosa sapete di mia madre, Corrado?",
     says(VALDIMORA.characters["corrado"].topics["clara"].text)),
]  # fmt: skip
```
- In `tests/test_ollama.py`, il blocco
```python
LIVIA = VALDIMORA.characters["livia"]
```
diventa
```python
LIVIA = VALDIMORA.characters["livia"]
ACT_THREE = ("atto_due", "busta_data", "atto_tre")
```
- In fondo a `tests/test_interpreter.py`:
```python
# --- Found playing the third act of Valdimora ----------------------------------------------------------


def test_tying_is_no_reading(valdimora):
    # «lego la corda alla trave del lucernario»: «lego» is nearly «leggo», and the model answered «leggi».
    reply = {"verbo": "leggi", "bersaglio": "corda da bucato", "con": "lucernario"}
    in_reach = valdimora_items(valdimora, "corda", "lucernario", "meccanismo")

    action = interpret(FakeLLMClient(json_replies=[reply]), "lego la corda alla trave del lucernario", in_reach)

    assert action == Action(verb="usa", target="corda", with_="lucernario")


def test_examining_something_unnamed_is_examining_the_only_thing_named(valdimora):
    # «guardo sotto il materasso»: the model looked at the candle stub.
    reply = {"verbo": "guarda", "bersaglio": "mozzicone di candela", "con": "nessuno"}
    in_reach = valdimora_items(valdimora, "letto_agnese", "mozzicone", "scarpe")

    action = interpret(FakeLLMClient(json_replies=[reply]), "guardo sotto il materasso", in_reach)

    assert action == Action(verb="esamina", target="letto_agnese")


def test_reading_what_the_sentence_names_by_its_very_words(valdimora):
    # «leggo le lettere della contessa»: the model read the countess's letter to Irene, named only by
    # another ending, while the sentence names the letters to Clara word for word.
    reply = {"verbo": "leggi", "bersaglio": "lettera della contessa", "con": "nessuno"}
    in_reach = valdimora_items(valdimora, "lettera", "medaglione", "lettere_clara")

    action = interpret(FakeLLMClient(json_replies=[reply]), "leggo le lettere della contessa", in_reach)

    assert action == Action(verb="leggi", target="lettere_clara")


def test_a_typo_is_not_another_item(valdimora):
    # The very words of another item win only where they name the same thing: «ciave» is the key.
    reply = {"verbo": "esamina", "bersaglio": "chiave della cantina", "con": "nessuno"}
    in_reach = valdimora_items(valdimora, "chiave_cantina", "lanterna")

    action = interpret(FakeLLMClient(json_replies=[reply]), "esamino la ciave e la lanterna", in_reach)

    assert action == Action(verb="esamina", target="chiave_cantina")


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("esco dal lucernario sul tetto", Action(verb="vai", direction="su")),
        ("salto dal lucernario sul tetto", Action(verb="salta", target="lucernario")),
    ],
    ids=["out on the roof", "a jump word: a jump"],
)
def test_a_jump_toward_a_room_named_is_a_move(valdimora, sentence, expected):
    # «esco dal lucernario sul tetto»: the model heard a jump into the skylight.
    reply = {"verbo": "salta", "bersaglio": "lucernario", "con": "nessuno"}
    in_reach = valdimora_items(valdimora, "lucernario", "meccanismo")
    exits = [(Direction.NORTH, valdimora.rooms["soffittone"]), (Direction.UP, valdimora.rooms["tetto"])]

    assert interpret(FakeLLMClient(json_replies=[reply]), sentence, in_reach, exits) == expected
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 4 test (`test_tying_is_no_reading`, `test_examining_something_unnamed_is_examining_the_only_thing_named`, `test_reading_what_the_sentence_names_by_its_very_words`, `test_a_jump_toward_a_room_named_is_a_move[out on the roof]`); i casi di guardia passano già.

- [ ] **Step 3: Implementazione**

- In `app/llm/interpreter.py`, il blocco
```python
    topics_named,
    words_of,
)
from app.llm.client
```
diventa
```python
    topics_named,
    words_of,
    words_saying,
)
from app.llm.client
```
- In `app/llm/interpreter.py`, il blocco
```python
# "lancio uno sguardo verso la valle", "getto un'occhiata nel pozzo": with a jump word, a look.
_GLANCE_WORDS = frozenset({"sguardo", "sguardi", "occhiata", "occhiate", "occhiatina", "occhio", "occhi"})
```
diventa
```python
# "lancio uno sguardo verso la valle", "getto un'occhiata nel pozzo": with a jump word, a look.
_GLANCE_WORDS = frozenset({"sguardo", "sguardi", "occhiata", "occhiate", "occhiatina", "occhio", "occhi"})
# "lego la corda alla trave": tying, which the model may take for reading ("lego" is nearly "leggo").
_TIE_WORDS = frozenset({"lego", "leghi", "lega", "legare", "legala", "legarla", "annodo", "annoda", "annodare"})
```
- In `app/llm/interpreter.py`, il blocco
```python
        said = _directions_said(words)
        if said and not JUMP_WORDS.intersection(words):
            # "salgo sul sasso": the model heard a jump in "salgo", and climbing is a move
            return _checked_move(Action(verb=Command.GO, direction=min(said)), words, exits)
```
diventa
```python
        said = _directions_said(words)
        places = _places_named(words, exits)
        if (said or len(places) == 1) and not JUMP_WORDS.intersection(words):
            # "salgo sul sasso": the model heard a jump in "salgo", and climbing is a move; so is going
            # out to the one place the sentence names ("esco dal lucernario sul tetto")
            return _checked_move(Action(verb=Command.GO, direction=min(said) if said else places[0]), words, exits)
```
- In `app/llm/interpreter.py`, il blocco
```python
    action = _read_what_is_named(action, words, in_reach)
    things = {
```
diventa
```python
    if action.verb is Verb.READ and _TIE_WORDS.intersection(words):
        action = Action(verb=Verb.USE, target=action.target, with_=action.with_)
    action = _read_what_is_named(action, words, in_reach)
    things = {
```
- In `app/llm/interpreter.py`, il blocco
```python
def _read_what_is_named(action: Action, words: list[str], in_reach: Sequence[Item]) -> Action:
    """Reading and examining have no tool: when the model picked the wrong item and put the one the
    sentence names as the tool ("leggo il biglietto della contessa"), that one is what is read."""
    if action.verb not in (Verb.READ, Verb.EXAMINE) or action.with_ is None:
        return action
    items = {item.id: item for item in in_reach}
    target = action.target
    if target in items and not is_named(items[target], words) and action.with_ in items and is_named(items[action.with_], words):
        target = action.with_
    return Action(verb=action.verb, target=target)
```
diventa
```python
def _read_what_is_named(action: Action, words: list[str], in_reach: Sequence[Item]) -> Action:
    """Reading and examining have no tool, and what the sentence names is what is read or examined: the
    tool, when the model picked the wrong item and put the one named as the tool ("leggo il biglietto
    della contessa"); the only item named, when the model examined one the sentence doesn't name
    ("guardo sotto il materasso"); the only item named by its very words, when the model's is named by
    the same words only with another ending ("leggo le lettere della contessa" is no "lettera")."""
    if action.verb not in (Verb.READ, Verb.EXAMINE):
        return action
    items = {item.id: item for item in in_reach}
    target = action.target
    if target in items and not is_named(items[target], words):
        named = [item.id for item in in_reach if is_named(item, words)]
        if action.with_ in items and is_named(items[action.with_], words):
            target = action.with_
        elif action.verb is Verb.EXAMINE and len(named) == 1:
            target = named[0]
    elif target in items and not _named_word_for_word(items[target], words):
        same_words = _words_naming(items[target], words)
        exact = [
            item.id
            for item in in_reach
            if item.id != target and _named_word_for_word(item, words) and _words_naming(item, words) & same_words
        ]
        if len(exact) == 1:
            target = exact[0]
    return Action(verb=action.verb, target=target)


def _named_word_for_word(item: Item, words: list[str]) -> bool:
    """Whether the words say a name of the item without changing a letter."""
    return any(set(name) <= set(words) for name in names_said(item, words))


def _words_naming(item: Item, words: list[str]) -> set[str]:
    """The words that name the item, at least nearly."""
    return {word for name in names_said(item, words) for word in words_saying(name, words)}
```
- In `app/llm/interpreter.py`, il blocco
```python
    said = _directions_said(words)
    places = [room for _, room in exits if room is not None and significant_words(room.name) in names_said(room, words)]
    if not (said or places) and gesture_said(words) is Gesture.FAREWELL:
```
diventa
```python
    said = _directions_said(words)
    places = _places_named(words, exits)
    if not (said or places) and gesture_said(words) is Gesture.FAREWELL:
```
- In `app/llm/interpreter.py`, il blocco
```python
def _directions_said(words: list[str]) -> set[Direction]:
```
diventa
```python
def _places_named(words: list[str], exits: Sequence[tuple[Direction, Room | None]]) -> list[Direction]:
    """The exits whose rooms the words name by their own name, not only by what is there."""
    return [
        direction
        for direction, room in exits
        if room is not None and significant_words(room.name) in names_said(room, words)
    ]


def _directions_said(words: list[str]) -> set[Direction]:
```

- [ ] **Step 4: Verificare**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1326 passati, 178 saltati).

- [ ] **Step 5: Il modello vero, prima le frasi del terzo atto, poi tutto**

Run (Ollama acceso): `OLLAMA_TESTS=1 .venv/Scripts/python -m pytest tests/test_ollama.py -v -s -p no:cacheprovider -k "camera_livia or corridoio_servitu or camera_clara or soffittone or stanza_orologio or sottotetto or (rimessa and lanterna) or (cucina and (lanterna or cantina)) or camera_agnese or piccionaia or archivio or (cucina and Ettore)"`
Expected: 23 passati (~5 min).

Run: `OLLAMA_TESTS=1 .venv/Scripts/python -m pytest tests/test_ollama.py -v -s -p no:cacheprovider`, in background con l'uscita in un file.
Expected: 171 passati e 7 xfailed (~28 min). Il modello non è del tutto deterministico: una frase che cambia tra un giro e l'altro si rigioca da sola prima di concludere.

- [ ] **Step 6: Commit**

```bash
git add app/llm/interpreter.py tests/test_interpreter.py tests/test_ollama.py
git commit -m "Valdimora, atto 3: le frasi libere col modello vero" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: CLAUDE.md e verifica finale

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md**

- In `CLAUDE.md`, il blocco
```markdown
      lo sveglia; chi mostra il medaglione già nel primo atto, di sopra, non sente «Ce l'avete fatta!».

## Decisioni ancora aperte
```
diventa
```markdown
      lo sveglia; chi mostra il medaglione già nel primo atto, di sopra, non sente «Ce l'avete fatta!».
- **Valdimora, atto 3** (2026-10-01, branch `feature/valdimora-atto-3`; decisioni nella spec,
  «Atto 3: decisioni prese al momento di costruirlo»; piano in
  `docs/superpowers/plans/2026-10-01-valdimora-atto-3.md`): la soffitta in
  `data/worlds/valdimora/soffitta.yaml` (12 stanze), nel menu con un finale provvisorio sul flag
  `atto_quattro` (la porta della cantina aperta con la lanterna accesa). Il secondo `acts`, «terzo
  atto», comincia aprendo la scala di servizio. Livia confessa davanti alla fotografia (solo con
  «dai»), le lettere «a mia figlia Clara» dicono a Irene che la contessa era sua nonna e Corrado se
  ne accorge, la casa delle bambole dà la chiave della cantina; l'asse sul pavimento marcio porta
  alla lanterna, da riempire col petrolio della rimessa e accendere coi fiammiferi della cucina.
  Facoltativi: Agnese mandata di sotto (il petrolio o una tisana) ci resta, e la sua camera resta
  aperta, con la prova 3; la corda legata al lucernario porta sul tetto, alla lettera del notaio.
  Tre morti: nel sottotetto senza l'asse, nel buco del pavimento, sul tetto senza la corda;
  entrando, il gioco mostra la stanza e poi il finale. Ferri resta nel biliardo; la luce sotto il
  tetto vista nel primo atto era Agnese.
  - Col modello vero, 23 frasi del terzo atto: 18 al primo giro. Le altre hanno mostrato difetti
    generali, corretti nell'interprete (il prompt non cambia): «lego» e «annodo» non sono leggere
    («lego» è quasi «leggo»); esaminare qualcosa che la frase non nomina diventa esaminare l'unica
    cosa che nomina («guardo sotto il materasso»); per leggere ed esaminare vince l'oggetto nominato
    con le parole esatte su quello nominato solo con un'altra desinenza («leggo le lettere della
    contessa» non è la lettera della contessa); un salto senza parola da salto che nomina una
    stanza tra le uscite è uno spostamento («esco dal lucernario sul tetto»: senza la corda, il
    gioco chiede prima). E l'alias «camera di Clara» sulla sua porta.

## Decisioni ancora aperte
```
- In `CLAUDE.md`, il blocco
```markdown
    `tests/test_ollama.py` (oggi 148 su 155, ~1360 s: i 36 casi di prima, gli 8 dei pericoli, i 17
    del primo atto di Valdimora e le 20 frasi dei dialoghi tutti, 28 delle 29 frasi del secondo atto
    e 39 delle 45 frasi trovate giocando; le altre 7 sono limiti noti, e «infilo il medaglione nella
    cornice» a volte passa).
```
diventa
```markdown
    `tests/test_ollama.py` (oggi 171 su 178, ~1700 s: i 36 casi di prima, gli 8 dei pericoli, i 17
    del primo atto di Valdimora, le 20 frasi dei dialoghi e le 23 del terzo atto tutti, 28 delle 29
    frasi del secondo atto e 39 delle 45 frasi trovate giocando; le altre 7 sono limiti noti, e
    «infilo il medaglione nella cornice» a volte passa).
```

- [ ] **Step 2: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1326 passati, 178 saltati).

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: Valdimora, atto 3" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
