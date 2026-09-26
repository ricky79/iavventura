# Più avventure e menu d'ingresso (pezzo 1) — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il gioco carica più avventure da `data/worlds/`, e il giocatore ne sceglie una da un menu nel browser e nel terminale, con un salvataggio per avventura; la Rocca si gioca esattamente come prima.

**Architecture:** ogni avventura è una cartella con un mondo completo; `avventure.yaml` dà l'ordine del menu. Il server tiene un `Engine` per avventura e riceve l'id con ogni richiesta, accanto allo stato (che resta solo del motore). Il prompt dell'interprete si compone di testa fissa + esempi del mondo (dal suo YAML) + coda fissa, e per la Rocca resta identico a oggi.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyYAML, pytest; pagina HTML/JS senza framework.

**Spec:** `docs/superpowers/specs/2026-09-26-piu-avventure-design.md` — sezione 1. I pezzi 2 («dai») e 3 (il draghetto) avranno ciascuno il loro piano.

## Global Constraints

- Nessuna dipendenza nuova. Comandi da PowerShell con `.venv\Scripts\python`.
- Codice e identificatori in inglese; testi per il giocatore, messaggi di commit e documentazione in italiano.
- Il motore (`app/engine/`) non importa nulla da `app/llm/`.
- Il prompt di sistema della Rocca resta **identico carattere per carattere** (lo controlla `tests/prompt_rocca.txt`).
- Nel pezzo 1 `data/worlds/avventure.yaml` elenca **solo** `rocca`.
- Ogni accesso a `localStorage` resta dentro `try/catch`.
- Mai nei commit: `run.bat`, `test_llm.txt` e la modifica non committata dell'utente a `stanze.yaml` («con la vera di pietra» → «di pietra»). Aggiungere i file uno per uno, mai `git add -A` o `git add .`.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Il prompt perde gli esempi del mondo** (Game o `test_ollama.py` che chiamano `interpret` senza `examples`): la Rocca tornerebbe al bug del rampino senza che nessun test col client finto se ne accorga → test in Task 2 (`test_the_llm_gets_the_examples_of_the_world`) e `understood()` di `test_ollama.py` aggiornato.
2. **Un browser con il vecchio salvataggio unico** (`castle-adventure.save`): deve ritrovare la sua partita nella Rocca, non il menu vuoto → prova a mano con lo snippet del Task 5.
3. **Risposte al menu che non corrispondono a un'avventura** («3», «0», riga vuota, una parola presente in due titoli): si richiede, niente eccezioni → test parametrizzato in Task 4 (stessa regola nella pagina, provata a mano).
4. **Un salvataggio di un'avventura che il server non ha più** (tolta dall'indice): 404 e ritorno al menu, salvataggio scartato → test in Task 3 e prova a mano in Task 5.
5. **Lo stato di un'avventura mandato con l'id di un'altra**: l'altra ricomincia («Il mondo è cambiato…»), nessun errore → test in Task 3 (`test_a_state_goes_with_its_own_adventure`).

---

### Task 1: Avventure in cartelle, indice e `summary`

**Files:**
- Move: `data/world/` → `data/worlds/rocca/` (con `git mv`)
- Create: `data/worlds/avventure.yaml`
- Modify: `app/engine/models.py` (`GameInfo`), `app/engine/loader.py`, `data/worlds/rocca/gioco.yaml`, `tests/conftest.py`
- Modify (solo il percorso del mondo): `app/cli.py`, `app/main.py`, `tests/test_castello.py`, `tests/test_cli.py`, `tests/test_game.py`, `tests/test_interpreter.py`, `tests/test_ollama.py`, `tests/test_web.py`
- Modify: `docs/formato-mondo.md`, `README.md`
- Test: `tests/test_loader.py`

**Interfaces:**
- Produces: `WORLDS_DIR: Path`, `INDEX_FILE = "avventure.yaml"`, `load_adventures(root: Path = WORLDS_DIR) -> dict[str, World]`; `load_world(directory: Path) -> World` **senza** valore predefinito; `GameInfo.summary: Text` (obbligatorio). Il mondo di prova di `conftest.py` ha `summary: "Un mondo di prova."`.

- [ ] **Step 1: Spostare il mondo senza toccare la modifica dell'utente**

