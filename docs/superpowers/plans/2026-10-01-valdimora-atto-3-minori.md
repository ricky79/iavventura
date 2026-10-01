# La Stella di Valdimora, atto 3: i minori rimandati — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** chiudere i minori rimandati dalla revisione dell'atto 3 — i testi che invecchiano andando avanti nell'atto (Livia dopo la confessione, Ettore e Corrado dopo le lettere, Agnese già di sotto), il tetto e la pioggia nella stanza dell'orologio, gli alias «casa», «appunti», «vestiti» — e un difetto trovato preparando il piano: nella camera di Clara «usa il medaglione con l'incavo» risponde «Non vedi niente del genere qui.».

**Architecture:** una sola aggiunta al formato del mondo: `hidden_aliases` sugli oggetti, nomi che il parser e i controlli sulle risposte del modello riconoscono ma che il modello non vede (Task 1). Il resto sono dati: `soffitta.yaml` (un arredo nuovo, una regola, alias nascosti), `pianterreno.yaml` (un alias nascosto della valigia), `personaggi.yaml` (varianti, e due argomenti nuovi di Agnese), più quattro parole in `parser.COMMON_WORDS`. Il motore e il prompt non cambiano; ciò che l'interprete riceve cambia solo nella stanza dell'orologio (un arredo in più) e in cucina con Agnese (gli argomenti), e lo verifica il modello vero.

**Tech Stack:** Python 3.12, Pydantic v2, PyYAML, pytest; Ollama con qwen2.5:3b per i test col modello vero.

**Spec:** `docs/superpowers/specs/2026-09-29-valdimora-design.md` (sezione 4, «Atto 3: decisioni prese al momento di costruirlo»), e la voce «Valdimora, atto 3» di `CLAUDE.md`, che elenca i rimandati.

## Global Constraints

- Branch: `feature/valdimora-atto-3-minori` (già creato da `main`, 160e94e). Prima del Task 1 questo piano si committa da solo:
  `git add docs/superpowers/plans/2026-10-01-valdimora-atto-3-minori.md` e
  `git commit -m "Piano dei minori dell'atto 3 di Valdimora" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`.
- Nessuna dipendenza nuova. Comandi con `.venv/Scripts/python` (Git Bash).
- Codice e identificatori in inglese; testi, commit e documentazione in italiano.
- **Il prompt dell'LLM non cambia** (`app/llm/prompts.py` non si tocca), e Valdimora non ha `game.examples`.
- **Testi**: Irene al femminile; i domestici, il dottore, Corrado e Agnese le danno del **voi** («signorina»); registro del 1927. Gli atti restano veri dopo il loro inizio: una variante dell'atto 3, o di un fatto dell'atto 3 (`lettere_lette`, `livia_confessa`, `tisana_bevuta`), viene prima di quelle degli atti precedenti, che restano per gli atti di prima.
- I testi scritti in questo piano sono quelli da usare, già provati su una copia del repository (vedi «Come è stato verificato»).
- **YAML**: un testo su una riga con «: » va tra virgolette doppie, oppure su più righe dopo `>`.
- Mai nei commit: `run.bat`, `run_log.bat`, `test_llm.txt`, `.claude/`. Aggiungere i file uno per uno.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Le modifiche ai file esistenti si fanno con Edit, sostituendo esattamente il blocco indicato (ognuno compare una volta sola nel suo file); i blocchi «in fondo a» vanno dopo l'ultima riga del file, separati da due righe vuote. Nessun testo di questo piano contiene backslash.

## Decisioni prese nel piano

