# Il draghetto raffreddato (pezzo 3) — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** una seconda avventura, fantastica e facile, per bambini di 8-10 anni che giocano da soli: aiutare un draghetto raffreddato a ritrovare il suo fuoco. Si sceglie dal menu accanto alla Rocca.

**Architecture:** solo dati e test. Il mondo sta in `data/worlds/draghetto/` (cinque file YAML come la Rocca) e usa quello che c'è già: `dai` ai personaggi, `visible_from`/`reveals` per la piuma nel nido, uscite chiuse con `otherwise`, argomenti con `variants`. Nessun cambiamento al motore, al parser o al prompt comune; se il modello sbaglia qualche frase, gli esempi vanno in `game.examples` del draghetto, che non tocca il prompt della Rocca.

**Tech Stack:** YAML (PyYAML), Pydantic v2, pytest; Ollama con qwen2.5:3b per i test col modello vero.

**Spec:** `docs/superpowers/specs/2026-09-26-piu-avventure-design.md` — sezione 3.

## Global Constraints

- Nessuna dipendenza nuova, nessuna modifica a `app/`. Comandi con `.venv\Scripts\python`.
- Contenuti **originali**; testi in italiano semplice, seconda persona, frasi brevi, descrizioni di 2-4 frasi, **nessun pericolo**.
- **Mai aggettivi che danno un genere al giocatore** (niente «attento», «bravo», «tranquillo», «sicuro», «pronto»…): il giocatore può essere una bambina o un bambino.
- Nessun oggetto si chiama «fuoco» (con «dai fuoco a…» il parser leggerebbe un `dai`).
- Il prompt comune e `tests/prompt_rocca.txt` **non cambiano**. Esempi per il modello, se servono, solo in `game.examples` del draghetto.
- Tutto `tests/test_ollama.py` verde prima della PR (i 28 di oggi più i nuovi).
- Mai nei commit: `run.bat`, `test_llm.txt`. File aggiunti uno per uno.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Prove nel browser sulla porta 8765, mai 8000 (lì c'è la partita vera dell'utente).
- **Branch**: `fase-7-draghetto` da `main` (che contiene le PR #13 e #14).

## Decisioni prese nel piano (la spec non le fissava)

1. **Le due uscite chiuse** (il sentiero di casa a sud della radura, «su» sulla quercia) portano a due stanze in cui non si entra mai: `sentiero` (si apre solo con il flag del finale, quando la partita è già finita) e `chioma` (condizione `player_in: chioma`, sempre falsa dalla quercia). Servono al motore per dare il messaggio gentile invece di «Non puoi andare da quella parte.».
2. **Riassunto più corto** per il menu: «Per bambini dagli 8 anni: aiuta un draghetto a ritrovare il suo fuoco.» (quello della spec superava le 80 colonne nel terminale).
3. **Tre regole-indizio in più** per i tentativi più probabili: le more al draghetto («Sai chi va matto per le more? L'orso Tobia!»), il miele all'orso («Portalo a chi ha mal di gola»), aprire il vasetto.
4. **La piuma** si vede solo esaminando il nido o la quercia, come la chiave nel pozzo (spec). La descrizione della quercia invita a guardare («chissà cosa c'è dentro»), e il draghetto parla del nido; «usa il ramo con il nido» funziona anche senza averlo esaminato.

## Review Focus

1. **Un bambino che scrive in modo naturale**: «prendi le more», «dai le more all'orso», «dai il miele al draghetto», «usa il ramo con il nido» col solo parser; frasi libere col modello («do le more all'orso», «stacco la piuma col bastone», «salgo sull'albero», «dai un'occhiata al draghetto») → test di partita a comandi (Task 1) e casi col modello vero (Task 3).
2. **Nessun vicolo cieco**: ogni oggetto utile resta ottenibile; la piuma prima del miele non consuma niente → test in Task 1.
3. **Ordine sbagliato o regalo sbagliato** (piuma prima del miele, more al draghetto, miele all'orso) → un indizio, stato invariato → test in Task 1.
4. **La piuma non ancora vista**: «prendi la piuma» → «Non vedi niente del genere qui.», dopo aver esaminato il nido → «Non ci arrivi.» → test in Task 1.
5. **Due avventure nel browser**: menu con due voci, salvataggi separati, titolo giusto → prova a mano in Task 4.

---

### Task 1: Il mondo del draghetto

**Files:**
- Create: `data/worlds/draghetto/gioco.yaml`, `stanze.yaml`, `oggetti.yaml`, `regole.yaml`, `personaggi.yaml`
- Test: `tests/test_draghetto.py`

**Interfaces:**
- Produces: il mondo con stanze `radura` (inizio), `roveto`, `ruscello`, `tana`, `quercia`, più `sentiero` e `chioma` (mai visitate); oggetti `sasso`, `cespugli`, `more`, `ramo`, `ponticello`, `ruscello`, `quercia`, `nido`, `piuma`, `vasetto_miele`; personaggi `draghetto` (radura), `orso` (tana); regole `scambia_more`, `stacca_piuma`, `miele_al_drago`, `solletico`, `more_al_drago`, `miele_all_orso`, `apri_vasetto`; flag `miele_dato`, `piuma_presa`, `gola_guarita`, `fuoco_tornato`.

- [ ] **Step 1: Branch**

```powershell
git checkout main; git pull --ff-only; git checkout -b fase-7-draghetto
```

- [ ] **Step 2: I test del mondo (falliscono: la cartella non c'è)**

Create `tests/test_draghetto.py`:

```python
"""Il draghetto raffreddato, the adventure for kids: invariants of its puzzles, then the game played
through the engine and with typed commands.

Chain: berries -> the bear gives the honey; the branch knocks the feather out of the nest; honey to
the dragon (its throat), then the feather (a sneeze) -> its fire is back and the game ends.
"""

import pytest

from app.engine import engine as messages
from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_world
from app.engine.models import Action, Direction, GameState, World
from app.game import Game


@pytest.fixture(scope="module")
def dragon() -> World:
    return load_world(WORLDS_DIR / "draghetto")


def start(world: World) -> tuple[Engine, GameState]:
    engine = Engine(world)
    state, _ = engine.new_game()
    return engine, state


def play(engine: Engine, state: GameState, actions: list[Action]) -> None:
    for action in actions:
        outcome = engine.execute(state, action)
        assert outcome.ok, f"{action} was refused: {outcome.text}"


# From the clearing: berries, branch, the bear's honey; back in the clearing with both.
TO_THE_HONEY = [
    Action(verb="vai", direction="est"),
    Action(verb="prendi", target="more"),
    Action(verb="vai", direction="ovest"),
    Action(verb="vai", direction="ovest"),
    Action(verb="prendi", target="ramo"),
    Action(verb="vai", direction="ovest"),
    Action(verb="dai", target="more", with_="orso"),
    Action(verb="vai", direction="est"),
    Action(verb="vai", direction="est"),
]
# From the clearing: the feather from the nest, and back.
TO_THE_FEATHER = [
    Action(verb="vai", direction="nord"),
    Action(verb="usa", target="ramo", with_="nido"),
    Action(verb="vai", direction="sud"),
]
HONEY = Action(verb="dai", target="vasetto_miele", with_="draghetto")
FEATHER = Action(verb="dai", target="piuma", with_="draghetto")


# --- Invariants ----------------------------------------------------------------------------------


def test_five_places_around_the_clearing(dragon):
    assert dragon.game.start_room == "radura"
    exits = dragon.rooms["radura"].exits
    assert {exits[d].to for d in (Direction.NORTH, Direction.EAST, Direction.WEST)} == {"quercia", "roveto", "ruscello"}
    assert dragon.rooms["ruscello"].exits[Direction.WEST].to == "tana"


def test_the_dragon_and_the_bear_only_give_hints(dragon):
    assert dragon.characters["draghetto"].location == "radura"
    assert dragon.characters["orso"].location == "tana"
    # No topic changes the game: talking can't open a shortcut.
    for character in dragon.characters.values():
        assert all(topic.effects == () for topic in character.topics.values())


def test_no_item_is_called_fuoco(dragon):
    # "dai fuoco a…" would become giving.
    assert all("fuoco" not in (item.name, *item.aliases) for item in dragon.items.values())


# --- Playing through the engine ----------------------------------------------------------------


def test_the_whole_game_can_be_played_to_the_end(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + TO_THE_FEATHER + [HONEY])

    last = engine.execute(state, FEATHER)

    assert last.text == dragon.rules["solletico"].text
    assert last.ending == dragon.game.endings[0].text
    assert state.finished


def test_the_feather_before_the_honey_is_only_a_hint(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + TO_THE_FEATHER)

    early = engine.execute(state, FEATHER)

    assert not early.ok
    assert early.text == dragon.rules["solletico"].otherwise
    assert state.item_locations["piuma"] == "inventory"
    assert not state.finished


@pytest.mark.parametrize(
    ("looked", "action"),
    [
        (False, Action(verb="usa", target="ramo", with_="nido")),
        (False, Action(verb="usa", target="ramo", with_="quercia")),
        (True, Action(verb="usa", target="ramo", with_="piuma")),
        (True, Action(verb="prendi", target="piuma", with_="ramo")),
    ],
    ids=["branch on the nest", "branch on the tree", "branch on the feather", "take the feather with the branch"],
)
def test_every_way_of_knocking_the_feather_down_works(dragon, looked, action):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY + [Action(verb="vai", direction="nord")])
    if looked:
        play(engine, state, [Action(verb="esamina", target="nido")])

    outcome = engine.execute(state, action)

    assert outcome.text == dragon.rules["stacca_piuma"].text
    assert state.item_locations["piuma"] == "inventory"


def test_the_feather_has_to_be_seen_before_it_can_be_named(dragon):
    engine, state = start(dragon)
    play(engine, state, [Action(verb="vai", direction="nord")])

    unseen = engine.execute(state, Action(verb="prendi", target="piuma"))
    engine.execute(state, Action(verb="esamina", target="nido"))
    seen = engine.execute(state, Action(verb="prendi", target="piuma"))

    assert unseen.text == messages.NOT_HERE
    assert seen.text == messages.OUT_OF_REACH


def test_the_way_home_and_the_top_of_the_tree_stay_closed(dragon):
    engine, state = start(dragon)

    home = engine.execute(state, Action(verb="vai", direction="sud"))
    engine.execute(state, Action(verb="vai", direction="nord"))
    climb = engine.execute(state, Action(verb="vai", direction="su"))

    assert home.text == dragon.rooms["radura"].exits[Direction.SOUTH].otherwise
    assert climb.text == dragon.rooms["quercia"].exits[Direction.UP].otherwise
    assert state.current_room == "quercia"


def test_the_berries_can_be_dropped_and_taken_again(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:3])

    play(engine, state, [Action(verb="lascia", target="more"), Action(verb="prendi", target="more")])

    assert state.item_locations["more"] == "inventory"


@pytest.mark.parametrize(
    ("before", "gift", "rule"),
    [
        (TO_THE_HONEY[:3], Action(verb="dai", target="more", with_="draghetto"), "more_al_drago"),
        (TO_THE_HONEY[:7], Action(verb="dai", target="vasetto_miele", with_="orso"), "miele_all_orso"),
    ],
    ids=["berries to the dragon", "honey to the bear"],
)
def test_the_wrong_gift_gets_a_hint_and_changes_nothing(dragon, before, gift, rule):
    engine, state = start(dragon)
    play(engine, state, before)
    carried = gift.target
    before_gift = state.model_dump(exclude={"turns"})

    outcome = engine.execute(state, gift)

    assert outcome.text == dragon.rules[rule].text
    assert state.model_dump(exclude={"turns"}) == before_gift
    assert state.item_locations[carried] == "inventory"


def test_the_bear_remembers_the_trade(dragon):
    engine, state = start(dragon)
    play(engine, state, TO_THE_HONEY[:6])
    ask = Action(verb="chiedi", target="orso", topic="miele")

    before = engine.execute(state, ask).text
    play(engine, state, [TO_THE_HONEY[6]])
    after = engine.execute(state, ask).text

    topic = dragon.characters["orso"].topics["miele"]
    assert before == topic.text
    assert after == topic.variants[0].text


# --- Typed commands ------------------------------------------------------------------------------

TYPED = [
    "est",
    "prendi le more",
    "ovest",
    "ovest",
    "prendi il ramo",
    "ovest",
    "dai le more all'orso",
    "est",
    "est",
    "nord",
    "esamina il nido",
    "usa il ramo con il nido",
    "sud",
    "dai il miele al draghetto",
    "dai la piuma al draghetto",
]


def test_a_kid_can_finish_with_simple_commands(dragon):
    game = Game(Engine(dragon))
    outputs = [game.turn(line) for line in TYPED]

    assert outputs[6].startswith(dragon.rules["scambia_more"].text)
    assert outputs[-1].endswith(dragon.game.endings[0].text)
    assert game.finished
```

Run: `.venv\Scripts\python -m pytest tests/test_draghetto.py -q`
Atteso: ERROR — `WorldError: …draghetto: no .yaml files found` (la cartella non esiste).

- [ ] **Step 3: `data/worlds/draghetto/gioco.yaml`**

```yaml
# Il draghetto raffreddato — dati generali della partita.
# Un'avventura per bambini dagli 8 anni: testi brevi, nessun pericolo, nessun vicolo cieco.
# Formato: docs/formato-mondo.md

game:
  title: Il draghetto raffreddato
  summary: "Per bambini dagli 8 anni: aiuta un draghetto a ritrovare il suo fuoco."
  intro: >
    Stai raccogliendo funghi ai margini del Bosco Fatato quando senti uno
    starnuto enorme, così forte che le foglie tremano. Segui il rumore fino a
    una radura e resti a bocca aperta: su un sasso coperto di muschio c'è un
    draghetto verde, con il naso tutto rosso.
  start_room: radura
  endings:
    - when: {flag: fuoco_tornato}
      text: >
        Il draghetto spalanca le ali: adesso sono calde come una coperta.
        «Salta su!», dice, e tu ti aggrappi al suo collo. Volate sopra il
        Bosco Fatato, sopra il ruscello e la tana di Tobia, che vi saluta con
        la zampa. In un attimo sei davanti a casa tua. Il draghetto ti fa
        l'occhiolino e riparte verso la Montagna Rossa, lasciando nel cielo una
        scia di scintille. Che avventura!
```

- [ ] **Step 4: `data/worlds/draghetto/stanze.yaml`**

```yaml
# Stanze del Bosco Fatato. La radura è al centro: il draghetto sta lì e ci si torna spesso.
# Le descrizioni citano gli arredi (scenery: true); gli oggetti trasportabili li elenca il motore.

rooms:
  radura:
    name: Radura
    description: >
      Una radura piena di sole, in mezzo al Bosco Fatato. Al centro c'è un
      grosso sasso coperto di muschio. A nord si vede una vecchia quercia, a
      est un roveto, a ovest si sente scorrere un ruscello. A sud c'è il
      sentiero che porta a casa tua.
    exits:
      nord: {to: quercia}
      est: {to: roveto}
      ovest: {to: ruscello}
      # Si apre solo con il finale, quando la partita è già finita.
      sud:
        to: sentiero
        when: {flag: fuoco_tornato}
        otherwise: >
          Non puoi lasciare il draghetto da solo proprio adesso: ha bisogno del
          tuo aiuto!

  roveto:
    name: Roveto
    description: >
      Cespugli di rovi alti fino alla tua testa, pieni di spine e di more
      mature, nere e lucide. La radura è a ovest.
    exits:
      ovest: {to: radura}

  ruscello:
    name: Ruscello
    description: >
      Un ruscello di acqua limpida chiacchiera tra i sassi. Un ponticello di
      legno lo attraversa verso ovest, dove c'è la tana di un orso. La radura è
      a est.
    exits:
      est: {to: radura}
      ovest: {to: tana}

  tana:
    name: Tana dell'orso
    description: >
      Davanti a una grotta tra le rocce l'erba è tutta schiacciata, e c'è un
      profumo di miele. Il ponticello sul ruscello è a est.
    exits:
      est: {to: ruscello}

  quercia:
    name: Vecchia quercia
    description: >
      Una quercia enorme, più vecchia di tutto il bosco. I rami più bassi sono
      troppo in alto per arrampicarsi. Lassù, tra le foglie, c'è un nido:
      chissà cosa c'è dentro. La radura è a sud.
    variants:
      - when: {flag: piuma_presa}
        text: >
          Una quercia enorme, più vecchia di tutto il bosco. I rami più bassi
          sono troppo in alto per arrampicarsi. Lassù, tra le foglie, c'è un
          nido vuoto. La radura è a sud.
    exits:
      sud: {to: radura}
      # Condizione sempre falsa dalla quercia: in cima non si sale, ma si riceve un indizio.
      su:
        to: chioma
        when: {player_in: chioma}
        otherwise: >
          Provi ad arrampicarti, ma i rami più bassi sono troppo in alto. Ti
          servirebbe qualcosa di lungo per arrivare al nido.

  # --- Stanze in cui non si entra mai: servono alle due uscite chiuse qui sopra ---
  sentiero:
    name: Sentiero
    description: Il sentiero che porta a casa.
    exits:
      nord: {to: radura}

  chioma:
    name: Cima della quercia
    description: In cima alla quercia.
    exits:
      giù: {to: quercia}
```

- [ ] **Step 5: `data/worlds/draghetto/oggetti.yaml`**

```yaml
# Oggetti del Bosco Fatato. location: una stanza, inventory, oppure null
# (fuori gioco: l'oggetto compare solo grazie a una regola).

items:
  # --- Radura ---
  sasso:
    name: sasso
    gender: m
    aliases: [masso, muschio, pietra]
    description: >
      Un grosso sasso rotondo, coperto di muschio morbido. È il posto
      preferito del draghetto.
    location: radura
    scenery: true

  # --- Roveto ---
  cespugli:
    name: cespugli
    gender: m
    plural: true
    aliases: [cespuglio, rovi, rovo, roveto]
    description: Rovi pieni di spine e di more mature. Attenzione a non pungerti!
    location: roveto
    scenery: true

  more:
    name: more
    gender: f
    plural: true
    aliases: [mora]
    description: Una manciata di more nere e lucide. Hanno un profumo dolcissimo.
    location: roveto

  # --- Ruscello ---
  ruscello:
    name: ruscello
    gender: m
    aliases: [acqua, torrente]
    description: Acqua limpida e freddissima. Sul fondo i sassi brillano come monete.
    location: ruscello
    scenery: true

  ponticello:
    name: ponticello
    gender: m
    aliases: [ponte]
    description: >
      Un ponticello di legno, un po' traballante ma solido. Porta alla tana
      dell'orso, a ovest.
    location: ruscello
    scenery: true

  ramo:
    name: ramo
    gender: m
    aliases: [bastone, legno]
    description: Un ramo lungo e dritto, leggero ma robusto. Con questo si arriva in alto!
    location: ruscello

  # --- Vecchia quercia ---
  quercia:
    name: quercia
    gender: f
    aliases: [albero, tronco]
    description: >
      Una quercia enorme: il tronco è così largo che non lo abbracceresti
      nemmeno in tre. Lassù, tra i rami, c'è un nido, e dal bordo spunta una
      lunga piuma bianca.
    location: quercia
    scenery: true
    reveals: [piuma]
    variants:
      - when: {flag: piuma_presa}
        text: >
          Una quercia enorme: il tronco è così largo che non lo abbracceresti
          nemmeno in tre. Lassù, tra i rami, c'è un nido vuoto.

  nido:
    name: nido
    gender: m
    description: >
      Un nido di rametti e paglia, lassù tra i rami, troppo in alto per le
      tue braccia. Dal bordo spunta una lunga piuma bianca.
    location: quercia
    scenery: true
    reveals: [piuma]
    variants:
      - when: {flag: piuma_presa}
        text: Un nido vuoto, lassù tra i rami.

  # --- Fuori gioco all'inizio ---
  piuma:
    name: piuma
    gender: f
    aliases: [penna, piuma bianca]
    description: Una piuma bianca, lunga e morbidissima. Fa il solletico solo a guardarla.
    location: null
    # Nel nido: si vede dalla quercia dopo aver guardato il nido o l'albero; solo il ramo ci arriva.
    visible_from:
      room: quercia
      when: {not: {flag: piuma_presa}}

  vasetto_miele:
    name: vasetto di miele
    gender: m
    aliases: [vasetto, miele, barattolo]
    description: Un vasetto di miele dorato, che profuma di fiori di campo.
    location: null
```

- [ ] **Step 6: `data/worlds/draghetto/regole.yaml`**

```yaml
# Regole del Bosco Fatato. Tre enigmi, ognuno con più soluzioni, e qualche indizio per i
# tentativi sbagliati più probabili. Niente si perde per sbaglio: non ci sono vicoli ciechi.

rules:
  # --- Lo scambio con l'orso ---
  scambia_more:
    trigger: {verb: dai, target: more, with: orso}
    effects:
      - remove: more
      - give: vasetto_miele
      - set_flag: miele_dato
    text: >
      L'orso Tobia annusa le more, se ne infila in bocca una manciata e fa un
      gran sorriso con il muso tutto viola. «Squisite! Un regalo così merita un
      regalo.» Entra nella tana e torna con un vasetto di miele, che ti mette in
      mano.

  # --- La piuma nel nido ---
  stacca_piuma:
    trigger:
      - {verb: usa, target: ramo, with: nido}
      - {verb: usa, target: ramo, with: quercia}
      - {verb: usa, target: ramo, with: piuma}
      - {verb: prendi, target: piuma, with: ramo}
    when: {not: {flag: piuma_presa}}
    otherwise: Nel nido non c'è più niente.
    effects:
      - give: piuma
      - set_flag: piuma_presa
    text: >
      Alzi il ramo più in alto che puoi e dai un colpetto al nido. La piuma si
      stacca, scende volteggiando piano piano… e la prendi al volo!

  # --- La cura del draghetto: prima il miele, poi il solletico ---
  miele_al_drago:
    trigger: {verb: dai, target: vasetto_miele, with: draghetto}
    effects:
      - remove: vasetto_miele
      - set_flag: gola_guarita
    text: >
      Il draghetto infila il muso nel vasetto e lecca il miele fino all'ultima
      goccia. «Mmm, che buono! La gola non mi brucia più.» Poi arriccia il naso:
      «Adesso mi servirebbe solo uno starnuto bello forte…»

  solletico:
    trigger: {verb: dai, target: piuma, with: draghetto}
    when: {flag: gola_guarita}
    otherwise: >
      Passi la piuma sotto il naso del draghetto. «Etci…» Dal naso esce solo
      un filo di fumo grigio. «Ahi, la gola mi brucia ancora troppo», dice con
      un colpo di tosse. «Prima mi servirebbe qualcosa di dolce.»
    effects:
      - set_flag: fuoco_tornato
    text: >
      Passi la piuma sotto il naso del draghetto. Lui strizza gli occhi, apre
      la bocca… «Ah… ah… ETCIÙÙÙ!» Una fiammata arancione illumina tutta la
      radura e fa tremare le foglie. Il draghetto ride e sbuffa scintille: il
      suo fuoco è tornato!

  # --- Indizi per i regali sbagliati ---
  more_al_drago:
    trigger: {verb: dai, target: more, with: draghetto}
    text: >
      Il draghetto annusa le more e sorride: «Grazie, ma con il raffreddore non
      ho fame. Sai chi va matto per le more? L'orso Tobia!»

  miele_all_orso:
    trigger: {verb: dai, target: vasetto_miele, with: orso}
    text: >
      L'orso ti guarda stupito: «Il miele ce l'ho già! Portalo a chi ha mal di
      gola.»

  apri_vasetto:
    trigger: {verb: apri, target: vasetto_miele}
    text: >
      Il vasetto è già aperto e profuma di fiori. Ma non è per te: nel bosco
      c'è qualcuno con un gran mal di gola…
```

- [ ] **Step 7: `data/worlds/draghetto/personaggi.yaml`**

```yaml
# Personaggi del Bosco Fatato. Rispondono solo con i testi scritti qui. Il draghetto dà gli
# indizi, sempre più precisi man mano che si va avanti; l'orso serve allo scambio. Nessuno dei
# due ha effetti: parlare non apre scorciatoie.

characters:
  draghetto:
    name: draghetto
    gender: m
    aliases: [drago, draghino]
    description: >
      Un draghetto verde, grande più o meno come un cane, con le ali piccole e
      ripiegate. Ha il naso tutto rosso, gli occhi lucidi, e ogni tanto
      starnutisce un filo di fumo grigio.
    variants:
      - when: {flag: gola_guarita}
        text: >
          Un draghetto verde, grande più o meno come un cane. Il naso è ancora
          rosso, ma gli occhi sono allegri: sembra aspettare solo uno starnuto.
    location: radura
    greeting: >
      «Etciù!» Il draghetto tira su col naso e ti guarda con gli occhi lucidi.
      «Ciao… scusa, ho un raffreddore tremendo. Mi si è spento il fuoco e non
      riesco più a volare fino a casa. Mi aiuti? Se hai dubbi, chiedimi pure.»
    unknown: >
      Il draghetto piega la testa di lato: «Questo non lo so. Però so tante cose
      sul bosco, sul miele e sul mio raffreddore!»
    refuses: >
      Il draghetto annusa e scuote la testa: «Grazie, ma non è questo che mi
      serve.»
    topics:
      raffreddore:
        name: raffreddore
        gender: m
        aliases: [fuoco, fiamma, gola, febbre]
        text: >
          «Ieri ho fatto il bagno nel ruscello gelato, e stamattina… etciù! Il
          raffreddore mi ha spento il fuoco. La nonna diceva che per la gola ci
          vuole qualcosa di dolce, e poi uno starnuto bello forte per far
          ripartire la fiamma.»
        variants:
          - when: {flag: gola_guarita}
            text: >
              «La gola va molto meglio, grazie al miele! Ora mi manca solo uno
              starnuto. Qualcosa che mi faccia il solletico al naso…»

      miele:
        name: miele
        gender: m
        aliases: [vasetto, dolce]
        text: >
          «L'orso Tobia ha sempre un vasetto di miele nella sua tana, di là dal
          ruscello. Ma è goloso: di sicuro vorrà qualcosa in cambio.»
        variants:
          - when: {flag: gola_guarita}
            text: «Era buonissimo. Grazie, grazie!»
          - when: {has: vasetto_miele}
            text: >
              «È miele quello che hai? Profuma di fiori! Dammelo, ti prego: la
              gola mi brucia tanto.»

      orso:
        name: orso
        gender: m
        aliases: [tobia, tana]
        text: >
          «Tobia è un orso buono, anche se brontola sempre. Va matto per le more:
          ne mangerebbe un cesto intero.»

      more:
        name: more
        gender: f
        plural: true
        aliases: [mora, roveto]
        text: «Le more crescono nel roveto, a est di qui. Attenzione alle spine!»

      solletico:
        name: solletico
        gender: m
        aliases: [piuma, starnuto, naso]
        text: >
          «Per starnutire forte mi servirebbe qualcosa che mi faccia il solletico
          al naso. Qualcosa di morbido e leggero… Gli uccelli ne perdono sempre
          qualcuna.»
        variants:
          - when: {all: [{has: piuma}, {flag: gola_guarita}]}
            text: «Una piuma! Presto, fammi il solletico!»
          - when: {has: piuma}
            text: >
              «Una piuma! È proprio quello che ci vuole. Ma prima la gola deve
              guarire, se no lo starnuto non viene.»

      quercia:
        name: quercia
        gender: f
        aliases: [nido, albero]
        text: >
          «La vecchia quercia è a nord della radura. Lassù c'è un nido, troppo
          alto per te… ma con qualcosa di lungo forse ci arrivi. Il ruscello
          porta sempre rami di tutte le misure.»

      casa:
        name: casa
        gender: f
        aliases: [montagna, montagna rossa, ali, volare]
        text: >
          «Abito sulla Montagna Rossa, oltre il bosco. Ma senza fuoco nella
          pancia ho le ali fredde, e con le ali fredde non si vola.»

      bosco:
        name: bosco
        gender: m
        aliases: [bosco fatato]
        text: >
          «È il Bosco Fatato: gli alberi sono vecchi e gentili, e nessuno fa del
          male a nessuno. Puoi girarlo senza paura.»

  orso:
    name: orso
    gender: m
    aliases: [tobia, orso tobia]
    description: >
      Un orso bruno e grosso, con la pancia rotonda e il muso sporco di
      briciole. Sta seduto davanti alla sua tana e brontola tra sé.
    location: tana
    greeting: >
      «Grrr… chi va là?» L'orso Tobia ti annusa da lontano, poi si siede per
      terra con un tonfo. «Ah, niente paura. Se hai qualcosa di buono da
      mangiare, siamo amici.»
    unknown: "L'orso si gratta la pancia: «Mah. Io penso solo a mangiare.»"
    refuses: "L'orso annusa e sbuffa: «Non è una cosa da mangiare.»"
    topics:
      miele:
        name: miele
        gender: m
        aliases: [vasetto]
        text: >
          «Il mio miele? È il più buono del bosco. Non lo regalo a nessuno… a
          meno che non mi porti qualcosa di altrettanto buono.»
        variants:
          - when: {flag: miele_dato}
            text: «Il miele te l'ho già dato. Le more erano squisite!»

      more:
        name: more
        gender: f
        plural: true
        aliases: [mora]
        text: >
          «More! Ah, le more… Crescono nel roveto, ma io con queste zampe mi
          pungo sempre.»

      draghetto:
        name: draghetto
        gender: m
        aliases: [drago]
        text: «Il draghetto starnutisce da stamattina, si sente fin qui. Poverino.»
```

- [ ] **Step 8: Verificare**

Run: `.venv\Scripts\python -m pytest tests/test_draghetto.py -q` → tutti verdi.
Run: `.venv\Scripts\python -m pytest -q` → tutti verdi.

Controllo dei testi (nessun aggettivo che dia un genere al giocatore):

```powershell
.venv\Scripts\python -m pytest -q
```
e Grep su `data/worlds/draghetto/` delle parole `attento|attenta|bravo|brava|tranquillo|tranquilla|sicuro|sicura|pronto|pronta|stanco|stanca|solo |sola ` (case-insensitive): nessun risultato riferito al giocatore («da solo» riferito al draghetto va bene).

- [ ] **Step 9: Commit**

```powershell
git add docs/superpowers/plans/2026-09-26-draghetto.md data/worlds/draghetto/gioco.yaml data/worlds/draghetto/stanze.yaml data/worlds/draghetto/oggetti.yaml data/worlds/draghetto/regole.yaml data/worlds/draghetto/personaggi.yaml tests/test_draghetto.py
git commit -m "Il draghetto raffreddato: il Bosco Fatato, i suoi enigmi e i suoi personaggi" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Nel menu, nel web e nella documentazione

**Files:**
- Modify: `data/worlds/avventure.yaml`, `README.md`, `docs/formato-mondo.md`
- Test: `tests/test_loader.py` (`test_the_real_adventures_load`), `tests/test_web.py`

**Interfaces:**
- Consumes: il mondo del Task 1.
- Produces: l'indice `[rocca, draghetto]`; il menu mostra due voci.

- [ ] **Step 1: Test che falliscono**

`tests/test_loader.py`, in `test_the_real_adventures_load`: `assert list(worlds) == ["rocca"]` → `assert list(worlds) == ["rocca", "draghetto"]`, e in fondo `assert worlds["draghetto"].game.title == "Il draghetto raffreddato"`.

`tests/test_web.py`, in fondo:

```python
def test_the_dragon_adventure_can_be_finished_through_http():
    worlds = load_adventures()
    client = TestClient(create_app({adventure_id: Engine(world) for adventure_id, world in worlds.items()}, llm=None))
    reply = new_game(client, "draghetto")
    commands = [
        "est", "prendi le more", "ovest", "ovest", "prendi il ramo", "ovest", "dai le more all'orso",
        "est", "est", "nord", "usa il ramo con il nido", "sud", "dai il miele al draghetto",
        "dai la piuma al draghetto",
    ]  # fmt: skip

    for line in commands:
        reply = turn(client, line, reply["state"], "draghetto")

    assert reply["finished"] is True
    assert reply["text"].endswith("Che avventura!")
    assert [a["id"] for a in client.get("/api/adventures").json()] == ["rocca", "draghetto"]
```

(con `from app.engine.loader import WORLDS_DIR, load_adventures, load_world` nell'import).

Run: `.venv\Scripts\python -m pytest tests/test_loader.py tests/test_web.py -q`
Atteso: FAIL su `test_the_real_adventures_load` e sull'elenco delle avventure (il draghetto non è nell'indice).

- [ ] **Step 2: L'indice**

`data/worlds/avventure.yaml`: la lista diventa

```yaml
adventures:
  - rocca
  - draghetto
```

Run: `.venv\Scripts\python -m pytest -q` → tutti verdi.

- [ ] **Step 3: Documentazione**

`docs/formato-mondo.md`, riga 5: «L'esempio completo è la Rocca di Serravento in `data/worlds/rocca/`.» → «Gli esempi completi sono la Rocca di Serravento (`data/worlds/rocca/`) e il draghetto raffreddato (`data/worlds/draghetto/`), che usa anche `dai` e le uscite chiuse con un indizio.»

`README.md` (con Edit, una sostituzione per punto):
- riga 3: «Un'avventura testuale in stile anni '80/'90, ambientata in un castello e giocabile dal browser.» → «Avventure testuali in stile anni '80/'90, giocabili dal browser: un castello per i grandi e un bosco fatato per i bambini.»
- nel riquadro «Stato»: «Il castello **si gioca dal browser o dal terminale**.» → «Le avventure **si giocano dal browser o dal terminale**.»
- il titolo «## Il mondo di esempio» → «## Le avventure»; dopo il paragrafo della Rocca, un paragrafo nuovo:

```markdown
**Il draghetto raffreddato**, per bambini dagli 8 anni: nel Bosco Fatato un draghetto ha perso
il fuoco per colpa di un raffreddore e non riesce più a volare fino a casa. Bisogna aiutarlo, con
l'orso Tobia, un nido in cima a una quercia e gli indizi del draghetto stesso.
```

- «Il mondo è descritto in file YAML in `data/worlds/rocca/` (stanze, oggetti, regole degli enigmi, finali).» → «Ogni avventura è descritta in file YAML in una cartella di `data/worlds/` (stanze, oggetti, regole degli enigmi, personaggi, finali), e `data/worlds/avventure.yaml` dà l'ordine del menu.»; «per scrivere un nuovo castello» → «per scrivere una nuova avventura»;
- «Come si gioca», il paragrafo «La partita si salva da sola nel browser…» diventa:

```markdown
All'inizio scegli l'avventura dal menu: toccandola, oppure scrivendo il numero o il nome.
Ogni avventura si salva da sola nel browser (`localStorage`): ricaricando la pagina riprendi da
dove eri. Il server non tiene nessuna partita, quindi riavviarlo non perde niente; ogni browser ha
le sue. Nella riga di stato in basso, «Avventure» torna al menu senza perdere niente e «Nuova
partita» ricomincia da capo l'avventura in corso, dopo una conferma. Se nel frattempo il mondo è
cambiato (stanze o oggetti diversi nei file YAML), la partita salvata ricomincia. Sempre nella riga
in basso scegli il colore dello schermo, fosfori verdi o ambra, come i monitor dell'epoca; la
scelta resta anche per le partite successive.
```

- dopo il blocco `python -m app.cli`: «Anche nel terminale si comincia scegliendo l'avventura.» prima di «I due modi usano lo stesso motore…».

- [ ] **Step 4: Commit**

```powershell
git add data/worlds/avventure.yaml tests/test_loader.py tests/test_web.py docs/formato-mondo.md README.md
git commit -m "Menu: il draghetto raffreddato accanto alla Rocca" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Frasi da bambino col modello vero

**Files:**
- Modify: `tests/test_ollama.py`; se serve, `data/worlds/draghetto/gioco.yaml` (`examples`)

**Interfaces:**
- Consumes: il mondo del Task 1.

- [ ] **Step 1: Gli esempi del mondo giusto**

In `tests/test_ollama.py`, `understood` passa oggi `CASTLE.game.examples`: diventa `engine.world.game.examples`, così ogni mondo usa i suoi.

- [ ] **Step 2: I casi del draghetto**

In fondo a `tests/test_ollama.py`:

```python
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
```

- [ ] **Step 3: Col modello vero, prima i casi del draghetto**

```powershell
$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s -k dragon
```
Atteso: 9 su 9.

Se un caso fallisce, nell'ordine (rilanciando `-k dragon` a ogni tentativo):
1. se il modello sceglie un altro modo sensato di fare la stessa cosa (per esempio `tira piuma con ramo`), aggiungere quel trigger alla regola, come per il rampino nella Rocca («più soluzioni per un enigma»), con il suo test in `tests/test_draghetto.py`;
2. altrimenti un esempio in `game.examples` del draghetto (`data/worlds/draghetto/gioco.yaml`, formato del prompt: righe `Oggetti:`, `Uscite:`, `Frase:` e risposta JSON), con un mondo **diverso** dal caso fallito, come fanno gli esempi generici;
3. se «dai un'occhiata al draghetto» diventa `dai`: annotarlo e riportarlo all'utente, senza toccare il prompt comune.

Se dopo i tentativi resta un caso rosso: **fermarsi** e riportare all'utente quali frasi cadono e cosa si è provato.

- [ ] **Step 4: Tutto il file**

```powershell
$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s
```
Atteso: 37 su 37 (28 della Rocca + 9 del draghetto). Il prompt della Rocca non è cambiato: `.venv\Scripts\python -m pytest -q` resta verde, compreso `test_the_castle_prompt_is_the_one_checked_on_the_real_model`.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_ollama.py
git commit -m "Test col modello vero: frasi da bambino nel draghetto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(più `data/worlds/draghetto/gioco.yaml`, `data/worlds/draghetto/regole.yaml` e `tests/test_draghetto.py` se lo Step 3 li ha toccati.)

---

### Task 4: Prova nel browser, CLAUDE.md e PR

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Prova a mano nel browser (porta 8765)**

`$env:LLM="off"; .venv\Scripts\python -m uvicorn app.main:create_app_from_env --factory --host 127.0.0.1 --port 8765` in background, poi `http://127.0.0.1:8765/?v=3` (con Claude in Chrome, via JavaScript: la finestra può essere nascosta). Controllare:
1. il menu ha due voci, «1. La Rocca di Serravento» e «2. Il draghetto raffreddato», con i riassunti;
2. scrivere `2` apre il draghetto: titolo «Il draghetto raffreddato», introduzione, «Radura», «Qui c'è un draghetto.», «Uscite: nord, sud, est, ovest.»;
3. qualche comando («parla con il draghetto», «est», «prendi le more»), poi «Avventure»: il draghetto ha «(partita in corso)»; scegliere la Rocca → partita nuova della Rocca; tornare al draghetto → riprende dalle more;
4. a 375 px il riassunto del draghetto sta nella colonna senza scorrimento orizzontale;
5. console senza errori; alla fine `localStorage.clear()`, chiudere la scheda, fermare il server.

- [ ] **Step 2: CLAUDE.md**

- «Decisioni prese»: nuova voce

```markdown
- **Il draghetto raffreddato** (fase 7, pezzo 3, 2026-09-26): avventura per bambini dagli 8 anni in
  `data/worlds/draghetto/`, solo dati. Cinque luoghi intorno alla radura, tre enigmi (le more
  all'orso per il miele, il ramo per la piuma nel nido, prima il miele e poi la piuma al drago),
  il draghetto che dà indizi sempre più precisi, qualche regola-indizio per i regali sbagliati.
  Le uscite chiuse con un indizio portano a stanze in cui non si entra mai (`sentiero`, `chioma`).
  Testi senza aggettivi che diano un genere al giocatore.
```

- «Risultati dei test»: il conteggio di `tests/test_ollama.py` diventa quello dello Step 4 del Task 3 (es. «37 su 37, ~4 min»), e una riga su cosa è servito per il draghetto (trigger o esempi aggiunti, se ci sono stati, e come è andata «dai un'occhiata al draghetto»).

- [ ] **Step 3: Verifica finale e commit**

```powershell
.venv\Scripts\python -m pytest -q
git add CLAUDE.md
git commit -m "CLAUDE.md: il draghetto raffreddato" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
```
Atteso: tutti verdi; restano solo `run.bat` e `test_llm.txt`.

- [ ] **Step 4: Chiedere all'utente prima di push e PR**

Mostrare `git log --oneline main..HEAD`, chiedere se fare push e PR. Senza `gh`, la PR si apre dal link di GitHub con titolo e testo precompilati; il testo finisce con:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
