# La Stella di Valdimora, atto 2: il piano nobile — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dall'atrio si sale al piano nobile e il secondo atto si gioca fino alla porta della scala di servizio, con il ritratto di Clara (rivelazione 2), la rosa bianca per Livia, il carillon, il filo facoltativo del flacone (prova 2), il pericolo del balcone con la ripresa dall'inizio dell'atto, i personaggi spostati di sopra coi loro testi nuovi, e un finale provvisorio «Fine del secondo atto».

**Architecture:** quasi tutto è dati: un file nuovo, `data/worlds/valdimora/piano-nobile.yaml` (13 stanze, gli oggetti e le regole del secondo atto, più la stanza provvisoria in cima alla scala di servizio), e ritocchi a `gioco.yaml` (il primo atto `acts`, il finale di morte, il finale provvisorio), `pianterreno.yaml` e `personaggi.yaml` (`moves`, varianti, argomenti). Il motore non cambia: atti, morti, ripresa, spostamenti e varianti ci sono già. Alla fine una giocata col modello vero.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, pytest; Ollama con qwen2.5:3b per i test col modello vero.

**Spec:** `docs/superpowers/specs/2026-09-29-valdimora-design.md` — sezioni 2 (atti e personaggi), 3 (piantina: primo piano), 4 (enigmi: atto 2, con le «decisioni prese al momento di costruirlo») e 6 (costruzione e prove).

## Global Constraints

- Branch: `feature/valdimora-atto-2` (già creato da `main`; contiene la spec aggiornata e, in un commit a parte, questo piano).
- Nessuna dipendenza nuova. Comandi con `.venv/Scripts/python` (Git Bash).
- Codice e identificatori in inglese; testi, commit e documentazione in italiano.
- **Il prompt dell'LLM non cambia**, e Valdimora non ha `game.examples`: solo se la giocata col modello vero (Task 5) ne mostra il bisogno, e allora tutto `tests/test_ollama.py` va rigiocato.
- **Testi**: Irene al femminile («sei salita»); i domestici, il dottore, Corrado e Agnese le danno del **voi** («signorina»); la contessa, nei biglietti, le dà del **tu**. Registro del 1927. Ogni descrizione di stanza nomina le stanze vicine col loro nome; ogni cosa nominata in una descrizione di stanza è un arredo esaminabile; un indizio che manda a fare qualcosa ha una variante per quando è fatto. Nessun gesto e nessun argomento nuovo ha effetti; nessuno rivela i segreti degli atti 3 e 4.
- I testi scritti in questo piano sono quelli da usare, già provati su una copia del mondo (vedi «Come è stato verificato»): l'utente li rilegge qui e nella PR.
- **Alias**: il riconoscimento dei nomi tollera i refusi («siete» è quasi «sete», «andate» quasi «annate»), quindi niente alias di una parola sola che somigli a parole comuni. Un testo YAML su una riga con «: » va tra virgolette doppie.
- Mai nei commit: `run.bat`, `run_log.bat`, `test_llm.txt`. Aggiungere i file uno per uno.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Le modifiche ai file esistenti si fanno con Edit, sostituendo esattamente il blocco indicato; i file nuovi con Write. Nessun testo di questo piano contiene backslash.

## Decisioni prese nel piano (la spec non le copriva)