1. **I testi che invecchiano** si correggono con varianti, senza toccare il motore: `livia_confessa` per Livia (la contessa, Ettore, le chiavi, il saluto ripetuto, grazie, scuse, congedo, come stai), `lettere_lette` per Ettore (il ritratto) e Corrado (l'eredità, come sta, chi è), `atto_tre` per i testi dell'atto 2 legati a un posto che i personaggi hanno lasciato: Livia che «si alza e guarda il cordone» (ora è in camera sua), Ettore che il carillon «l'ha sentito fin qui» (ora è in cucina), le chiavi di Livia (non le ha più alla cintura). Oltre ai casi che `CLAUDE.md` nomina, ho riletto tutti i testi dei personaggi nel terzo atto: queste sono tutte le frasi che non tornano. Nel terzo atto vero `ritratto_scoperto`, `livia_permette` e `carillon_suonato` sono sempre accesi (servono per arrivarci), e i test li accendono dove contano.
2. **Agnese di sotto**: l'argomento `aiuto` ha le varianti per la cucina e la rimessa; la tisana chiesta in rimessa la manda «verso la cucina» invece che «scende». Gli effetti di un argomento valgono per l'argomento intero, prima che il testo sia scelto (spec, «Le commissioni di Agnese»), quindi:
   - **la tazza** è un argomento a parte (`tazza`, «tazza di tisana»), solo con Agnese in cucina: dà la tisana e accende `tisana_bevuta`, che il saluto di Agnese e l'argomento «Agnese» di Ettore seguono. L'argomento `tisana` vale solo finché lei non è in cucina. Hanno gli stessi alias: non sono mai presenti insieme, e parser e interprete ricevono solo gli argomenti che il personaggio conosce in quel momento (`Engine.characters_here`). La validazione vuole nomi diversi, non alias diversi.
   - **la tanica** è un argomento a parte (`tanica`), senza effetti, con Agnese in cucina o con la tanica in mano: prima rispondeva «Non saprei, signorina. Chiedete a Ettore, forse.». Con la tanica in mano Agnese non deve scendere, e l'argomento `petrolio` (che la manda in rimessa) resta escluso come prima.
3. **Alias nascosti al modello** (`Item.hidden_aliases`, Task 1). Ogni nome in più nell'elenco degli oggetti cambia le risposte del modello anche alle altre frasi della stanza: nella camera di Clara, un alias in più sulla casa delle bambole («incavo», anche al posto di «comignolo») o «vestiti» sul baule faceva diventare «inventario» la frase già in test «infilo il medaglione nel tetto della casa delle bambole» (vedi «Come è stato verificato»); nell'atto 3 era successo con la trave. Un nome che serve solo perché il parser e i controlli riconoscano una parola delle descrizioni va quindi in `hidden_aliases`: vale come gli alias per il parser (`parser._phrases`), per i controlli sulle risposte del modello e per «Non vedi niente del genere qui.» (`parser.names_said`, da cui `is_named`), e per la validazione; il modello non lo vede (`prompts._names` legge solo `aliases`) e quindi non lo darà mai come risposta (`interpreter._ids_by_name` non cambia). Solo sugli oggetti: per stanze, personaggi e argomenti non è servito.
4. **Il tetto dalla stanza dell'orologio** è un arredo nuovo, `tetto_visto` («tetto», alias pioggia, vento, tegole: alias visibili, perché l'arredo entra comunque nell'elenco, e col modello vero aiutano), con la variante a corda legata. Saltarci sopra («salta sul tetto», che ora il parser capisce) è un indizio, non una morte: si muore uscendo sul tetto senza corda, come deciso nell'atto 3. Nelle altre stanze che nominano il tetto, «tetto» è un alias nascosto di ciò che c'è: le travi (soffittone), la tegola rotta (sottotetto), la tempesta (sul tetto, dove «esamina il tetto» non era capito), la casa delle bambole (la sua descrizione: «Sul tetto, al posto del comignolo…»). Nello stenditoio e nel cortile («sotto il tetto») non c'è un arredo adatto: lì «esamina il tetto» risponde ora «Non vedi niente del genere qui.» invece di «Non ho capito.» — limite accettato.
5. **La casa delle bambole** ha gli alias nascosti «incavo» e «tetto». «incavo» era solo della meridiana e del ritratto, quindi «usa il medaglione con l'incavo», la frase che negli atti 1 e 2 funzionava, rispondeva «Non vedi niente del genere qui.». Ora la capisce il parser, e la frase libera «metto il medaglione nell'incavo», a cui il modello risponde col letto di Clara, diventa l'ipotesi «Vuoi usare il medaglione con la casa delle bambole?».
6. **«vestiti»** è un alias nascosto della valigia («Dentro, solo i tuoi vestiti.») e del baule («vestiti da ragazza»): prima «esamina i vestiti» trovava solo l'armadio di Livia, di sopra, e rispondeva «Non vedi niente del genere qui.».
7. **«casa», «appunti», «vestiti» restano alias**, perché servono: «esamina la casa» nella stanza dell'enigma, «esamina i vestiti» nella camera di Livia, «leggi gli appunti». Il rischio era la tolleranza ai refusi: «caso» e «causa» nominavano la casa delle bambole, «appunto» il quaderno di Agnese, «vestita» l'armadio di Livia, e una frase non capita rispondeva «Non vedi niente del genere qui.». Diventano parole comuni (`parser.COMMON_WORDS`). Le parole intere nominano ancora, come oggi.
8. **Fuori da questo piano**, trovato preparandolo: «Agnese, mi date la tisana?» è un «dai» senza oggetto anche oggi (il modello legge «mi date» come dare), e risponde «Non ho capito.».

## Come è stato verificato, prima di scriverlo

Tutte le modifiche di questo piano sono state applicate a copie del repository, e il piano è generato da lì. Per ogni task i test nuovi falliscono sul codice di prima (Task 1: 3; Task 2: 15; Task 3: 15; Task 4: 8) e passano dopo, con tutta la suite verde (1339, poi 1358, 1377, 1384 passati; nel Task 5 i casi nuovi col modello vero, che senza Ollama si saltano: 1384 passati e 186 saltati).

Col modello vero, sulla copia con tutte le modifiche, le frasi libere di Valdimora (`test_valdimora_free_sentences`, con le 7 nuove): 76 passati e il limite noto «infilo il medaglione nella cornice» (xfail), in 949 s; «infilo il medaglione nel tetto della casa delle bambole» è di nuovo «usa il medaglione con la casa delle bambole».

Prima di arrivare agli alias nascosti, con alias normali: la frase «infilo il medaglione nel tetto della casa delle bambole» passava 4 volte su 4 sul mondo di oggi e falliva («inventario») nel giro completo con «incavo» aggiunto sulla casa, anche al posto di «comignolo»; in prove da sola, 0 su 4 con «incavo» sulla casa e «vestiti» sul baule, 1 su 4 con «incavo» e «tetto», 0 su 3 coi vestiti come arredo che compare aprendo il baule. Una frase da sola dipende anche dalla chiamata che la precede (la cache di Ollama): conta il giro completo, dove l'ordine è sempre lo stesso. Con gli alias nascosti, nella camera di Clara il modello riceve esattamente il prompt di oggi.

## Review Focus

1. **Le frasi libere di prima**: il modello riceve un elenco diverso solo nella stanza dell'orologio e in cucina con Agnese, altrove lo stesso di oggi — tutto `tests/test_ollama.py` col modello vero nel Task 5; che gli alias nascosti non arrivino al modello lo fissa un test nel Task 1.
2. **Saltare sul tetto non uccide**, né col parser né col modello; uscire sul tetto senza corda resta la morte di prima — test nel Task 2, e «mi arrampico sul tetto» nel Task 5.
3. **Con la tanica in mano Agnese non scende**: l'argomento nuovo non ha effetti — test nel Task 4.
4. **Le parole comuni nuove non tolgono i nomi interi**: «esamina la casa», «leggo gli appunti», «guardo il vestito» nominano ancora — test di guardia nel Task 2.
5. **Gli atti di prima dicono ancora quello che dicevano**: nel secondo atto Livia si alza e guarda il cordone, Ettore ha sentito il carillon «fin qui» e non ha detto il resto, Corrado non ha altri eredi — test di guardia nel Task 3.

---

### Task 1: Alias nascosti al modello

**Files:**
- Modify: `app/engine/models.py` (`Item.hidden_aliases`), `app/engine/parser.py` (`names_of`, usato da `names_said` e `_phrases`), `app/engine/validation.py` (gli alias nascosti fra i nomi controllati), `docs/formato-mondo.md`
- Test: `tests/test_parser.py`, `tests/test_interpreter.py`, `tests/test_validation.py`

**Interfaces:**
- Consumes: le fixture `world_data` (`tests/conftest.py`) e `castle` (`tests/test_interpreter.py`).
- Produces: il campo `hidden_aliases: tuple[Text, ...] = ()` di `Item` (YAML: `hidden_aliases: [incavo, tetto]`); `parser.names_of(thing) -> tuple[str, ...]` (nome, alias e alias nascosti).

- [ ] **Step 1: Test che falliscono**

- In fondo a `tests/test_parser.py`:
```python
def test_a_hidden_alias_names_the_item_like_the_others(world_data):
    # Item.hidden_aliases: the parser and the checks on the model's answers know them, the model isn't shown them.
    world_data["items"]["leva"]["hidden_aliases"] = ["maniglia"]
    world = World.model_validate(world_data)
    lever = world.items["leva"]

    assert parse("tira la maniglia", world, [lever]) == Action(verb="tira", target="leva")
    assert is_named(lever, words_of("tiro la maniglia"))
```
- In fondo a `tests/test_interpreter.py`:
```python
def test_the_model_is_not_shown_the_hidden_aliases_but_they_name_the_item(castle):
    # Valdimora's doll's house: «incavo» in the list changed the model's answer to another sentence.
    well = castle.items["pozzo"].model_copy(update={"hidden_aliases": ("buco",)})
    fake = FakeLLMClient(json_replies=[{"verbo": "esamina", "bersaglio": "pozzo", "con": "nessuno"}])

    action = interpret(fake, "guardo nel buco", [well])

    assert fake.calls[0][1].splitlines()[0] == "Oggetti: pozzo (vera)"
    assert action == Action(verb="esamina", target="pozzo")
```
- In `tests/test_validation.py`, il blocco
```python
    "item alias with no significant word": (
        lambda d: d["items"]["moneta"].update(aliases=["soldo", "la"]),
        ["items.moneta.aliases.1", "'la'"],
    ),
```
diventa
```python
    "item alias with no significant word": (
        lambda d: d["items"]["moneta"].update(aliases=["soldo", "la"]),
        ["items.moneta.aliases.1", "'la'"],
    ),
    "hidden alias with no significant word": (
        lambda d: d["items"]["moneta"].update(hidden_aliases=["la"]),
        ["items.moneta.hidden_aliases.0", "'la'"],
    ),
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 3 test: `test_a_hidden_alias_names_the_item_like_the_others`, `test_the_model_is_not_shown_the_hidden_aliases_but_they_name_the_item` e il caso «hidden alias with no significant word» di `test_broken_world_is_reported` (il campo non esiste: Pydantic lo rifiuta).

- [ ] **Step 3: Implementazione**

- In `app/engine/models.py`, il blocco
```python
    aliases: tuple[Text, ...] = ()
    description: Text
    # A room id, INVENTORY, or None when the item enters play only through an effect.
```
diventa
```python
    aliases: tuple[Text, ...] = ()
    # Names the parser and the checks on the model's answers know, but the model isn't shown: one name
    # more in the list of items changes its answers to the other sentences of the room.
    hidden_aliases: tuple[Text, ...] = ()
    description: Text
    # A room id, INVENTORY, or None when the item enters play only through an effect.
```
- In `app/engine/parser.py`, il blocco
```python
def names_said(thing: Named | Room, words: Sequence[str]) -> list[tuple[str, ...]]:
    """The names and aliases of the thing that the words say (see is_named), as significant words."""
    names = dict.fromkeys(significant_words(name) for name in (thing.name, *thing.aliases))
```
diventa
```python
def names_of(thing: Named | Room) -> tuple[str, ...]:
    """The name and the aliases of the thing, also those the model isn't shown (Item.hidden_aliases)."""
    return (thing.name, *thing.aliases, *(thing.hidden_aliases if isinstance(thing, Item) else ()))


def names_said(thing: Named | Room, words: Sequence[str]) -> list[tuple[str, ...]]:
    """The names and aliases of the thing that the words say (see is_named), as significant words."""
    names = dict.fromkeys(significant_words(name) for name in names_of(thing))
```
- In `app/engine/parser.py`, il blocco
```python
        for name in (item.name, *item.aliases):
            for key in {significant_words(name), _marked_words(name)}:
```
diventa
```python
        for name in names_of(item):
            for key in {significant_words(name), _marked_words(name)}:
```
- In `app/engine/validation.py`, il blocco
```python
    Has,
    Not,
```
diventa
```python
    Has,
    Item,
    Not,
```
- In `app/engine/validation.py`, il blocco
```python
        for index, alias in enumerate(thing.aliases):
            yield f"{path}.aliases.{index}", alias
```
diventa
```python
        for index, alias in enumerate(thing.aliases):
            yield f"{path}.aliases.{index}", alias
        for index, alias in enumerate(thing.hidden_aliases if isinstance(thing, Item) else ()):
            yield f"{path}.hidden_aliases.{index}", alias
```
- In `docs/formato-mondo.md`, il blocco
```markdown
    aliases: [gancio, uncino]    # altri nomi; possono coincidere con quelli di altri oggetti
```
diventa
```markdown
    aliases: [gancio, uncino]    # altri nomi; possono coincidere con quelli di altri oggetti
    hidden_aliases: []           # facoltativo: altri nomi che il modello non vede (vedi sotto)
```
- In `docs/formato-mondo.md`, il blocco
```markdown
nella lista va evitato, oppure la parola va aggiunta alla lista ("fuori" nominava i "fiori").
```
diventa
```markdown
nella lista va evitato, oppure la parola va aggiunta alla lista ("fuori" nominava i "fiori").

**Alias nascosti al modello.** Il modello riceve l'elenco degli oggetti con i loro alias, e ogni nome
in più cambia le sue risposte anche alle altre frasi della stanza: nella camera di Clara, «incavo»
sulla casa delle bambole faceva diventare «inventario» la frase «infilo il medaglione nel tetto della
casa delle bambole». Un nome che serve solo perché il parser e i controlli riconoscano una parola
delle descrizioni va quindi in `hidden_aliases`: vale come gli alias per il parser, per i controlli
sulle risposte del modello e per «Non vedi niente del genere qui.», ma il modello non lo vede. Il
modello non lo sceglierà mai da solo; se però sceglie l'oggetto per un'altra via (la «casetta»), la
frase che usa il nome nascosto è valida.
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1339 passati, 179 saltati).