```powershell
git mv data/world data/worlds/rocca
git status --short
```
Atteso: `R  data/world/… -> data/worlds/rocca/…` per i cinque file, e ` M data/worlds/rocca/stanze.yaml` (la modifica dell'utente, **non** in stage). Da qui in poi non fare mai `git add data/worlds/rocca/stanze.yaml`.

- [ ] **Step 2: Scrivere i test del loader che falliscono**

In `tests/conftest.py`, nella sezione `game` di `world_data`, dopo `"title": "Prova",` aggiungere:

```python
            "summary": "Un mondo di prova.",
```

In `tests/test_loader.py` cambiare l'import in
`from app.engine.loader import INDEX_FILE, WORLDS_DIR, WorldError, load_adventures, load_world, parse_world`
e aggiungere in fondo:

```python
# --- Several adventures -----------------------------------------------------------------------------


@pytest.fixture
def worlds_root(tmp_path: Path, world_data: dict) -> Path:
    """Two adventures, listed in the index in the opposite of alphabetical order."""
    for adventure_id in ("zeta", "alfa"):
        directory = tmp_path / adventure_id
        directory.mkdir()
        write_yaml(directory, "gioco.yaml", {**world_data, "game": {**world_data["game"], "title": adventure_id.title()}})
    write_yaml(tmp_path, INDEX_FILE, {"adventures": ["zeta", "alfa"]})
    return tmp_path


def test_adventures_come_in_the_order_of_the_index(worlds_root):
    worlds = load_adventures(worlds_root)

    assert list(worlds) == ["zeta", "alfa"]
    assert worlds["alfa"].game.title == "Alfa"


def test_a_folder_that_is_not_in_the_index_is_not_loaded(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa"]})

    assert list(load_adventures(worlds_root)) == ["alfa"]


def test_a_missing_index_is_rejected(worlds_root):
    (worlds_root / INDEX_FILE).unlink()

    with pytest.raises(WorldError) as error:
        load_adventures(worlds_root)

    assert error.value.problems == [f"{INDEX_FILE}: not found in {worlds_root}"]


@pytest.mark.parametrize(
    "index",
    [{"adventures": []}, {"adventures": "alfa"}, {"avventure": ["alfa"]}, ["alfa"], {"adventures": ["Alfa!"]}],
    ids=["empty", "not a list", "misspelled key", "not a mapping", "not an id"],
)
def test_a_malformed_index_is_rejected(worlds_root, index):
    write_yaml(worlds_root, INDEX_FILE, index)

    with pytest.raises(WorldError) as error:
        load_adventures(worlds_root)

    assert all(problem.startswith(f"{INDEX_FILE}: ") for problem in error.value.problems)


def test_an_adventure_listed_twice_is_rejected(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa", "zeta", "alfa"]})

    with pytest.raises(WorldError) as error:
        load_adventures(worlds_root)

    assert error.value.problems == [f"{INDEX_FILE}: 'alfa' is listed twice"]


def test_a_listed_adventure_without_its_folder_is_rejected(worlds_root):
    write_yaml(worlds_root, INDEX_FILE, {"adventures": ["alfa", "beta"]})

    with pytest.raises(WorldError) as error:
        load_adventures(worlds_root)

    assert error.value.problems == ["beta: folder not found"]


def test_the_problems_of_every_adventure_come_with_its_id(worlds_root):
    write_text(worlds_root / "alfa", "rotto.yaml", """
        rooms:
          sala: [non chiusa
    """)
    write_text(worlds_root / "zeta", "extra.yaml", """
        items:
          sasso:
            name: sasso
            gender: m
            description: Un sasso.
            location: soffitta
    """)

    with pytest.raises(WorldError) as error:
        load_adventures(worlds_root)

    problems = error.value.problems
    assert any(problem.startswith("zeta: ") and "soffitta" in problem for problem in problems)
    assert any(problem.startswith("alfa: rotto.yaml, line ") for problem in problems)


def test_the_summary_for_the_menu_is_required(world_data):
    del world_data["game"]["summary"]

    with pytest.raises(WorldError) as error:
        parse_world(world_data)

    assert "game.summary: Field required" in error.value.problems


def test_the_real_adventures_load():
    worlds = load_adventures()

    assert list(worlds) == ["rocca"]
    assert worlds["rocca"].game.title == "La Rocca di Serravento"
    assert load_world(WORLDS_DIR / "rocca") == worlds["rocca"]
```

- [ ] **Step 3: Verificare che falliscano**

Run: `.venv\Scripts\python -m pytest tests/test_loader.py -q`
Atteso: errore di import (`cannot import name 'INDEX_FILE'`).

- [ ] **Step 4: `summary` nel modello e nella Rocca**

In `app/engine/models.py`, `class GameInfo`, dopo `title: Text`:

```python
    summary: Text  # one or two lines for the menu of the adventures
```

In `data/worlds/rocca/gioco.yaml`, dopo `title: La Rocca di Serravento`:

```yaml
  summary: Un castello abbandonato, una bufera, un portone che non si riapre.
```

- [ ] **Step 5: Il loader**

In `app/engine/loader.py`:

1. Docstring del modulo:

```python
"""Loads the adventures from data/worlds/ and validates them.

Each adventure is a folder of YAML files (its id is the folder's name); data/worlds/avventure.yaml
lists the ones to load, in the order of the menu. Every file of a folder may contain any of the
top-level sections (game, rooms, items, rules, characters): the sections are merged, so how a world
is split across files is only a convention.
"""
```

2. Import: `from pydantic import BaseModel, ConfigDict, Field, ValidationError` e `from app.engine.models import Id, World`.

3. Sostituire `DEFAULT_WORLD_DIR = …` con:

```python
WORLDS_DIR = Path(__file__).resolve().parents[2] / "data" / "worlds"
INDEX_FILE = "avventure.yaml"
```

4. `def load_world(directory: Path = DEFAULT_WORLD_DIR) -> World:` diventa `def load_world(directory: Path) -> World:`.

5. Dopo `load_world`, aggiungere:

```python
def load_adventures(root: Path = WORLDS_DIR) -> dict[str, World]:
    """Every adventure listed in the index, keyed by its folder, in the order of the menu.

    The problems of all the adventures are reported together, each one after the id of its adventure.
    """
    worlds: dict[str, World] = {}
    problems: list[str] = []
    for adventure_id in _adventure_ids(root):
        directory = root / adventure_id
        if not directory.is_dir():
            problems.append(f"{adventure_id}: folder not found")
            continue
        try:
            worlds[adventure_id] = load_world(directory)
        except WorldError as exc:
            problems += [f"{adventure_id}: {problem}" for problem in exc.problems]
    if problems:
        raise WorldError(problems)
    return worlds


class _Index(BaseModel):
    """avventure.yaml: the folders of the adventures, in the order of the menu."""

    model_config = ConfigDict(extra="forbid")

    adventures: list[Id] = Field(min_length=1)


def _adventure_ids(root: Path) -> list[str]:
    path = root / INDEX_FILE
    if not path.is_file():
        raise WorldError([f"{INDEX_FILE}: not found in {root}"])
    try:
        index = _Index.model_validate(_read_yaml(path))
    except yaml.YAMLError as exc:
        raise WorldError([_describe_yaml_error(path, exc)]) from None
    except ValidationError as exc:
        raise WorldError([f"{INDEX_FILE}: {_describe_validation_error(err)}" for err in exc.errors()]) from None
    repeated = sorted({adventure_id for adventure_id in index.adventures if index.adventures.count(adventure_id) > 1})
    if repeated:
        raise WorldError([f"{INDEX_FILE}: '{adventure_id}' is listed twice" for adventure_id in repeated])
    return index.adventures
```

- [ ] **Step 6: L'indice**

Create `data/worlds/avventure.yaml`:

```yaml
# Le avventure del menu, nell'ordine in cui compaiono: ogni id è una cartella accanto a questo
# file. Una cartella che non è qui non viene caricata. Formato: docs/formato-mondo.md
adventures:
  - rocca
```

- [ ] **Step 7: Il percorso esplicito della Rocca dove serviva il mondo predefinito**

In ognuno di questi file l'import di `load_world` diventa `from app.engine.loader import WORLDS_DIR, load_world` e ogni `load_world()` senza argomenti diventa `load_world(WORLDS_DIR / "rocca")`:
`app/cli.py` (riga `game = Game(Engine(load_world()), llm)`), `app/main.py` (riga `return create_app(Engine(load_world()), …)`), `tests/test_castello.py`, `tests/test_cli.py` (dentro `play`: `world or load_world(WORLDS_DIR / "rocca")`), `tests/test_game.py`, `tests/test_interpreter.py`, `tests/test_ollama.py` (`CASTLE = load_world(WORLDS_DIR / "rocca")`), `tests/test_web.py`.
(Terminale e server avranno il menu nei Task 3 e 4: qui cambia solo il percorso.)

Controllo: `.venv\Scripts\python -m pytest -q` e poi Grep di `load_world()` in `app/` e `tests/`: nessun risultato.

- [ ] **Step 8: Verificare che passi tutto**

Run: `.venv\Scripts\python -m pytest -q`
Atteso: tutti verdi (i test col modello vero restano saltati).

- [ ] **Step 9: Documentazione**

`docs/formato-mondo.md`:
- riga 5: «L'esempio completo è la Rocca di Serravento in `data/worlds/rocca/`.»
- sezione «## File», primo punto sostituito da:

```markdown
- Ogni avventura sta in una cartella `data/worlds/<id>/`: l'id è il nome della cartella. Il loader
  legge tutti i file `.yaml` della cartella e ne unisce le sezioni.
- `data/worlds/avventure.yaml` elenca le avventure nell'ordine del menu (`adventures: [rocca]`).
  Una cartella che non è nell'elenco non viene caricata: così se ne può preparare una senza
  mostrarla. Gli errori di un'avventura portano il suo id davanti (`rocca: items.pozzo: …`).
```

- nell'esempio YAML della sezione «## `game`», dopo `title:`:

```yaml
  summary: Una o due righe per il menu delle avventure.
```

`README.md`: riga 42 «in `data/worlds/rocca/`»; il comando a riga 147-151 diventa

```markdown
Controllare che le avventure in `data/worlds/` siano valide:

```powershell
.venv\Scripts\python -c "from app.engine.loader import load_adventures; print([w.game.title for w in load_adventures().values()])"
```
```

e nella struttura (riga 175) `data/worlds/         # le avventure: una cartella ciascuna, e l'indice del menu`.

- [ ] **Step 10: Commit**

```powershell
git add data/worlds/avventure.yaml data/worlds/rocca/gioco.yaml app/engine/models.py app/engine/loader.py app/cli.py app/main.py tests/conftest.py tests/test_loader.py tests/test_castello.py tests/test_cli.py tests/test_game.py tests/test_interpreter.py tests/test_ollama.py tests/test_web.py docs/formato-mondo.md README.md
git status --short
```
Atteso: ` M data/worlds/rocca/stanze.yaml` ancora **non** in stage (colonna sinistra vuota), `run.bat` e `test_llm.txt` non tracciati. Poi:

```powershell
git commit -m "Avventure in cartelle: data/worlds/ con l'indice del menu e il riassunto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Il prompt dell'interprete con gli esempi del mondo

**Files:**
- Create: `tests/prompt_rocca.txt` (copia del prompt di oggi, generata)
- Modify: `app/llm/prompts.py`, `app/llm/interpreter.py`, `app/game.py:104`, `app/engine/models.py` (`GameInfo`), `data/worlds/rocca/gioco.yaml`, `tests/test_ollama.py` (`understood`), `docs/formato-mondo.md`
- Test: `tests/test_interpreter.py`, `tests/test_game.py`

**Interfaces:**
- Consumes: `load_world(WORLDS_DIR / "rocca")` (Task 1).
- Produces: `interpreter_system(examples: str | None = None) -> str` in `app/llm/prompts.py` (sostituisce la costante `INTERPRETER_SYSTEM`, che sparisce); `interpret(llm, sentence, in_reach, exits=(), characters=(), examples: str | None = None)`; `GameInfo.examples: Text | None`.

- [ ] **Step 1: Fotografare il prompt di oggi, prima di toccarlo**

```powershell
.venv\Scripts\python -c "from pathlib import Path; from app.llm.prompts import INTERPRETER_SYSTEM; Path('tests/prompt_rocca.txt').write_text(INTERPRETER_SYSTEM, encoding='utf-8')"
```
Controllo: il file finisce con `{"verbo": "chiedi", "bersaglio": "cuoca", "con": "nessuno"}` e contiene la riga del rampino.

- [ ] **Step 2: Scrivere i test che falliscono**

In `tests/test_interpreter.py`: l'import `from app.llm.prompts import INTERPRETER_SYSTEM` diventa `from app.llm.prompts import interpreter_system`, e si aggiunge `from pathlib import Path` in testa. Poi:

1. `test_the_prompt_shows_a_sentence_with_a_purpose`: `) in INTERPRETER_SYSTEM` diventa `) in interpreter_system(castle.game.examples)`.
2. `test_the_prompt_shows_how_to_talk_to_a_character` diventa:

```python
def test_the_prompt_shows_how_to_talk_to_a_character(castle):
    for system in (interpreter_system(), interpreter_system(castle.game.examples)):
        assert "- parla: " in system
        assert "- chiedi: " in system
        # Last, after the grapple: anywhere before it, "getta il rampino nel pozzo" went to the door.
        assert system.endswith('{"verbo": "chiedi", "bersaglio": "cuoca", "con": "nessuno"}')
