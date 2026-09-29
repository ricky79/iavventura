# La Stella di Valdimora, atto 1: il pianterreno — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Valdimora compare nel menu e il suo primo atto si gioca dall'arrivo fino allo scalone aperto, con il filo facoltativo della prova 1, cinque personaggi che parlano, tutti gli arredi esaminabili e un finale provvisorio «Fine del primo atto».

**Architecture:** quasi tutto è dati in `data/worlds/valdimora/` (`gioco.yaml`, `pianterreno.yaml`, `personaggi.yaml`), provati da `tests/test_valdimora.py` giocando con i comandi semplici. Una sola aggiunta al codice, necessaria per i personaggi di Valdimora: i nomi propri (`article`), perché oggi il motore scriverebbe «Qui c'è un Ettore» e «chiedi all'Ettore». Alla fine una giocata col modello vero, le cui frasi diventano casi di `tests/test_ollama.py`.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, pytest; Ollama con qwen2.5:3b per i test col modello vero.

**Spec:** `docs/superpowers/specs/2026-09-29-valdimora-design.md` — sezioni 1 (storia), 2 (atti), 3 (piantina: piano terra), 4 (enigmi: atto 1) e 6 (costruzione e prove).

## Global Constraints

- Branch: `feature/valdimora-atto-1` (già creato da `main` aggiornato). Il piano si committa nel primo commit del Task 1.
- Nessuna dipendenza nuova. Comandi con `.venv/Scripts/python` (Git Bash) o `.venv\Scripts\python` (PowerShell).
- Codice e identificatori in inglese; testi, commit e documentazione in italiano.
- **Il prompt dell'LLM della Rocca non cambia.** Valdimora non ha `game.examples` finché la giocata col modello vero (Task 5) non ne mostra il bisogno; se se ne aggiungono, tutto `tests/test_ollama.py` va rigiocato e deve restare verde (a parte i limiti noti).
- **Testi**: la protagonista è **Irene** e i testi le si rivolgono **al femminile** («sei entrata»); i domestici, il dottore, Corrado e Agnese le danno del **voi** («signorina»); la contessa, nei biglietti privati, le dà del **tu** e firma «A.». Registro del 1927, senza anacronismi. Ogni descrizione di stanza nomina le stanze vicine col loro nome; ogni cosa nominata in una descrizione è un arredo esaminabile; un indizio che manda a fare qualcosa ha una variante per quando è fatto (regole di CLAUDE.md).
- I testi scritti in questo piano sono quelli da usare: l'utente li rilegge qui e poi nella PR.
- Mai nei commit: `run.bat`, `run_log.bat`, `test_llm.txt`. Aggiungere i file uno per uno, mai `git add -A` o `git add .`.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Heredoc e backslash: per testi con `\n` o `\u` usare Edit (mai heredoc né `sed`), e controllare con grep dopo Write. I file YAML di questo piano non contengono backslash: si scrivono con Write.
- Prove nel browser, se servono: porta 8799 (la 8000 e la 8765 sono occupate nel Chrome dell'utente).

## Decisioni prese nel piano (la spec non le copriva)

1. **Nomi propri** (Task 1): campo facoltativo `article` su oggetti, personaggi e argomenti. `none` per i nomi di persona («Ettore», «a Ettore», «di Livia», «Qui c'è Agnese»), `definite` per i nomi col titolo o gli oggetti unici («il dottor Ferri», «al dottor Ferri», «Qui c'è il dottor Ferri», mai «un dottor Ferri»). Senza `article`, tutto come oggi.
2. **La Loggia provvisoria**: lo scalone porta a una stanza `loggia` con un testo segnaposto; nessuno ci entra, perché aprire la porta dello scalone chiude il primo atto (finale provvisorio sul flag `atto_due`). L'atto 2 la riscriverà.
3. **Ettore garantisce per Irene anche prima della lettera**: l'argomento «Livia» è sempre disponibile e attiva `ettore_garantisce`. Un effetto non può dipendere da una condizione, e la spec voleva l'argomento solo dopo il dubbio di Livia, che però sta in un `otherwise` (che non attiva flag). Si risolve comunque parlando con tutti e due, in qualunque ordine.
4. **Gli oggetti degli atti futuri si piantano ora**: forbici da potatura e tanica di petrolio nella rimessa, fiammiferi in cucina, il rosaio della serra, la porta della cantina. Così il castello si intreccia fin dal primo atto («un oggetto trovato ora serve dopo»), e gli atti successivi non devono tornare sui file del pianterreno solo per aggiungerli.
5. **La valigia non si prende**: è un arredo (troppo pesante da portarsi dietro); si apre.
6. **Gli argomenti dei personaggi ai loro primi passi**: nessun argomento dà scorciatoie; gli unici effetti sono la garanzia di Ettore e la chiave della credenza (filo facoltativo). Lo controlla un test.
7. **Niente atti (`acts`) nel primo atto**: nel pianterreno non si muore, quindi non serve il salvataggio; gli atti entrano con l'atto 2.
8. **«ad» come «a»** (Task 3): il parser ignora già «a», ma non la sua forma davanti a vocale; senza, «dai il medaglione ad Agnese» non si capisce senza LLM. «ad» entra tra le parole che il parser ignora (`STOPWORDS`).

## Review Focus

1. **Le cose fatte nell'ordine sbagliato**: il biglietto a Livia prima della parola di Ettore; il medaglione nella meridiana prima dell'olio; l'olio prima di aver letto la busta; la credenza senza chiave; la borsa col dottore sveglio. Ognuna deve dare un testo che aiuta, e lasciare lo stato com'era — test nel Task 2 (`test_things_done_in_the_wrong_order_give_a_hint`) e nel Task 3 (`test_the_optional_thread_in_the_wrong_order`).
2. **Due chiavi in tasca**: con la chiave dello scalone e quella della credenza, «apri la credenza con la chiave» chiede «Quale intendi», e nominando la chiave giusta funziona — test nel Task 3 (`test_two_keys_ask_which_one`).
3. **Regali sbagliati**: la grappa a Corrado, la lettera a Livia, il medaglione a chiunque: rifiutati, e l'oggetto resta a Irene — test nel Task 3 (`test_wrong_gifts_are_refused_and_kept`).
4. **Il dottore addormentato**: parlargli o chiedergli qualcosa risponde che russa, non con i testi di quando è sveglio — test nel Task 3 (`test_the_sleeping_doctor_only_snores`).
5. **Frasi libere con le parole che un giocatore usa davvero** («mostro la lettera al maggiordomo», «leggo il biglietto della contessa», «infilo il medaglione nell'incavo») — Task 5, col modello vero.

---

### Task 1: I nomi propri

**Files:**
- Modify: `app/engine/models.py` (nuovo enum `Article`, campo `article` su `Item`, `Character`, `Topic`), `app/engine/text.py` (`definite`, `articulated`, `indefinite`), `docs/formato-mondo.md`
- Test: `tests/test_text.py`

**Interfaces:**
- Produces: `Article.DEFINITE == "definite"`, `Article.NONE == "none"`; `Item.article`, `Character.article`, `Topic.article`: `Article | None = None`. `definite`, `articulated` e `indefinite` ne tengono conto; tutto ciò che scrive nomi (riga «Qui c'è…», «Quale intendi», azioni tra parentesi, conferme) passa da lì.

- [ ] **Step 1: Committare il piano**

```bash
git status --short   # atteso: run.bat, run_log.bat, test_llm.txt e questo piano non tracciati
git add docs/superpowers/plans/2026-09-29-valdimora-atto-1.md
```
(il commit arriva allo Step 5, col codice.)

- [ ] **Step 2: Test che falliscono**

In `tests/test_text.py`:

l'import dei modelli diventa `from app.engine.models import Action, Article, Direction, Item, RoomView, World` (controllare la riga esistente e aggiungere solo `Article`);

dopo `test_prepositions_join_the_article`:
```python
@pytest.mark.parametrize(
    ("name", "gender", "article", "the", "a", "to_the", "of_the"),
    [
        ("Ettore", "m", "none", "Ettore", "Ettore", "a Ettore", "di Ettore"),
        ("Livia", "f", "none", "Livia", "Livia", "a Livia", "di Livia"),
        ("dottor Ferri", "m", "definite", "il dottor Ferri", "il dottor Ferri", "al dottor Ferri", "del dottor Ferri"),
        ("Stella di Valdimora", "f", "definite", "la Stella di Valdimora", "la Stella di Valdimora",
         "alla Stella di Valdimora", "della Stella di Valdimora"),
    ],
)  # fmt: skip
def test_proper_names_take_their_own_article(name, gender, article, the, a, to_the, of_the):
    proper = Item(id="nome", name=name, gender=gender, article=article, description="-", location=None)

    assert (definite(proper), indefinite(proper)) == (the, a)
    assert (articulated("a", proper), articulated("di", proper)) == (to_the, of_the)
```

in fondo al file:
```python
def test_characters_with_a_proper_name(keeper_world):
    keeper_world["characters"]["custode"].update(name="Ettore", article="none")
    keeper_world["characters"]["custode"]["topics"]["cella"].update(name="Livia", article="none")
    world = World.model_validate(keeper_world)

    here = render(Outcome(ok=True, room=room_with(world, "custode")), world)

    assert "Qui c'è Ettore." in here
    assert action_text(Action(verb="chiedi", target="custode", topic="cella"), world) == "chiedi a Ettore di Livia"
    assert confirmation(Action(verb="dai", target="moneta", with_="custode"), world) == "Vuoi dare la moneta a Ettore?"


def test_a_title_is_always_definite(keeper_world):
    keeper_world["characters"]["custode"].update(name="dottor Ferri", article="definite")
    world = World.model_validate(keeper_world)

    here = render(Outcome(ok=True, room=room_with(world, "custode")), world)

    assert "Qui c'è il dottor Ferri." in here
    assert action_text(Action(verb="parla", target="custode"), world) == "parla con il dottor Ferri"


def room_with(world: World, *characters: str) -> RoomView:
    return RoomView(id="atrio", name="Atrio", description="Un atrio.", items=(), exits=(), first_visit=True,
                    characters=characters)  # fmt: skip
```
e aggiungere `Outcome` all'import dei modelli se non c'è già.

- [ ] **Step 3: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_text.py -q`
Expected: FAIL — `Article` non esiste (errore d'import).

- [ ] **Step 4: Implementazione**

In `app/engine/models.py`, dopo `class Gender`:
```python
class Article(StrEnum):
    """How a name takes its article, when not like a common noun (il gancio, un gancio)."""

    DEFINITE = "definite"  # always the definite article: "il dottor Ferri", never "un dottor Ferri"
    NONE = "none"  # no article: a first name, "Ettore", "a Ettore", "di Livia"
```
e in `class Item`, `class Topic` e `class Character`, subito dopo `plural: bool = False`:
```python
    article: Article | None = None  # a proper name or a title (Article); without it, like a common noun
```

In `app/engine/text.py`, importare `Article` dai modelli e:
```python
def definite(item: Named) -> str:
    """The name with its definite article: il gancio, lo specchio, l'uncino, la corda, gli attrezzi;
    a first name without one: Ettore."""
    if item.article is Article.NONE:
        return item.name
    return _definite_article(item) + item.name


def articulated(preposition: str, item: Named) -> str:
    """The name after "a", "di" or "in", joined to its article: al pellegrino, della torre, nel pozzo;
    a first name keeps the preposition apart: a Ettore, di Livia."""
    if item.article is Article.NONE:
        return f"{preposition} {item.name}"
    return _ARTICULATED[preposition][_definite_article(item)] + item.name
```
e all'inizio di `indefinite`:
```python
    if item.article is not None:
        # Someone or something already known by name: "Qui c'è Ettore", "Qui c'è il dottor Ferri".
        return definite(item)
```
(aggiornare la docstring di `indefinite`: «…; a proper name or a title keeps its own: Ettore, il dottor Ferri»).

In `docs/formato-mondo.md`:
- nel blocco YAML di `items`, dopo `plural: false …`: `    article: definite            # facoltativo: definite (sempre l'articolo determinativo) o none (nessun articolo)`;
- nel blocco YAML di `characters`, dopo `plural: false`: `    article: none                # facoltativo: none per un nome di persona, definite per un titolo`;
- dopo l'elenco degli articoli degli oggetti («`gender` e `plural` servono agli articoli…»), un punto:
  > - `article` per i nomi propri: `none` per un nome di persona, che non vuole articolo («Ettore», «a Ettore», «di Livia», «Qui c'è Agnese»); `definite` per un titolo o una cosa unica, che vuole sempre il determinativo («il dottor Ferri», «Qui c'è il dottor Ferri», mai «un dottor Ferri»). Vale anche per gli argomenti dei personaggi («chiedi a Ettore di Livia»).

- [ ] **Step 5: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde.

```bash
git add app/engine/models.py app/engine/text.py docs/formato-mondo.md tests/test_text.py
git commit -m "Testi: i nomi propri (article: none per Ettore, definite per il dottor Ferri)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Il pianterreno, il filo principale, Ettore e Livia

**Files:**
- Create: `data/worlds/valdimora/gioco.yaml`, `data/worlds/valdimora/pianterreno.yaml`, `data/worlds/valdimora/personaggi.yaml`, `tests/test_valdimora.py`
- Modify: `data/worlds/avventure.yaml`, `tests/test_loader.py:303`, `tests/test_web.py:288`

**Interfaces:**
- Consumes: `article` (Task 1).
- Produces: il mondo `valdimora` con le 13 stanze e la Loggia provvisoria; i flag `busta_data`, `busta_letta`, `meridiana_oliata`, `meridiana_aperta`, `ettore_garantisce`, `livia_chiave`, `valigia_aperta`, `atto_due`; gli oggetti del filo principale; Ettore e Livia. In `tests/test_valdimora.py` la fixture `valdimora` e l'helper `play(game, *lines) -> list[str]`, usati dai Task 3 e 4.

- [ ] **Step 1: Test che falliscono**

Creare `tests/test_valdimora.py`:
```python
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
```

In `tests/test_loader.py:303` e `tests/test_web.py:288`, l'elenco atteso diventa `["rocca", "draghetto", "valdimora"]`.

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py tests/test_loader.py tests/test_web.py -q`
Expected: FAIL — la cartella `valdimora` non esiste; i due elenchi non hanno `valdimora`.

- [ ] **Step 3: `data/worlds/avventure.yaml`**

In fondo all'elenco: `  - valdimora`.

- [ ] **Step 4: `data/worlds/valdimora/gioco.yaml`**

```yaml
# La Stella di Valdimora — dati generali della partita.
# Spec: docs/superpowers/specs/2026-09-29-valdimora-design.md. Formato: docs/formato-mondo.md
# Il primo atto finisce aprendo la porta dello scalone (finale provvisorio: lo toglie l'atto 2).

game:
  title: La Stella di Valdimora
  summary: >-
    Autunno 1927: una contessa che non conosci ti chiama nel suo castello di montagna.
    (In costruzione: per ora il primo atto.)
  intro: >
    Genova, ottobre 1927. La lettera è arrivata su carta color avorio, firmata da una contessa di
    cui non avevi mai sentito parlare: «Ho una cosa che appartiene a voi e a vostra madre. Venite a
    Valdimora, vi spiegherò ogni cosa.» Tua madre, Clara, è morta da nove anni, e di Valdimora non
    ti ha mai detto una parola. Ti ha lasciato soltanto un medaglione d'argento con una stella
    incisa. Così hai preso la corriera. L'ultimo tratto di strada sale tra i castagni sotto una
    pioggia fitta; il vetturino ti lascia davanti al castello, mette la tua valigia nella rimessa e
    riparte in fretta verso valle. Poco dopo, un boato: una frana ha chiuso la strada alle sue
    spalle. Il portone di Valdimora è socchiuso. Entri.
  start_room: atrio
  endings:
    - when: {flag: atto_due}
      text: >
        Sali i primi gradini dello scalone. Sopra di te il piano nobile è buio, e da qualche parte,
        lassù, c'è qualcuno che ti somiglia. Fine del primo atto. (Il secondo è in costruzione.)
```

- [ ] **Step 5: `data/worlds/valdimora/pianterreno.yaml` — stanze, oggetti e regole del filo principale**

```yaml
# Il pianterreno di Valdimora (piano terra): stanze, oggetti e regole del primo atto.
# Spec: docs/superpowers/specs/2026-09-29-valdimora-design.md, sezioni 3 e 4 (atto 1).

rooms:
  atrio:
    name: Atrio
    description: >
      Un atrio alto e freddo, col pavimento a scacchi bianchi e neri. Sul portone da cui sei entrata
      pende un drappo nero, e accanto, su un cavalletto, c'è un annuncio listato a lutto. In fondo,
      lo scalone di pietra sale verso il piano nobile, chiuso da una porta di legno scuro. A nord,
      oltre una vetrata, il cortile; a ovest il salotto, a est la sala del biliardo. A sud, fuori
      sotto la pioggia, la rimessa.
    exits:
      nord: {to: cortile}
      sud: {to: rimessa}
      ovest: {to: salotto}
      est: {to: biliardo}
      su:
        to: loggia
        when: {flag: atto_due}
        otherwise: La porta dello scalone è chiusa a chiave.

  rimessa:
    name: Rimessa
    aliases: [carrozze]
    description: >
      Una rimessa per le carrozze, che sa di cuoio e di fieno bagnato. Di carrozze non ce n'è più:
      solo un calesse senza ruote e, appoggiata al muro, la tua valigia, dove l'ha lasciata il
      vetturino. Sugli scaffali, attrezzi e barattoli. Oltre il cancello, verso valle, la strada
      sparisce sotto la frana. A nord si torna nell'atrio.
    exits:
      nord: {to: atrio}

  salotto:
    name: Salotto
    description: >
      Un salotto di velluti rossi e di specchi appannati. Le poltrone sono coperte da teli bianchi,
      come si usa nelle case in lutto, e il pianoforte è chiuso. Una porta a vetri dà a ovest sulla
      serra; a nord c'è la sala da pranzo, a est l'atrio.
    exits:
      ovest: {to: serra}
      nord: {to: sala_da_pranzo}
      est: {to: atrio}

  serra:
    name: Serra
    description: >
      Una serra di ferro e di vetro, calda e umida dopo il freddo della casa. Limoni in vaso, felci
      e, contro la parete di fondo, un grande rosaio di rose bianche: l'unica cosa in fiore in tutto
      il castello. La pioggia batte sui vetri. A est si torna nel salotto.
    exits:
      est: {to: salotto}

  sala_da_pranzo:
    name: Sala da pranzo
    description: >
      Una lunga tavola apparecchiata per nessuno, sotto un lampadario spento. Contro la parete, una
      credenza di noce. A nord una porta di servizio dà sulla stanza del maggiordomo; a est si esce
      nel cortile, a sud si torna nel salotto.
    exits:
      nord: {to: stanza_maggiordomo}
      est: {to: cortile}
      sud: {to: salotto}

  stanza_maggiordomo:
    name: Stanza del maggiordomo
    description: >
      Una stanzetta di servizio: un tavolo con l'argenteria da lucidare, una sedia impagliata e,
      sopra la porta, una fila di campanelli, uno per ogni stanza del castello. A sud la sala da
      pranzo, a est la cucina.
    exits:
      sud: {to: sala_da_pranzo}
      est: {to: cucina}

  cucina:
    name: Cucina
    description: >
      Una cucina enorme, col focolare acceso e le pentole di rame appese alle travi. In un angolo,
      una porta bassa e sbarrata scende in cantina. A ovest la stanza del maggiordomo, a est la
      dispensa, a nord la lavanderia; a sud si esce nel cortile.
    exits:
      ovest: {to: stanza_maggiordomo}
      est: {to: dispensa}
      nord: {to: lavanderia}
      sud: {to: cortile}

  lavanderia:
    name: Lavanderia
    description: >
      Vasche di pietra, un mastello, lenzuola stese ad asciugare davanti a una stufa di ghisa. Tutto
      sa di sapone e di cenere. A sud si torna in cucina.
    exits:
      sud: {to: cucina}

  dispensa:
    name: Dispensa
    description: >
      Scaffali di conserve, forme di formaggio, sacchi di farina. Appeso al muro, un armadietto dei
      medicinali con lo sportello di vetro smerigliato. A ovest la cucina, a est l'ufficio della
      governante.
    exits:
      ovest: {to: cucina}
      est: {to: ufficio_governante}

  ufficio_governante:
    name: Ufficio della governante
    aliases: [ufficio]
    description: >
      Un ufficio ordinato fino all'ossessione: libri contabili allineati, un calendario fermo al 14
      ottobre e, alla parete, un quadro di legno con decine di chiavi appese, ognuna col suo
      cartellino. A ovest la dispensa, a sud la cappella.
    exits:
      ovest: {to: dispensa}
      sud: {to: cappella}

  cappella:
    name: Cappella
    aliases: [chiesetta]
    description: >
      Una piccola cappella fredda, che sa di cera e di gigli. Tra due file di candele accese c'è una
      bara di legno scuro, chiusa: la contessa riposa qui, in attesa che la strada riapra. A nord
      l'ufficio della governante, a sud la sala del biliardo, a ovest il cortile.
    exits:
      nord: {to: ufficio_governante}
      sud: {to: biliardo}
      ovest: {to: cortile}

  biliardo:
    name: Sala del biliardo
    aliases: [biliardo]
    description: >
      Fumo di sigaro, un tavolo da biliardo con le stecche abbandonate sul panno, un carrello di
      liquori quasi vuoto. Sul tavolino accanto alla poltrona, una borsa da medico di pelle nera. A
      nord la cappella, a ovest l'atrio.
    exits:
      nord: {to: cappella}
      ovest: {to: atrio}

  cortile:
    name: Cortile
    description: >
      Un cortile quadrato, lucido di pioggia. Al centro, su un piedistallo di pietra, c'è una
      vecchia meridiana: con questo cielo non segna nessuna ora. Tutt'intorno, le finestre del
      castello, quasi tutte buie. A sud l'atrio, a nord la cucina, a ovest la sala da pranzo, a est
      la cappella.
    exits:
      sud: {to: atrio}
      nord: {to: cucina}
      ovest: {to: sala_da_pranzo}
      est: {to: cappella}

  # Provvisoria: nessuno ci entra, perché aprire lo scalone chiude il primo atto. La riscrive l'atto 2.
  loggia:
    name: Loggia dello scalone
    description: In cima allo scalone, il piano nobile è buio e silenzioso.
    exits:
      giù: {to: atrio}

items:
  # --- Quello che Irene porta con sé ---
  lettera:
    name: lettera della contessa
    gender: f
    aliases: [lettera, invito]
    description: >
      Carta color avorio, una grafia sottile e un po' tremante. Poche righe, firmate «Adelaide di
      Valdimora».
    location: inventory

  medaglione:
    name: medaglione
    gender: m
    aliases: [ciondolo, medaglione d'argento]
    description: >
      Un medaglione d'argento grande quanto una moneta, con una stella a otto punte incisa sul
      coperchio. Il bordo ha una forma strana, a dentelli, come quello di una chiave. Era di tua
      madre; lo porti al collo.
    location: inventory

  # --- Rimessa ---
  valigia:
    name: valigia
    gender: f
    aliases: [bagaglio]
    description: La tua valigia di cartone, ancora bagnata di pioggia.
    location: rimessa
    scenery: true
    variants:
      - when: {flag: valigia_aperta}
        text: La tua valigia di cartone, aperta. Dentro, solo i tuoi vestiti.

  fotografia:
    name: fotografia di tua madre
    gender: f
    aliases: [fotografia, foto]
    description: >
      Tua madre a trent'anni, in uno studio fotografico di Genova: il vestito scuro, i capelli
      raccolti, il medaglione al collo. Non sorride, ma ha gli occhi buoni.
    location: null

  oliatore:
    name: oliatore
    gender: m
    aliases: [olio, lattina]
    description: Un oliatore di latta col beccuccio lungo, per le ruote delle carrozze. È quasi pieno.
    location: rimessa

  # --- Atrio ---
  porta_scalone:
    name: porta dello scalone
    gender: f
    aliases: [porta, scalone]
    description: Una porta di legno scuro, in cima ai primi gradini dello scalone. È chiusa a chiave.
    location: atrio
    scenery: true
    variants:
      - when: {flag: atto_due}
        text: La porta dello scalone, aperta sullo scalone buio.

  # --- La pista della contessa ---
  busta:
    name: busta della contessa
    gender: f
    aliases: [busta, cartoncino, indovinello, biglietto della contessa]
    description: >
      Una busta color avorio col sigillo della contessa, ormai rotto. Dentro c'è un cartoncino
      scritto a mano.
    location: null

  meridiana:
    name: meridiana
    gender: f
    aliases: [orologio solare, gnomone, piedistallo, incavo]
    description: >
      Una meridiana di pietra su un piedistallo, con lo gnomone di bronzo verde di ruggine. Sul
      quadrante è inciso un motto: «Horas non numero nisi serenas». Conto solo le ore serene.
    location: cortile
    scenery: true
    variants:
      - when: {flag: meridiana_aperta}
        text: >
          La meridiana di pietra. Alla base del piedistallo, dietro l'incavo a stella, lo
          scomparto è aperto e vuoto.
      - when: {flag: busta_letta}
        text: >
          Una meridiana di pietra con un motto inciso: «Horas non numero nisi serenas». Chinandoti,
          alla base del piedistallo trovi quello che la pioggia nascondeva: un piccolo incavo a
          forma di stella, incrostato di ruggine. Della misura giusta per il tuo medaglione.

  biglietto_livia:
    name: biglietto sigillato
    gender: m
    aliases: [biglietto, biglietto per livia]
    description: Un biglietto piegato e chiuso con la ceralacca della contessa. Sopra c'è scritto «Per Livia».
    location: null

  foglietto:
    name: foglietto
    gender: m
    aliases: [foglio, indizio]
    description: Un foglietto piegato in quattro, nella stessa grafia tremante della busta.
    location: null

  chiave_scalone:
    name: chiave dello scalone
    gender: f
    aliases: [chiave, chiave lunga]
    description: Una chiave lunga, di ferro brunito, ancora tiepida della mano di Livia.
    location: null

rules:
  # --- La valigia e ciò che Irene porta con sé ---
  apri_valigia:
    trigger: {verb: apri, target: valigia}
    when: {not: {flag: valigia_aperta}}
    otherwise: Dentro restano solo i tuoi vestiti.
    effects:
      - give: fotografia
      - set_flag: valigia_aperta
    text: >
      Apri la valigia: i tuoi due vestiti buoni, la camicia da notte e, in fondo, avvolta in un
      fazzoletto, la fotografia di tua madre. La prendi con te.

  prendi_valigia:
    trigger: {verb: prendi, target: valigia}
    text: È troppo pesante per portarla in giro per il castello. La lasci dov'è, per ora.

  lascia_medaglione:
    trigger: {verb: lascia, target: medaglione}
    text: "No: è tutto ciò che ti resta di tua madre."

  leggi_lettera:
    trigger: {verb: leggi, target: lettera}
    text: >
      «Gentile signorina, perdonerete se vi scrivo senza conoscervi. Ho una cosa che appartiene a
      voi e a vostra madre. Venite a Valdimora appena potete: vi spiegherò ogni cosa. Adelaide di
      Valdimora.»

  # --- Ettore e la busta ---
  dai_lettera_ettore:
    trigger: {verb: dai, target: lettera, with: ettore}
    when: {not: {flag: busta_data}}
    otherwise: Ettore scuote la testa. «L'ho già letta, signorina. Tenetela voi.»
    effects:
      - give: busta
      - set_flag: busta_data
    text: >
      Ettore legge la lettera due volte. Poi alza gli occhi, e il suo sguardo si ferma sul
      medaglione che porti al collo. Impallidisce. «Avete gli occhi di vostra madre», mormora.
      Prima che tu possa chiedergli niente, si ricompone e ti porge una busta color avorio, col
      sigillo della contessa. «Mi ha lasciato questa per voi. Solo per voi, ha detto: per la
      ragazza con la lettera.» E ti rende la lettera.

  leggi_busta:
    trigger: {verb: leggi, target: busta}
    effects:
      - set_flag: busta_letta
    text: >
      Sul cartoncino, nella grafia tremante della lettera: «Cara Irene, se leggi queste righe non
      ho fatto in tempo, e te ne chiedo perdono. Quello che ti appartiene l'ho nascosto dove nessun
      altro potrà trovarlo, e la strada comincia qui. Conto le ore solo col sole; quando piove,
      cercami più in basso. A.»

  # --- La meridiana ---
  ungi_meridiana:
    trigger: {verb: usa, target: oliatore, with: meridiana}
    when: {not: {flag: meridiana_oliata}}
    otherwise: Il meccanismo è già unto a dovere.
    effects:
      - set_flag: meridiana_oliata
    text: >
      Versi l'olio nell'incavo e intorno al perno dello gnomone. La ruggine si scioglie in rivoli
      scuri, e la pioggia li porta via.

  apri_meridiana:
    trigger: {verb: usa, target: medaglione, with: meridiana}
    when: {all: [{flag: meridiana_oliata}, {not: {flag: meridiana_aperta}}]}
    otherwise: "Il medaglione entra nell'incavo, ma non gira: il meccanismo è bloccato dalla ruggine."
    otherwise_variants:
      - when: {flag: meridiana_aperta}
        text: Lo scomparto è aperto, e dentro non c'è altro.
    effects:
      - give: biglietto_livia
      - give: foglietto
      - set_flag: meridiana_aperta
    text: >
      Appoggi il medaglione nell'incavo: entra perfettamente, come una chiave nella sua toppa. Lo
      giri, e con uno scatto una lastra di pietra si apre alla base del piedistallo. Dentro,
      avvolti in una tela cerata, ci sono un biglietto sigillato con la scritta «Per Livia» e un
      foglietto piegato in quattro. Li prendi, e ti rimetti il medaglione al collo.

  leggi_foglietto:
    trigger: {verb: leggi, target: foglietto}
    text: «Livia ti aprirà la strada, se sarò io a chiederglielo. Poi, lassù, cerca chi ti somiglia.»

  leggi_biglietto_livia:
    trigger: {verb: leggi, target: biglietto_livia}
    text: È chiuso con la ceralacca, e sopra c'è scritto «Per Livia». Non spetta a te aprirlo.

  # --- Livia e lo scalone ---
  dai_biglietto_livia:
    trigger: {verb: dai, target: biglietto_livia, with: livia}
    when: {flag: ettore_garantisce}
    otherwise: >
      Livia legge il biglietto e stringe le labbra. «È la sua scrittura. Ma una lettera si ruba,
      signorina. Chi garantisce per voi?» Ti rende il biglietto senza aggiungere altro.
    effects:
      - remove: biglietto_livia
      - give: chiave_scalone
      - set_flag: livia_chiave
    text: >
      Livia legge il biglietto, e le mani le tremano. Poi ti guarda a lungo, come se ti vedesse per
      la prima volta. «Ettore dice che siete chi dite di essere. Ed è la sua scrittura», dice piano.
      Si sfila dalla cintura una chiave lunga e te la porge. «Lo scalone. Non fatemene pentire.»

  apri_scalone:
    trigger: {verb: apri, target: porta_scalone, with: chiave_scalone}
    when: {not: {flag: atto_due}}
    otherwise: La porta dello scalone è già aperta.
    effects:
      - set_flag: atto_due
    text: >
      La chiave gira con un rumore secco. La porta si apre sullo scalone buio, che sale verso il
      piano nobile.

  apri_scalone_senza_chiave:
    trigger: {verb: apri, target: porta_scalone}
    when: {not: {flag: atto_due}}
    otherwise: La porta dello scalone è già aperta.
    text: È chiusa a chiave. In questa casa, le chiavi le tiene la governante.
```

- [ ] **Step 6: `data/worlds/valdimora/personaggi.yaml` — Ettore e Livia**

```yaml
# I personaggi di Valdimora. Dove stanno nel primo atto: spec, sezione 2 (tabella dei personaggi);
# gli spostamenti (moves) arrivano con gli atti successivi.
# I domestici danno del voi a Irene («signorina»).

characters:
  ettore:
    name: Ettore
    article: none
    gender: m
    aliases: [maggiordomo, vecchio]
    description: >
      Un uomo alto e magro, sui settant'anni, in livrea nera. Ha gli occhi rossi di chi non dorme da
      giorni.
    location: stanza_maggiordomo
    greeting: >
      Ettore si alza a fatica dalla sedia. «Perdonate, signorina: la casa è in lutto. La contessa ci
      ha lasciati tre giorni fa. Chi siete, e chi vi manda?»
    greeting_variants:
      - when: {flag: busta_data}
        text: «Signorina Irene.» Ettore si inchina appena. «Chiedete pure. Quello che so, è vostro.»
    unknown: Ettore scuote la testa. «Su questo non so dirvi niente, signorina.»
    refuses: «No, signorina, tenetelo voi.»
    topics:
      contessa:
        name: contessa
        gender: f
        aliases: [adelaide, padrona, morte]
        text: >
          «Il cuore, dicono. Da mesi non stava bene, ma quella notte…» Ettore tace, e guarda altrove.
          «Il dottore l'ha trovata all'alba.»
      lettera:
        name: lettera
        gender: f
        aliases: [invito, lettera della contessa]
        text: «La contessa vi ha scritto?» Ettore tende la mano. «Posso vederla?»
        variants:
          - when: {flag: busta_data}
            text: «L'ha scritta con le ultime forze, ne sono sicuro.»
      clara:
        name: Clara
        article: none
        gender: f
        aliases: [madre, mamma, mia madre, tua madre]
        when: {flag: busta_data}
        text: >
          Ettore distoglie lo sguardo. «Non qui, signorina. Non ancora. La contessa ha voluto che le
          cose le trovaste da voi.»
      livia:
        name: Livia
        article: none
        gender: f
        aliases: [governante, chiavi]
        effects:
          - set_flag: ettore_garantisce
        text: >
          «Livia? Tiene le chiavi di tutto, ed è dura. Ma è onesta.» Ettore annuisce, deciso. «Se vi
          serve qualcosa da lei, una parola gliela metto io: saprà che siete chi dite di essere.»
        variants:
          - when: {flag: livia_chiave}
            text: «Visto? Livia è dura, ma è giusta.»
      corrado:
        name: Corrado
        article: none
        gender: m
        aliases: [nipote]
        text: >
          «Il nipote del conte. Si considera già il padrone.» Ettore abbassa la voce. «Non fidatevi
          troppo, signorina.»
      agnese:
        name: Agnese
        article: none
        gender: f
        aliases: [dama di compagnia]
        text: >
          «La dama di compagnia della contessa. Le leggeva i romanzi, le dava le medicine. Da quando
          è morta non si stacca da lei, in cappella.»
      frana:
        name: frana
        gender: f
        aliases: [strada, notaio]
        text: «Finché non liberano la strada, qui non arriva nessuno. Nemmeno il notaio.»

  livia:
    name: Livia
    article: none
    gender: f
    aliases: [governante, signora livia]
    description: >
      Una donna sulla cinquantina, vestita di grigio, con un mazzo di chiavi alla cintura. Ti guarda
      come si guarda una macchia sul tappeto.
    location: ufficio_governante
    greeting: >
      «Siete voi, quella della corriera.» Livia non si alza. «La casa è in lutto, signorina. Non so
      che cosa siate venuta a cercare, ma qui non troverete niente.»
    greeting_variants:
      - when: {flag: livia_chiave}
        text: «Avete la chiave. Non toccate le cose della contessa.»
    unknown: «Non sono cose che vi riguardano.»
    refuses: «Tenete le vostre cose, signorina.»
    topics:
      scalone:
        name: scalone
        gender: m
        aliases: [piano nobile, piano di sopra, chiave dello scalone, porta]
        text: «Il piano nobile resta chiuso finché non arriva il notaio. Ordini miei.»
        variants:
          - when: {flag: livia_chiave}
            text: «Avete la chiave. Non fatemene pentire.»
      contessa:
        name: contessa
        gender: f
        aliases: [adelaide, padrona, morte]
        text: >
          «Trent'anni al suo servizio.» Per un attimo la voce le si incrina. «Non parlo della
          contessa con gli estranei.»
      ettore:
        name: Ettore
        article: none
        gender: m
        aliases: [maggiordomo]
        text: «Ettore è vecchio, e crede ancora alle favole.»
      notaio:
        name: notaio
        gender: m
        aliases: [frana, strada]
        text: «Il notaio doveva venire il 20. Con la frana, chissà quando.»
      chiavi:
        name: chiavi
        gender: f
        plural: true
        aliases: [mazzo di chiavi, quadro delle chiavi]
        text: «Ogni chiave di questa casa passa da me.»
```

Nota: l'argomento «chiavi» di Livia e l'alias «chiavi» dell'argomento «Livia» di Ettore stanno su personaggi diversi: nessun conflitto.

- [ ] **Step 7: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde. Se il caricamento segnala problemi (`find_problems`), correggere i dati secondo il messaggio, che dice file e percorso.

- [ ] **Step 8: Commit**

```bash
git add data/worlds/avventure.yaml data/worlds/valdimora/gioco.yaml data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py tests/test_loader.py tests/test_web.py
git commit -m "Valdimora, atto 1: il pianterreno, la pista della meridiana, Ettore e Livia" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Il filo facoltativo e gli altri personaggi

**Files:**
- Modify: `data/worlds/valdimora/pianterreno.yaml` (oggetti e regole del filo facoltativo, regola del medaglione per Agnese), `data/worlds/valdimora/personaggi.yaml` (Corrado, Ferri, Agnese; l'argomento «credenza» di Ettore), `app/engine/parser.py` (`STOPWORDS`: «ad»)
- Test: `tests/test_valdimora.py`, `tests/test_parser.py`

**Interfaces:**
- Consumes: fixture `valdimora`, `new_game`, `play`, `TO_THE_STAIRCASE` (Task 2).
- Produces: flag `credenza_aperta`, `ferri_addormentato`, `chiavetta_presa`, `armadietto_aperto`; oggetti `credenza`, `chiave_credenza`, `grappa`, `borsa`, `chiavetta`, `armadietto`, `registro` (la prova 1, che l'atto 4 conterà con `has: registro`); personaggi `corrado`, `ferri`, `agnese`.

- [ ] **Step 1: Test che falliscono**

In fondo a `tests/test_valdimora.py`:
```python
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
```

In `tests/test_parser.py`, nell'elenco parametrizzato di `test_giving_an_item_to_a_character` (che si aspetta `Action(verb="dai", target="moneta", with_="custode")`), in fondo:
```python
        "dai la moneta ad un custode",  # «ad» before a vowel, as in «dai il medaglione ad Agnese»
```
(«un» è già tra le parole ignorate.)

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py tests/test_parser.py -q`
Expected: FAIL — mancano credenza, borsa, armadietto e i tre personaggi; «ad» non è una parola ignorata.

- [ ] **Step 3: «ad» nel parser**

In `app/engine/parser.py`, in `STOPWORDS`, la riga `di a da in con su per tra fra verso contro dentro` diventa `di a ad da in con su per tra fra verso contro dentro`.

- [ ] **Step 3b: Oggetti e regole in `pianterreno.yaml`**

In fondo alla sezione `items:` (prima di `rules:`):
```yaml
  # --- Il filo facoltativo: la prova 1 ---
  credenza:
    name: credenza
    gender: f
    aliases: [mobile]
    description: >
      Una credenza di noce scuro, chiusa a chiave. Dietro i vetri si intravedono bicchieri e
      bottiglie.
    location: sala_da_pranzo
    scenery: true
    variants:
      - when: {flag: credenza_aperta}
        text: La credenza di noce, aperta. Dentro restano solo bicchieri.

  chiave_credenza:
    name: chiave della credenza
    gender: f
    aliases: [chiave, chiavina]
    description: Una chiave piccola e ornata, legata a un nastrino.
    location: null

  grappa:
    name: bottiglia di grappa
    gender: f
    aliases: [grappa, bottiglia, liquore]
    description: Una bottiglia di grappa di vinacce, ancora sigillata.
    location: null

  borsa:
    name: borsa del dottore
    gender: f
    aliases: [borsa, borsa da medico]
    description: Una borsa da medico di pelle nera, consumata agli angoli.
    location: biliardo
    scenery: true
    variants:
      - when: {flag: chiavetta_presa}
        text: La borsa del dottore, aperta sul tavolino. Fiale, ricettari, uno stetoscopio.
      - when: {flag: ferri_addormentato}
        text: >
          La borsa del dottore, sul tavolino accanto a lui. Il dottore dorme: nessuno ti impedirebbe
          di aprirla.

  chiavetta:
    name: chiavetta dell'armadietto
    gender: f
    aliases: [chiavetta]
    description: Una chiavetta d'ottone con un cartellino scritto a mano, «Armadietto medicinali».
    location: null

  armadietto:
    name: armadietto dei medicinali
    gender: m
    aliases: [armadietto, sportello]
    description: Un armadietto bianco con lo sportello di vetro smerigliato, chiuso a chiave.
    location: dispensa
    scenery: true
    variants:
      - when: {flag: armadietto_aperto}
        text: L'armadietto dei medicinali, aperto. Bende, sciroppi, flaconi.

  registro:
    name: registro delle medicine
    gender: m
    aliases: [registro]
    description: >
      Un quaderno dalla copertina nera, con le colonne tirate a righello: date, medicine, gocce.
    location: null
```

In fondo alla sezione `rules:`:
```yaml
  # --- Il filo facoltativo: la grappa, la borsa, l'armadietto ---
  apri_credenza:
    trigger: {verb: apri, target: credenza, with: chiave_credenza}
    when: {not: {flag: credenza_aperta}}
    otherwise: La credenza è già aperta, e dentro restano solo bicchieri.
    effects:
      - give: grappa
      - set_flag: credenza_aperta
    text: >
      La chiavina gira senza fatica. Tra i bicchieri buoni c'è una bottiglia di grappa ancora
      sigillata. La prendi.

  apri_credenza_senza_chiave:
    trigger: {verb: apri, target: credenza}
    when: {not: {flag: credenza_aperta}}
    otherwise: La credenza è già aperta, e dentro restano solo bicchieri.
    text: È chiusa a chiave. Le cose della sala da pranzo, di solito, sono affare del maggiordomo.

  dai_grappa_ferri:
    trigger: {verb: dai, target: grappa, with: ferri}
    effects:
      - remove: grappa
      - set_flag: ferri_addormentato
    text: >
      Il dottore ti guarda come si guarda un angelo. «Signorina, voi siete una santa.» Ne versa un
      bicchiere, poi un altro, poi un terzo. Al quarto si appoggia allo schienale, chiude gli occhi
      e comincia a russare.

  prendi_borsa:
    trigger:
      - {verb: prendi, target: borsa}
      - {verb: apri, target: borsa}
    when: {all: [{flag: ferri_addormentato}, {not: {flag: chiavetta_presa}}]}
    otherwise: >
      Il dottor Ferri ti ferma la mano. «Giù le mani, signorina. Lì dentro c'è il segreto
      professionale.»
    otherwise_variants:
      - when: {flag: chiavetta_presa}
        text: Nella borsa non c'è altro che ti serva.
    effects:
      - give: chiavetta
      - set_flag: chiavetta_presa
    text: >
      Mentre il dottore russa, apri piano la borsa. Fiale, ricettari, uno stetoscopio e, legata a
      un cartellino, una chiavetta d'ottone: «Armadietto medicinali». La prendi.

  apri_armadietto:
    trigger: {verb: apri, target: armadietto, with: chiavetta}
    when: {not: {flag: armadietto_aperto}}
    otherwise: L'armadietto è già aperto.
    effects:
      - give: registro
      - set_flag: armadietto_aperto
    text: >
      Lo sportello si apre con un cigolio. Bende, sciroppi, flaconi e, sul ripiano più basso, un
      quaderno nero: il registro delle medicine. Lo prendi.

  apri_armadietto_senza_chiave:
    trigger: {verb: apri, target: armadietto}
    when: {not: {flag: armadietto_aperto}}
    otherwise: L'armadietto è già aperto.
    text: È chiuso a chiave. Una chiave così, di solito, ce l'ha il medico.

  leggi_registro:
    trigger: {verb: leggi, target: registro}
    text: >
      Colonne ordinate: data, farmaco, dose. «Digitale, dieci gocce, la sera.» Pagina dopo pagina,
      sempre uguale, e ogni riga siglata con la stessa iniziale, «A.». Nell'ultima settimana di vita
      della contessa, però, le gocce diventano venti. Sempre siglate «A.».

  # --- Agnese e il medaglione (nell'atto 4 questa regola porterà al finale «tradita») ---
  dai_medaglione_agnese:
    trigger: {verb: dai, target: medaglione, with: agnese}
    text: >
      Agnese prende il medaglione e lo rigira a lungo tra le dita, alla luce delle candele. Poi te
      lo rende con un sorriso. «Che strana stella.»
```

Nota: `trigger` di `prendi_borsa` è una lista, perché «apri la borsa» vuol dire la stessa cosa.

- [ ] **Step 4: Personaggi in `personaggi.yaml`**

Tra gli argomenti di Ettore, dopo `lettera`:
```yaml
      credenza:
        name: credenza
        gender: f
        aliases: [grappa, liquori, chiave della credenza]
        when: {flag: busta_data}
        effects:
          - give: chiave_credenza
        text: >
          «La grappa buona è nella credenza della sala da pranzo.» Ettore ti mette in mano una
          chiavina legata a un nastro. «Ecco la chiave. Ma non ditelo alla signora Livia.»
        variants:
          - when: {flag: credenza_aperta}
            text: «Avete trovato la grappa? Acqua in bocca con Livia, mi raccomando.»
```

In fondo alla sezione `characters:`:
```yaml
  corrado:
    name: Corrado
    article: none
    gender: m
    aliases: [nipote, signor corrado]
    description: >
      Un uomo sui quarant'anni, elegante ma trasandato, con la cravatta allentata e un bicchiere
      vuoto in mano. Ha l'aria di chi aspetta un treno in ritardo.
    location: biliardo
    greeting: >
      «Un'altra parente sconosciuta?» Corrado ride senza allegria. «Mettetevi in fila. Quando
      arriverà il notaio vedrete che qui non c'è niente per nessuno, tranne che per me.»
    unknown: Corrado scrolla le spalle. «Chiedetelo a Ettore, lui sa tutto.»
    refuses: «Non accetto regali dagli estranei.»
    topics:
      eredita:
        name: eredità
        gender: f
        aliases: [notaio, testamento, castello, soldi]
        text: >
          «Il castello, le terre, tutto quanto. Il conte non aveva altri eredi che me, e mia zia,
          pace all'anima sua, si è solo presa il suo tempo.»
      contessa:
        name: contessa
        gender: f
        aliases: [zia, adelaide, morte]
        text: >
          «Il cuore. Ferri l'ha detto subito, e meno se ne parla meglio è: i giornali della città
          non aspettano altro.»
      ferri:
        name: dottor Ferri
        article: definite
        gender: m
        aliases: [dottore, medico, ferri]
        text: «Il nostro dottore beve più di quanto curi. Ma sa quando tacere.»
      frana:
        name: frana
        gender: f
        aliases: [strada]
        text: «Una settimana, dicono, per liberare la strada. Una settimana chiuso qui con voi tutti.»

  ferri:
    name: dottor Ferri
    article: definite
    gender: m
    aliases: [dottore, medico, ferri]
    description: >
      Un uomo grasso e rubicondo, col panciotto slacciato. Accanto a lui, sul tavolino, la sua borsa
      da medico.
    variants:
      - when: {flag: ferri_addormentato}
        text: >
          Il dottor Ferri dorme sprofondato in poltrona, con la bocca aperta. La sua borsa è sul
          tavolino.
    location: biliardo
    greeting: >
      «Signorina.» Il dottore solleva il bicchiere vuoto e lo guarda con tristezza. «In questa casa
      si muore, e non si beve nemmeno più.»
    greeting_variants:
      - when: {flag: ferri_addormentato}
        text: Il dottor Ferri russa. Non c'è verso di svegliarlo.
    unknown: «Sono un medico, signorina, non un indovino.»
    refuses: «Grazie, ma no.»
    topics:
      contessa:
        name: contessa
        gender: f
        aliases: [morte, adelaide, certificato, cuore]
        text: >
          «Arresto cardiaco. Il cuore era stanco, lo sapevamo tutti. Ho firmato il certificato la
          mattina stessa.» Beve un sorso dal bicchiere vuoto. «Corrado insisteva per non chiamare
          nessuno da fuori.»
        variants:
          - when: {flag: ferri_addormentato}
            text: Il dottore russa.
      grappa:
        name: grappa
        gender: f
        aliases: [bottiglia, bere, liquore]
        text: >
          «Questa è vuota. La grappa buona Ettore la tiene sotto chiave, nella credenza della sala da
          pranzo. Come un tesoro.»
        variants:
          - when: {flag: ferri_addormentato}
            text: Il dottore russa.
      medicine:
        name: medicine
        gender: f
        plural: true
        aliases: [farmaco, gocce, digitale, borsa]
        text: >
          «Digitale, gocce per il cuore. Io le prescrivevo, e la ragazza, Agnese, gliele dava ogni
          sera.»
        variants:
          - when: {flag: ferri_addormentato}
            text: Il dottore russa.

  agnese:
    name: Agnese
    article: none
    gender: f
    aliases: [dama di compagnia, ragazza]
    description: >
      Una ragazza di trent'anni, pallida, vestita di nero. Ha gli occhi gonfi e un rosario tra le
      dita.
    location: cappella
    greeting: >
      Agnese si alza di scatto, poi ti sorride tra le lacrime. «Voi dovete essere la signorina di
      Genova. La contessa parlava di una visita… Se vi serve qualcosa, qualunque cosa, chiedete a
      me.»
    unknown: «Non saprei, signorina. Chiedete a Ettore, forse.»
    refuses: «Oh, no, non potrei.»
    topics:
      contessa:
        name: contessa
        gender: f
        aliases: [adelaide, padrona, morte]
        text: >
          «Era così buona con me. La sera le leggevo i romanzi, e le davo le sue gocce.» Si asciuga
          gli occhi. «Quella notte dormiva così tranquilla…»
      medicine:
        name: medicine
        gender: f
        plural: true
        aliases: [gocce, digitale, farmaco]
        text: «Le gocce per il cuore. Le contavo io, una per una, come diceva il dottore.»
      aiuto:
        name: aiuto
        gender: m
        aliases: [aiutare, serve]
        text: «Qualunque cosa. La contessa avrebbe voluto così.»
```

Nota: «Qui ci sono Corrado e il dottor Ferri.» viene dall'ordine dei personaggi nel file (Corrado prima di Ferri) e da `article` (Task 1).

- [ ] **Step 5: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde.

- [ ] **Step 6: Commit**

```bash
git add app/engine/parser.py data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py tests/test_parser.py
git commit -m "Valdimora, atto 1: la prova del registro, Corrado, il dottor Ferri e Agnese" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Gli arredi e gli oggetti degli atti futuri

**Files:**
- Modify: `data/worlds/valdimora/pianterreno.yaml`
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Produces: un arredo per ogni cosa nominata nelle descrizioni; gli oggetti portatili per gli atti futuri: `forbici` e `tanica` (rimessa), `fiammiferi` (cucina); gli arredi `rosaio` (serra) e `porta_cantina` (cucina), che gli atti 2 e 3 useranno.

- [ ] **Step 1: Test che falliscono**

In fondo a `tests/test_valdimora.py`:
```python
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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_valdimora.py -q`
Expected: FAIL — gli arredi e gli oggetti nuovi non ci sono.

- [ ] **Step 3: Arredi e oggetti in `pianterreno.yaml`**

In fondo alla sezione `items:` (prima di `rules:`):
```yaml
  # --- Arredi: ogni cosa nominata in una descrizione si può esaminare ---
  portone:
    name: portone
    gender: m
    aliases: [drappo, drappo nero]
    description: Il portone da cui sei entrata, con un drappo nero appeso ai battenti. Fuori piove.
    location: atrio
    scenery: true

  annuncio:
    name: annuncio funebre
    gender: m
    aliases: [annuncio, avviso, cavalletto, lutto]
    description: >
      Un cartoncino listato di nero, su un cavalletto: «Il 14 ottobre 1927 è mancata all'affetto dei
      suoi cari la contessa Adelaide di Valdimora. Le esequie si terranno non appena la strada lo
      permetterà.»
    location: atrio
    scenery: true

  calesse:
    name: calesse
    gender: m
    aliases: [carrozza]
    description: Un calesse senza ruote, sollevato su due cavalletti. Il cuoio dei sedili è screpolato.
    location: rimessa
    scenery: true

  attrezzi:
    name: attrezzi
    gender: m
    plural: true
    aliases: [scaffali, barattoli]
    description: Rastrelli, vanghe, barattoli di chiodi e di vernice secca. Niente di utile, a parte quello che vedi qui intorno.
    location: rimessa
    scenery: true

  frana:
    name: frana
    gender: f
    aliases: [strada, cancello]
    description: >
      Oltre il cancello, dove prima c'era la strada, ora c'è una colata di fango e di sassi. Ci
      vorranno giorni per liberarla.
    location: rimessa
    scenery: true

  poltrone:
    name: poltrone
    gender: f
    plural: true
    aliases: [teli, velluti]
    description: Poltrone di velluto rosso, coperte da teli bianchi come fantasmi seduti.
    location: salotto
    scenery: true

  pianoforte:
    name: pianoforte
    gender: m
    aliases: [piano]
    description: Un pianoforte a coda, chiuso. Sul leggio, uno spartito di Chopin ingiallito.
    location: salotto
    scenery: true

  specchi:
    name: specchi
    gender: m
    plural: true
    aliases: [specchio]
    description: Specchi dalle cornici dorate, appannati dal tempo. Ti ci vedi appena.
    location: salotto
    scenery: true

  rosaio:
    name: rosaio
    gender: m
    aliases: [rose, rose bianche, rosa]
    description: Un rosaio rampicante carico di rose bianche. Qualcuno se ne prende ancora cura.
    location: serra
    scenery: true

  limoni:
    name: limoni
    gender: m
    plural: true
    aliases: [felci, vasi]
    description: Limoni in grandi vasi di terracotta, e felci che arrivano al soffitto.
    location: serra
    scenery: true

  tavola:
    name: tavola
    gender: f
    aliases: [tavolo da pranzo, tovaglia]
    description: Una tavola per dodici, apparecchiata con piatti e posate d'argento. Nessuno la sparecchia.
    location: sala_da_pranzo
    scenery: true

  lampadario:
    name: lampadario
    gender: m
    description: Un lampadario di vetro di Murano, spento, con metà delle candele consumate.
    location: sala_da_pranzo
    scenery: true

  argenteria:
    name: argenteria
    gender: f
    aliases: [argento, posate]
    description: Posate, vassoi e candelieri d'argento, in attesa di essere lucidati.
    location: stanza_maggiordomo
    scenery: true

  campanelli:
    name: campanelli
    gender: m
    plural: true
    aliases: [campanello]
    description: >
      Una fila di campanelli di ottone, ognuno con una targhetta: «Salotto», «Biblioteca», «Camera
      della contessa»… Quello della contessa ha il filo tagliato.
    location: stanza_maggiordomo
    scenery: true

  focolare:
    name: focolare
    gender: m
    aliases: [fuoco, camino]
    description: Un focolare acceso, l'unico fuoco di tutta la casa. Ci si scalda le mani volentieri.
    location: cucina
    scenery: true

  pentole:
    name: pentole
    gender: f
    plural: true
    aliases: [rame, travi]
    description: Pentole e padelle di rame, appese alle travi, lucide come specchi.
    location: cucina
    scenery: true

  porta_cantina:
    name: porta della cantina
    gender: f
    aliases: [porta, cantina, porta bassa]
    description: Una porta bassa di legno massiccio, sbarrata e chiusa a chiave. Da sotto sale odore di muffa.
    location: cucina
    scenery: true

  fiammiferi:
    name: scatola di fiammiferi
    gender: f
    aliases: [fiammiferi, cerini, scatola]
    description: Una scatola di fiammiferi da cucina, quasi piena.
    location: cucina

  vasche:
    name: vasche
    gender: f
    plural: true
    aliases: [mastello, vasche di pietra]
    description: Vasche di pietra per il bucato, e un mastello di legno pieno d'acqua saponata.
    location: lavanderia
    scenery: true

  lenzuola:
    name: lenzuola
    gender: f
    plural: true
    aliases: [lenzuolo]
    description: Lenzuola di lino stese ad asciugare. Una porta ricamate le iniziali «A. V.».
    location: lavanderia
    scenery: true

  stufa:
    name: stufa
    gender: f
    aliases: [stufa di ghisa]
    description: Una stufa di ghisa che scalda la lavanderia. Sopra, un ferro da stiro.
    location: lavanderia
    scenery: true

  conserve:
    name: conserve
    gender: f
    plural: true
    aliases: [scaffali, formaggio, farina, sacchi]
    description: Barattoli di pomodori e di pesche, forme di formaggio, sacchi di farina. Provviste per l'inverno.
    location: dispensa
    scenery: true

  quadro_chiavi:
    name: quadro delle chiavi
    gender: m
    aliases: [chiavi, cartellini]
    description: >
      Decine di chiavi appese, ognuna col suo cartellino scritto da Livia: «Cantina», «Soffitta»,
      «Biblioteca»… Il gancio dello «Scalone» è vuoto.
    location: ufficio_governante
    scenery: true

  calendario:
    name: calendario
    gender: m
    description: Un calendario da muro, fermo al 14 ottobre. Nessuno ha più voltato il foglio.
    location: ufficio_governante
    scenery: true

  libri_contabili:
    name: libri contabili
    gender: m
    plural: true
    aliases: [contabilità, libri]
    description: >
      File di libri contabili rilegati in tela, uno per anno. La calligrafia di Livia, minuta e
      diritta, riempie tutte le pagine.
    location: ufficio_governante
    scenery: true

  bara:
    name: bara della contessa
    gender: f
    aliases: [bara, feretro]
    description: >
      Una bara di legno scuro, chiusa, coperta di gigli bianchi. Sul coperchio, una targhetta
      d'ottone: «Adelaide di Valdimora, 1855 – 1927».
    location: cappella
    scenery: true

  candele:
    name: candele
    gender: f
    plural: true
    aliases: [candela, ceri]
    description: Due file di candele accese, che qualcuno cambia con cura.
    location: cappella
    scenery: true

  gigli:
    name: gigli
    gender: m
    plural: true
    aliases: [fiori]
    description: Gigli bianchi, freschi. Il profumo è così forte che quasi stordisce.
    location: cappella
    scenery: true

  tavolo_biliardo:
    name: tavolo da biliardo
    gender: m
    aliases: [tavolo, panno]
    description: Un tavolo da biliardo dal panno verde consumato, con le bilie ferme a metà partita.
    location: biliardo
    scenery: true

  stecche:
    name: stecche
    gender: f
    plural: true
    aliases: [stecca, bilie]
    description: Due stecche abbandonate sul panno, come se i giocatori fossero appena usciti.
    location: biliardo
    scenery: true

  carrello:
    name: carrello dei liquori
    gender: m
    aliases: [carrello, liquori]
    description: Un carrello d'ottone con bottiglie di liquore. Sono tutte vuote.
    location: biliardo
    scenery: true

  finestre:
    name: finestre
    gender: f
    plural: true
    aliases: [finestra]
    description: >
      Le finestre del castello, su tre piani, quasi tutte buie. Solo in alto, sotto il tetto, una
      luce trema per un momento, poi si spegne.
    location: cortile
    scenery: true

  # --- Oggetti per gli atti futuri: le forbici (atto 2), la tanica (atto 3) ---
  forbici:
    name: forbici da potatura
    gender: f
    plural: true
    aliases: [forbici, cesoie]
    description: Un paio di forbici da potatura, ben affilate.
    location: rimessa

  tanica:
    name: tanica di petrolio
    gender: f
    aliases: [tanica, petrolio]
    description: Una tanica di latta, piena di petrolio per le lampade.
    location: rimessa
```

In fondo alla sezione `rules:`:
```yaml
  # --- Risposte d'atmosfera ---
  leggi_annuncio:
    trigger: {verb: leggi, target: annuncio}
    text: >
      «Il 14 ottobre 1927 è mancata all'affetto dei suoi cari la contessa Adelaide di Valdimora. Le
      esequie si terranno non appena la strada lo permetterà.»

  apri_portone:
    trigger: {verb: apri, target: portone}
    text: >
      Fuori c'è solo la pioggia. La strada verso valle è chiusa dalla frana: di qui, per ora, non
      si va da nessuna parte.

  apri_porta_cantina:
    trigger: {verb: apri, target: porta_cantina}
    text: È sbarrata e chiusa a chiave. Sul quadro delle chiavi di Livia, il gancio «Cantina» è vuoto.

  prendi_quadro_chiavi:
    trigger: {verb: prendi, target: quadro_chiavi}
    text: Livia ti ferma con un'occhiata. «Quelle non si toccano.»

  prendi_candele:
    trigger: {verb: prendi, target: candele}
    text: Non ti sembra il caso di toccare niente, qui.

  apri_bara:
    trigger: {verb: apri, target: bara}
    text: Non ne hai il coraggio, e non ne hai il diritto.

  suona_pianoforte:
    trigger: {verb: usa, target: pianoforte}
    text: Sollevi il coperchio e sfiori un tasto. La nota rimbomba nella casa in lutto, e lo richiudi subito.
```

Nota: il quadro delle chiavi dice che il gancio «Cantina» è vuoto: un indizio che l'atto 3 paga (la chiave della cantina è nella casa delle bambole). Nel `test_what_a_room_describes_can_be_examined`, «esamina la porta della cantina» nella cucina deve trovare l'arredo: se il parser trovasse ambiguo «porta» con la porta dello scalone, non succede, perché la porta dello scalone è nell'atrio.

- [ ] **Step 4: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde.

- [ ] **Step 5: Commit**

```bash
git add data/worlds/valdimora/pianterreno.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 1: gli arredi del pianterreno e gli oggetti per gli atti futuri" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Il primo atto col modello vero

**Files:**
- Modify: `tests/test_ollama.py` (casi di Valdimora), eventualmente `data/worlds/valdimora/*.yaml` (alias e argomenti), eventualmente `tests/test_game.py` o `tests/test_interpreter.py` (test sul client finto accanto ai casi nuovi, se una correzione tocca il codice)
- Test: `tests/test_ollama.py`

**Interfaces:**
- Consumes: il mondo del Task 4.

- [ ] **Step 1: Verificare che Ollama risponda**

```bash
curl -s -m 5 http://127.0.0.1:11434/api/tags | head -c 200
```
Se non risponde, fermarsi e chiedere all'utente di avviarlo.

- [ ] **Step 2: Scrivere i casi**

In fondo a `tests/test_ollama.py`, una sezione nuova:
```python
# --- La Stella di Valdimora, atto 1 ------------------------------------------------------------------

VALDIMORA = load_world(WORLDS_DIR / "valdimora")
VALDIMORA_RULE = {rule_id: rule.text for rule_id, rule in VALDIMORA.rules.items()}
ETTORE = VALDIMORA.characters["ettore"]

VALDIMORA_CASES = [
    # (room, carried, flags, sentence, check on (answer, game))
    ("atrio", (), (), "leggo l'annuncio funebre", says(VALDIMORA_RULE["leggi_annuncio"])),
    ("rimessa", (), (), "apro la mia valigia", lambda a, g: g.state.item_locations["fotografia"] == "inventory"),
    ("rimessa", (), (), "prendo l'olio", lambda a, g: g.state.item_locations["oliatore"] == "inventory"),
    ("stanza_maggiordomo", (), (), "mostro la lettera al maggiordomo",
     lambda a, g: g.state.item_locations["busta"] == "inventory"),
    ("stanza_maggiordomo", (), (), "faccio vedere la lettera a Ettore",
     lambda a, g: g.state.item_locations["busta"] == "inventory"),
    ("stanza_maggiordomo", ("busta",), ("busta_data",), "leggo il biglietto della contessa",
     says(VALDIMORA_RULE["leggi_busta"])),
    ("cortile", (), ("busta_letta",), "guardo bene sotto la meridiana",
     says(VALDIMORA.items["meridiana"].variants[1].text)),
    ("cortile", ("oliatore",), ("busta_letta",), "metto un po' d'olio sulla meridiana",
     lambda a, g: "meridiana_oliata" in g.state.flags),
    ("cortile", (), ("busta_letta", "meridiana_oliata"), "infilo il medaglione nell'incavo",
     lambda a, g: g.state.item_locations["biglietto_livia"] == "inventory"),
    ("stanza_maggiordomo", (), ("busta_data",), "chiedo a Ettore di mettere una buona parola con Livia",
     lambda a, g: "ettore_garantisce" in g.state.flags),
    ("ufficio_governante", ("biglietto_livia",), ("ettore_garantisce",), "consegno il biglietto a Livia",
     lambda a, g: g.state.item_locations["chiave_scalone"] == "inventory"),
    ("atrio", ("chiave_scalone",), (), "salgo lo scalone",
     says(VALDIMORA.rooms["atrio"].exits["su"].otherwise)),
    ("stanza_maggiordomo", (), ("busta_data",), "gli chiedo di mia madre",
     says(ETTORE.topics["clara"].text)),
    ("biliardo", ("grappa",), (), "offro la grappa al dottore", lambda a, g: "ferri_addormentato" in g.state.flags),
    ("biliardo", (), ("ferri_addormentato",), "frugo nella borsa del dottore",
     lambda a, g: g.state.item_locations["chiavetta"] == "inventory" or "nessuno ti impedirebbe" in a),
    ("dispensa", ("chiavetta",), (), "apro l'armadietto dei medicinali con la chiavetta",
     lambda a, g: g.state.item_locations["registro"] == "inventory"),
    # «chi sei?» to Agnese: her greeting or her answer to what she doesn't know; no action may start.
    ("cappella", (), (), "chi sei?", says(VALDIMORA.characters["agnese"].greeting,
                                          VALDIMORA.characters["agnese"].unknown)),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "sentence", "check"),
    [pytest.param(*case, id=f"{case[0]}: {case[3]}") for case in VALDIMORA_CASES],
)
def test_valdimora_free_sentences(llm, room, carried, flags, sentence, check):
    game = playing(llm, VALDIMORA, room, carried, flags, ())

    answer = game.turn(sentence)
    print(f"\n  {sentence!r} -> {answer.splitlines()[0]!r}")

    assert check(answer, game)
```

`says(*texts)`, `playing(llm, world, room, carried=(), flags=(), seen=())` e la fixture `llm` esistono già in `tests/test_ollama.py`; `says` e `playing` sono definiti poco prima di `PLAYED`, quindi la sezione di Valdimora va **in fondo al file**, dopo `test_sentences_found_while_playing`.

- [ ] **Step 3: Eseguire col modello vero**

Run: `OLLAMA_TESTS=1 LLM_LOG=off .venv/Scripts/python -m pytest tests/test_ollama.py -v -s -k valdimora > <workspace>/valdimora-ollama.txt 2>&1` (circa 2 minuti), poi leggerne il riassunto e le righe `->`.

- [ ] **Step 4: Decidere caso per caso**

Per ogni caso che fallisce, nell'ordine:
1. **Correggere i dati**, se basta un alias o un argomento (per esempio «mostro» che il modello traduce in un esame: controllare se la frase nomina oggetti e personaggi con nomi che i dati non conoscono). Ogni correzione di dati ha il suo test sul client finto o col parser in `tests/test_valdimora.py`.
2. **Accettare un comportamento innocuo** (nessuna azione sbagliata, al massimo «Non ho capito» o una domanda di conferma): allargare il controllo del caso solo se il risultato è ragionevole per il giocatore, e scriverlo in un commento.
3. **Limite noto**: se niente di questo basta, aggiungere il caso a `KNOWN_LIMITS` con la ragione, come gli altri.
4. **Esempi nel prompt** (`game.examples` di Valdimora) solo come ultima risorsa, e in quel caso rigiocare **tutto** `tests/test_ollama.py` (circa 12 minuti) prima di andare avanti.

Rieseguire lo Step 3 dopo le correzioni; due giri di fila senza fallimenti nuovi (il modello non è del tutto deterministico).

- [ ] **Step 5: Verificare tutta la suite senza modello, e commit**

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde, i test col modello vero saltati.

```bash
git add tests/test_ollama.py data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, atto 1: le frasi libere provate col modello vero" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
(aggiungere solo i file cambiati davvero.)

---

### Task 6: CLAUDE.md e verifica finale

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: CLAUDE.md**

In «Decisioni prese», dopo la voce **Motore per Valdimora**:
> - **Valdimora, atto 1** (2026-09-29, branch `feature/valdimora-atto-1`; piano in `docs/superpowers/plans/2026-09-29-valdimora-atto-1.md`): il pianterreno in `data/worlds/valdimora/` (`gioco.yaml`, `pianterreno.yaml`, `personaggi.yaml`), nel menu con un finale provvisorio sul flag `atto_due` (aprendo la porta dello scalone). Nomi propri: campo `article` (`none` per Ettore, Livia, Corrado, Agnese e Clara; `definite` per il dottor Ferri). La Loggia dello scalone è provvisoria. Oggetti degli atti futuri già piantati (forbici, tanica, fiammiferi, rosaio, porta della cantina). Col modello vero: [risultato del Task 5: quante frasi su quante, e cosa è stato corretto o lasciato come limite noto].

(sostituire la parte tra quadre con il risultato vero.)

- [ ] **Step 2: Verifica finale**

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde.
Run: `git diff main --stat -- app/llm/` — Expected: nessun file (il prompt non è cambiato).
Una partita nel terminale senza LLM fino alla fine dell'atto:
```bash
printf '3\nsud\napri la valigia\nprendi l oliatore\nnord\novest\nnord\nnord\ndai la lettera a Ettore\nleggi la busta\nchiedi a Ettore di Livia\nsud\nest\nusa l oliatore con la meridiana\nusa il medaglione con la meridiana\nest\nnord\ndai il biglietto sigillato a Livia\nsud\nsud\novest\napri la porta dello scalone con la chiave\nno\n' | LLM=off LLM_LOG=off COMMAND_LOG=off PYTHONIOENCODING=utf-8 .venv/Scripts/python -m app.cli | tail -8
```
Expected: «Fine del primo atto. (Il secondo è in costruzione.)», poi «Vuoi giocare ancora? (s/n)» e «Alla prossima!». (Nota: `printf` con `\n` va bene in Bash; «l oliatore» senza apostrofo evita problemi di quoting, e il parser toglie comunque «l».)

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: Valdimora, atto 1" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Poi chiedere all'utente se pubblicare il branch per la PR verso `main` (non pubblicarlo senza il suo sì).