```bash
git add app/engine/models.py app/engine/parser.py app/engine/validation.py docs/formato-mondo.md tests/test_parser.py tests/test_interpreter.py tests/test_validation.py
git commit -m "Alias nascosti al modello: nomi che capisce solo il parser" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Il tetto, l'incavo, i vestiti e le parole comuni

**Files:**
- Modify: `data/worlds/valdimora/soffitta.yaml` (alias nascosti di travi, tegola rotta, tempesta, baule e casa delle bambole; arredo `tetto_visto`; regola `salta_sul_tetto`), `data/worlds/valdimora/pianterreno.yaml` (alias nascosto della valigia), `app/engine/parser.py` (`COMMON_WORDS`)
- Test: `tests/test_valdimora.py`, `tests/test_parser.py`

**Interfaces:**
- Consumes: `Item.hidden_aliases` (Task 1); `in_act_three(valdimora, room, *flags, carried=())` di `tests/test_valdimora.py`; `World`, `is_named`, `words_of` già importati in `tests/test_parser.py`.
- Produces: oggetto `tetto_visto`, regola `salta_sul_tetto`; «caso», «causa», «appunto», «vestita» in `parser.COMMON_WORDS`.

- [ ] **Step 1: Test che falliscono**

- In fondo a `tests/test_valdimora.py`:
```python
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
```
- In `tests/test_parser.py`, il blocco
```python
        ("non ne vale la pena", "valle"),
    ],