```

3. Nuovi test, in fondo:

```python
# --- The examples of each world -------------------------------------------------------------------

ROCCA_PROMPT = Path(__file__).parent / "prompt_rocca.txt"
TRUNK = 'Oggetti: baule\nUscite: nessuna\nFrase: apri il baule\n{"verbo": "apri", "bersaglio": "baule", "con": "nessuno"}'


def test_the_castle_prompt_is_the_one_checked_on_the_real_model(castle):
    # Any change to the prompt has to pass the whole tests/test_ollama.py first; then update the file.
    assert interpreter_system(castle.game.examples) == ROCCA_PROMPT.read_text(encoding="utf-8")


def test_the_examples_of_a_world_come_after_the_generic_ones_and_before_the_dialogue():
    system = interpreter_system(TRUNK)

    generic = system.index("Frase: buongiorno, che ore sono?")
    own = system.index("Frase: apri il baule")
    dialogue = system.index("Oggetti: mestolo")
    assert generic < own < dialogue


def test_a_world_without_examples_gets_the_generic_ones_and_the_dialogue():
    system = interpreter_system()

    assert "rampino" not in system
    assert '{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}\nOggetti: mestolo\n' in system


def test_the_system_prompt_carries_the_examples_it_is_given(in_reach):
    fake = FakeLLMClient(json_replies=[{"verbo": "altro"}])

    interpret(fake, "apri il baule", in_reach, examples=TRUNK)

    assert fake.calls[0][0] == interpreter_system(TRUNK)
```

In `tests/test_game.py`, import `from app.llm.prompts import interpreter_system`, e in fondo:

```python
def test_the_llm_gets_the_examples_of_the_world(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}])

    Game(Engine(castle), llm).turn("che bella giornata")

    assert llm.calls[0][0] == interpreter_system(castle.game.examples)
    assert "usa il rampino per recuperare la chiave dal pozzo" in llm.calls[0][0]
```

- [ ] **Step 3: Verificare che falliscano**

Run: `.venv\Scripts\python -m pytest tests/test_interpreter.py tests/test_game.py -q`
Atteso: errore di import (`cannot import name 'interpreter_system'`).

- [ ] **Step 4: Il prompt in tre parti**

In `app/llm/prompts.py` la costante `INTERPRETER_SYSTEM` (righe 10-60) si divide così:
- `_HEAD`: dalla riga 10 alla riga 46 compresa, cioè fino a `{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}` (la risposta a «buongiorno, che ore sono?»), chiusa da `"""`;
- le righe 47-50 (il blocco del rampino, da `Oggetti: pozzo; portone; …` a `{"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}`) si **tolgono** e vanno nello YAML (Step 5);
- `_DIALOGUE`: le righe 51-60 (da `Oggetti: mestolo` alla fine), in una nuova stringa che comincia con `"""\`.

Risultato:

```python
_HEAD = """\
Sei l'interprete di un'avventura testuale. Traduci la frase del giocatore in un'azione.
…(righe 12-45 invariate)…
{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}"""

# Last, after the world's examples: anywhere before the grapple, "getta il rampino nel pozzo" went
# to the door (qwen2.5:3b).
_DIALOGUE = """\
Oggetti: mestolo
Personaggi: cuoca (donna)
Argomenti: cantina (scantinato); cena
Uscite: est
Frase: buongiorno, signora
{"verbo": "parla", "bersaglio": "cuoca", "con": "nessuno"}
Frase: cosa sai dello scantinato?
{"verbo": "chiedi", "bersaglio": "cuoca", "con": "cantina"}
Frase: le chiedo se ha visto il re
{"verbo": "chiedi", "bersaglio": "cuoca", "con": "nessuno"}"""


def interpreter_system(examples: str | None = None) -> str:
    """The fixed part of the prompt: instructions and generic examples, then the world's own examples
    (`game.examples`, in the same format), then the dialogue. It doesn't change from turn to turn,
    so Ollama keeps it in its cache."""
    return "\n".join(part for part in (_HEAD, examples, _DIALOGUE) if part)