1. **Le chiavi usate restano nella serratura** (Task 1): la chiave dello scalone, quella della credenza e la chiavetta dell'armadietto, una volta usate, spariscono dall'inventario («la lasci nella toppa»); lo stesso per la chiave della scala di servizio. Così in tasca non si accumulano chiavi: meno «Quale intendi», e l'interprete non deve scegliere fra tre «chiave». La chiavetta dell'armadietto e la chiavetta di carica restano due oggetti con l'alias «chiavetta»: se le hai entrambe, il gioco chiede quale (test).
2. **Il secondo atto è il primo `acts`**: `game.acts` ha «secondo atto» su `atto_due`; il salvataggio automatico scatta quando si apre lo scalone, e dopo la morte del balcone «riprendi» riporta lì. Il terzo atto entrerà col suo branch.
3. **La rosa si può cogliere già nel primo atto** (forbici e serra ci sono), ma Livia la accetta solo dall'atto 2, nella camera della contessa; prima: «Tenetela voi». La rosa bianca e il rosaio hanno tutti e due l'alias «rosa»: vale quello a portata, e nella serra con la rosa in mano il gioco chiede quale (così si chiude il difetto rimandato dell'alias del rosaio).
4. **Il cilindro e la chiave della scala di servizio portano il loro biglietto** nella descrizione («Suonala per me, come faceva lei», «Dove lei dormiva bambina»): niente altri oggetti chiamati «biglietto», che nel primo atto sono già tre.
5. **Il carillon suona la ninna nanna che Clara cantava a Irene**: è il momento emotivo dell'atto, insieme al ritratto riconosciuto con la fotografia.
6. **Il pericolo del balcone**: `prendi vaso` (finché non l'hai agganciato col bastone), `spingi balaustra`, `salta balaustra` uccidono; `tira vaso` e `esamina balaustra` avvertono. Dopo averlo agganciato, prendere il vaso è innocuo.
7. **Ferri e la prova 2**: se chiedi al dottore delle medicine col flacone in mano, riconosce la digitale della contessa e dice che l'aveva portata piena una settimana prima (variante dell'argomento `medicine`, nessun effetto).
8. **«vai sullo scalone»** (difetto rimandato): la loggia ha l'alias «scalone», e l'atrio, dopo l'apertura, nomina «la loggia del piano nobile», così l'uscita è nota e il parser la capisce. Limite accettato: nella loggia, «vado nel salone» da solo (i saloni sono due) può rispondere «Sei già qui.», perché «salone» è quasi «scalone».
9. **Le partite salvate nel browser durante il primo atto ricominciano una volta** («Il mondo è cambiato»): ci sono oggetti nuovi. Succedeva anche con l'atto 1.

## Come è stato verificato, prima di scriverlo

I dati di questo piano (il file del piano nobile e ogni modifica ai file esistenti) sono stati applicati a una copia di Valdimora e giocati: la soluzione del primo e del secondo atto, il filo facoltativo, le tre morti con la ripresa, gli ordini sbagliati, i dialoghi, l'esame di ogni arredo. Poi la suite di oggi è girata sulla copia: l'unico test che cambia è quello del primo atto (Task 2), che oggi finisce con lo scalone. Il controllo ha trovato e fatto togliere alias pericolosi («sete», «annate», «cera», «cappelli», «vuoto», «scala» sulla porta).

## Review Focus

1. **Le cose fatte nell'ordine sbagliato** nel piano nobile: il medaglione nella cornice col quadro ancora coperto, la chiavetta nel carillon senza cilindro, il boudoir senza la rosa, la porta di servizio senza chiave, la rosa senza forbici: ognuna dà un indizio e lascia lo stato com'era — test nel Task 2 (`test_act_two_in_the_wrong_order_gives_hints`).
2. **Le morti e la ripresa**: ognuno dei tre modi di cadere dal balcone uccide, e «riprendi» riporta all'inizio del secondo atto nell'atrio con la porta aperta; dopo aver agganciato il vaso, prenderlo non uccide — test nel Task 3.
3. **Due oggetti con lo stesso alias a portata**: le due chiavette, la rosa e il rosaio nella serra — test nel Task 2.
4. **I personaggi al piano di sopra**: nessun testo del primo atto che parli del posto sbagliato (il congedo di Agnese accanto alla bara), e le loro domande nuove — test nel Task 4.
5. **Frasi libere per gli enigmi nuovi** («tolgo il drappo dal quadro», «taglio una rosa», «carico il carillon con la chiavetta») e per il pericolo («guardo giù dal balcone» non deve uccidere) — Task 5, col modello vero.

---

### Task 1: Le chiavi usate restano nella serratura, e «fotografia di mia madre»

**Files:**
- Modify: `data/worlds/valdimora/pianterreno.yaml` (regole `apri_scalone`, `apri_credenza`, `apri_armadietto`; alias della fotografia)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Produces: dopo `apri_scalone`, `apri_credenza`, `apri_armadietto` la chiave usata ha `item_locations[...] is None`. L'alias «fotografia di mia madre» della fotografia.

- [ ] **Step 1: Test che falliscono**

In fondo a `tests/test_valdimora.py`:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py -q -p no:cacheprovider`
Expected: FAIL — le chiavi sono ancora in inventario; la frase della fotografia dà «Non ho capito.».

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
    aliases: [fotografia, foto]
```
diventa
```yaml
    aliases: [fotografia, foto, fotografia di mia madre, foto di mia madre]
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
    effects:
      - set_flag: atto_due
    text: >
      La chiave gira con un rumore secco. La porta si apre sullo scalone buio, che sale verso il
      piano nobile.
```
diventa
```yaml
    effects:
      - remove: chiave_scalone
      - set_flag: atto_due
    text: >
      La chiave gira con un rumore secco, e la lasci nella toppa. La porta si apre sullo scalone
      buio, che sale verso il piano nobile.
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
    effects:
      - give: grappa
      - set_flag: credenza_aperta
    text: >
      La chiavina gira senza fatica. Tra i bicchieri buoni c'è una bottiglia di grappa ancora
      sigillata. La prendi.
```
diventa
```yaml
    effects:
      - remove: chiave_credenza
      - give: grappa
      - set_flag: credenza_aperta
    text: >
      La chiavina gira senza fatica, e la lasci nella serratura. Tra i bicchieri buoni c'è una
      bottiglia di grappa ancora sigillata. La prendi.
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
    effects:
      - give: registro
      - set_flag: armadietto_aperto
    text: >
      Lo sportello si apre con un cigolio. Bende, sciroppi, flaconi e, sul ripiano più basso, un
      quaderno nero: il registro delle medicine. Lo prendi.
```
diventa
```yaml
    effects:
      - remove: chiavetta
      - give: registro
      - set_flag: armadietto_aperto
    text: >
      La chiavetta gira, e la lasci nella serratura. Lo sportello si apre con un cigolio. Bende,
      sciroppi, flaconi e, sul ripiano più basso, un quaderno nero: il registro delle medicine. Lo
      prendi.
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde.

```bash
git add data/worlds/valdimora/pianterreno.yaml tests/test_valdimora.py
git commit -m "Valdimora: le chiavi usate restano nella serratura, e «fotografia di mia madre»" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Il piano nobile e il filo principale

**Files:**
- Create: `data/worlds/valdimora/piano-nobile.yaml`
- Modify: `data/worlds/valdimora/gioco.yaml` (commento, `summary`, `acts`, finale provvisorio), `data/worlds/valdimora/pianterreno.yaml` (via la Loggia provvisoria; variante dell'atrio; `chiave_sbagliata`), `data/worlds/valdimora/personaggi.yaml` (`moves` di Ettore, Livia, Corrado, Agnese)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: la chiave dello scalone che resta nella serratura (Task 1).
- Produces: stanze `loggia`, `salone_feste`, `balcone`, `salottino_verde`, `camera_contessa`, `boudoir`, `guardaroba`, `galleria`, `pianerottolo_servizio`, `salone_musica`, `biblioteca`, `studio_conte`, `camera_corrado`, `pianerottolo_soffitta` (provvisoria); oggetti `ritratto`, `drappo`, `cilindro`, `rosa_bianca`, `chiavetta_carica`, `carillon`, `chiave_servizio`, `porta_scala_servizio`, `vaso`, `balaustra` e gli arredi; flag `ritratto_scoperto`, `cornice_aperta`, `rosa_colta`, `livia_permette`, `portagioie_aperto`, `cilindro_messo`, `carillon_suonato`, `atto_tre`. Nei test, le costanti `TO_THE_SERVICE_STAIRS` e l'aiuto `in_act_two(valdimora, room, *flags, carried=())`.

- [ ] **Step 1: Test che falliscono**

In `tests/test_valdimora.py`, `test_the_first_act_can_be_played_to_its_end` finisce così (le prime righe restano):
```python
    assert "Per Livia" in answers[14]
    assert "cerca chi ti somiglia" in answers[15]
    assert "Non fatemene pentire" in answers[18]
    # The staircase opens the second act: its state is kept, to go on from here after a death.
    assert "la lasci nella toppa" in answers[-1]
    assert not game.finished and game.state.act == 1 and game.state.checkpoint is not None
```
(al posto delle due righe con «Fine del primo atto» e `game.finished and not game.state.lost`); nella docstring del file, «atto 1 (il pianterreno)» diventa «atti 1 e 2 (il pianterreno e il piano nobile)». In fondo al file:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py -q -p no:cacheprovider`
Expected: FAIL — lo scalone chiude ancora la partita, e le stanze e gli oggetti del piano nobile non esistono.

- [ ] **Step 3: `data/worlds/valdimora/piano-nobile.yaml`**

Crearlo con Write:
```yaml
# Il piano nobile di Valdimora (primo piano): stanze, oggetti e regole del secondo atto.
# Spec: docs/superpowers/specs/2026-09-29-valdimora-design.md, sezioni 3 e 4 (atto 2).
# Il rosaio della serra e le forbici stanno al pianterreno; la regola della rosa bianca è qui.

rooms:
  loggia:
    name: Loggia dello scalone
    aliases: [loggia, scalone]
    description: >
      In cima allo scalone si apre la loggia del piano nobile: un colonnato di pietra grigia, un
      pavimento di marmo che rimbomba a ogni passo, due candelabri di ferro spenti. Fa freddo. A
      nord, oltre un arco, la galleria dei ritratti; a ovest il salone delle feste, a est il salone
      della musica. Lo scalone scende all'atrio.
    exits:
      giù: {to: atrio}
      nord: {to: galleria}
      ovest: {to: salone_feste}
      est: {to: salone_musica}

  salone_feste:
    name: Salone delle feste
    aliases: [sala delle feste]
    description: >
      Un salone immenso, fatto per cento invitati e vuoto da anni. I lampadari sono chiusi in sacchi
      di tela, e le sedie dorate stanno in fila tutt'intorno, come per una festa che non comincia
      mai. A sud, una portafinestra dà sul balcone; a nord il salottino verde, a est si torna nella
      loggia.
    exits:
      est: {to: loggia}
      sud: {to: balcone}
      nord: {to: salottino_verde}

  balcone:
    name: Balcone
    description: >
      Un balcone di pietra sospeso sulla valle, battuto dal vento e dalla pioggia. La balaustra è
      crepata in più punti, e in un angolo ne manca un pezzo: meglio non appoggiarcisi. Sull'orlo
      esterno, in bilico sopra il vuoto, c'è un vaso di gerani secchi. A nord si rientra nel salone
      delle feste.
    exits:
      nord: {to: salone_feste}

  salottino_verde:
    name: Salottino verde
    aliases: [salottino]
    description: >
      Un salottino tappezzato di seta verde, piccolo e caldo di tappeti. Su un tavolino da gioco è
      rimasto un solitario a metà, le carte in fila come le ha lasciate la contessa. A nord la camera
      della contessa, a est la galleria dei ritratti, a sud il salone delle feste.
    exits:
      sud: {to: salone_feste}
      nord: {to: camera_contessa}
      est: {to: galleria}

  camera_contessa:
    name: Camera della contessa
    description: >
      La camera della contessa: un letto a baldacchino rifatto con cura, le tende tirate, un odore di
      lavanda e di medicine. Sul comodino, un vasetto d'argento vuoto. Accanto al letto pende il
      cordone di seta del campanello. A ovest una porta bassa dà sul boudoir; a est il guardaroba, a
      sud il salottino verde.
    variants:
      - when: {flag: livia_permette}
        text: >
          La camera della contessa: un letto a baldacchino rifatto con cura, le tende tirate, un
          odore di lavanda e di medicine. Sul comodino, nel vasetto d'argento, la rosa bianca che hai
          portato dalla serra. Accanto al letto pende il cordone di seta del campanello. A ovest la
          porta del boudoir è aperta; a est il guardaroba, a sud il salottino verde.
    exits:
      sud: {to: salottino_verde}
      est: {to: guardaroba}
      ovest:
        to: boudoir
        when: {flag: livia_permette}
        otherwise: >
          Livia si alza e si mette davanti alla porta. «Il boudoir no, signorina. Lì dentro la
          contessa non voleva nessuno.»

  boudoir:
    name: Boudoir
    description: >
      Un boudoir minuscolo, tutto merletti e velluti, che sa ancora di cipria. Sulla toeletta, tra
      spazzole d'argento e boccette di profumo, c'è un portagioie di legno intarsiato. A est si torna
      nella camera della contessa.
    exits:
      est: {to: camera_contessa}

  guardaroba:
    name: Guardaroba
    description: >
      Un corridoio stretto, foderato di armadi a muro. Dietro le ante socchiuse, gli abiti della
      contessa: sete scure, una pelliccia, cappelli nelle loro scatole rotonde. A ovest la camera
      della contessa; a est una porticina dà sul pianerottolo di servizio.
    exits:
      ovest: {to: camera_contessa}
      est: {to: pianerottolo_servizio}

  galleria:
    name: Galleria dei ritratti
    aliases: [galleria]
    description: >
      Una galleria lunga e stretta, fredda come una chiesa. Alle pareti, i ritratti degli antenati
      di Valdimora: dame incipriate, cavalieri, un vescovo. Uno solo dei quadri è coperto da un
      drappo di velluto nero. A sud la loggia, a ovest il salottino verde, a est la biblioteca; a
      nord la galleria finisce sul pianerottolo di servizio.
    variants:
      - when: {flag: ritratto_scoperto}
        text: >
          Una galleria lunga e stretta, fredda come una chiesa. Alle pareti, i ritratti degli
          antenati di Valdimora: dame incipriate, cavalieri, un vescovo. Il drappo di velluto nero
          giace a terra, sotto il ritratto di una ragazza vestita di bianco. A sud la loggia, a ovest
          il salottino verde, a est la biblioteca; a nord la galleria finisce sul pianerottolo di
          servizio.
    exits:
      sud: {to: loggia}
      ovest: {to: salottino_verde}
      est: {to: biblioteca}
      nord: {to: pianerottolo_servizio}

  pianerottolo_servizio:
    name: Pianerottolo di servizio
    aliases: [pianerottolo]
    description: >
      Un pianerottolo spoglio, per la servitù: pareti imbiancate a calce e un odore di cera. Una
      porta stretta chiude la scala di servizio, che sale verso la soffitta. A sud si torna nella
      galleria dei ritratti, a ovest nel guardaroba.
    exits:
      sud: {to: galleria}
      ovest: {to: guardaroba}
      su:
        to: pianerottolo_soffitta
        when: {flag: atto_tre}
        otherwise: La porta della scala di servizio è chiusa a chiave.

  salone_musica:
    name: Salone della musica
    aliases: [sala della musica]
    description: >
      Un salone chiaro, con un'arpa senza corde in un angolo e file di poltroncine davanti a un
      piccolo palco. Su un tavolino rotondo, sotto una campana di vetro, c'è un carillon d'argento. A
      ovest la loggia, a nord la biblioteca.
    exits:
      ovest: {to: loggia}
      nord: {to: biblioteca}

  biblioteca:
    name: Biblioteca
    description: >
      Una biblioteca a due piani, con un ballatoio che corre lungo gli scaffali e una scala di legno
      su ruote. Libri in latino, atlanti, annate di giornali rilegate in pelle. Su uno scrittoio,
      aperto, c'è un grosso libro di enigmi pieno di segni a matita. A sud il salone della musica, a
      ovest la galleria dei ritratti, a nord lo studio del conte.
    exits:
      sud: {to: salone_musica}
      ovest: {to: galleria}
      nord: {to: studio_conte}

  studio_conte:
    name: Studio del conte
    aliases: [studio]
    description: >
      Lo studio del conte Ruggero, rimasto com'era nel 1915: una scrivania di mogano, trofei di
      caccia alle pareti, una rastrelliera di bastoni da passeggio in un angolo. Sulla scrivania,
      carte sparse e un posacenere pieno: qualcuno ci lavora ancora. A sud la biblioteca, a nord la
      camera di Corrado.
    exits:
      sud: {to: biblioteca}
      nord: {to: camera_corrado}

  camera_corrado:
    name: Camera di Corrado
    description: >
      Una camera da scapolo in disordine: il letto sfatto, una sacca da viaggio mai disfatta,
      bottiglie vuote sul davanzale. Sul tavolino da notte, un mucchio di cambiali tenute insieme da
      un elastico. A sud si torna nello studio del conte.
    exits:
      sud: {to: studio_conte}

  # Provvisoria: nessuno ci entra, perché aprire la scala di servizio chiude il secondo atto. La
  # riscrive l'atto 3, nel file della soffitta.
  pianerottolo_soffitta:
    name: Pianerottolo della soffitta
    description: In cima alla scala di servizio, la soffitta è buia e silenziosa.
    exits:
      giù: {to: pianerottolo_servizio}

items:
  # --- La galleria: il ritratto di Clara ---
  ritratto:
    name: ritratto
    gender: m
    aliases: [quadro, quadro coperto, ritratto coperto, cornice, incavo, ragazza]
    description: >
      Un quadro alto quanto una persona, nascosto da un drappo di velluto nero inchiodato tutto
      intorno alla cornice.
    location: galleria
    scenery: true
    variants:
      - when: {all: [{flag: cornice_aperta}, {has: fotografia}]}
        text: >
          Tua madre a vent'anni, vestita di bianco, col medaglione al collo: la fotografia che hai
          in mano non lascia dubbi. Nella cornice, lo scomparto dietro l'incavo a stella è aperto e
          vuoto.
      - when: {all: [{flag: ritratto_scoperto}, {has: fotografia}]}
        text: >
          Una ragazza di vent'anni in un abito bianco da ballo, ritta accanto a una finestra
          fiorita. I capelli raccolti, gli occhi buoni; al collo, una stella d'argento. Il tuo
          medaglione. Alzi la fotografia accanto al quadro, e non c'è più nessun dubbio: è lei. È
          tua madre, qui, in questa casa, prima che tu nascessi. Nella cornice dorata, in basso, c'è
          un incavo a forma di stella.
      - when: {flag: cornice_aperta}
        text: >
          La ragazza vestita di bianco, col medaglione al collo. Quel viso l'hai già visto, più
          vecchio e più stanco. Nella cornice, lo scomparto dietro l'incavo a stella è aperto e
          vuoto.
      - when: {flag: ritratto_scoperto}
        text: >
          Una ragazza di vent'anni in un abito bianco da ballo, ritta accanto a una finestra
          fiorita. I capelli raccolti, gli occhi buoni; al collo, una stella d'argento. Il tuo
          medaglione. Quel viso l'hai già visto, più vecchio e più stanco: se avessi con te la
          fotografia di tua madre… Nella cornice dorata, in basso, c'è un incavo a forma di stella.

  drappo:
    name: drappo di velluto
    gender: m
    aliases: [drappo, velluto, velluto nero, drappo nero]
    description: Un drappo di velluto nero, inchiodato tutto intorno alla cornice del quadro.
    location: galleria
    scenery: true
    variants:
      - when: {flag: ritratto_scoperto}
        text: Il drappo di velluto nero, a terra sotto il ritratto, coi chiodi ancora attaccati.

  antenati:
    name: ritratti degli antenati
    gender: m
    plural: true
    aliases: [ritratti, antenati, quadri, dame, cavalieri, vescovo, pareti]
    description: >
      Generazioni di Valdimora in cornici dorate: dame incipriate, cavalieri in armatura, un vescovo
      dall'aria severa. Sotto ognuno, una targhetta col nome e le date. Nessuno di quei volti ti
      somiglia.
    location: galleria
    scenery: true

  cilindro:
    name: cilindro del carillon
    gender: m
    aliases: [cilindro, rullo, striscia di carta]
    description: >
      Un piccolo cilindro d'ottone irto di punte sottilissime: il cuore di un carillon. Era avvolto
      in una striscia di carta, con la grafia della contessa: «Suonala per me, come faceva lei.»
    location: null

  # --- La camera della contessa, la rosa bianca e il boudoir ---
  letto_contessa:
    name: letto a baldacchino
    gender: m
    aliases: [letto, baldacchino, tende, cuscino]
    description: >
      Un letto a baldacchino rifatto con cura, il cuscino ancora segnato. Le tende sono tirate a
      metà, come se qualcuno dovesse tornare a dormirci.
    location: camera_contessa
    scenery: true

  comodino:
    name: comodino
    gender: m
    aliases: [vasetto, vasetto d'argento]
    description: >
      Un comodino di noce con un vasetto d'argento, vuoto. Sul ripiano, un cerchio più chiaro dove
      per anni è stata appoggiata sempre la stessa cosa.
    location: camera_contessa
    scenery: true
    variants:
      - when: {flag: livia_permette}
        text: Nel vasetto d'argento, sul comodino, la rosa bianca che hai portato dalla serra.

  cordone:
    name: cordone del campanello
    gender: m
    aliases: [cordone, campanello, seta rossa]
    description: >
      Un cordone di seta rossa per chiamare la servitù. È tagliato di netto all'altezza del letto:
      il pezzo che arrivava al cuscino è sparito.
    location: camera_contessa
    scenery: true

  porta_boudoir:
    name: porta del boudoir
    gender: f
    aliases: [porta, porta bassa]
    description: Una porta bassa, dipinta di bianco e d'oro, che dà sul boudoir della contessa.
    location: camera_contessa
    scenery: true
    variants:
      - when: {flag: livia_permette}
        text: La porta del boudoir, aperta.

  rosa_bianca:
    name: rosa bianca
    gender: f
    aliases: [rosa]
    description: Una rosa bianca appena aperta, colta nella serra. Profuma di pioggia.
    location: null

  toeletta:
    name: toeletta
    gender: f
    aliases: [spazzole, boccette, profumo, merletti, velluti, cipria]
    description: >
      Una toeletta coperta di merletti: spazzole d'argento, boccette di profumo mezze vuote, un
      piumino da cipria. Tutto è rimasto come l'ha lasciato la contessa.
    location: boudoir
    scenery: true

  portagioie:
    name: portagioie
    gender: m
    aliases: [cofanetto, scrigno, gioielli, legno intarsiato]
    description: Un portagioie di legno intarsiato, con una stella di madreperla sul coperchio. Non ha serratura.
    location: boudoir
    scenery: true
    variants:
      - when: {flag: portagioie_aperto}
        text: >
          Il portagioie è aperto: collane, spille, gli orecchini di granato della contessa. Non sono
          tuoi, e li lasci dove sono.

  chiavetta_carica:
    name: chiavetta di carica
    gender: f
    aliases: [chiavetta, chiave a farfalla, farfalla]
    description: Una chiavetta d'ottone con la testa a farfalla, per caricare un carillon.
    location: null

  armadi:
    name: armadi a muro
    gender: m
    plural: true
    aliases: [armadi, armadio, ante, abiti, pelliccia, scatole]
    description: >
      Abiti di seta scura, una pelliccia di volpe, cappelli nelle loro scatole rotonde. Profumano di
      lavanda. Nelle tasche, solo fazzoletti ricamati «A. V.».
    location: guardaroba
    scenery: true

  porticina:
    name: porticina
    gender: f
    aliases: [porta]
    description: Una porticina per la cameriera, che dà sul pianerottolo di servizio.
    location: guardaroba
    scenery: true

  # --- Il carillon e la scala di servizio ---
  carillon:
    name: carillon
    gender: m
    aliases: [carillon d'argento, campana, campana di vetro, tavolino, tavolino rotondo, scatola musicale, tempietto, base]
    description: >
      Un carillon d'argento a forma di tempietto, sotto una campana di vetro. Sopra, l'alloggio vuoto
      del cilindro della musica; alla base, un piccolo foro per la chiavetta di carica.
    location: salone_musica
    scenery: true
    variants:
      - when: {flag: carillon_suonato}
        text: >
          Il carillon d'argento, col cilindro al suo posto e la base aperta come un cassetto. Dentro
          non c'è più niente.
      - when: {flag: cilindro_messo}
        text: >
          Il carillon d'argento, col cilindro nel suo alloggio. Manca solo di caricarlo: alla base
          c'è il foro per la chiavetta.

  chiave_servizio:
    name: chiave della scala di servizio
    gender: f
    aliases: [chiave, chiave di servizio, chiave di ferro, nastro]
    description: >
      Una chiave di ferro, legata a un nastro azzurro con un cartellino. Sul cartellino, la grafia
      della contessa: «Dove lei dormiva bambina.»
    location: null

  porta_scala_servizio:
    name: porta della scala di servizio
    gender: f
    aliases: [porta, porta stretta, porta di servizio, scala di servizio]
    description: Una porta stretta di legno grezzo, chiusa a chiave. Dietro, una scala sale verso la soffitta.
    location: pianerottolo_servizio
    scenery: true

  pareti_imbiancate:
    name: pareti imbiancate
    gender: f
    plural: true
    aliases: [pareti, calce]
    description: >
      Pareti imbiancate a calce e un pavimento di legno tirato a cera. Di qui passava la servitù,
      senza farsi vedere.
    location: pianerottolo_servizio
    scenery: true

  arpa:
    name: arpa
    gender: f
    aliases: [corde]
    description: Un'arpa dorata, in un angolo, senza più corde. Nessuno la suona da anni.
    location: salone_musica
    scenery: true

  poltroncine:
    name: poltroncine
    gender: f
    plural: true
    aliases: [poltroncina, palco, piccolo palco]
    description: >
      Poltroncine di velluto azzurro in file ordinate, davanti a un palco vuoto. Qui, una volta, si
      davano concerti.
    location: salone_musica
    scenery: true

  # --- Gli arredi della loggia, del salone delle feste, del balcone e del salottino ---
  scalone_pietra:
    name: scalone di pietra
    gender: m
    aliases: [scalone, gradini]
    description: Lo scalone di pietra da cui sei salita. Scende nel buio verso l'atrio.
    location: loggia
    scenery: true

  colonnato:
    name: colonnato
    gender: m
    aliases: [colonne, colonna, arco]
    description: Colonne di pietra grigia, lisce e fredde. Tra l'una e l'altra, il buio del piano nobile.
    location: loggia
    scenery: true

  pavimento_marmo:
    name: pavimento di marmo
    gender: m
    aliases: [pavimento, marmo]
    description: Marmo bianco e grigio, lucidato da generazioni di passi. Rimbomba a ogni passo.
    location: loggia
    scenery: true

  candelabri:
    name: candelabri
    gender: m
    plural: true
    aliases: [candelabro]
    description: >
      Due candelabri di ferro battuto, alti quanto te. Le candele si sono consumate fino in fondo, e
      nessuno le ha cambiate.
    location: loggia
    scenery: true

  lampadari_coperti:
    name: lampadari coperti
    gender: m
    plural: true
    aliases: [lampadari, lampadario, sacchi, sacchi di tela, tela]
    description: >
      Tre lampadari di cristallo, chiusi in sacchi di tela grezza contro la polvere. Da anni nessuno
      li accende.
    location: salone_feste
    scenery: true

  sedie_dorate:
    name: sedie dorate
    gender: f
    plural: true
    aliases: [sedie, sedia]
    description: Sedie dorate dal sedile di velluto rosso, in fila lungo i muri. Sulla polvere dei sedili, nessun segno.
    location: salone_feste
    scenery: true

  portafinestra:
    name: portafinestra
    gender: f
    aliases: [porta, vetri]
    description: Una portafinestra coi vetri rigati di pioggia. Dà sul balcone.
    location: salone_feste
    scenery: true

  balaustra:
    name: balaustra
    gender: f
    aliases: [parapetto, crepe, angolo]
    description: >
      Una balaustra di pietra, crepata in più punti. In un angolo ne manca un pezzo, e sotto c'è solo
      il vuoto. Non ti fideresti ad appoggiarci nemmeno una mano.
    location: balcone
    scenery: true

  vaso:
    name: vaso di gerani
    gender: m
    aliases: [vaso, gerani, terracotta]
    description: >
      Un vaso di terracotta coi gerani secchi, in bilico sull'orlo esterno della balaustra, appena
      fuori dalla tua portata. Tra i gerani brilla qualcosa di vetro.
    location: balcone
    scenery: true

  valle:
    name: valle
    gender: f
    aliases: [panorama, montagne]
    description: La valle sparisce nella pioggia. Laggiù, da qualche parte, la frana ha chiuso l'unica strada.
    location: balcone
    scenery: true

  solitario:
    name: solitario
    gender: m
    aliases: [carte, mazzo, tavolino, tavolino da gioco]
    description: >
      Un solitario lasciato a metà sul tavolino da gioco, le carte in fila perfetta. Manca poco a
      chiuderlo, ma nessuno l'ha più toccato.
    location: salottino_verde
    scenery: true

  tappezzeria:
    name: tappezzeria
    gender: f
    aliases: [seta, seta verde, tappeti, tappeto]
    description: Seta verde alle pareti, tappeti persiani uno sull'altro. È la stanza più calda del piano.
    location: salottino_verde
    scenery: true

  # --- Gli arredi della biblioteca, dello studio e della camera di Corrado ---
  scaffali_biblioteca:
    name: scaffali della biblioteca
    gender: m
    plural: true
    aliases: [scaffali, libri, atlanti, giornali, ballatoio, scala, scala di legno]
    description: >
      Migliaia di libri, dal pavimento al soffitto: latino, storia, atlanti, annate di giornali
      rilegate in pelle. Una scala di legno su ruote corre lungo il ballatoio.
    location: biblioteca
    scenery: true

  libro_enigmi:
    name: libro di enigmi
    gender: m
    aliases: [libro, enigmi, sciarade, scrittoio, segni, matita]
    description: >
      Un grosso volume di enigmi, sciarade e rebus, consumato dall'uso. Nei margini, la grafia della
      contessa li ha risolti quasi tutti. Accanto all'ultimo c'è scritto soltanto: «Per I.»
    location: biblioteca
    scenery: true

  scrivania:
    name: scrivania di mogano
    gender: f
    aliases: [scrivania, carte, posacenere, mogano]
    description: >
      Una scrivania di mogano ingombra di carte: conti, lettere di banche, il catalogo di una casa
      d'aste di Milano. Il posacenere è pieno di mozziconi freschi.
    location: studio_conte
    scenery: true

  trofei:
    name: trofei di caccia
    gender: m
    plural: true
    aliases: [trofei, corna, pareti]
    description: >
      Corna di cervo e di camoscio, e un cinghiale impagliato che digrigna i denti. Il conte cacciava
      su queste montagne fino all'ultimo.
    location: studio_conte
    scenery: true

  rastrelliera:
    name: rastrelliera
    gender: f
    aliases: [bastoni, bastoni da passeggio, portabastoni]
    description: "Una rastrelliera di bastoni da passeggio, quasi tutti col pomo d'argento: la collezione del conte."
    location: studio_conte
    scenery: true

  disordine:
    name: disordine
    gender: m
    aliases: [letto, letto sfatto, sacca, sacca da viaggio, bottiglie, davanzale]
    description: >
      Il letto sfatto, una sacca da viaggio pronta per partire, bottiglie vuote in fila sul
      davanzale. Corrado non ha l'aria di uno che dorme molto.
    location: camera_corrado
    scenery: true

  cambiali:
    name: cambiali
    gender: f
    plural: true
    aliases: [cambiale, elastico, tavolino, tavolino da notte, debiti]
    description: >
      Cambiali firmate da Corrado, una sopra l'altra, alcune già protestate: Torino, Milano,
      Sanremo. Debiti di gioco, per una somma da far girare la testa.
    location: camera_corrado
    scenery: true

rules:
  # --- La galleria: il ritratto e la cornice ---
  scopri_ritratto:
    trigger:
      - {verb: prendi, target: drappo}
      - {verb: tira, target: drappo}
      - {verb: tira, target: ritratto}
      - {verb: apri, target: ritratto}
      - {verb: prendi, target: drappo, with: ritratto}
      - {verb: tira, target: drappo, with: ritratto}
    when: {not: {flag: ritratto_scoperto}}
    otherwise: Il drappo è già a terra.
    effects:
      - set_flag: ritratto_scoperto
    text: >
      Afferri il velluto e tiri. I chiodi cedono uno dopo l'altro, e il drappo scivola a terra in
      una nuvola di polvere. Da sotto, una ragazza vestita di bianco ti guarda.

  prendi_ritratto:
    trigger: {verb: prendi, target: ritratto}
    text: È grande quanto una porta, e inchiodato al muro. Lo lasci dov'è.

  apri_cornice:
    trigger: {verb: usa, target: medaglione, with: ritratto}
    when: {all: [{flag: ritratto_scoperto}, {not: {flag: cornice_aperta}}]}
    otherwise: "Il quadro è coperto dal drappo: non vedi dove potrebbe servire il medaglione."
    otherwise_variants:
      - when: {flag: cornice_aperta}
        text: Lo scomparto della cornice è aperto, e dentro non c'è altro.
    effects:
      - give: cilindro
      - set_flag: cornice_aperta
    text: >
      Appoggi il medaglione nell'incavo della cornice. Entra perfettamente, come nella meridiana; lo
      giri, e con uno scatto un listello dorato si stacca. Dietro, avvolto in una striscia di carta,
      c'è un piccolo cilindro d'ottone irto di punte, come quelli dei carillon. Sulla carta, la
      grafia della contessa: «Suonala per me, come faceva lei.» Lo prendi, e ti rimetti il medaglione
      al collo.

  leggi_cilindro:
    trigger: {verb: leggi, target: cilindro}
    text: "Sulla striscia di carta che avvolgeva il cilindro: «Suonala per me, come faceva lei.»"

  # --- La rosa bianca (il rosaio e le forbici sono al pianterreno) ---
  cogli_rosa:
    trigger:
      - {verb: usa, target: forbici, with: rosaio}
      - {verb: prendi, target: rosaio, with: forbici}
    when: {not: {flag: rosa_colta}}
    otherwise: Hai già colto la tua rosa. Le altre lasciale alla serra.
    otherwise_variants:
      - when: {flag: livia_permette}
        text: La tua rosa è sul comodino della contessa. Le altre lasciale alla serra.
    effects:
      - give: rosa_bianca
      - set_flag: rosa_colta
    text: >
      Scegli la rosa più bella, appena aperta, e la tagli con un colpo netto delle forbici. Profuma
      di pioggia.

  prendi_rosaio:
    trigger: {verb: prendi, target: rosaio}
    when: {not: {flag: rosa_colta}}
    otherwise: Hai già colto la tua rosa. Le altre lasciale alla serra.
    otherwise_variants:
      - when: {flag: livia_permette}
        text: La tua rosa è sul comodino della contessa. Le altre lasciale alla serra.
    text: >
      Allunghi la mano, ma i gambi sono irti di spine lunghe come aghi. Senza qualcosa per tagliarli
      non ne cogli nemmeno una.

  dai_rosa_livia:
    trigger: {verb: dai, target: rosa_bianca, with: livia}
    when: {flag: atto_due}
    otherwise: >
      Livia guarda la rosa, e per un attimo le si addolcisce lo sguardo. Poi scuote la testa.
      «Tenetela voi, signorina.»
    effects:
      - remove: rosa_bianca
      - set_flag: livia_permette
    text: >
      Livia prende la rosa e la guarda a lungo, senza parlare. Poi la mette nel vasetto d'argento
      sul comodino, e ne sistema il gambo con cura, come faceva ogni mattina. Quando si volta ha gli
      occhi lucidi. «Il boudoir», dice piano, e si scosta dalla porta. «Andate. Lei avrebbe voluto
      così.»

  apri_porta_boudoir:
    trigger: {verb: apri, target: porta_boudoir}
    when: {flag: livia_permette}
    otherwise: >
      Livia si alza e si mette davanti alla porta. «Il boudoir no, signorina. Lì dentro la contessa
      non voleva nessuno.»
    text: La porta del boudoir è aperta. Basta entrare.

  # --- Il boudoir ---
  apri_portagioie:
    trigger: {verb: apri, target: portagioie}
    when: {not: {flag: portagioie_aperto}}
    otherwise: Il portagioie è aperto. Il resto sono gioielli della contessa, e non sono tuoi.
    effects:
      - give: chiavetta_carica
      - set_flag: portagioie_aperto
    text: >
      Sollevi il coperchio. Collane, spille, un paio di orecchini di granato e, in uno scomparto
      foderato di velluto, una chiavetta d'ottone con la testa a farfalla, come quelle che servono a
      caricare i carillon. Prendi la chiavetta; i gioielli li lasci dove sono.

  prendi_portagioie:
    trigger: {verb: prendi, target: portagioie}
    text: È della contessa, e il suo posto è sulla toeletta. Lo lasci lì.

  # --- Il carillon ---
  metti_cilindro:
    trigger: {verb: usa, target: cilindro, with: carillon}
    effects:
      - remove: cilindro
      - set_flag: cilindro_messo
    text: Sollevi la campana di vetro e incastri il cilindro nel suo alloggio. Combacia alla perfezione.

  carica_carillon:
    trigger: {verb: usa, target: chiavetta_carica, with: carillon}
    when: {all: [{flag: cilindro_messo}, {not: {flag: carillon_suonato}}]}
    otherwise: La musica è finita, e la base del carillon è aperta e vuota.
    otherwise_variants:
      - when: {not: {flag: cilindro_messo}}
        text: >
          Carichi la molla, e il carillon gira a vuoto con un ronzio: nell'alloggio del cilindro non
          c'è niente da suonare.
    effects:
      - give: chiave_servizio
      - set_flag: carillon_suonato
    text: >
      Infili la chiavetta e la giri, tre, quattro volte. Il cilindro comincia a ruotare, e la stanza
      si riempie di una musica piccola e lenta. La conosci. È la ninna nanna che ti cantava tua
      madre la sera, a Genova, quando eri bambina. Resti ferma finché l'ultima nota si spegne.
      Allora, con uno scatto, la base del carillon si apre come un cassetto: dentro c'è una chiave di
      ferro, legata a un nastro azzurro. La prendi.

  apri_carillon:
    trigger:
      - {verb: apri, target: carillon}
      - {verb: tira, target: carillon}
    when: {not: {flag: carillon_suonato}}
    otherwise: La base del carillon è aperta, e dentro non c'è più niente.
    text: La base non ha serrature né cassetti che tu veda, solo un piccolo foro per la chiavetta di carica.

  prendi_carillon:
    trigger: {verb: prendi, target: carillon}
    text: È troppo delicato, e la campana di vetro pesa. Lo lasci sul suo tavolino.

  leggi_chiave_servizio:
    trigger: {verb: leggi, target: chiave_servizio}
    text: "Sul cartellino legato al nastro, la grafia della contessa: «Dove lei dormiva bambina.»"

  # --- La scala di servizio ---
  apri_scala_servizio:
    trigger: {verb: apri, target: porta_scala_servizio, with: chiave_servizio}
    when: {not: {flag: atto_tre}}
    otherwise: La porta della scala di servizio è già aperta.
    effects:
      - remove: chiave_servizio
      - set_flag: atto_tre
    text: La chiave gira dura, poi scatta. La lasci nella serratura, e spingi la porta.

  apri_scala_servizio_senza_chiave:
    trigger: {verb: apri, target: porta_scala_servizio}
    when: {all: [{not: {flag: atto_tre}}, {not: {has: chiave_servizio}}]}
    otherwise: "Hai la chiave della scala di servizio: usala."
    otherwise_variants:
      - when: {flag: atto_tre}
        text: La porta della scala di servizio è già aperta.
    text: È chiusa a chiave, e una chiave così non l'hai mai vista sul quadro di Livia.

  # --- Risposte d'atmosfera ---
  leggi_libro_enigmi:
    trigger: {verb: leggi, target: libro_enigmi}
    text: >
      Ne leggi uno a caso: «Più ne togli, più diventa grande.» Accanto, a matita, la contessa ha
      scritto: «la buca». Sull'ultima pagina, soltanto: «Per I.»

  leggi_cambiali:
    trigger: {verb: leggi, target: cambiali}
    text: Leggi le cifre, e ti gira la testa. Corrado deve a mezzo Piemonte quasi quanto vale questo castello.

  prendi_cambiali:
    trigger: {verb: prendi, target: cambiali}
    text: Non sono affari tuoi. Almeno per ora.

  suona_arpa:
    trigger: {verb: usa, target: arpa}
    text: Sfiori il legno dove una volta c'erano le corde. Non ne esce niente.
```

- [ ] **Step 4: Gli altri file**

- In `data/worlds/valdimora/pianterreno.yaml`, togliere il blocco:
```yaml
  # Provvisoria: nessuno ci entra, perché aprire lo scalone chiude il primo atto. La riscrive l'atto 2.
  loggia:
    name: Loggia dello scalone
    description: In cima allo scalone, il piano nobile è buio e silenzioso.
    exits:
      giù: {to: atrio}

```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
      lo scalone di pietra sale verso il piano nobile, chiuso da una porta di legno scuro. A nord,
      oltre una vetrata, il cortile; a ovest il salotto, a est la sala del biliardo. A sud, fuori
      sotto la pioggia, la rimessa.
    exits:
```
diventa
```yaml
      lo scalone di pietra sale verso il piano nobile, chiuso da una porta di legno scuro. A nord,
      oltre una vetrata, il cortile; a ovest il salotto, a est la sala del biliardo. A sud, fuori
      sotto la pioggia, la rimessa.
    variants:
      - when: {flag: atto_due}
        text: >
          Un atrio alto e freddo, col pavimento a scacchi bianchi e neri. Sul portone da cui sei
          entrata pende un drappo nero, e accanto, su un cavalletto, c'è un annuncio listato a lutto.
          In fondo, lo scalone di pietra sale verso la loggia del piano nobile: la sua porta ora è
          aperta. A nord, oltre una vetrata, il cortile; a ovest il salotto, a est la sala del
          biliardo. A sud, fuori sotto la pioggia, la rimessa.
    exits:
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
      - {verb: apri, target: porta_cantina, with: chiavetta}
    text: La chiave non entra nella serratura.
```
diventa
```yaml
      - {verb: apri, target: porta_cantina, with: chiavetta}
      - {verb: apri, target: porta_cantina, with: chiave_servizio}
      - {verb: apri, target: porta_cantina, with: chiavetta_carica}
      - {verb: apri, target: porta_scala_servizio, with: chiave_credenza}
      - {verb: apri, target: porta_scala_servizio, with: chiavetta}
      - {verb: apri, target: porta_scala_servizio, with: chiavetta_carica}
    text: La chiave non entra nella serratura.
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
# Il primo atto finisce aprendo la porta dello scalone (finale provvisorio: lo toglie l'atto 2).
```
diventa
```yaml
# Il secondo atto finisce aprendo la porta della scala di servizio (finale provvisorio: lo toglie
# l'atto 3). Dopo una morte si riprende dall'inizio del secondo atto.
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
    (In costruzione: per ora il primo atto.)
```
diventa
```yaml
    (In costruzione: per ora i primi due atti.)
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
  start_room: atrio
  endings:
    - when: {flag: atto_due}
      text: >
        Sali i primi gradini dello scalone. Sopra di te il piano nobile è buio, e da qualche parte,
        lassù, c'è qualcuno che ti somiglia. Fine del primo atto. (Il secondo è in costruzione.)
```
diventa
```yaml
  start_room: atrio
  acts:
    - name: secondo atto
      when: {flag: atto_due}
  endings:
    - when: {flag: atto_tre}
      text: >
        La porta si apre su una scala di legno stretta e ripida, che sale nel buio verso la soffitta.
        Da lassù scende un odore di polvere e di lavanda. «Dove lei dormiva bambina.» Fine del
        secondo atto. (Il terzo è in costruzione.)
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
    location: stanza_maggiordomo
```
aggiungere
```yaml
    moves:
      - when: {flag: atto_due}
        room: galleria
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
    location: ufficio_governante
```
aggiungere
```yaml
    moves:
      - when: {flag: atto_due}
        room: camera_contessa
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
treno in ritardo.
    location: biliardo
```
aggiungere
```yaml
    moves:
      - when: {flag: atto_due}
        room: studio_conte
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
    location: cappella
```
aggiungere
```yaml
    moves:
      - when: {flag: atto_due}
        room: loggia
```

- [ ] **Step 5: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde.

```bash
git add data/worlds/valdimora/piano-nobile.yaml data/worlds/valdimora/gioco.yaml data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 2: il piano nobile e il filo principale" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Il filo facoltativo e il pericolo del balcone

**Files:**
- Modify: `data/worlds/valdimora/piano-nobile.yaml` (bastone, flacone, varianti del balcone e del vaso, regole), `data/worlds/valdimora/gioco.yaml` (finale di morte), `data/worlds/valdimora/personaggi.yaml` (Ferri e il flacone)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: `in_act_two`, `TO_THE_STAIRCASE` (Task 2).
- Produces: oggetti `bastone` (nello studio), `flacone`; flag `vaso_recuperato`, `caduta_dal_balcone`; il finale di morte del balcone.

- [ ] **Step 1: Test che falliscono**

In fondo a `tests/test_valdimora.py`:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py -q -p no:cacheprovider`
Expected: FAIL — il bastone e il flacone non esistono, e dal balcone non si cade.

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/piano-nobile.yaml`, prima del blocco
```yaml
rules:
```
aggiungere
```yaml
  # --- Il filo facoltativo: il bastone del conte e il flacone sul balcone ---
  bastone:
    name: bastone dal manico ricurvo
    gender: m
    aliases: [bastone, bastone del conte, manico, manico ricurvo]
    description: >
      Un bastone da passeggio di frassino, col manico ricurvo come un uncino. Il conte ci si
      appoggiava negli ultimi anni.
    location: studio_conte

  flacone:
    name: flacone vuoto
    gender: m
    aliases: [flacone, boccetta, boccetta vuota]
    description: >
      Una boccetta di vetro scuro, vuota e senza tappo. Sull'etichetta, scritto a mano: «Digitale,
      gocce». Ha ancora un odore amaro.
    location: null
```
- In `data/worlds/valdimora/piano-nobile.yaml`, dopo il blocco
```yaml
    text: Sfiori il legno dove una volta c'erano le corde. Non ne esce niente.
```
aggiungere
```yaml
  # --- Il balcone: il vaso, il flacone (prova 2) e la balaustra (pericolo) ---
  aggancia_vaso:
    trigger:
      - {verb: usa, target: bastone, with: vaso}
      - {verb: prendi, target: vaso, with: bastone}
      - {verb: tira, target: vaso, with: bastone}
    when: {not: {flag: vaso_recuperato}}
    otherwise: Il vaso è già al sicuro ai tuoi piedi, e dentro non c'è altro.
    effects:
      - give: flacone
      - set_flag: vaso_recuperato
    text: >
      Tenendoti lontana dal bordo, allunghi il bastone e agganci il vaso col manico ricurvo. Lo tiri
      piano verso di te lungo la pietra, finché non è al sicuro ai tuoi piedi. Tra i gerani secchi
      c'è una boccetta di vetro scuro, vuota. Qualcuno l'ha nascosta qui. La prendi.

  prendi_vaso:
    trigger: {verb: prendi, target: vaso}
    when: {not: {flag: vaso_recuperato}}
    otherwise: È pesante e pieno di terra. Lo lasci dov'è, al sicuro.
    effects:
      - set_flag: caduta_dal_balcone
    text: Ti sporgi oltre la balaustra, allunghi il braccio verso il vaso e ci appoggi tutto il peso.

  tira_vaso:
    trigger: {verb: tira, target: vaso}
    when: {not: {flag: vaso_recuperato}}
    otherwise: È pesante e pieno di terra. Lo lasci dov'è, al sicuro.
    text: >
      Con le mani non ci arrivi, e sporgerti su quella balaustra sarebbe una follia. Ti servirebbe
      qualcosa di lungo, per agganciarlo.

  spingi_balaustra:
    trigger: {verb: spingi, target: balaustra}
    effects:
      - set_flag: caduta_dal_balcone
    text: Appoggi tutte e due le mani sulla balaustra crepata, e spingi.

  scavalca_balaustra:
    trigger: {verb: salta, target: balaustra}
    effects:
      - set_flag: caduta_dal_balcone
    text: Metti un piede sulla balaustra per scavalcarla.
```
- In `data/worlds/valdimora/piano-nobile.yaml`, il blocco
```yaml
      delle feste.
    exits:
      nord: {to: salone_feste}
```
diventa
```yaml
      delle feste.
    variants:
      - when: {flag: vaso_recuperato}
        text: >
          Un balcone di pietra sospeso sulla valle, battuto dal vento e dalla pioggia. La balaustra è
          crepata in più punti, e in un angolo ne manca un pezzo: meglio non appoggiarcisi. Il vaso
          di gerani ora è al sicuro ai tuoi piedi. A nord si rientra nel salone delle feste.
    exits:
      nord: {to: salone_feste}
```
- In `data/worlds/valdimora/piano-nobile.yaml`, dopo il blocco
```yaml
      fuori dalla tua portata. Tra i gerani brilla qualcosa di vetro.
    location: balcone
    scenery: true
```
aggiungere
```yaml
    variants:
      - when: {flag: vaso_recuperato}
        text: Il vaso di gerani, al sicuro sul pavimento del balcone. Tra i gerani secchi non c'è più niente.
```
- In `data/worlds/valdimora/gioco.yaml`, il blocco
```yaml
  endings:
    - when: {flag: atto_tre}
```
diventa
```yaml
  endings:
    - when: {flag: caduta_dal_balcone}
      death: true
      text: >
        La pietra cede con uno schiocco secco, e tu con lei. Per un attimo vedi la valle sotto di
        te, grigia di pioggia; poi più niente. Sei morta.
    - when: {flag: atto_tre}
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        aliases: [farmaco, gocce, digitale, borsa]
        text: >
          «Digitale, gocce per il cuore. Io le prescrivevo, e la ragazza, Agnese, gliele dava ogni
          sera.»
        variants:
          - when: {flag: ferri_addormentato}
            text: Il dottore russa.
```
diventa
```yaml
        aliases: [farmaco, gocce, digitale, borsa, flacone, boccetta]
        text: >
          «Digitale, gocce per il cuore. Io le prescrivevo, e la ragazza, Agnese, gliele dava ogni
          sera.»
        variants:
          - when: {flag: ferri_addormentato}
            text: Il dottore russa.
          - when: {has: flacone}
            text: >
              Il dottore vede la boccetta che hai in mano, e il colore gli sparisce dalla faccia.
              «Questa è la digitale della contessa. Dove l'avete trovata?» La annusa, e te la rende
              con la mano che trema. «L'avevo portata piena, una settimana prima che morisse.»
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde.

```bash
git add data/worlds/valdimora/piano-nobile.yaml data/worlds/valdimora/gioco.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 2: il bastone, il flacone e il pericolo del balcone" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: I personaggi nel secondo atto

**Files:**
- Modify: `data/worlds/valdimora/personaggi.yaml` (varianti del saluto di Ettore, Livia, Corrado, Agnese; argomenti nuovi; il congedo di Agnese)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: `in_act_two` (Task 2).
- Produces: argomenti `ettore.ritratto`, `ettore.carillon`, `livia.rose`, `livia.boudoir`, `livia.campanello`, `livia.scala_servizio`, `corrado.bastone`, `corrado.studio`, `corrado.cambiali`, `agnese.medaglione`; nessuno con effetti.

- [ ] **Step 1: Test che falliscono**

In fondo a `tests/test_valdimora.py`:
```python
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
```
`test_no_character_gives_a_shortcut` resta com'è: gli argomenti nuovi non hanno effetti.

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py -q -p no:cacheprovider`
Expected: FAIL — i personaggi rispondono coi testi del primo atto, o `unknown`.

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: busta_data}
        text: «Signorina Irene.» Ettore si inchina appena. «Chiedete pure. Quello che so, è vostro.»
```
diventa
```yaml
    greeting_variants:
      - when: {flag: ritratto_scoperto}
        text: Ettore guarda il ritratto, poi guarda te. «Ora avete visto», dice soltanto.
      - when: {flag: atto_due}
        text: >
          Ettore è in piedi davanti al quadro coperto, le mani dietro la schiena. «Signorina. Sapevo
          che prima o poi sareste venuta qui.»
      - when: {flag: busta_data}
        text: «Signorina Irene.» Ettore si inchina appena. «Chiedete pure. Quello che so, è vostro.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          cose le trovaste da voi.»
        again: «Abbiate pazienza, signorina. Ogni cosa a suo tempo.»
```
diventa
```yaml
          cose le trovaste da voi.»
        variants:
          - when: {flag: ritratto_scoperto}
            text: >
              «L'avete vista, ora. Aveva il vostro stesso modo di guardare le cose.» Ettore si passa
              una mano sugli occhi. «Non chiedetemi altro, signorina. Non ancora.»
        again: «Abbiate pazienza, signorina. Ogni cosa a suo tempo.»
      ritratto:
        name: ritratto
        gender: m
        aliases: [quadro, quadro coperto, drappo, galleria]
        when: {flag: atto_due}
        text: >
          «Quel quadro è coperto dal 1897. Ordini del conte: nessuno doveva più vederlo.» Ettore
          guarda il drappo nero. «Il conte è morto da dodici anni, signorina, e io sono vecchio. Se
          volete guardare, non sarò io a fermarvi.»
        variants:
          - when: {flag: ritratto_scoperto}
            text: >
              «La signorina Clara, a vent'anni. Viveva qui, in questa casa.» Ettore si schiarisce la
              voce. «Il resto la contessa ha voluto che lo scopriste da voi, e io le ho dato la mia
              parola.»
        again: «Il drappo, signorina. Nessuno vi fermerà.»
      carillon:
        name: carillon
        gender: m
        aliases: [cilindro, ninna nanna, musica, salone della musica]
        when: {flag: ritratto_scoperto}
        text: >
          «Il carillon d'argento, nel salone della musica? Era della signorina Clara. Da bambina non
          si addormentava senza la sua ninna nanna.»
        again: «Nel salone della musica, signorina.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: livia_chiave}
```
diventa
```yaml
    greeting_variants:
      - when: {flag: livia_permette}
        text: Livia è seduta accanto al letto, e guarda la rosa sul comodino. «Grazie», dice soltanto.
      - when: {flag: atto_due}
        text: >
          Livia è seduta rigida su una sedia accanto al letto vuoto. «Siete salita, allora. Questa era
          la sua camera, signorina: non toccate niente.»
      - when: {flag: livia_chiave}
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
        text: «Ogni chiave di questa casa passa da me.»
        again: «Tutte da me. Non fatemelo ripetere.»
```
aggiungere
```yaml
      rose:
        name: rosa bianca
        gender: f
        aliases: [rosa, rose, rose bianche, fiori, vasetto, comodino]
        when: {flag: atto_due}
        text: >
          «Ogni mattina, per trent'anni, le ho portato una rosa bianca della serra, per il comodino.
          Le piacevano solo quelle.» Livia guarda il vasetto vuoto. «Da quando è morta non ho avuto
          il coraggio di coglierne una.»
        variants:
          - when: {flag: livia_permette}
            text: «È bella, la vostra rosa. Lei l'avrebbe tenuta fino all'ultimo petalo.»
        again: «Una rosa bianca, ogni mattina. Dalla serra.»
      boudoir:
        name: boudoir
        gender: m
        aliases: [porta del boudoir, porta bassa, portagioie]
        when: {flag: atto_due}
        text: >
          «Il boudoir era suo e basta. Nessuno ci entrava, nemmeno io, se non chiamata.» Livia stringe
          le labbra. «Non lo apro al primo che capita.»
        variants:
          - when: {flag: livia_permette}
            text: «Andate pure. Ve l'ho detto.»
        again: «Lì dentro no, signorina.»
      campanello:
        name: campanello
        gender: m
        aliases: [cordone, cordone del campanello, filo, campanelli]
        when: {flag: atto_due}
        text: >
          «Tagliato?» Livia si alza e guarda il cordone, e per la prima volta la vedi turbata. «Non me
          n'ero accorta. La notte la contessa non chiamava mai: c'era Agnese, con le sue gocce.»
        again: «Non so chi l'abbia tagliato, signorina. Non lo so.»
      scala_servizio:
        name: scala di servizio
        gender: f
        aliases: [porta di servizio, porta della scala di servizio, chiave della scala di servizio, soffitta]
        when: {flag: atto_due}
        text: «La chiave della scala di servizio la teneva la contessa, non io. Chissà dove l'ha messa.»
        again: "«Ve l'ho detto: la teneva lei.»"
```
- In `data/worlds/valdimora/personaggi.yaml`, prima del blocco
```yaml
    greeting_again: «Ancora qui?» Corrado alza il bicchiere vuoto, come per un brindisi. «Allora mettetevi comoda.»
```
aggiungere
```yaml
    greeting_variants:
      - when: {flag: atto_due}
        text: >
          Corrado è seduto alla scrivania del conte, coi piedi sul piano di mogano. «Guarda chi si
          vede. Siete arrivata fin quassù? Prendete pure quello che volete, signorina: tanto, tra
          poco, qui sarà tutto mio.»
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
        text: «Una settimana, dicono, per liberare la strada. Una settimana chiuso qui con voi tutti.»
        again: «Una settimana. Contate i giorni con me, se vi diverte.»
```
aggiungere
```yaml
      bastone:
        name: bastone
        gender: m
        aliases: [bastone del conte, bastoni, rastrelliera, manico ricurvo]
        when: {flag: atto_due}
        text: «Il bastone di mio zio? Prendetelo pure, se vi fa comodo. Prendete quello che volete, ve l'ho detto.»
        again: «Prendetelo, vi ho detto.»
      studio:
        name: studio
        gender: m
        aliases: [studio del conte, scrivania, conte, zio, ruggero]
        when: {flag: atto_due}
        text: >
          «Lo studio di mio zio Ruggero. È morto nel '15, e da allora qui dentro non ha comandato più
          nessuno.» Si accende una sigaretta. «Fino a me.»
        again: «Il mio studio, signorina. Quasi.»
      cambiali:
        name: cambiali
        gender: f
        plural: true
        aliases: [debiti, cambiale, gioco]
        when: {flag: atto_due}
        text: >
          «Siete stata in camera mia?» Per un attimo Corrado perde il sorriso. «Debiti di gioco. Il
          notaio li pagherà tutti, quando arriverà. Tutti.»
        again: «Il notaio li pagherà. Parliamo d'altro.»
```
- In `data/worlds/valdimora/personaggi.yaml`, prima del blocco
```yaml
    greeting_again: «Eccovi di nuovo.» Agnese ti sorride. «Avete bisogno di me?»
```
aggiungere
```yaml
    greeting_variants:
      - when: {flag: atto_due}
        text: >
          Agnese ti aspetta in cima allo scalone, con una candela in mano. «Ce l'avete fatta! Livia vi
          ha dato la chiave?» Si avvicina, e i suoi occhi vanno al tuo collo. «Posso vedere il vostro
          medaglione? La contessa ne parlava tanto…»
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
        text: «Andate pure. Io resto con lei.» Agnese torna a guardare la bara.
```
aggiungere
```yaml
        variants:
          - when: {flag: atto_due}
            text: «Andate pure. Io resto qui ad aspettarvi, se vi serve qualcosa.»
```
- In `data/worlds/valdimora/personaggi.yaml`, dopo il blocco
```yaml
        text: «Qualunque cosa. La contessa avrebbe voluto così.»
        again: «Qualunque cosa, ve l'ho detto.»
```
aggiungere
```yaml
      medaglione:
        name: medaglione
        gender: m
        aliases: [stella, ciondolo]
        text: >
          «Che bella stella. La contessa la disegnava dappertutto, sapete? Sui biglietti, sui margini
          dei libri…» Agnese si morde il labbro. «Posso vederlo da vicino?»
        again: «Me lo fate vedere?»
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (anche `tests/test_dialoghi.py`: ogni personaggio ha ancora i sei gesti).

```bash
git add data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 2: i personaggi al piano nobile" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Il secondo atto col modello vero

**Files:**
- Modify: `tests/test_ollama.py` (casi del secondo atto), eventualmente `data/worlds/valdimora/*.yaml` (alias e argomenti) e test sul client finto accanto, se una correzione tocca il codice

- [ ] **Step 1: Ollama**

`curl -s -m 5 http://127.0.0.1:11434/api/tags | head -c 200` — se non risponde, fermarsi e chiedere all'utente.

- [ ] **Step 2: I casi nuovi**

In `tests/test_ollama.py`, in fondo a `VALDIMORA_CASES` (prima di `]  # fmt: skip`):
```python
    # The second act (2026-09-30): the flags say how far the player has got.
    ("galleria", (), ("atto_due",), "tolgo il drappo dal quadro", lambda a, g: "ritratto_scoperto" in g.state.flags),
    ("galleria", ("fotografia",), ("atto_due", "ritratto_scoperto"), "guardo bene il ritratto della ragazza",
     says("È tua madre")),
    ("galleria", (), ("atto_due", "ritratto_scoperto"), "infilo il medaglione nella cornice",
     lambda a, g: g.state.item_locations["cilindro"] == "inventory"
     or g.pending == Action(verb="usa", target="medaglione", with_="ritratto")),
    ("galleria", (), ("atto_due",), "chiedo a Ettore del quadro coperto", says(ETTORE.topics["ritratto"].text)),
    ("camera_contessa", (), ("atto_due",), "chiedo a Livia delle rose", says(LIVIA.topics["rose"].text)),
    ("serra", ("forbici",), ("atto_due",), "taglio una rosa con le forbici",
     lambda a, g: g.state.item_locations["rosa_bianca"] == "inventory"),
    ("camera_contessa", ("rosa_bianca",), ("atto_due",), "regalo la rosa alla governante",
     lambda a, g: "livia_permette" in g.state.flags),
    ("camera_contessa", (), ("atto_due", "livia_permette"), "entro nel boudoir",
     lambda a, g: g.state.current_room == "boudoir" or g.pending == Action(verb="vai", direction="ovest")),
    ("boudoir", (), ("atto_due", "livia_permette"), "apro il portagioie della contessa",
     lambda a, g: g.state.item_locations["chiavetta_carica"] == "inventory"),
    ("salone_musica", ("cilindro",), ("atto_due",), "metto il cilindro nel carillon",
     lambda a, g: "cilindro_messo" in g.state.flags),
    ("salone_musica", ("chiavetta_carica",), ("atto_due", "cilindro_messo"), "carico il carillon con la chiavetta",
     lambda a, g: "carillon_suonato" in g.state.flags),
    ("pianerottolo_servizio", ("chiave_servizio",), ("atto_due",), "apro la porta di servizio con la chiave",
     lambda a, g: "atto_tre" in g.state.flags),
    ("studio_conte", (), ("atto_due",), "prendo il bastone del conte",
     lambda a, g: g.state.item_locations["bastone"] == "inventory"),
    ("studio_conte", (), ("atto_due",), "chiedo a Corrado se posso prendere il bastone",
     says(VALDIMORA.characters["corrado"].topics["bastone"].text, VALDIMORA.characters["corrado"].topics["studio"].text)),
    ("balcone", ("bastone",), ("atto_due",), "aggancio il vaso con il bastone",
     lambda a, g: g.state.item_locations["flacone"] == "inventory"),
    # Nobody dies without asking for it.
    ("balcone", (), ("atto_due",), "guardo giù dal balcone", lambda a, g: not g.finished),
    ("loggia", (), ("atto_due",), "faccio vedere il medaglione ad Agnese",
     says("Che strana stella", VALDIMORA.characters["agnese"].topics["medaglione"].text)),
    ("camera_contessa", (), ("atto_due",), "chi ha tagliato il cordone del campanello?",
     says(LIVIA.topics["campanello"].text)),
    ("atrio", (), ("atto_due",), "salgo al piano nobile", lambda a, g: g.state.current_room == "loggia"),
    ("atrio", (), ("atto_due",), "vado su per lo scalone", lambda a, g: g.state.current_room == "loggia"),
```
e, subito dopo `ETTORE = VALDIMORA.characters["ettore"]`, la riga `LIVIA = VALDIMORA.characters["livia"]` (poi in fondo al file la definizione ripetuta `LIVIA = VALDIMORA.characters["livia"]` dei gesti si toglie, perché ora c'è sopra).

Con `playing()` la partita non è ancora «nel secondo atto» (`act` è 0): va bene, i casi guardano solo la frase.

- [ ] **Step 3: Eseguire i casi nuovi**

Run: `OLLAMA_TESTS=1 LLM_LOG=off COMMAND_LOG=off PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_ollama.py -v -s -p no:cacheprovider -k "valdimora_free_sentences" > logs/atto2-1.txt 2>&1` e leggerne le righe `->` e il riassunto.

- [ ] **Step 4: Decidere caso per caso**

Come negli atti e nei dialoghi precedenti: prima i dati (alias, argomenti, un trigger in più su una regola), poi un esito innocuo accettato allargando il controllo con un commento, poi `KNOWN_LIMITS`. Una correzione di codice solo col suo test sul client finto; esempi nel prompt solo come ultima risorsa (e allora tutto `test_ollama.py`). Ogni caso aggiustato si riprova da solo, e una frase che il modello sbaglia due volte su tre è un limite, non un caso verde.

- [ ] **Step 5: Tutto `test_ollama.py`**

Run: `OLLAMA_TESTS=1 LLM_LOG=off COMMAND_LOG=off PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_ollama.py -v -s -p no:cacheprovider > logs/ollama-atto2.txt 2>&1` (circa 20 minuti per 146 casi, in background).
Expected: tutto verde a parte i limiti noti.

- [ ] **Step 6: Commit**

```bash
git add tests/test_ollama.py
git commit -m "Valdimora, atto 2: le frasi libere col modello vero" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(aggiungere anche i file di dati o di codice cambiati nello Step 4, con i loro test.)

---

### Task 6: CLAUDE.md e verifica finale

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md**

In «Decisioni prese», dopo la voce **Valdimora, atto 1**, la voce qui sotto, con i numeri del giro completo del Task 5 al posto di N e M (casi verdi e casi in tutto) e, al posto dell'ultima frase, le correzioni o i limiti trovati dal Task 5 (una riga ciascuno):
> - **Valdimora, atto 2** (2026-09-30, branch `feature/valdimora-atto-2`; piano in `docs/superpowers/plans/2026-09-30-valdimora-atto-2.md`): il piano nobile in `data/worlds/valdimora/piano-nobile.yaml` (13 stanze e una provvisoria in cima alla scala di servizio), nel menu con un finale provvisorio sul flag `atto_tre`. Il primo `acts` («secondo atto», su `atto_due`): si muore cadendo dal balcone e si riprende dall'inizio dell'atto. Ettore, Livia, Corrado e Agnese salgono di sopra (`moves`), Ferri resta nel biliardo con la sua borsa; i loro testi seguono il posto e la partita. Le chiavi usate restano nella serratura. Alias: niente parole sole simili a parole comuni («sete»/«siete»). Col modello vero N su M.

e in «Risultati dei test», nella riga «Ogni modifica al prompt va verificata su tutto `tests/test_ollama.py` (oggi …)», i numeri e il tempo del giro completo del Task 5, con le frasi del secondo atto nell'elenco.

- [ ] **Step 2: Verifica finale**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde.
Una partita nel terminale senza LLM, fino al secondo atto:
```bash
printf '3\nsud\napri la valigia\nprendi l oliatore\nnord\novest\nnord\nnord\ndai la lettera a Ettore\nleggi la busta\nchiedi a Ettore di Livia\nsud\nest\nesamina la meridiana\nusa l oliatore con la meridiana\nusa il medaglione con la meridiana\nest\nnord\ndai il biglietto sigillato a Livia\nsud\nsud\novest\napri la porta dello scalone con la chiave\nsu\nnord\nprendi il drappo\nesamina il ritratto\nfine\ns\n' | LLM=off LLM_LOG=off COMMAND_LOG=off PYTHONIOENCODING=utf-8 .venv/Scripts/python -m app.cli | tail -12
```
Expected: la galleria, il drappo che cade, «È tua madre», poi «Alla prossima!».

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: Valdimora, atto 2" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Poi la revisione finale di tutto il branch, e chiedere all'utente se pubblicarlo.