```
diventa
```python
        ("non ne vale la pena", "valle"),
        ("per caso", "casa"),  # the doll's house of Valdimora
        ("a causa della frana", "casa"),
        ("appunto, ve l'avevo detto", "appunti"),  # Agnese's notebook
        ("siete vestita di grigio", "vestiti"),  # Livia's wardrobe
    ],
```
- In `tests/test_parser.py`, il blocco
```python
    assert is_named(key, words_of("mi siedo sul letto"))
```
diventa
```python
    assert is_named(key, words_of("mi siedo sul letto"))


@pytest.mark.parametrize(
    ("text", "alias"), [("esamina la casa", "casa"), ("leggo gli appunti", "appunti"), ("guardo il vestito", "vestiti")]
)
def test_a_name_said_whole_still_names_its_thing(world_data, text, alias):
    # «caso», «causa», «appunto», «vestita» are common words; the names themselves still name.
    world_data["items"]["chiave"]["aliases"] = [alias]
    key = World.model_validate(world_data).items["chiave"]

    assert is_named(key, words_of(text))
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 15 test: i 7 casi di `test_the_roof_can_be_examined_where_it_is_described`, `test_jumping_on_the_roof_from_the_clock_room_is_a_hint`, `test_the_medallion_fits_the_star_slot_of_the_doll_s_house`, i casi della rimessa e della camera di Clara di `test_the_clothes_are_examined_where_they_are` e i 4 casi nuovi di `test_a_common_word_is_no_typo_for_a_name`. Passano già, e devono continuare a passare, il caso della camera di Livia e `test_a_name_said_whole_still_names_its_thing`.

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
    aliases: [trave]
    description: Travi di castagno
```
diventa
```yaml
    aliases: [trave]
    hidden_aliases: [tetto]
    description: Travi di castagno
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
    aliases: [tegola, spioventi, pioggia]
```
diventa
```yaml
    aliases: [tegola, spioventi, pioggia]
    hidden_aliases: [tetto]
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
    aliases: [tegole, colmo, vento, pioggia]
```
diventa
```yaml
    aliases: [tegole, colmo, vento, pioggia]
    hidden_aliases: [tetto]
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
    aliases: [casa, casetta, bambole, comignolo]
```
diventa
```yaml
    aliases: [casa, casetta, bambole, comignolo]
    hidden_aliases: [incavo, tetto]
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
    aliases: [baule di Clara, coperchio]
```
diventa
```yaml
    aliases: [baule di Clara, coperchio]
    hidden_aliases: [vestiti]
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
  corda_legata:
    name: corda legata
```
diventa
```yaml
  tetto_visto:
    name: tetto
    gender: m
    aliases: [pioggia, vento, tegole]
    description: >
      Dal lucernario vedi il tetto: tegole lucide di pioggia, ripide come uno scivolo, e oltre la
      grondaia il vuoto. Uscirci senza niente a cui tenersi sarebbe una follia.
    location: stanza_orologio
    scenery: true
    variants:
      - when: {flag: corda_legata}
        text: Dal lucernario vedi il tetto, lucido di pioggia e ripido. La tua corda pende fin lassù.

  corda_legata:
    name: corda legata
```
- In `data/worlds/valdimora/soffitta.yaml`, il blocco
```yaml
  prendi_corda_legata:
```
diventa
```yaml
  salta_sul_tetto:
    trigger: {verb: salta, target: tetto_visto}
    when: {not: {flag: corda_legata}}
    otherwise: "Non serve saltare: la corda pende dal lucernario. Sali, e tieniti a lei."
    text: >
      Saltare, lassù? Il tetto è ripido e lucido di pioggia. Ci si sale dal lucernario, e solo con
      qualcosa a cui tenersi.

  prendi_corda_legata:
```
- In `data/worlds/valdimora/pianterreno.yaml`, il blocco
```yaml
    aliases: [bagaglio]
```
diventa
```yaml
    aliases: [bagaglio]
    hidden_aliases: [vestiti]
```
- In `app/engine/parser.py`, il blocco
```python
    porto porti fermo fermi figlio corre crede parti sogni
```
diventa
```python
    porto porti fermo fermi figlio corre crede parti sogni caso causa appunto vestita
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1358 passati, 179 saltati).

```bash
git add app/engine/parser.py data/worlds/valdimora/pianterreno.yaml data/worlds/valdimora/soffitta.yaml tests/test_parser.py tests/test_valdimora.py
git commit -m "Valdimora, minori dell'atto 3: il tetto, l'incavo, i vestiti e le parole comuni" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Livia dopo la confessione, Ettore e Corrado dopo le lettere

**Files:**
- Modify: `data/worlds/valdimora/personaggi.yaml` (varianti di Livia, Ettore e Corrado)
- Test: `tests/test_valdimora.py`, `tests/test_ollama.py` (un caso che leggeva la variante del ritratto per posizione)

**Interfaces:**
- Consumes: `in_act_three` e `in_act_two` di `tests/test_valdimora.py`; i flag `livia_confessa`, `lettere_lette`, `atto_tre`, `ritratto_scoperto`, `carillon_suonato`, `livia_chiave`.
- Produces: solo testi. La variante `lettere_lette` del ritratto di Ettore diventa la prima: il caso di `tests/test_ollama.py` che la cercava per posizione la cerca ora per condizione.

- [ ] **Step 1: Test che falliscono**

- In fondo a `tests/test_valdimora.py`:
```python
@pytest.mark.parametrize(
    ("room", "flags", "line", "expected", "stale"),
    [
        ("camera_livia", ("livia_confessa",), "chiedi a Livia della contessa", "mai una parola su Clara",
         "con gli estranei"),
        ("camera_livia", ("livia_confessa",), "chiedi a Livia di Ettore", "la favola siete voi", "crede ancora"),
        ("camera_livia", (), "chiedi a Livia delle chiavi", "Quassù non mi serve", "passa da me"),
        ("camera_livia", ("livia_confessa",), "chiedi a Livia delle chiavi", "L'unica che contava", "passa da me"),
        ("camera_livia", ("livia_chiave", "livia_confessa"), "come state, Livia?", "taciuto per trent'anni",
         "chiave dello scalone"),
        ("camera_livia", ("livia_confessa",), "grazie, Livia", "trent'anni fa", "il mio dovere"),
        ("camera_livia", ("livia_confessa",), "scusate, Livia", "Non siete voi", "non riaprono le porte"),
        ("camera_livia", ("livia_confessa",), "arrivederci, Livia", "chiudete piano la porta", "non toccate"),
        ("camera_livia", (), "chiedi a Livia del campanello", "Ci penso da quando", "si alza e guarda il cordone"),
        ("cucina", ("ritratto_scoperto", "lettere_lette"), "chiedi a Ettore del ritratto", "Vostra madre",
         "Il resto la contessa"),
        ("cucina", ("ritratto_scoperto", "carillon_suonato"), "chiedi a Ettore del carillon", "fin dalla galleria",
         "fin qui"),
        ("archivio", ("lettere_lette",), "chiedi a Corrado dell'eredità", "Vedremo chi la spunta",
         "altri eredi che me"),
        ("archivio", ("lettere_lette",), "come state, Corrado?", "una nipotina tra i piedi", "da una settimana"),
        ("archivio", ("lettere_lette",), "chi siete, Corrado?", "arrivano in corriera", "E, salvo sorprese"),
    ],
)  # fmt: skip
def test_what_the_characters_say_follows_the_third_act(valdimora, room, flags, line, expected, stale):
    # Livia after her confession, Ettore and Corrado after the letters, Livia and Ettore away from the
    # rooms of the second act.
    answer = in_act_three(valdimora, room, *flags).turn(line)

    assert expected in answer
    assert stale not in answer