```

Nella docstring del modulo aggiungere, dopo la prima frase: «The examples of a world come from its YAML (`game.examples`): the Rocca's is the grapple.»

- [ ] **Step 5: Gli esempi della Rocca nel suo YAML**

In `app/engine/models.py`, `class GameInfo`, dopo `summary`:

```python
    # Examples for the LLM interpreter, in the prompt's format (app/llm/prompts.py): they go between
    # the generic ones and the dialogue.
    examples: Text | None = None
```

In `data/worlds/rocca/gioco.yaml`, dopo `summary:`:

```yaml
  # Esempi per l'interprete, nel formato del prompt (app/llm/prompts.py): vanno tra quelli
  # generici e il dialogo. Senza, «usa il rampino per recuperare la chiave dal pozzo» finiva sul
  # portone. Ogni modifica va verificata su tutto tests/test_ollama.py.
  examples: |-
    Oggetti: pozzo; portone; corda con gancio (corda, gancio, rampino); chiave di ferro (chiave)
    Uscite: est (Scuderia)
    Frase: usa il rampino per recuperare la chiave dal pozzo
    {"verbo": "usa", "bersaglio": "pozzo", "con": "corda con gancio"}
```

- [ ] **Step 6: Interprete, gioco e test col modello vero li usano**

`app/llm/interpreter.py`: import `from app.llm.prompts import interpreter_system, interpreter_user`; firma

```python
def interpret(
    llm: LLMClient,
    sentence: str,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Characters = (),
    examples: str | None = None,
) -> Action | NotUnderstood:
```

nella docstring: «`examples` are the world's own (`game.examples`), for the system prompt.»; e la chiamata usa `interpreter_system(examples),` al posto di `INTERPRETER_SYSTEM,`.

`app/game.py:104`:

```python
        interpreted = interpret(self.llm, line, near, exits, characters, self.world.game.examples)
```

`tests/test_ollama.py`, in `understood`:

```python
    action = interpret(
        llm, sentence, near(engine, state), engine.known_exits(state), engine.characters_here(state), CASTLE.game.examples
    )
```

- [ ] **Step 7: Verificare**

Run: `.venv\Scripts\python -m pytest -q`
Atteso: tutti verdi, compreso `test_the_castle_prompt_is_the_one_checked_on_the_real_model`. Se quel test fallisce, confrontare con `difflib` il testo generato e il file: lo spazio o l'a capo fuori posto è nello YAML o nel taglio dello Step 4.

- [ ] **Step 8: Documentazione**

`docs/formato-mondo.md`, sezione `game`, nell'esempio dopo `summary:`:

```yaml
  examples: |-             # facoltativo: esempi per l'interprete LLM (vedi sotto)
    Oggetti: …
```

e sotto l'esempio:

```markdown
`examples` sono esempi per l'interprete, scritti come nel prompt (`app/llm/prompts.py`): righe
`Oggetti:`, `Uscite:`, `Frase:` e la risposta JSON. Si mettono solo per una frase che il modello
sbaglia giocando, e ogni modifica va verificata su tutto `tests/test_ollama.py`. Nella Rocca c'è
la frase del rampino.
```

- [ ] **Step 9: Commit**

```powershell
git add tests/prompt_rocca.txt app/llm/prompts.py app/llm/interpreter.py app/game.py app/engine/models.py data/worlds/rocca/gioco.yaml tests/test_interpreter.py tests/test_game.py tests/test_ollama.py docs/formato-mondo.md
git commit -m "Interprete: gli esempi di ogni mondo nel suo YAML, il rampino in quello della Rocca" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Il server con più avventure

**Files:**
- Modify: `app/main.py`, `app/game.py` (`Game.__init__`, `Game._log`)
- Test: `tests/test_web.py`, `tests/test_game.py`

**Interfaces:**
- Consumes: `load_adventures()` (Task 1).
- Produces: `create_app(engines: dict[str, Engine], llm: LLMClient | None) -> FastAPI`; `GET /api/adventures` → `[{id, title, summary}]`; `POST /api/new` `{adventure}` → `{text, state, room, title, notice}`; `POST /api/turn` `{adventure, line, state, pending}` → come oggi; 404 `{"detail": "Avventura sconosciuta."}` per un id che non c'è; `UNKNOWN_ADVENTURE` in `app/main.py`; `Game(…, adventure: str | None = None)`.

- [ ] **Step 1: Test del log con l'avventura (fallisce)**

In `tests/test_game.py`, in fondo:

```python
def test_the_log_names_the_adventure_when_the_game_knows_it(castle, caplog):
    [entry] = logged(caplog, Game(Engine(castle), adventure="rocca"), "nord")

    assert list(entry)[:2] == ["avventura", "stanza"]
    assert entry["avventura"] == "rocca"
```

- [ ] **Step 2: Test del server (falliscono)**

In `tests/test_web.py`:

1. Import: `from app.engine.models import World` e `from app.main import UNKNOWN_ADVENTURE, WORLD_CHANGED, create_app`.
2. Fixture e helper in testa (sostituiscono `client`, `new_game`, `turn`):

```python
@pytest.fixture
def client(castle) -> TestClient:
    return TestClient(create_app({"rocca": Engine(castle)}, llm=None))


@pytest.fixture
def two(castle, world_data) -> TestClient:
    """The castle and the small test world, in this order."""
    engines = {"rocca": Engine(castle), "prova": Engine(World.model_validate(world_data))}
    return TestClient(create_app(engines, llm=None))


def new_game(client: TestClient, adventure: str = "rocca") -> dict:
    response = client.post("/api/new", json={"adventure": adventure})
    assert response.status_code == 200
    return response.json()


def turn(client: TestClient, line: str, state, adventure: str = "rocca", pending=None) -> dict:
    response = client.post("/api/turn", json={"adventure": adventure, "line": line, "state": state, "pending": pending})
    assert response.status_code == 200
    return response.json()
```

3. Nei test esistenti: ogni `create_app(Engine(castle), llm=…)` diventa `create_app({"rocca": Engine(castle)}, llm=…)`; ogni `client.post("/api/new")` diventa `new_game(client)`; ogni `client.post("/api/turn", json={…})` riceve anche `"adventure": "rocca"` nel JSON (sono in `test_the_castle_can_be_finished_through_http`, `test_the_action_asked_about_travels_with_the_state`, `test_a_broken_pending_action_is_ignored`, `test_overlong_lines_are_rejected`).
4. Nuovi test:

```python
# --- Several adventures ------------------------------------------------------------------------------


def test_the_adventures_are_listed_in_the_order_of_the_menu(two):
    assert two.get("/api/adventures").json() == [
        {
            "id": "rocca",
            "title": "La Rocca di Serravento",
            "summary": "Un castello abbandonato, una bufera, un portone che non si riapre.",
        },
        {"id": "prova", "title": "Prova", "summary": "Un mondo di prova."},
    ]


def test_each_adventure_plays_its_own_world(two):
    castle = new_game(two, "rocca")
    test = new_game(two, "prova")

    assert (castle["title"], castle["state"]["current_room"]) == ("La Rocca di Serravento", "cortile")
    assert (test["title"], test["state"]["current_room"]) == ("Prova", "atrio")
    assert turn(two, "tira la leva", test["state"], "prova")["text"] == "Clac! Qualcosa cade ai tuoi piedi."


def test_a_state_goes_with_its_own_adventure(two):
    castle = new_game(two, "rocca")

    reply = turn(two, "guarda", castle["state"], "prova")

    assert reply["restarted"] is True
    assert reply["text"].startswith(f"{WORLD_CHANGED}\n\nInizio.")
    assert reply["state"]["current_room"] == "atrio"


@pytest.mark.parametrize(
    "url, body",
    [("/api/new", {"adventure": "atlantide"}), ("/api/turn", {"adventure": "atlantide", "line": "guarda", "state": None})],
    ids=["new", "turn"],
)
def test_an_unknown_adventure_is_not_found(two, url, body):
    response = two.post(url, json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": UNKNOWN_ADVENTURE}


@pytest.mark.parametrize("url", ["/api/new", "/api/turn"])
def test_the_adventure_is_required(two, url):
    assert two.post(url, json={"line": "guarda", "state": None}).status_code == 422
```