def test_after_her_confession_livia_asks_to_be_left_alone(valdimora):
    game = in_act_three(valdimora, "camera_livia", "livia_confessa")

    assert "Vi ho detto tutto" in game.turn("parla con Livia")
    assert "Vi prego" in game.turn("parla con Livia")


@pytest.mark.parametrize(
    ("room", "flags", "line", "expected"),
    [
        ("camera_contessa", (), "chiedi a Livia del campanello", "si alza e guarda il cordone"),
        ("galleria", ("ritratto_scoperto", "carillon_suonato"), "chiedi a Ettore del carillon", "L'ho sentito fin qui"),
        ("galleria", ("ritratto_scoperto",), "chiedi a Ettore del ritratto", "Il resto la contessa"),
        ("studio_conte", (), "chiedi a Corrado dell'eredità", "altri eredi che me"),
    ],
)  # fmt: skip
def test_in_the_second_act_they_still_say_what_they_said(valdimora, room, flags, line, expected):
    assert expected in in_act_two(valdimora, room, *flags).turn(line)
```
- In `tests/test_ollama.py`, il blocco
```python
     says(ETTORE.topics["ritratto"].variants[0].text)),
```
diventa
```python
     says(next(v.text for v in ETTORE.topics["ritratto"].variants if v.when == FlagSet(flag="ritratto_scoperto")))),
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 15 test: i 14 casi di `test_what_the_characters_say_follows_the_third_act` e `test_after_her_confession_livia_asks_to_be_left_alone`. Passano già, e devono continuare a passare, i 4 casi di `test_in_the_second_act_they_still_say_what_they_said`.

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          Livia è seduta sul letto, con le mani in grembo e gli occhi rossi. «Vi ho detto tutto,
          signorina. Ora lasciatemi sola.»
```
diventa
```yaml
          Livia è seduta sul letto, con le mani in grembo e gli occhi rossi. «Vi ho detto tutto,
          signorina. Ora lasciatemi sola.»
        again: Livia non alza gli occhi. «Lasciatemi sola, signorina. Vi prego.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
      congedo:
        text: «Andate pure. E non toccate niente.»
      grazie:
        text: «Non ringraziatemi. Faccio il mio dovere.»
        again: «Basta ringraziare, signorina. Non serve.»
      scuse:
        text: «Le scuse non riaprono le porte, signorina.»
      come_stai:
        text: >
          «Come si sta, in una casa senza padrona.» Livia rimette in fila una penna che era già in
          fila.
        variants:
          - when: {flag: livia_chiave}
```
diventa
```yaml
      congedo:
        text: «Andate pure. E non toccate niente.»
        variants:
          - when: {flag: livia_confessa}
            text: «Andate, signorina. E chiudete piano la porta.»
      grazie:
        text: «Non ringraziatemi. Faccio il mio dovere.»
        again: «Basta ringraziare, signorina. Non serve.»
        variants:
          - when: {flag: livia_confessa}
            text: «Non ringraziatemi. Avrei dovuto farlo trent'anni fa.»
      scuse:
        text: «Le scuse non riaprono le porte, signorina.»
        variants:
          - when: {flag: livia_confessa}
            text: «Non siete voi a dovervi scusare, signorina.»
      come_stai:
        text: >
          «Come si sta, in una casa senza padrona.» Livia rimette in fila una penna che era già in
          fila.
        variants:
          - when: {flag: livia_confessa}
            text: >
              «Come una che ha taciuto per trent'anni, e stanotte ha parlato.» Livia si stringe le mani
              in grembo. «Non lo so, signorina.»
          - when: {flag: livia_chiave}
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          «Trent'anni al suo servizio.» Per un attimo la voce le si incrina. «Non parlo della
          contessa con gli estranei.»
        again: «Ho detto che non ne parlo.»
```
diventa
```yaml
          «Trent'anni al suo servizio.» Per un attimo la voce le si incrina. «Non parlo della
          contessa con gli estranei.»
        variants:
          - when: {flag: livia_confessa}
            text: >
              «Non me l'ha mai perdonato, e non me l'ha mai detto.» Livia guarda la rosa secca sul
              davanzale. «Trent'anni così, signorina: una rosa ogni mattina, e mai una parola su Clara.»
        again: «Ho detto che non ne parlo.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        text: «Ettore è vecchio, e crede ancora alle favole.»
        again: «Chiedete a lui le sue favole.»
```
diventa
```yaml
        text: «Ettore è vecchio, e crede ancora alle favole.»
        variants:
          - when: {flag: livia_confessa}
            text: «Ettore faceva bene a credere alle favole.» Livia quasi sorride. «Questa volta la favola siete voi.»
        again: «Chiedete a lui le sue favole.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        text: «Ogni chiave di questa casa passa da me.»
        again: «Tutte da me. Non fatemelo ripetere.»
```
diventa
```yaml
        text: «Ogni chiave di questa casa passa da me.»
        variants:
          - when: {flag: livia_confessa}
            text: «L'unica che contava ve l'ho data. Le altre sono giù, nel mio ufficio.»
          - when: {flag: atto_tre}
            text: «Il mazzo l'ho lasciato giù, nel mio ufficio. Quassù non mi serve.»
        again: «Tutte da me. Non fatemelo ripetere.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          «Tagliato?» Livia si alza e guarda il cordone, e per la prima volta la vedi turbata. «Non me
          n'ero accorta. La notte la contessa non chiamava mai: c'era Agnese, con le sue gocce.»
```
diventa
```yaml
          «Tagliato?» Livia si alza e guarda il cordone, e per la prima volta la vedi turbata. «Non me
          n'ero accorta. La notte la contessa non chiamava mai: c'era Agnese, con le sue gocce.»
        variants:
          - when: {flag: atto_tre}
            text: >
              «Il cordone tagliato? Ci penso da quando l'avete visto.» Livia si stringe le mani in
              grembo. «La notte la contessa non chiamava mai: c'era Agnese, con le sue gocce.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        variants:
          - when: {flag: ritratto_scoperto}
            text: >
              «La signorina Clara, a vent'anni. Viveva qui, in questa casa.»
```
diventa
```yaml
        variants:
          - when: {flag: lettere_lette}
            text: >
              «La signorina Clara, a vent'anni. Vostra madre.» Ettore si schiarisce la voce. «Ora
              sapete tutto, e io sono sciolto dalla mia parola. Le somigliate più di quanto crediate.»
          - when: {flag: ritratto_scoperto}
            text: >
              «La signorina Clara, a vent'anni. Viveva qui, in questa casa.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        variants:
          - when: {flag: carillon_suonato}
            text: >
              «L'avete fatto suonare. L'ho sentito fin qui.»
```
diventa
```yaml
        variants:
          - when: {all: [{flag: atto_tre}, {flag: carillon_suonato}]}
            text: >
              «L'avete fatto suonare, il carillon. L'ho sentito fin dalla galleria.» Ettore chiude gli
              occhi. «La ninna nanna della signorina Clara. Non la sentivo da trent'anni.»
          - when: {flag: carillon_suonato}
            text: >
              «L'avete fatto suonare. L'ho sentito fin qui.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        again: «Tutto a me, ve l'ho detto. Mettetevi il cuore in pace.»
```
diventa
```yaml
        variants:
          - when: {flag: lettere_lette}
            text: >
              «L'eredità?» Corrado ride, ma gli riesce male. «Fino a stasera era tutta mia. Ora c'è una
              nipotina col medaglione, e un notaio che non arriva. Vedremo chi la spunta.»
            again: «Vedremo, signorina. Vedremo.»
        again: «Tutto a me, ve l'ho detto. Mettetevi il cuore in pace.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          «Come uno che aspetta un'eredità da una settimana. Benissimo, quindi. Grazie per
          l'interesse.»
```
diventa
```yaml
          «Come uno che aspetta un'eredità da una settimana. Benissimo, quindi. Grazie per
          l'interesse.»
        variants:
          - when: {flag: lettere_lette}
            text: «Come uno che aspettava un'eredità, e si è trovato una nipotina tra i piedi. Benissimo, grazie.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          «Corrado di Valdimora, nipote del conte buonanima. E, salvo sorprese, il prossimo padrone
          di tutto questo.»
```
diventa
```yaml
          «Corrado di Valdimora, nipote del conte buonanima. E, salvo sorprese, il prossimo padrone
          di tutto questo.»
        variants:
          - when: {flag: lettere_lette}
            text: >
              «Corrado di Valdimora, nipote del conte buonanima. Il prossimo padrone di tutto questo,
              salvo sorprese.» Ti guarda il medaglione. «E le sorprese, a quanto pare, arrivano in
              corriera.»
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1377 passati, 179 saltati).

```bash
git add data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py tests/test_ollama.py
git commit -m "Valdimora, minori dell'atto 3: Livia dopo la confessione, Ettore e Corrado dopo le lettere" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Agnese di sotto

**Files:**
- Modify: `data/worlds/valdimora/personaggi.yaml` (saluto, `aiuto`, `tisana`, argomenti nuovi `tanica` e `tazza`; l'argomento «Agnese» di Ettore)
- Test: `tests/test_valdimora.py`

**Interfaces:**
- Consumes: `in_act_three`; i flag `agnese_in_cucina`, `agnese_in_rimessa` dell'atto 3.
- Produces: argomenti `agnese.tanica` (senza effetti) e `agnese.tazza` (accende `tisana_bevuta`); flag `tisana_bevuta`, letto solo da varianti di testo.

- [ ] **Step 1: Test che falliscono**

- In fondo a `tests/test_valdimora.py`:
```python
def test_after_the_tea_agnese_no_longer_says_it_is_almost_ready(valdimora):
    game = in_act_three(valdimora, "cucina", "agnese_in_cucina")

    assert "bella calda" in game.turn("chiedi ad Agnese della tisana")
    assert "Vi ha scaldata" in game.turn("parla con Agnese")
    assert "Un'altra tazza?" in game.turn("chiedi ad Agnese della tisana")
    assert "Vi ha fatto la tisana" in game.turn("chiedi a Ettore di Agnese")


def test_from_the_coach_house_agnese_goes_to_the_kitchen_for_the_tea(valdimora):
    game = in_act_three(valdimora, "rimessa", "agnese_in_rimessa")

    answer = game.turn("chiedi ad Agnese della tisana")

    assert "verso la cucina" in answer and "scende" not in answer
    assert game.engine.character_room(valdimora.characters["agnese"], game.state) == "cucina"


@pytest.mark.parametrize(
    ("room", "flags", "carried", "line", "expected"),
    [
        ("cucina", ("agnese_in_cucina",), (), "chiedi ad Agnese di aiuto", "la tisana è sul fuoco"),
        ("rimessa", ("agnese_in_rimessa",), (), "chiedi ad Agnese di aiuto", "vado in cucina"),
        ("cucina", ("agnese_in_cucina",), (), "chiedi ad Agnese del petrolio", "accanto al muro"),
        ("rimessa", ("agnese_in_rimessa",), ("tanica",), "chiedi ad Agnese del petrolio", "L'avete presa voi"),
    ],
)  # fmt: skip
def test_downstairs_agnese_no_longer_offers_to_go_down(valdimora, room, flags, carried, line, expected):
    answer = in_act_three(valdimora, room, *flags, carried=carried).turn(line)

    assert expected in answer
    assert "Le scale le conosco" not in answer
    assert "Non saprei" not in answer


def test_with_the_oil_can_in_hand_agnese_stays_upstairs(valdimora):
    game = in_act_three(valdimora, "corridoio_servitu", carried=("tanica",))

    assert "L'avete presa voi" in game.turn("chiedi ad Agnese del petrolio")
    assert game.engine.character_room(valdimora.characters["agnese"], game.state) == "corridoio_servitu"
```
- In `tests/test_valdimora.py`, il blocco
```python
    # Only Ettore's word for Livia and the key of the sideboard come from talking; Agnese's errands, in the
    # third act, only send her downstairs.
```
diventa
```python
    # Only Ettore's word for Livia and the key of the sideboard come from talking; Agnese's errands, in the
    # third act, only send her downstairs, and the tea she gives there only changes what she says.
```
- In `tests/test_valdimora.py`, il blocco
```python
    assert set(effects) == {("ettore", "livia"), ("ettore", "credenza"), ("agnese", "petrolio"), ("agnese", "tisana")}
    assert [*effects["agnese", "petrolio"], *effects["agnese", "tisana"]] == [
        SetFlag(set_flag="agnese_in_rimessa"),
        SetFlag(set_flag="agnese_in_cucina"),
    ]