- [ ] **Step 3: Verificare che falliscano**

Run: `.venv\Scripts\python -m pytest tests/test_web.py tests/test_game.py -q`
Atteso: errore di import (`UNKNOWN_ADVENTURE`) e `TypeError` su `adventure=` in `Game`.

- [ ] **Step 4: `Game` conosce la sua avventura**

`app/game.py`, `Game.__init__`: nuovo parametro in fondo `adventure: str | None = None`, con `self.adventure = adventure` e nella docstring «`adventure` is the id of the world, for the log.». In `_log`, dopo la costruzione di `entry`:

```python
        if self.adventure is not None:
            entry = {"avventura": self.adventure, **entry}
```

- [ ] **Step 5: Il server**

`app/main.py`:

1. Docstring: «The server keeps no game: the browser holds the state of each adventure (in localStorage) and sends it with every line, with the id of the adventure; the server checks it against that world, plays the turn with Game and sends the new state back.»
2. Import: `from fastapi import FastAPI, HTTPException`; `from app.engine.loader import load_adventures` (al posto di `WORLDS_DIR, load_world`).
3. Costante: `UNKNOWN_ADVENTURE = "Avventura sconosciuta."`
4. Modelli (aggiunti o cambiati):

```python
class Adventure(BaseModel):
    """An entry of the menu."""

    id: str
    title: str
    summary: str


class NewGameRequest(BaseModel):
    adventure: str


class NewGameReply(BaseModel):
    text: str
    state: GameState
    room: str  # name of the current room, for the status line
    title: str  # of the adventure, for the top of the page
    # Set when the LLM can't be used: only simple commands are understood.
    notice: str | None = None


class TurnRequest(BaseModel):
    adventure: str
    line: str = Field(max_length=MAX_LINE)
    # Checked by the engine, not here: a state that doesn't fit restarts the game instead of an error.
    state: Any = None
    # The action asked about in the last reply ("Vuoi…?"), sent back as it came; a broken one is ignored.
    pending: Any = None
```

5. `create_app`:

```python
def create_app(engines: dict[str, Engine], llm: LLMClient | None) -> FastAPI:
    """`engines`: one per adventure, keyed by its id, in the order of the menu."""
    app = FastAPI(title="I.A.vventura", docs_url=None, redoc_url=None)

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        return FileResponse(PAGE, media_type="text/html")

    @app.get("/api/adventures")
    def adventures() -> list[Adventure]:
        return [
            Adventure(id=adventure_id, title=engine.world.game.title, summary=engine.world.game.summary)
            for adventure_id, engine in engines.items()
        ]

    @app.post("/api/new")
    def new_game(request: NewGameRequest) -> NewGameReply:
        engine = engine_of(request.adventure)
        # Checked at every new game: Ollama may have been started after the server.
        reason = llm.unavailable_reason() if llm is not None else None
        _log.info("--- nuova partita (web): %s ---", request.adventure)
        game = Game(engine, llm, adventure=request.adventure)
        notice = f"{reason} Si gioca con i soli comandi semplici." if reason else None
        return NewGameReply(
            text=game.opening(), state=game.state, room=room_of(game), title=engine.world.game.title, notice=notice
        )

    @app.post("/api/turn")
    def turn(request: TurnRequest) -> TurnReply:
        engine = engine_of(request.adventure)
        try:
            state = engine.restore(request.state)
        except StateError:
            game = Game(engine, llm, adventure=request.adventure)
            text = f"{WORLD_CHANGED}\n\n{game.opening()}"
            return TurnReply(text=text, state=game.state, room=room_of(game), finished=False, restarted=True)
        game = Game(engine, llm, state=state, pending=pending_action(request.pending), adventure=request.adventure)
        text = game.turn(request.line)
        return TurnReply(
            text=text, state=game.state, room=room_of(game), finished=game.finished, pending=game.pending
        )

    def engine_of(adventure: str) -> Engine:
        """The page goes back to the menu on a 404: the adventure was taken out of the index."""
        if adventure not in engines:
            raise HTTPException(status_code=404, detail=UNKNOWN_ADVENTURE)
        return engines[adventure]

    def room_of(game: Game) -> str:
        return game.world.rooms[game.state.current_room].name

    def pending_action(data: Any) -> Action | None:
        try:
            return None if data is None else Action.model_validate(data)
        except ValidationError:
            return None

    return app
```

6. `create_app_from_env`:

```python
    engines = {adventure_id: Engine(world) for adventure_id, world in load_adventures().items()}
    return create_app(engines, make_client(settings))
```

- [ ] **Step 6: Verificare**

Run: `.venv\Scripts\python -m pytest -q`
Atteso: tutti verdi. (`test_the_page_is_served` controlla ancora il vecchio `<title>`: la pagina cambia nel Task 5.)

- [ ] **Step 7: Commit**

```powershell
git add app/main.py app/game.py tests/test_web.py tests/test_game.py
git commit -m "Server: un motore per avventura, l'elenco per il menu e l'id con ogni richiesta" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Il menu nel terminale

**Files:**
- Modify: `app/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_adventures()` (Task 1), `Game(…, adventure=…)` (Task 3), `words_of` da `app/engine/parser.py`.
- Produces: `CHOOSE = "Scegli la tua avventura:"`, `WHICH_ADVENTURE = "Scrivi il numero dell'avventura."`, `menu(worlds: Mapping[str, World]) -> str`, `pick(worlds: Mapping[str, World], line: str) -> str | None`, `choose(worlds, read_line, write) -> str`. La pagina (Task 5) applica la stessa regola di `pick`.

- [ ] **Step 1: Test che falliscono**

In `tests/test_cli.py`: `import pytest`; `from app.cli import WHICH_ADVENTURE, choose, menu, pick, run`. In fondo:

```python
# --- The menu of the adventures ---------------------------------------------------------------------


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
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv\Scripts\python -m pytest tests/test_cli.py -q`
Atteso: errore di import (`cannot import name 'WHICH_ADVENTURE'`).

- [ ] **Step 3: Implementare**

`app/cli.py`:
- docstring: dopo `python -m app.cli` aggiungere «First the menu of the adventures (data/worlds/avventure.yaml), then the game.»
- import: `from collections.abc import Callable, Mapping`; `from app.engine.loader import load_adventures`; `from app.engine.models import World` (e togliere `WORLDS_DIR, load_world`).
- costanti accanto alle altre:

```python
CHOOSE = "Scegli la tua avventura:"
WHICH_ADVENTURE = "Scrivi il numero dell'avventura."
```

- funzioni, prima di `run`:

```python
def menu(worlds: Mapping[str, World]) -> str:
    """The adventures numbered as on the page: the title, and the summary indented below it."""
    entries = [
        f" {number}. {world.game.title}\n    {world.game.summary}" for number, world in enumerate(worlds.values(), start=1)
    ]
    return "\n\n".join([CHOOSE, *entries])