```
diventa
```python
    assert set(effects) == {
        ("ettore", "livia"), ("ettore", "credenza"), ("agnese", "petrolio"), ("agnese", "tisana"), ("agnese", "tazza")
    }  # fmt: skip
    assert [*effects["agnese", "petrolio"], *effects["agnese", "tisana"], *effects["agnese", "tazza"]] == [
        SetFlag(set_flag="agnese_in_rimessa"),
        SetFlag(set_flag="agnese_in_cucina"),
        SetFlag(set_flag="tisana_bevuta"),
    ]
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider`
Expected: FAIL — 8 test: `test_no_character_gives_a_shortcut` (l'argomento `tazza` non c'è), `test_after_the_tea_agnese_no_longer_says_it_is_almost_ready`, `test_from_the_coach_house_agnese_goes_to_the_kitchen_for_the_tea`, i 4 casi di `test_downstairs_agnese_no_longer_offers_to_go_down` e `test_with_the_oil_can_in_hand_agnese_stays_upstairs`.

- [ ] **Step 3: Implementazione**

- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
    greeting_variants:
      - when: {flag: agnese_in_cucina}
        text: >
          Agnese è in cucina, davanti al focolare, e versa l'acqua bollente in una tazza.
```
diventa
```yaml
    greeting_variants:
      - when: {flag: tisana_bevuta}
        text: Agnese è davanti al focolare, e sciacqua la tua tazza. «Vi ha scaldata, la tisana? Se vi serve altro, sono qui.»
        again: «Vi aspetto qui, signorina, se vi serve altro.»
      - when: {flag: agnese_in_cucina}
        text: >
          Agnese è in cucina, davanti al focolare, e versa l'acqua bollente in una tazza.
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
        variants:
          - when: {flag: atto_tre}
            text: >
              «Se vi serve qualcosa di sotto, chiedete a me:
```
diventa
```yaml
        variants:
          - when: {flag: agnese_in_cucina}
            text: >
              «Ci sono io, signorina: la tisana è sul fuoco. Il petrolio è in rimessa, ma la tanica per
              me è troppo pesante.»
          - when: {flag: agnese_in_rimessa}
            text: >
              «La tanica è lì, accanto al muro. E se volete qualcosa di caldo, vado in cucina e vi
              preparo una tisana.»
          - when: {flag: atto_tre}
            text: >
              «Se vi serve qualcosa di sotto, chiedete a me:
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
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
```
diventa
```yaml
            text: «La tanica è lì, signorina, accanto al muro. Prendetela pure, per me è troppo pesante.»
      # Once she is in the kitchen, or the oil can is in hand: the same question, and Agnese stays.
      tanica:
        name: tanica
        gender: f
        aliases: [petrolio, tanica di petrolio]
        when: {all: [{flag: atto_tre}, {any: [{has: tanica}, {flag: agnese_in_cucina}]}]}
        text: «La tanica è in rimessa, signorina, accanto al muro. Per me è troppo pesante, ma voi ce la fate.»
        variants:
          - when: {has: tanica}
            text: «L'avete presa voi, la tanica? Brava. Pesa, eh?»
      tisana:
        name: tisana
        gender: f
        aliases: [camomilla, infuso, qualcosa di caldo, tazza]
        when: {all: [{flag: atto_tre}, {not: {flag: agnese_in_cucina}}]}
        effects:
          - set_flag: agnese_in_cucina
        text: >
          «Una tisana? Ma certo, signorina: vado in cucina e ve la preparo. Vi aspetto là, al caldo.»
          Agnese prende la candela e scende.
        variants:
          - when: {player_in: rimessa}
            text: >
              «Una tisana? Ma certo, signorina: vado in cucina e ve la preparo. Vi aspetto là, al caldo.»
              Agnese si pulisce le mani nel grembiule ed esce, verso la cucina.
      # In the kitchen: the tea is ready, and from then on her greeting knows it.
      tazza:
        name: tazza di tisana
        gender: f
        aliases: [tisana, camomilla, infuso, qualcosa di caldo, tazza]
        when: {flag: agnese_in_cucina}
        effects:
          - set_flag: tisana_bevuta
        text: >
          «Eccola, bella calda.» Agnese ti porge una tazza fumante, e tu la bevi a piccoli sorsi. Sa di
          camomilla e di miele. «Vi aspetto qui, se vi serve altro.»
        again: >
          «Un'altra tazza?» Agnese te ne versa ancora. «Bevete, signorina: vi scalda.»
```
- In `data/worlds/valdimora/personaggi.yaml`, il blocco
```yaml
          - when: {flag: agnese_in_cucina}
            text: «È qui con noi, signorina, davanti al focolare. Dice che vi prepara una tisana.»
```
diventa
```yaml
          - when: {flag: tisana_bevuta}
            text: "«È qui con noi, davanti al focolare. Vi ha fatto la tisana, vedo: una ragazza servizievole.»"
          - when: {flag: agnese_in_cucina}
            text: «È qui con noi, signorina, davanti al focolare. Dice che vi prepara una tisana.»
```

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1384 passati, 179 saltati). Restano verdi anche `test_sent_downstairs_agnese_leaves_her_room_open` e `test_downstairs_agnese_does_the_errand` («chiedi ad Agnese della tisana» in cucina ora trova la tazza).

```bash
git add data/worlds/valdimora/personaggi.yaml tests/test_valdimora.py
git commit -m "Valdimora, minori dell'atto 3: Agnese di sotto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Il modello vero e CLAUDE.md

**Files:**
- Modify: `tests/test_ollama.py` (7 casi nuovi in `VALDIMORA_CASES`), `CLAUDE.md`

**Interfaces:**
- Consumes: `tetto_visto` e gli alias nascosti di `casa_bambole` (Task 2), il flag `tisana_bevuta` (Task 4); `says`, `Action`, `ACT_THREE`, `VALDIMORA` di `tests/test_ollama.py`.
- Produces: niente per altri task.

- [ ] **Step 1: I casi col modello vero**

- In `tests/test_ollama.py`, il blocco
```python
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "sentence", "check"),
```
diventa
```python
    # The minors of act 3: the roof seen from the clock room, the star slot of the doll's house, the tea.
    ("stanza_orologio", (), ACT_THREE, "do un'occhiata al tetto", says(VALDIMORA.items["tetto_visto"].description)),
    ("stanza_orologio", (), ACT_THREE, "guardo la pioggia sul tetto", says(VALDIMORA.items["tetto_visto"].description)),
    ("stanza_orologio", (), ACT_THREE, "mi arrampico sul tetto", lambda a, g: not g.finished),
    ("soffittone", (), ACT_THREE, "guardo il tetto", lambda a, g: "Non vedi" not in a and not g.finished),
    ("camera_clara", (), (*ACT_THREE, "camera_clara_aperta"), "uso il medaglione con l'incavo della casetta",
     lambda a, g: g.state.item_locations["chiave_cantina"] == "inventory"
     or g.pending == Action(verb="usa", target="medaglione", with_="casa_bambole")),
    ("camera_clara", (), (*ACT_THREE, "camera_clara_aperta"), "metto il medaglione nell'incavo",
     lambda a, g: g.state.item_locations["chiave_cantina"] == "inventory"
     or g.pending == Action(verb="usa", target="medaglione", with_="casa_bambole")),
    ("cucina", (), (*ACT_THREE, "agnese_in_cucina"), "Agnese, mi preparate una camomilla?",
     lambda a, g: "tisana_bevuta" in g.state.flags),
]  # fmt: skip


@pytest.mark.parametrize(
    ("room", "carried", "flags", "sentence", "check"),
```

- [ ] **Step 2: Il modello vero, prima le frasi di Valdimora, poi tutto**

Con Ollama acceso e `qwen2.5:3b` scaricato:

Run: `OLLAMA_TESTS=1 .venv/Scripts/python -m pytest tests/test_ollama.py -k valdimora_free_sentences -v -s` (circa 17 minuti)
Expected: i 7 casi nuovi passano, e quelli di prima come su `main`. Sulla copia: 76 passati e il limite noto «infilo il medaglione nella cornice» (xfail), in 949 s; «infilo il medaglione nel tetto della casa delle bambole» è di nuovo «usa il medaglione con la casa delle bambole».

Run: `OLLAMA_TESTS=1 .venv/Scripts/python -m pytest tests/test_ollama.py -v -s` (circa 30 minuti)
Expected: 179 passati e 7 limiti noti (xfail), 186 in tutto; su `main` erano 172 su 179.

Il modello non è del tutto deterministico (2 o 3 frasi su 80 cambiano da un giro all'altro). Se una frase di prima fallisce, rilanciare il giro di Valdimora, poi provarla su `main` (in un worktree o dopo `git stash`). Se fallisce solo col branch, fermarsi e riferire, con la risposta del modello (`LLM_LOG=on`, in `logs/llm.log`): il prompt non si tocca, e un alias visibile si sposta fra quelli nascosti solo dopo averne discusso.

- [ ] **Step 3: CLAUDE.md**

- In `CLAUDE.md`, il blocco
```markdown
    «casa», «appunti», «vestiti».

## Decisioni ancora aperte
```
diventa
```markdown
    «casa», «appunti», «vestiti».
- **Minori dell'atto 3** (2026-10-01, branch `feature/valdimora-atto-3-minori`; piano in
  `docs/superpowers/plans/2026-10-01-valdimora-atto-3-minori.md`):
  - **Alias nascosti al modello** (`hidden_aliases` sugli oggetti, formato in
    `docs/formato-mondo.md`): il parser, i controlli sulle risposte del modello e «Non vedi niente
    del genere qui.» li riconoscono come gli alias, ma il modello non li vede. Ogni nome in più
    nell'elenco degli oggetti cambia le risposte del modello anche alle altre frasi della stanza:
    un alias in più sulla casa delle bambole, o «vestiti» sul baule, faceva diventare «inventario»
    «infilo il medaglione nel tetto della casa delle bambole». Un nome che serve solo perché il
    parser riconosca una parola delle descrizioni va lì.
  - Il tetto visto dalla stanza dell'orologio è un arredo (`tetto_visto`, anche pioggia e vento), e
    saltarci sopra è un indizio; altrove «tetto» è un alias nascosto di ciò che c'è (travi, tegola
    rotta, tempesta, casa delle bambole). La casa delle bambole ha anche «incavo» («usa il
    medaglione con l'incavo» rispondeva «Non vedi niente del genere qui.»: era della meridiana e
    del ritratto), la valigia e il baule «vestiti» (erano solo l'armadio di Livia). «caso»,
    «causa», «appunto» e «vestita» sono parole comuni: non nominano più la casa delle bambole, il
    quaderno e l'armadio.
  - I testi che invecchiano andando avanti nell'atto: Livia dopo la confessione, Ettore e Corrado
    dopo le lettere, Livia ed Ettore lontani dalle stanze dell'atto 2, Agnese di sotto che non si
    offre più di scendere e, in rimessa, va in cucina per la tisana. Due argomenti nuovi di Agnese:
    la tazza di tisana (solo in cucina; poi il suo saluto ed Ettore sanno che l'hai bevuta, flag
    `tisana_bevuta`) e la tanica (con lei in cucina o la tanica in mano, senza effetti: prima
    rispondeva «Non saprei»). Gli effetti di un argomento valgono per l'argomento intero: per un
    effetto che vale in un posto solo serve un argomento a parte, con un `when` che escluda l'altro
    (gli alias possono essere gli stessi, i nomi no).
  - Limiti accettati: nello stenditoio e nel cortile «esamina il tetto» risponde «Non vedi niente
    del genere qui.» (è il tetto visto dalla stanza dell'orologio); «Agnese, mi date la tisana?» è
    un «dai» senza oggetto, come prima.

## Decisioni ancora aperte
```
- In `CLAUDE.md`, il blocco
```markdown
    `tests/test_ollama.py` (oggi 172 su 179, ~1780 s: i 36 casi di prima, gli 8 dei pericoli, i 17
    del primo atto di Valdimora, le 20 frasi dei dialoghi e le 24 del terzo atto tutti, 28 delle 29
    frasi del secondo atto e 39 delle 45 frasi trovate giocando; le altre 7 sono limiti noti, e
    «infilo il medaglione nella cornice» a volte passa).
```
diventa
```markdown
    `tests/test_ollama.py` (oggi 179 su 186, ~1850 s: i 36 casi di prima, gli 8 dei pericoli, i 17
    del primo atto di Valdimora, le 20 frasi dei dialoghi, le 24 del terzo atto e le 7 dei suoi
    minori tutti, 28 delle 29 frasi del secondo atto e 39 delle 45 frasi trovate giocando; le altre
    7 sono limiti noti, e «infilo il medaglione nella cornice» a volte passa).
```
Se il giro completo dello Step 2 dà numeri o tempi diversi, scrivere quelli del giro.

- [ ] **Step 4: Verificare, e commit**

Run: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` — Expected: tutto verde (1384 passati, 186 saltati).

```bash
git add tests/test_ollama.py CLAUDE.md
git commit -m "Valdimora, minori dell'atto 3: le frasi col modello vero, e CLAUDE.md" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