def pick(worlds: Mapping[str, World], line: str) -> str | None:
    """The adventure chosen by its number, or by a word of its title of at least three letters
    ("rocca"); None when the answer fits no adventure, or more than one. The page does the same."""
    words = words_of(line)
    ids = list(worlds)
    if len(words) == 1 and words[0].isdigit():
        number = int(words[0])
        return ids[number - 1] if 1 <= number <= len(ids) else None
    matching = {
        adventure_id
        for adventure_id, world in worlds.items()
        for word in words
        if len(word) >= 3 and word in words_of(world.game.title)
    }
    return matching.pop() if len(matching) == 1 else None


def choose(worlds: Mapping[str, World], read_line: Callable[[], str], write: Callable[[str], None]) -> str:
    """Shows the menu and asks until the answer is an adventure (EOFError if the input runs out)."""
    write(menu(worlds))
    while (adventure_id := pick(worlds, read_line())) is None:
        write(WHICH_ADVENTURE)
    return adventure_id
```

- `main()`, dopo il controllo della disponibilità dell'LLM:

```python
    worlds = load_adventures()
    try:
        adventure_id = choose(worlds, lambda: input("\n> "), print)
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if llm is None:
        _log.info("--- nuova partita (%s), senza LLM ---", adventure_id)
    else:
        _log.info("--- nuova partita (%s): %s su %s ---", adventure_id, settings.model, settings.ollama_url)
    game = Game(Engine(worlds[adventure_id]), llm, adventure=adventure_id)
```

(sostituisce le due righe `_log.info` di prima e `game = Game(Engine(load_world(…)), llm)`; il resto di `main` resta com'è).

- [ ] **Step 4: Verificare**

Run: `.venv\Scripts\python -m pytest -q`
Atteso: tutti verdi.

Prova a mano: `$env:LLM="off"; .venv\Scripts\python -m app.cli`, scrivere `5` (atteso «Scrivi il numero dell'avventura.»), poi `1` (atteso: l'introduzione della Rocca), poi `fine` e `s`.

- [ ] **Step 5: Commit**

```powershell
git add app/cli.py tests/test_cli.py
git commit -m "Terminale: il menu delle avventure prima della partita" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Il menu e i salvataggi nella pagina

**Files:**
- Modify: `static/index.html`
- Test: `tests/test_web.py` (`test_the_page_is_served`), prova a mano nel browser

**Interfaces:**
- Consumes: `GET /api/adventures`, `POST /api/new {adventure}` → `{…, title}`, `POST /api/turn {adventure, …}`, 404 per un'avventura sconosciuta (Task 3); la regola di scelta di `pick` (Task 4).
- Produces: chiavi `localStorage`: `castle-adventure.save.<id>`, `castle-adventure.adventure`; `castle-adventure.color` invariata; `castle-adventure.save` letta una volta e tolta.

- [ ] **Step 1: Test della pagina (fallisce)**

In `tests/test_web.py`, `test_the_page_is_served`:

```python
    assert "<title>I.A.vventura</title>" in response.text
    assert "/api/adventures" in response.text
```
(al posto dell'assert sul vecchio titolo). Run: `.venv\Scripts\python -m pytest tests/test_web.py -q` → FAIL.

- [ ] **Step 2: Titolo, presentazione e menu nel markup**

In `static/index.html`:

1. `<title>I.A.vventura nel Castello</title>` → `<title>I.A.vventura</title>`.
2. L'intestazione:

```html
  <header class="title">
    <h1 id="title">I.A.vventura</h1>
    <p id="title-rule" aria-hidden="true">============</p>
  </header>
```

3. Dentro `<main>`, al posto della `section.intro` di oggi:

```html
    <section class="transcript intro" id="intro" hidden>
      <p>Avventure testuali come quelle degli anni '80, in cui le tue frasi le capisce anche un'intelligenza artificiale. La Rocca di Serravento è liberamente ispirata ad «Avventura nel castello», l'avventura testuale di Enrico Colombini del 1982: il castello, gli enigmi e i testi sono nuovi.</p>
    </section>
    <nav class="transcript menu" id="menu" aria-label="Avventure" hidden>
      <p>Scegli la tua avventura:</p>
      <ol id="adventures"></ol>
      <p class="notice" id="menu-notice" hidden></p>
    </nav>
```

4. Nella riga di stato, prima di `<button type="button" id="new-game">`:

```html
      <button type="button" id="to-menu" hidden>Avventure</button>
```
e `id="new-game"` riceve anche `hidden`.

- [ ] **Step 3: Lo stile del menu**

In fondo allo `<style>`, prima di `@media (max-width: 40rem)`:

```css
  /* The menu: each adventure is one button as wide as the column, its number and title on the first
     line, the summary indented below, as the terminal prints it. */
  .menu ol { list-style: none; margin: 0; padding: 0; }
  .menu li { margin: 0 0 calc(var(--line) * 1em); }
  .menu button { display: block; width: 100%; padding: 0 1ch; text-align: left; }
  .menu .summary, .menu .saved { display: block; padding-left: 4ch; color: var(--dim); }
  .menu button:hover span, .menu button:focus-visible span { color: inherit; }
  .menu[hidden], .intro[hidden], .status button[hidden] { display: none; }
```

- [ ] **Step 4: Lo script**

Sostituire tutto il contenuto di `<script>…</script>` con:

```js
(() => {
  const SAVE_PREFIX = "castle-adventure.save.";   // + the id: one game per adventure
  const OLD_SAVE_KEY = "castle-adventure.save";   // the only game, before there were several adventures
  const LAST_KEY = "castle-adventure.adventure";  // the adventure played last
  const HOME = "I.A.vventura";
  const MAX_LINES = 200;         // what the page keeps of the transcript
  const WAIT_DELAY_MS = 300;     // simple commands answer at once: show the dots only for the LLM

  const $ = (id) => document.getElementById(id);
  const screen = $("screen"), transcript = $("transcript"), waiting = $("waiting");
  const prompt = $("prompt"), input = $("line"), confirmBar = $("confirm");
  const intro = $("intro"), menu = $("menu"), menuNotice = $("menu-notice");

  // The adventures the server offers ({id, title, summary}), in the order of the menu.
  let adventures = [];
  // The adventure being played ({id, title, summary}); null while the menu is on screen.
  let current = null;
  // A request is on its way: the answer will go to the current adventure.
  let busy = false;
  // Everything the page needs to pick a game up again: the engine's state, what is on screen
  // and the action the game is asking about ("Vuoi…?"), which goes back with the next line.
  let save = blank();

  function blank() {
    return { state: null, room: "", finished: false, lines: [], pending: null };
  }

  // localStorage may throw (private browsing, storage disabled or full): the game goes on without it.
  function stored(use) {
    try { return use(); } catch { return null; }
  }

  function load(id) {
    const saved = stored(() => JSON.parse(localStorage.getItem(SAVE_PREFIX + id)));
    return saved && saved.state && Array.isArray(saved.lines) ? saved : null;
  }

  function inProgress(id) {
    const saved = load(id);
    return saved !== null && !saved.finished;
  }

  function store() {
    save.lines = save.lines.slice(-MAX_LINES);
    stored(() => {
      localStorage.setItem(SAVE_PREFIX + current.id, JSON.stringify(save));
      localStorage.setItem(LAST_KEY, current.id);
    });
  }

  // The game saved before there were several adventures was a game in the Rocca.
  function migrate() {
    stored(() => {
      const old = localStorage.getItem(OLD_SAVE_KEY);
      if (old === null) return;
      if (localStorage.getItem(SAVE_PREFIX + "rocca") === null) {
        localStorage.setItem(SAVE_PREFIX + "rocca", old);
        localStorage.setItem(LAST_KEY, "rocca");
      }
      localStorage.removeItem(OLD_SAVE_KEY);
    });
  }

  function setTitle(text) {
    $("title").textContent = text;
    $("title-rule").textContent = "=".repeat(text.length);
    document.title = text;
  }

  function show(kind, text, fresh = true) {
    const p = document.createElement("p");
    p.className = kind + (fresh ? " fresh" : "");
    p.textContent = text;
    transcript.append(p);
  }

  function say(kind, text) {
    if (!text) return;
    save.lines.push({ kind, text });
    show(kind, text);
  }

  function scrollToEnd() {
    screen.scrollTop = screen.scrollHeight;
  }

  function status() {
    $("room").textContent = current ? save.room : "Scegli un'avventura";
    $("moves").textContent = current && save.state ? `Mosse: ${save.state.turns}` : "";
    $("to-menu").hidden = $("new-game").hidden = !current;
  }

  function setBusy(value) {
    busy = value;
    input.disabled = busy || save.finished;
    input.placeholder = save.finished ? "La partita è finita." : "";
  }

  // GET without a body, POST with one; a failed answer throws an error with its HTTP status.
  async function call(url, body) {
    const response = await fetch(url, body === undefined ? undefined : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw Object.assign(new Error(`HTTP ${response.status}`), { status: response.status });
    return response.json();
  }

  async function withWaiting(work) {
    setBusy(true);
    const timer = setTimeout(() => { waiting.hidden = false; scrollToEnd(); }, WAIT_DELAY_MS);
    try {
      return await work();
    } finally {
      clearTimeout(timer);
      waiting.hidden = true;
      setBusy(false);
    }
  }

  // --- The menu ---

  function openMenu(notice = "") {
    current = null;
    save = blank();
    transcript.replaceChildren();
    confirmBar.hidden = true;
    prompt.hidden = false;
    setTitle(HOME);
    $("adventures").replaceChildren(...adventures.map(entry));
    menuNotice.textContent = notice;
    menuNotice.hidden = !notice;
    intro.hidden = menu.hidden = false;
    status();
    setBusy(false);
    screen.scrollTop = 0;
    // A touch on an adventure is the easy way on a phone: the keyboard stays closed.
    menu.querySelector("button")?.focus();
  }

  function entry(adventure, index) {
    const button = document.createElement("button");
    button.type = "button";
    button.append(span("name", `${index + 1}. ${adventure.title}`), span("summary", adventure.summary));
    if (inProgress(adventure.id)) button.append(span("saved", "(partita in corso)"));
    button.addEventListener("click", () => choose(adventure));
    const item = document.createElement("li");
    item.append(button);
    return item;
  }

  function span(kind, text) {
    const element = document.createElement("span");
    element.className = kind;
    element.textContent = text;
    return element;
  }

  // "2", or a word of the title of at least three letters ("draghetto"): the same rule as the
  // terminal (pick in app/cli.py). null when the answer fits no adventure, or more than one.
  function pick(line) {
    const words = wordsOf(line);
    if (words.length === 1 && /^\d+$/.test(words[0])) return adventures[Number(words[0]) - 1] ?? null;
    const matching = adventures.filter((adventure) => {
      const title = wordsOf(adventure.title);
      return words.some((word) => word.length >= 3 && title.includes(word));
    });
    return matching.length === 1 ? matching[0] : null;
  }

  function wordsOf(text) {
    return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().match(/[a-z0-9]+/g) ?? [];
  }

  // A game in progress goes on; a finished one, or none, starts anew.
  function choose(adventure) {
    current = adventure;
    intro.hidden = menu.hidden = true;
    setTitle(adventure.title);
    const saved = load(adventure.id);
    if (saved && !saved.finished) resume(saved);
    else newGame();
  }

  function resume(saved) {
    save = saved;
    transcript.replaceChildren();
    for (const { kind, text } of save.lines) show(kind, text, false);
    store(); // it is now the adventure played last
    status();
    setBusy(false);
    scrollToEnd();
    input.focus();
  }

  // The server doesn't have the adventure any more (taken out of the index): its game can't go on.
  function lost() {
    stored(() => localStorage.removeItem(SAVE_PREFIX + current.id));
    adventures = adventures.filter((adventure) => adventure.id !== current.id);
    openMenu("[Questa avventura non c'è più: scegline un'altra.]");
  }

  // --- The game ---

  async function newGame() {
    transcript.replaceChildren();
    save = blank();
    status();
    try {
      const reply = await withWaiting(() => call("/api/new", { adventure: current.id }));
      setTitle(reply.title);
      save.state = reply.state;
      save.room = reply.room;
      if (reply.notice) say("notice", `[${reply.notice}]`);
      say("story", reply.text);
      store();
    } catch (error) {
      if (error.status === 404) return lost();
      say("notice", "[Il server non risponde. Ricarica la pagina tra poco.]");
    }
    status();
    screen.scrollTop = 0; // a new game opens on the intro
    input.focus();
  }

  async function play(line) {
    if (current === null) {
      const adventure = pick(line);
      if (adventure) return choose(adventure);
      menuNotice.textContent = "Scrivi il numero dell'avventura.";
      menuNotice.hidden = false;
      return;
    }
    say("typed", line);
    scrollToEnd();
    let reply = null;
    try {
      reply = await withWaiting(() => call("/api/turn", {
        adventure: current.id, line, state: save.state, pending: save.pending ?? null,
      }));
      if (reply.restarted) {
        transcript.replaceChildren();
        save.lines = [];
      }
      save.state = reply.state;
      save.room = reply.room;
      save.finished = reply.finished;
      save.pending = reply.pending ?? null;
      say("story", reply.text);
      if (reply.finished) say("notice", "[Fine. Per giocare ancora scegli «Nuova partita» o «Avventure».]");
      store();
      setBusy(false);
    } catch (error) {
      if (error.status === 404) return lost();
      say("notice", "[Il server non risponde: il comando non è stato eseguito. Riprova.]");
      input.value = line;
    }
    status();
    if (reply?.restarted) screen.scrollTop = 0;
    else scrollToEnd();
    input.focus();
  }

  prompt.addEventListener("submit", (event) => {
    event.preventDefault();
    const line = input.value.trim();
    if (!line || input.disabled) return;
    input.value = "";
    play(line);
  });

  // "Nuova partita" asks first, in the page, in place of the prompt.
  function askRestart(asking) {
    confirmBar.hidden = !asking;
    prompt.hidden = asking;
    scrollToEnd();
    (asking ? $("keep") : input).focus();
  }
  $("new-game").addEventListener("click", () => askRestart(true));
  $("keep").addEventListener("click", () => askRestart(false));
  $("restart").addEventListener("click", () => { askRestart(false); newGame(); });
  confirmBar.addEventListener("keydown", (event) => { if (event.key === "Escape") askRestart(false); });
  // Back to the menu at once: nothing is lost, the game stays saved. Not while an answer is coming.
  $("to-menu").addEventListener("click", () => { if (!busy) openMenu(); });

  // Green or amber: kept apart from the games, so a new game doesn't change it.
  const COLOR_KEY = "castle-adventure.color";
  const colorButtons = document.querySelectorAll("[data-color-choice]");
  function showColor(color) {
    for (const button of colorButtons) button.setAttribute("aria-pressed", String(button.dataset.colorChoice === color));
  }
  function setColor(color) {
    if (color === "amber") document.documentElement.dataset.color = "amber";
    else delete document.documentElement.dataset.color;
    showColor(color);
    try { localStorage.setItem(COLOR_KEY, color); } catch { /* not remembered, still applied */ }
  }
  for (const button of colorButtons) button.addEventListener("click", () => setColor(button.dataset.colorChoice));
  showColor(document.documentElement.dataset.color === "amber" ? "amber" : "green");

  // The adventure played last goes on if its game is in progress; otherwise the menu.
  async function start() {
    migrate();
    try {
      adventures = await call("/api/adventures");
    } catch {
      openMenu("[Il server non risponde. Ricarica la pagina tra poco.]");
      return;
    }
    const lastId = stored(() => localStorage.getItem(LAST_KEY));
    const last = adventures.find((adventure) => adventure.id === lastId);
    if (last && inProgress(last.id)) choose(last);
    else openMenu();
  }
  start();
})();
```

- [ ] **Step 5: Test automatici**

Run: `.venv\Scripts\python -m pytest -q`
Atteso: tutti verdi.

- [ ] **Step 6: Prova a mano nel browser**

Avviare il server in background: `$env:LLM="off"; .venv\Scripts\python -m app.main`, poi aprire `http://127.0.0.1:8000` (con Claude in Chrome o a mano). Controllare, nell'ordine:

1. **Migrazione**: dalla console del browser, con `localStorage` vuoto per il sito:
   ```js
   const r = await (await fetch("/api/new", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({adventure: "rocca"})})).json();
   localStorage.clear();
   localStorage.setItem("castle-adventure.save", JSON.stringify({state: r.state, room: r.room, finished: false, lines: [{kind: "story", text: "VECCHIO SALVATAGGIO"}], pending: null}));
   location.reload();
   ```
   Atteso: si riprende nella Rocca con la riga «VECCHIO SALVATAGGIO», titolo «La Rocca di Serravento»; in `localStorage` c'è `castle-adventure.save.rocca`, `castle-adventure.adventure` = `rocca`, e **non** c'è più `castle-adventure.save`.
2. **Menu**: «Avventure» → menu con titolo «I.A.vventura», presentazione, «1. La Rocca di Serravento», riassunto e «(partita in corso)»; riga di stato «Scegli un'avventura», senza «Avventure» e «Nuova partita».
3. **Scelta scritta**: `9` → «Scrivi il numero dell'avventura.»; `rocca` → si riprende la partita salvata.
4. **Nuova partita**: «Nuova partita» → conferma → «Ricomincia» → introduzione della Rocca, «Mosse: 0».
5. **Partita finita**: in console `localStorage.setItem("castle-adventure.save.rocca", JSON.stringify({...JSON.parse(localStorage.getItem("castle-adventure.save.rocca")), finished: true})); location.reload();` → si apre il menu, senza «(partita in corso)»; scegliere la Rocca → partita nuova.
6. **Avventura sparita**: in console `localStorage.setItem("castle-adventure.save.atlantide", localStorage.getItem("castle-adventure.save.rocca")); localStorage.setItem("castle-adventure.adventure", "atlantide"); location.reload();` → si apre il menu (l'avventura non è nell'elenco del server).
7. **Telefono**: finestra larga 375 px: menu leggibile, nessuno scorrimento orizzontale, la riga di stato va su due righe.
8. **Colori**: «Ambra» resta scelto passando da menu a partita e ricaricando.

Fermare il server alla fine.

- [ ] **Step 7: Commit**

```powershell
git add static/index.html tests/test_web.py
git commit -m "Pagina: menu delle avventure, un salvataggio per avventura e quello vecchio alla Rocca" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Verifica col modello vero, CLAUDE.md e PR

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Tutti i test, poi quelli col modello vero**

```powershell
.venv\Scripts\python -m pytest -q
$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s
```
Atteso: tutto verde; `test_ollama.py` 25 su 25 come prima (il prompt della Rocca è identico). Se un caso fallisce, fermarsi e riportarlo: non cambiare il prompt in questo pezzo.

- [ ] **Step 2: CLAUDE.md**

- «Struttura proposta»: `data/world/*.yaml` → `data/worlds/avventure.yaml` (indice del menu) e `data/worlds/<id>/*.yaml` (un'avventura per cartella).
- Righe 100 e 182: `data/world/` → `data/worlds/rocca/`.
- Riga del prompt nei «Risultati dei test»: «Esempio nel prompt: la frase del rampino … Lega il prompt fisso alla Rocca: quando ci sarà un secondo mondo, gli esempi andranno nel suo YAML.» → «… è in `game.examples` della Rocca (`data/worlds/rocca/gioco.yaml`); il prompt è testa fissa + esempi del mondo + dialogo della cuoca, e `tests/prompt_rocca.txt` ne tiene la copia verificata.»
- Nuova voce in «Decisioni prese»:

```markdown
- **Più avventure** (fase 7, pezzo 1, 2026-09-26; spec in
  `docs/superpowers/specs/2026-09-26-piu-avventure-design.md`):
  - Un'avventura per cartella in `data/worlds/`, l'ordine del menu in `avventure.yaml`;
    `game.summary` per il menu, `game.examples` per gli esempi dell'interprete.
  - Server: un `Engine` per avventura, `GET /api/adventures`, l'id dell'avventura in `/api/new` e
    `/api/turn` accanto allo stato (404 se non c'è). Il log dei comandi ha il campo `avventura`.
  - Pagina: menu nella console (tocco, numero o parola del titolo), titolo dell'avventura in alto,
    «Avventure» nella riga di stato; un salvataggio per avventura (`castle-adventure.save.<id>`) e
    si riprende l'ultima in corso. Il vecchio `castle-adventure.save` è diventato quello della Rocca.
  - Terminale: lo stesso menu prima della partita.
```

- «Comandi utili»: dopo `python -m app.cli` il commento diventa `# giocare nel terminale: prima il menu delle avventure`.

- [ ] **Step 3: Commit**

```powershell
git add CLAUDE.md
git commit -m "CLAUDE.md: più avventure, il menu e gli esempi dell'interprete nel mondo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Chiedere all'utente prima di push e PR**

Mostrare `git log --oneline main..HEAD` e `git status --short` (atteso: solo ` M data/worlds/rocca/stanze.yaml`, `run.bat`, `test_llm.txt`), e chiedere se fare push del branch `fase-7-avventure` e aprire la PR, e cosa fare della modifica a `stanze.yaml`. La PR si apre solo dopo il sì, con il corpo che finisce con:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
