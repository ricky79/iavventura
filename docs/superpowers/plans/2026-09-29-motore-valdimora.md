# Il motore per Valdimora — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** il motore sa spostare i personaggi con le condizioni, riconosce le morti, tiene da parte lo stato all'inizio di ogni atto e, dopo una morte, fa riprendere la partita da lì (nel web con «riprendi», nel terminale con una domanda); le regole hanno varianti anche per `otherwise`.

**Architecture:** tutto passa dal modello del mondo (`Move`, `Act`, `Ending.death`, `Rule.otherwise_variants`) e da `GameState` (`lost`, `act`, `checkpoint`), e il motore è l'unico a scriverli: `execute` comincia gli atti e segna le morti, `resumable`/`resume` riprendono. `Game`, il server e il terminale si limitano a chiedere al motore se e da dove si può riprendere. Niente verbi nuovi: il parser e il prompt dell'LLM non cambiano.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest; JS senza framework in `static/index.html`.

**Spec:** `docs/superpowers/specs/2026-09-29-valdimora-design.md` — sezione 5 (il motore). Il resto della spec (la storia, gli atti, i dati) è per i piani successivi, uno per atto.

## Global Constraints

- Branch: `feature/inizia_l_Avventura` (già creato da `main`, contiene la spec). Il piano si committa nel primo commit del Task 1.
- Nessuna dipendenza nuova. Comandi con `.venv\Scripts\python` (PowerShell) o `.venv/Scripts/python` (Git Bash).
- Codice e identificatori in inglese; testi per il giocatore, commit e documentazione in italiano.
- Il motore (`app/engine/`) non importa nulla da `app/llm/`.
- **Il prompt dell'LLM non cambia** (nessun verbo nuovo, `app/llm/prompts.py` intatto): non serve il giro di `tests/test_ollama.py`. Se per qualche motivo il prompt cambiasse, quel giro diventa obbligatorio (vedi CLAUDE.md).
- La Rocca e il draghetto si giocano come prima: i test esistenti restano verdi, tranne quelli che questo piano aggiorna dichiarandolo.
- I salvataggi già nel browser devono restare validi: ogni campo nuovo di `GameState` ha un valore predefinito.
- Mai nei commit: `run.bat`, `run_log.bat`, `test_llm.txt`. Aggiungere i file uno per uno, mai `git add -A` o `git add .`.
- Ogni commit finisce con la riga `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Heredoc e backslash: per testi con `\n` o `\u` usare Edit (mai heredoc né `sed`), e controllare con grep dopo Write.
- Prove nel browser su una porta diversa da 8000 (per esempio 8765): nel Chrome dell'utente l'origine `127.0.0.1:8000` ha la sua partita salvata.

## Una precisazione rispetto alla spec

La spec (5.2) dice che il testo della morte si chiude con «Scrivi «riprendi»…». Nel piano l'invito lo compongono **i front end**, come già fa la pagina con «[Fine. Per giocare ancora…]»: il server manda `resumable` (il nome dell'atto) e la pagina scrive «[Scrivi «riprendi» per ricominciare dall'inizio del secondo atto, oppure scegli «Nuova partita».]»; il terminale invece fa la sua domanda (s/n). Così il terminale non mostra un invito che lì non vale. Il Task 7 aggiorna la spec.

## Review Focus

1. **Salvataggi di prima nel browser** (senza `lost`, `act`, `checkpoint`, e senza `resumable` nella pagina): devono riprendere come partite normali, senza «Il mondo è cambiato» — test nel Task 3 (`test_a_state_saved_before_acts_existed_is_restored`); nella pagina `resumable` mancante vale come falso (Task 5).
2. **Un mondo modificato dopo il salvataggio** in modo che il checkpoint non gli vada più bene (stanza sparita, atti tolti): il server non deve andare in errore, ma ricominciare con «Il mondo è cambiato» — test nel Task 3 (`test_a_checkpoint_that_does_not_fit_the_world_is_refused`, `test_a_state_past_the_acts_of_the_world_is_refused`).
3. **«riprendi» scritto durante la partita**, o dopo una vittoria: non deve riprendere niente né rompere niente — test nel Task 4 (`test_riprendi_means_nothing_while_playing_or_after_winning`).
4. **Morire due volte nello stesso atto**: la seconda ripresa deve funzionare come la prima — test nel Task 4 (`test_one_can_die_and_go_on_again`).
5. **Un personaggio che si è spostato** mentre il giocatore è nella sua vecchia stanza: parlargli o dargli qualcosa lì risponde «Non vedi nessuno del genere qui.» — test nel Task 1 (`test_a_character_that_moved_away_is_not_here`).

---

### Task 1: Personaggi che si spostano

**Files:**
- Modify: `app/engine/models.py` (nuova classe `Move`, campo `Character.moves`), `app/engine/engine.py` (`character_room`, `characters_here`), `app/engine/validation.py` (stanze e condizioni dei `moves`)
- Test: `tests/test_engine.py`, `tests/test_validation.py`

**Interfaces:**
- Produces: `Move(when: Condition, room: Id)`; `Character.moves: tuple[Move, ...] = ()`; `Engine.character_room(character: Character, state: GameState) -> str`. `Engine.characters_here` usa `character_room`, quindi tutto ciò che passa da lì (descrizione della stanza, parser, dialoghi, `dai`, prompt dell'interprete) segue gli spostamenti senza altre modifiche.

- [ ] **Step 1: Committare il piano**

```bash
git status --short   # atteso: solo run.bat, run_log.bat, test_llm.txt e questo piano non tracciati
git add docs/superpowers/plans/2026-09-29-motore-valdimora.md
```
(il commit arriva allo Step 7, insieme al codice del task).

- [ ] **Step 2: Test che falliscono (motore)**

In `tests/test_engine.py`, nella sezione `# --- Characters ---`, subito dopo `test_the_room_shows_the_characters_in_it`:

```python
def test_a_character_moves_while_a_condition_holds(keeper_world):
    # Agnese follows the player from floor to floor: `moves`, the first that holds wins.
    keeper_world["characters"]["custode"]["moves"] = [
        {"when": {"has": "chiave"}, "room": "atrio"},
        {"when": {"flag": "porta_aperta"}, "room": "cella"},
    ]
    engine, state = start(keeper_world)
    custode = engine.world.characters["custode"]

    at_first = engine.character_room(custode, state)
    state.flags.add("porta_aperta")
    with_the_flag = engine.character_room(custode, state)
    state.item_locations["chiave"] = "inventory"
    with_the_key_too = engine.character_room(custode, state)

    assert (at_first, with_the_flag, with_the_key_too) == ("atrio", "cella", "atrio")


def test_a_character_that_moved_away_is_not_here(keeper_world):
    keeper_world["characters"]["custode"]["moves"] = [{"when": {"flag": "porta_aperta"}, "room": "cella"}]
    engine, state = start(keeper_world)
    engine.execute(state, Action(verb="tira", target="leva"))

    talk = engine.execute(state, Action(verb="parla", target="custode"))
    give = engine.execute(state, Action(verb="dai", target="moneta", with_="custode"))
    state.current_room = "cella"
    look = engine.execute(state, Action(verb="guarda"))

    assert (talk.text, give.text) == (messages.NOBODY_HERE, messages.NOBODY_HERE)
    assert look.room.characters == ("custode",)
    assert [character.id for character, _ in engine.characters_here(state)] == ["custode"]
```

Nota: `tira leva` apre la porta (flag `porta_aperta`) e dà la chiave. Nel mondo di prova entrare nella cella fa finire la partita («Fine.»), ma l'esito di `guarda` ha comunque la stanza, perché il finale si aggiunge all'esito dell'azione: per questo il test mette il giocatore nella cella direttamente e poi guarda.

- [ ] **Step 3: Test che falliscono (validazione)**

In `tests/test_validation.py`, dentro `BROKEN_KEEPERS`, in fondo (prima della `}` di chiusura):

```python
    "move to an unknown room": (
        lambda d: keeper(d).update(moves=[{"when": {"flag": "porta_aperta"}, "room": "cantina"}]),
        ["characters.custode.moves.0.room", "cantina"],
    ),
    "move on a flag never set": (
        lambda d: keeper(d).update(moves=[{"when": {"flag": "allarme"}, "room": "cella"}]),
        ["characters.custode.moves.0.when", "allarme"],
    ),
```

- [ ] **Step 4: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py tests/test_validation.py -q`
Expected: FAIL — `moves` è un campo sconosciuto (`extra_forbidden`) e `character_room` non esiste.

- [ ] **Step 5: Implementazione**

In `app/engine/models.py`, prima di `class Character`:

```python
class Move(_Frozen):
    """Where a character is while a condition holds: Agnese on the floor the player has just opened."""

    when: Condition
    room: Id
```

In `class Character`, sostituire la riga di `location`:

```python
    location: Id  # a room: characters don't move
```
con:
```python
    location: Id  # a room: where the character is while none of its moves holds
    moves: tuple[Move, ...] = ()  # the first whose condition holds says where the character is now
```

In `app/engine/engine.py`, in `class Engine`, subito prima di `def characters_here`:

```python
    def character_room(self, character: Character, state: GameState) -> str:
        """Where the character is now: the room of its first move whose condition holds, else its location."""
        return next((move.room for move in character.moves if holds(move.when, state)), character.location)
```
e in `characters_here` sostituire `if character.location == state.current_room` con
`if self.character_room(character, state) == state.current_room`.

In `app/engine/validation.py`:
- nel ciclo `for character in world.characters.values():` che controlla `location`, dopo `check_room(f"characters.{character.id}.location", character.location)`:
```python
        for index, move in enumerate(character.moves):
            check_room(f"characters.{character.id}.moves.{index}.room", move.room)
```
- in `_conditions`, nel ciclo dei personaggi, dopo quello dei `greeting_variants`:
```python
        for index, move in enumerate(character.moves):
            yield f"{path}.moves.{index}.when", move.when
```

- [ ] **Step 6: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde.

- [ ] **Step 7: Commit**

```bash
git add app/engine/models.py app/engine/engine.py app/engine/validation.py tests/test_engine.py tests/test_validation.py
git commit -m "Motore: personaggi che si spostano con le condizioni (moves)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Varianti di `otherwise` nelle regole

**Files:**
- Modify: `app/engine/models.py` (`Rule.otherwise_variants`), `app/engine/engine.py` (`_apply_rule`), `app/engine/validation.py` (`_conditions`)
- Test: `tests/test_engine.py`, `tests/test_validation.py`

**Interfaces:**
- Produces: `Rule.otherwise_variants: tuple[TextVariant, ...] = ()`: quando `when` è falso, la prima variante valida sostituisce `otherwise` (come `Exit.otherwise_variants`).

- [ ] **Step 1: Test che falliscono**

In `tests/test_engine.py`, dopo `test_rule_whose_condition_fails_without_otherwise_gives_the_generic_answer`:

```python
def test_the_text_of_a_rule_whose_condition_fails_follows_the_game(data):
    # The medallion in the sundial: "it doesn't turn, it's rusty" / "the compartment is empty".
    data["rules"]["tira_leva"]["otherwise_variants"] = [
        {"when": {"has": "chiave"}, "text": "La leva non si muove più, e la chiave l'hai già presa."}
    ]
    engine, state = start(data)
    engine.execute(state, Action(verb="tira", target="leva"))

    with_the_key = engine.execute(state, Action(verb="tira", target="leva"))
    engine.execute(state, Action(verb="lascia", target="chiave"))
    without = engine.execute(state, Action(verb="tira", target="leva"))

    assert with_the_key.text == "La leva non si muove più, e la chiave l'hai già presa."
    assert without.text == "La leva non si muove più."
```

In `tests/test_validation.py`, in `BROKEN_WORLDS` (dizionario del mondo senza personaggi), in fondo:

```python
    "rule otherwise variant is checked": (
        lambda d: d["rules"]["tira_leva"].update(
            otherwise_variants=[{"when": {"flag": "allarme"}, "text": "Suona un allarme."}]
        ),
        ["rules.tira_leva.otherwise_variants.0.when", "allarme"],
    ),
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py tests/test_validation.py -q`
Expected: FAIL — `otherwise_variants` è un campo sconosciuto nelle regole.

- [ ] **Step 3: Implementazione**

In `app/engine/models.py`, in `class Rule`, dopo `otherwise: Text | None = None`:

```python
    otherwise_variants: tuple[TextVariant, ...] = ()  # the first that holds replaces otherwise
```

In `app/engine/engine.py`, in `_apply_rule`, sostituire
`return Outcome(ok=False, text=rule.otherwise or NOTHING_HAPPENS)` con:

```python
            return Outcome(
                ok=False, text=_first_variant(rule.otherwise_variants, rule.otherwise or NOTHING_HAPPENS, state)
            )
```

In `app/engine/validation.py`, in `_conditions`, nel ciclo delle regole, dopo `yield f"rules.{rule.id}.when", rule.when`
(allo stesso livello dell'`if`, non dentro):

```python
        for index, variant in enumerate(rule.otherwise_variants):
            yield f"rules.{rule.id}.otherwise_variants.{index}.when", variant.when
```

- [ ] **Step 4: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde.

- [ ] **Step 5: Commit**

```bash
git add app/engine/models.py app/engine/engine.py app/engine/validation.py tests/test_engine.py tests/test_validation.py
git commit -m "Motore: varianti di otherwise anche nelle regole" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Morti, atti e ripresa nel motore

**Files:**
- Modify: `app/engine/models.py` (`Ending.death`, nuova classe `Act`, `GameInfo.acts`, `GameState.lost/act/checkpoint`), `app/engine/engine.py` (`new_game`, `execute`, `_begin_acts`, `resumable`, `resume`, `restore`), `app/engine/validation.py` (condizioni degli atti)
- Modify: `tests/conftest.py` (fixture `acts_world`)
- Test: `tests/test_engine.py`, `tests/test_state.py`, `tests/test_validation.py`

**Interfaces:**
- Consumes: niente dai task precedenti.
- Produces:
  - `Ending.death: bool = False`; `Act(name: Text, when: Condition)`; `GameInfo.acts: tuple[Act, ...] = ()`.
  - `GameState.lost: bool = False`, `GameState.act: int = 0`, `GameState.checkpoint: GameState | None = None`.
  - `Engine.resumable(state: GameState) -> str | None` — il nome dell'atto da cui riprendere («secondo atto»), o `None`.
  - `Engine.resume(state: GameState) -> tuple[GameState, Outcome]` — solleva `ValueError` se `resumable` è `None`; l'esito ha `text == "Riprendi dall'inizio del secondo atto."` e la stanza.
  - Costante `RESUMED = "Riprendi dall'inizio del {act}."` in `app/engine/engine.py`.
  - Fixture `acts_world` in `tests/conftest.py`, usata anche dai Task 4, 5 e 6.

- [ ] **Step 1: La fixture del mondo in due atti**

In `tests/conftest.py`, in fondo:

```python
@pytest.fixture
def acts_world(world_data) -> dict:
    """The test world in two acts: pulling the lever begins the second; jumping on the lever kills."""
    world_data["game"]["acts"] = [{"name": "secondo atto", "when": {"flag": "porta_aperta"}}]
    world_data["game"]["endings"].insert(0, {"when": {"flag": "caduta"}, "death": True, "text": "Sei morta."})
    world_data["rules"]["salta_leva"] = {
        "trigger": {"verb": "salta", "target": "leva"},
        "effects": [{"set_flag": "caduta"}],
        "text": "Salti sulla leva e scivoli.",
    }
    return world_data
```

- [ ] **Step 2: Test che falliscono (motore)**

In `tests/test_engine.py`, dopo `test_nothing_can_be_done_once_the_game_is_over`, una sezione nuova:

```python
# --- Acts, deaths and going on from the last act ------------------------------------------------


def test_an_ending_may_be_a_death(acts_world):
    engine, state = start(acts_world)

    outcome = engine.execute(state, Action(verb="salta", target="leva"))

    assert outcome.ending == "Sei morta."
    assert state.finished and state.lost


def test_winning_is_no_death(acts_world):
    engine, state = start(acts_world)
    engine.execute(state, Action(verb="tira", target="leva"))

    engine.execute(state, Action(verb="vai", direction="nord"))

    assert state.finished and not state.lost


def test_an_act_begins_when_its_condition_first_holds_and_keeps_the_state(acts_world):
    engine, state = start(acts_world)

    engine.execute(state, Action(verb="guarda"))
    before = (state.act, state.checkpoint)
    engine.execute(state, Action(verb="tira", target="leva"))

    assert before == (0, None)
    assert state.act == 1
    assert state.checkpoint.flags == {"porta_aperta"}
    assert state.checkpoint.item_locations["chiave"] == "inventory"
    assert state.checkpoint.turns == 2
    assert state.checkpoint.checkpoint is None


def test_an_act_begins_only_once(acts_world):
    engine, state = start(acts_world)
    engine.execute(state, Action(verb="tira", target="leva"))
    kept = state.checkpoint.model_copy(deep=True)

    engine.execute(state, Action(verb="lascia", target="moneta"))

    assert state.checkpoint == kept
    assert state.checkpoint.item_locations["moneta"] == "inventory"


def test_an_act_that_holds_from_the_start_begins_with_the_game(acts_world):
    acts_world["game"]["acts"].insert(0, {"name": "primo atto", "when": {"player_in": "atrio"}})
    engine, state = start(acts_world)

    assert state.act == 1
    assert state.checkpoint.turns == 0


def test_after_a_death_the_game_goes_on_from_the_beginning_of_the_last_act(acts_world):
    engine, state = start(acts_world)
    engine.execute(state, Action(verb="tira", target="leva"))
    engine.execute(state, Action(verb="lascia", target="moneta"))
    engine.execute(state, Action(verb="salta", target="leva"))

    act = engine.resumable(state)
    resumed, outcome = engine.resume(state)

    assert act == "secondo atto"
    assert outcome.text == "Riprendi dall'inizio del secondo atto."
    assert outcome.room.id == "atrio"
    assert not resumed.finished and not resumed.lost
    assert resumed.item_locations["moneta"] == "inventory"  # as it was when the act began
    assert resumed.checkpoint == state.checkpoint  # so it can go on from there again


def test_a_death_before_any_act_cannot_go_on(acts_world):
    engine, state = start(acts_world)
    engine.execute(state, Action(verb="salta", target="leva"))

    assert engine.resumable(state) is None
    with pytest.raises(ValueError):
        engine.resume(state)


def test_a_game_won_does_not_go_on(acts_world):
    engine, state = start(acts_world)
    engine.execute(state, Action(verb="tira", target="leva"))
    engine.execute(state, Action(verb="vai", direction="nord"))

    assert engine.resumable(state) is None
```

- [ ] **Step 3: Test che falliscono (stato salvato)**

In `tests/test_state.py`, in fondo:

```python
# --- Acts: the state kept when an act began travels with the saved state -------------------------


def acts_saved(acts_world) -> dict:
    """A saved state after the second act began: it carries its checkpoint."""
    engine = Engine(World.model_validate(acts_world))
    state, _ = engine.new_game()
    engine.execute(state, Action(verb="tira", target="leva"))
    return json.loads(state.model_dump_json())


def test_a_state_with_a_checkpoint_is_restored(acts_world):
    data = acts_saved(acts_world)

    state = Engine(World.model_validate(acts_world)).restore(data)

    assert state.act == 1
    assert state.checkpoint.flags == {"porta_aperta"}


def test_a_checkpoint_that_does_not_fit_the_world_is_refused(acts_world):
    data = acts_saved(acts_world)
    data["checkpoint"]["current_room"] = "cantina"

    with pytest.raises(StateError, match="checkpoint.*cantina"):
        Engine(World.model_validate(acts_world)).restore(data)


def test_a_checkpoint_inside_a_checkpoint_is_refused(acts_world):
    data = acts_saved(acts_world)
    data["checkpoint"]["checkpoint"] = dict(data["checkpoint"])

    with pytest.raises(StateError, match="checkpoint"):
        Engine(World.model_validate(acts_world)).restore(data)


def test_a_state_past_the_acts_of_the_world_is_refused(acts_world, world_data):
    data = acts_saved(acts_world)
    del world_data["game"]["acts"]  # the world lost its acts after the game was saved

    with pytest.raises(StateError, match="act"):
        Engine(World.model_validate(world_data)).restore(data)


def test_a_state_saved_before_acts_existed_is_restored(world_data):
    data = saved(world_data)
    for field in ("lost", "act", "checkpoint"):
        data.pop(field, None)

    state = Engine(World.model_validate(world_data)).restore(data)

    assert (state.lost, state.act, state.checkpoint) == (False, 0, None)
```

e in cima al file aggiungere `Action` all'import dei modelli:
`from app.engine.models import Action, GameState, World`.

Nota su `test_a_state_past_the_acts_of_the_world_is_refused`: `acts_world` e `world_data` sono lo stesso dizionario (la fixture `acts_world` modifica `world_data`); per questo `acts_saved` va chiamata **prima** di togliere gli atti, come scritto.

- [ ] **Step 4: Test che falliscono (validazione)**

In `tests/test_validation.py`, in `BROKEN_WORLDS`, in fondo:

```python
    "act on a flag never set": (
        lambda d: d["game"].update(acts=[{"name": "secondo atto", "when": {"flag": "allarme"}}]),
        ["game.acts.0.when", "allarme"],
    ),
```

e dopo `test_minimal_world_has_no_problems`:

```python
def test_a_world_in_acts_with_a_death_has_no_problems(acts_world):
    assert problems_for(acts_world) == []
```

- [ ] **Step 5: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py tests/test_state.py tests/test_validation.py -q`
Expected: FAIL — `acts` e `death` sono campi sconosciuti, `resumable`/`resume` non esistono.

- [ ] **Step 6: Implementazione (modelli)**

In `app/engine/models.py`:

`class Ending` diventa:
```python
class Ending(_Frozen):
    when: Condition
    text: Text
    death: bool = False  # the player dies: the game can go on from the beginning of the last act
```

subito dopo `class Ending`:
```python
class Act(_Frozen):
    """A part of the game (a floor of Valdimora). When its condition first holds the state is kept:
    after a death the game goes on from there."""

    name: Text  # read after "dall'inizio del": "secondo atto"
    when: Condition
```

in `class GameInfo`, dopo `start_room: Id`:
```python
    acts: tuple[Act, ...] = ()  # in order: each begins after the one before
```

in `class GameState`, sostituire `finished: bool = False` con:
```python
    finished: bool = False
    # The game ended with a death (Ending.death): it can go on from the last act begun, if any.
    lost: bool = False
    # How many acts of the world have begun (GameInfo.acts), and the state when the last one began,
    # without its own checkpoint: after a death the game goes on from there.
    act: int = 0
    checkpoint: "GameState | None" = None
```

Pydantic v2 risolve da solo il riferimento di `GameState` a se stesso. Se all'import segnala un tipo non definito (`PydanticUndefinedAnnotation`, oppure «`GameState` is not fully defined»), aggiungere subito dopo la classe la riga `GameState.model_rebuild()`.

- [ ] **Step 7: Implementazione (motore)**

In `app/engine/engine.py`:

tra i messaggi, dopo `GAME_OVER = "La partita è finita."`:
```python
RESUMED = "Riprendi dall'inizio del {act}."
```

`new_game` diventa:
```python
    def new_game(self) -> tuple[GameState, Outcome]:
        state = GameState.new(self.world)
        self._begin_acts(state)
        return state, Outcome(ok=True, text=self.world.game.intro, room=self._room_view(state, first_visit=True))
```

`restore` diventa (i controlli di oggi passano in `_state_problems`, applicati anche al checkpoint):
```python
    def restore(self, data: Any) -> GameState:
        """A state saved elsewhere (the browser keeps it), checked against this world, together with
        the state kept at the beginning of the last act.

        Texts may have changed since it was saved; rooms, items and acts must still be the same.
        """
        try:
            state = GameState.model_validate(data)
        except ValidationError as exc:
            raise StateError(f"not a game state: {exc}") from None
        problems = self._state_problems(state)
        if state.checkpoint is not None:
            problems += [f"checkpoint: {problem}" for problem in self._state_problems(state.checkpoint)]
            if state.checkpoint.checkpoint is not None:
                problems.append("checkpoint: it has a checkpoint of its own")
        if problems:
            raise StateError("; ".join(problems))
        return state

    def _state_problems(self, state: GameState) -> list[str]:
        rooms, items = self.world.rooms, self.world.items
        problems = []
        if state.current_room not in rooms:
            problems.append(f"unknown room '{state.current_room}'")
        problems += [f"item '{item_id}' is missing" for item_id in items if item_id not in state.item_locations]
        for item_id, location in state.item_locations.items():
            if item_id not in items:
                problems.append(f"unknown item '{item_id}'")
            elif location not in (None, INVENTORY) and location not in rooms:
                problems.append(f"item '{item_id}' in unknown room '{location}'")
        problems += [f"unknown visited room '{room_id}'" for room_id in sorted(state.visited) if room_id not in rooms]
        problems += [f"unknown seen item '{item_id}'" for item_id in sorted(state.seen) if item_id not in items]
        if state.act > len(self.world.game.acts):
            problems.append(f"act {state.act}, but the world has {len(self.world.game.acts)} acts")
        return problems
```

`execute` diventa:
```python
    def execute(self, state: GameState, action: Action) -> Outcome:
        """Applies the action to `state` and tells what happened. An act whose condition now holds
        begins (its state is kept), then the first ending that holds closes the game."""
        if state.finished:
            return Outcome(ok=False, text=GAME_OVER)
        outcome = self._perform(state, action)
        state.turns += 1
        self._begin_acts(state)
        ending = next((ending for ending in self.world.game.endings if holds(ending.when, state)), None)
        if ending is not None:
            state.finished = True
            state.lost = ending.death
            outcome = outcome.model_copy(update={"ending": ending.text})
        return outcome
```

subito dopo `execute`:
```python
    def resumable(self, state: GameState) -> str | None:
        """The act a game lost by a death can go on from ("secondo atto"), or None."""
        if not state.lost or state.checkpoint is None:
            return None
        return self.world.game.acts[state.checkpoint.act - 1].name

    def resume(self, state: GameState) -> tuple[GameState, Outcome]:
        """After a death, the game again as it was when the last act began. It keeps that act's
        checkpoint, so it can go on from there again."""
        act = self.resumable(state)
        if act is None:
            raise ValueError("only a game lost after an act began can go on")
        kept = state.checkpoint
        resumed = kept.model_copy(deep=True, update={"checkpoint": kept.model_copy(deep=True)})
        return resumed, Outcome(ok=True, text=RESUMED.format(act=act), room=self._room_view(resumed, first_visit=False))

    def _begin_acts(self, state: GameState) -> None:
        """The acts whose condition now holds begin, in order; the state is kept, to go on from here
        after a death."""
        acts = self.world.game.acts
        while state.act < len(acts) and holds(acts[state.act].when, state):
            state.act += 1
            state.checkpoint = state.model_copy(deep=True, update={"checkpoint": None})
```

- [ ] **Step 8: Implementazione (validazione)**

In `app/engine/validation.py`, in `_conditions`, in fondo (dopo il ciclo dei finali):
```python
    for index, act in enumerate(world.game.acts):
        yield f"game.acts.{index}.when", act.when
```

- [ ] **Step 9: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde. Se `test_state.py::test_new_game_starts_from_the_world` o altri confrontano uno stato intero, i campi nuovi hanno valori predefiniti e non li cambiano.

- [ ] **Step 10: Commit**

```bash
git add app/engine/models.py app/engine/engine.py app/engine/validation.py tests/conftest.py tests/test_engine.py tests/test_state.py tests/test_validation.py
git commit -m "Motore: morti, atti e ripresa dall'inizio dell'ultimo atto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: «riprendi» nel gioco

**Files:**
- Modify: `app/game.py`
- Test: `tests/test_game.py`

**Interfaces:**
- Consumes: `Engine.resumable`, `Engine.resume`, `GAME_OVER` (Task 3); fixture `acts_world`.
- Produces: `Game.resumable -> str | None` (proprietà); `Game.resume() -> str` (il testo reso: «Riprendi dall'inizio del secondo atto.» e la stanza); costante `RESUME_WORD = "riprendi"`. Su una partita finita `Game.turn` non chiama più l'LLM.

- [ ] **Step 1: Test che falliscono**

In `tests/test_game.py`, in fondo:

```python
# --- After a death: «riprendi» -------------------------------------------------------------------


@pytest.fixture
def two_acts(acts_world) -> Game:
    """The test world in two acts; the LLM would answer "not understood" to anything."""
    return Game(Engine(World.model_validate(acts_world)), FakeLLMClient())


def test_after_a_death_riprendi_goes_on_from_the_last_act(two_acts):
    say(two_acts, "tira la leva")
    death = say(two_acts, "salta sulla leva")

    act = two_acts.resumable
    output = say(two_acts, "riprendi")

    assert death.endswith("Sei morta.")
    assert act == "secondo atto"
    assert output.startswith("Riprendi dall'inizio del secondo atto.\n\nAtrio\n")
    assert not two_acts.finished
    assert say(two_acts, "nord").endswith("Fine.")


def test_one_can_die_and_go_on_again(two_acts):
    say(two_acts, "tira la leva")
    for _ in range(2):
        say(two_acts, "salta sulla leva")
        assert say(two_acts, "riprendi").startswith("Riprendi dall'inizio del secondo atto.")

    assert not two_acts.finished


def test_a_finished_game_answers_without_the_llm(two_acts):
    say(two_acts, "salta sulla leva")  # dead before any act began: nothing to go on from

    assert say(two_acts, "riprendi") == "La partita è finita."
    assert say(two_acts, "provo a scappare dalla finestra") == "La partita è finita."
    assert two_acts.llm.calls == []


def test_riprendi_means_nothing_while_playing_or_after_winning(two_acts):
    playing = say(two_acts, "riprendi")
    say(two_acts, "tira la leva")
    say(two_acts, "nord")
    won = say(two_acts, "riprendi")

    assert playing == NOT_UNDERSTOOD  # the fake LLM understands nothing
    assert won == "La partita è finita."
    assert two_acts.state.current_room == "cella"
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_game.py -q`
Expected: FAIL — `Game` non ha `resumable`; «riprendi» dopo la morte risponde «La partita è finita.»; e su una partita finita la frase libera passa dall'LLM (`llm.calls` non è vuoto).

- [ ] **Step 3: Implementazione**

In `app/game.py`:

- l'import del motore diventa `from app.engine.engine import GAME_OVER, NOBODY_HERE, NOT_HERE, Engine`;
- dopo `ALL_RIGHT = "Va bene."`:
```python
RESUME_WORD = "riprendi"  # after a death: the game again from the beginning of the last act
```
- in `class Game`, dopo la proprietà `finished`:
```python
    @property
    def resumable(self) -> str | None:
        """After a death, the act the game can go on from ("secondo atto"); otherwise None."""
        return self.engine.resumable(self.state)

    def resume(self) -> str:
        """The game again from the beginning of the last act, after a death."""
        self.state, outcome = self.engine.resume(self.state)
        self.pending = None
        return render(outcome, self.world)
```
- in `turn`, subito dopo `if not words: return ""`:
```python
        if self.finished:
            # Nothing to do and nothing for the LLM to interpret, but going on after a death.
            if words == [RESUME_WORD] and self.resumable is not None:
                return self.resume()
            return GAME_OVER
```

- [ ] **Step 4: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde (anche `tests/test_web.py::test_a_finished_game_stays_finished` e `tests/test_castello.py::test_the_player_who_jumps_into_the_well_dies`, che si aspettano «La partita è finita.»).

- [ ] **Step 5: Commit**

```bash
git add app/game.py tests/test_game.py
git commit -m "Gioco: «riprendi» dopo una morte; una partita finita non chiama l'LLM" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Il web

**Files:**
- Modify: `app/main.py` (`TurnReply.resumable`), `static/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `Game.resumable` (Task 4).
- Produces: `TurnReply.resumable: str | None = None` nella risposta di `/api/turn`. La pagina tiene `save.resumable`; una partita finita con `resumable` non è «finita» per la pagina: input attivo, «(partita in corso)» nel menu, ripresa scegliendo l'avventura.

- [ ] **Step 1: Test che falliscono**

In `tests/test_web.py`, dopo `test_a_finished_game_stays_finished`:

```python
@pytest.fixture
def two_acts(acts_world) -> TestClient:
    return TestClient(create_app({"prova": Engine(World.model_validate(acts_world))}, llm=None))


def test_after_a_death_the_game_goes_on_from_the_last_act(two_acts):
    state = new_game(two_acts, "prova")["state"]
    state = turn(two_acts, "tira la leva", state, "prova")["state"]

    dead = turn(two_acts, "salta sulla leva", state, "prova")
    again = turn(two_acts, "riprendi", dead["state"], "prova")

    assert (dead["finished"], dead["resumable"]) == (True, "secondo atto")
    assert again["text"].startswith("Riprendi dall'inizio del secondo atto.")
    assert (again["finished"], again["resumable"]) == (False, None)
    assert again["state"]["checkpoint"]["flags"] == ["porta_aperta"]


def test_the_page_offers_to_go_on_after_a_death(client):
    page = client.get("/").text

    assert "reply.resumable" in page
    assert "Scrivi «riprendi» per ricominciare dall'inizio del" in page
```

e in `test_a_finished_game_stays_finished` aggiungere in fondo:
```python
    assert reply["resumable"] is None
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_web.py -q`
Expected: FAIL — la risposta non ha `resumable`, la pagina non lo usa.

- [ ] **Step 3: Implementazione (server)**

In `app/main.py`, in `class TurnReply`, dopo `pending: Action | None = None`:
```python
    # After a death: the act the game can go on from with «riprendi» ("secondo atto").
    resumable: str | None = None
```
e in `turn`, nel `return TurnReply(...)` finale aggiungere `resumable=game.resumable`:
```python
        return TurnReply(
            text=text,
            state=game.state,
            room=room_of(game),
            finished=game.finished,
            pending=game.pending,
            resumable=game.resumable,
        )
```

- [ ] **Step 4: Implementazione (pagina)**

In `static/index.html`:

`blank()`:
```js
  function blank() {
    return { state: null, room: "", finished: false, resumable: null, lines: [], pending: null };
  }
```

dopo `inProgress`, e `inProgress` stessa:
```js
  function inProgress(id) {
    const saved = load(id);
    return saved !== null && !over(saved);
  }

  // Over for good: finished, and not after a death the game can go on from («riprendi»).
  function over(saved) {
    return saved.finished && !saved.resumable;
  }
```

in `setBusy`, le due righe dell'input:
```js
    input.disabled = busy || over(save);
    input.placeholder = over(save) ? "La partita è finita." : save.resumable ? "riprendi" : "";
```

in `choose`, il commento e la condizione:
```js
  // A game in progress goes on (also after a death, with «riprendi»); a finished one, or none, starts anew.
  ...
    if (saved && !over(saved)) resume(saved);
```

in `play`, dopo `save.finished = reply.finished;` e al posto della riga dell'avviso di fine:
```js
      save.finished = reply.finished;
      save.resumable = reply.resumable ?? null;
      save.pending = reply.pending ?? null;
      say("story", reply.text);
      if (reply.resumable) {
        say("notice", `[Scrivi «riprendi» per ricominciare dall'inizio del ${reply.resumable}, oppure scegli «Nuova partita».]`);
      } else if (reply.finished) {
        say("notice", "[Fine. Per giocare ancora scegli «Nuova partita» o «Avventure».]");
      }
```
(la riga `save.pending = reply.pending ?? null;` c'è già: non duplicarla; `say("story", reply.text);` pure.)

- [ ] **Step 5: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde.

- [ ] **Step 6: Prova nel browser (porta 8765)**

Nessun mondo vero ha ancora atti: si prova con un server usa e getta nello scratchpad, che serve il mondo di prova in due atti. Scrivere con Write il file `<scratchpad>/due_atti.py`:

```python
"""Throwaway: the test world in two acts, served on port 8765 to try «riprendi» in the browser."""

import sys

sys.path.insert(0, r"C:\Progetti\IAvventura nel castello")

import uvicorn

from app.engine.engine import Engine
from app.engine.models import World
from app.main import create_app

WORLD = {
    "game": {
        "title": "Prova in due atti",
        "summary": "Tira la leva, poi salta sulla leva.",
        "intro": "Inizio.",
        "start_room": "atrio",
        "acts": [{"name": "secondo atto", "when": {"flag": "porta_aperta"}}],
        "endings": [
            {"when": {"flag": "caduta"}, "death": True, "text": "Sei morta."},
            {"when": {"player_in": "cella"}, "text": "Fine."},
        ],
    },
    "rooms": {
        "atrio": {
            "name": "Atrio",
            "description": "Un atrio spoglio, con una leva. A nord la cella.",
            "exits": {"nord": {"to": "cella", "when": {"flag": "porta_aperta"}, "otherwise": "La porta è chiusa."}},
        },
        "cella": {"name": "Cella", "description": "Una cella umida.", "exits": {"sud": {"to": "atrio"}}},
    },
    "items": {
        "leva": {"name": "leva", "gender": "f", "description": "Una leva.", "location": "atrio", "scenery": True},
    },
    "rules": {
        "tira_leva": {"trigger": {"verb": "tira", "target": "leva"}, "effects": [{"set_flag": "porta_aperta"}], "text": "Clac!"},
        "salta_leva": {"trigger": {"verb": "salta", "target": "leva"}, "effects": [{"set_flag": "caduta"}], "text": "Scivoli."},
    },
}

uvicorn.run(create_app({"prova": Engine(World.model_validate(WORLD))}, llm=None), host="127.0.0.1", port=8765)
```

Avviarlo in background (`.venv/Scripts/python <scratchpad>/due_atti.py`), aprire `http://127.0.0.1:8765` (claude-in-chrome, scheda nuova) e controllare, con uno screenshot per passo:
1. «1» → «tira la leva» → «salta sulla leva»: compaiono «Sei morta.» e l'avviso «[Scrivi «riprendi»…]»; l'input resta attivo con il segnaposto «riprendi».
2. Ricaricare la pagina: la partita riprende con l'avviso ancora a schermo (nel menu, «(partita in corso)»).
3. «riprendi»: «Riprendi dall'inizio del secondo atto.» e l'Atrio; «nord» → «Fine.» e l'avviso di sempre, input disattivato.
Poi fermare il server (Stop-Process sul processo in ascolto sulla 8765) e chiudere la scheda.

- [ ] **Step 7: Commit**

```bash
git add app/main.py static/index.html tests/test_web.py
git commit -m "Web: dopo una morte si riprende dall'inizio dell'atto con «riprendi»" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Il terminale

**Files:**
- Modify: `app/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `Game.resumable`, `Game.resume()` (Task 4); fixture `acts_world`; `play_session` già in `tests/test_cli.py`.
- Produces: costante `RESUME = "\nVuoi riprendere dall'inizio del {act}? (s/n)"`; funzione `keep_playing(game, read_line, write)` (il ciclo di oggi di `run`, senza l'apertura); `run` = apertura + `keep_playing`.

- [ ] **Step 1: Test che falliscono**

In `tests/test_cli.py`, l'import diventa:
```python
from app.cli import GOODBYE, PLAY_AGAIN, RESUME, WHICH_ADVENTURE, choose, menu, pick, run, session
```
e in fondo:

```python
# --- After a death -----------------------------------------------------------------------------------

GO_ON = RESUME.format(act="secondo atto")


def test_after_a_death_the_terminal_offers_to_go_on_from_the_last_act(acts_world):
    output = play_session({"prova": World.model_validate(acts_world)}, "1", "tira la leva", "salta sulla leva", "sì", "nord", "no")

    after_the_question = output[output.index(GO_ON) + 1]
    assert after_the_question.startswith("Riprendi dall'inizio del secondo atto.")
    assert output[-3].endswith("Fine.")
    assert output[-2:] == [PLAY_AGAIN, GOODBYE]


def test_not_going_on_after_a_death_asks_whether_to_play_again(acts_world):
    output = play_session({"prova": World.model_validate(acts_world)}, "1", "tira la leva", "salta sulla leva", "no", "no")

    assert output[-3:] == [GO_ON, PLAY_AGAIN, GOODBYE]


def test_a_death_before_any_act_only_asks_whether_to_play_again(acts_world):
    output = play_session({"prova": World.model_validate(acts_world)}, "1", "salta sulla leva", "no")

    assert GO_ON not in output
    assert output[-2:] == [PLAY_AGAIN, GOODBYE]
```

- [ ] **Step 2: Verificare che falliscano**

Run: `.venv/Scripts/python -m pytest tests/test_cli.py -q`
Expected: FAIL — `RESUME` non esiste (errore d'import).

- [ ] **Step 3: Implementazione**

In `app/cli.py`:

dopo `PLAY_AGAIN = ...`:
```python
RESUME = "\nVuoi riprendere dall'inizio del {act}? (s/n)"  # after a death, when an act has begun
```

`session` diventa:
```python
def session(
    worlds: Mapping[str, World],
    new_game: Callable[[str], Game],
    read_line: Callable[[], str],
    write: Callable[[str], None],
) -> None:
    """Menu and game, again and again. After a death the game may go on from the beginning of the
    last act; a game that ends (won or lost) asks whether to play another. Quitting, or the input
    running out, ends the session."""
    try:
        while True:
            game = new_game(choose(worlds, read_line, write))
            run(game, read_line, write)
            while game.resumable is not None:
                write(RESUME.format(act=game.resumable))
                if not _yes(read_line()):
                    break
                write(game.resume())
                keep_playing(game, read_line, write)
            if not game.finished:
                return
            write(PLAY_AGAIN)
            if not _yes(read_line()):
                write(GOODBYE)
                return
    except EOFError:
        return
```

`run` si divide in due:
```python
def run(game: Game, read_line: Callable[[], str], write: Callable[[str], None]) -> None:
    """Opens a new game and plays until it ends, the player quits, or the input runs out (EOFError)."""
    write(game.opening())
    keep_playing(game, read_line, write)


def keep_playing(game: Game, read_line: Callable[[], str], write: Callable[[str], None]) -> None:
    """Plays until the game ends, the player quits, or the input runs out (EOFError)."""
    try:
        while not game.finished:
            line = read_line()
            words = words_of(line)
            if len(words) == 1 and words[0] in _QUIT_WORDS:
                write(CONFIRM_QUIT)
                if _yes(read_line()):
                    write(GOODBYE)
                    return
                write(GO_ON)
                continue
            answer = game.turn(line)
            if answer:
                write(answer)
    except EOFError:
        return


def _yes(line: str) -> bool:
    answer = words_of(line)
    return bool(answer) and answer[0] in _YES_WORDS
```

(Attenzione: in `app/cli.py` esiste già una costante `GO_ON = "Allora continuiamo."`; il `GO_ON` dei test è un'altra cosa, locale al file dei test.)

- [ ] **Step 4: Verificare che passino, e tutta la suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde, compresi i test di oggi su `run`, «fine»/«esci» e «Vuoi giocare ancora?».

- [ ] **Step 5: Commit**

```bash
git add app/cli.py tests/test_cli.py
git commit -m "Terminale: dopo una morte chiede se riprendere dall'inizio dell'atto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: La Rocca, la documentazione e la verifica finale

**Files:**
- Modify: `data/worlds/rocca/gioco.yaml`, `docs/formato-mondo.md`, `CLAUDE.md`, `docs/superpowers/specs/2026-09-29-valdimora-design.md`
- Test: `tests/test_castello.py`

**Interfaces:**
- Consumes: tutto quanto sopra.

- [ ] **Step 1: Test che fallisce**

In `tests/test_castello.py`, in `test_the_player_who_jumps_into_the_well_dies`, in fondo:
```python
    assert game.state.lost
    assert game.resumable is None  # the castle has no acts: a new game, as before
```

Run: `.venv/Scripts/python -m pytest tests/test_castello.py -q`
Expected: FAIL — `game.state.lost` è falso.

- [ ] **Step 2: Il pozzo è una morte**

In `data/worlds/rocca/gioco.yaml`, nel finale `- when: {flag: caduto_nel_pozzo}`, aggiungere sotto `when` la riga:
```yaml
      death: true
```

Run: `.venv/Scripts/python -m pytest -q` — Expected: tutto verde.

- [ ] **Step 3: `docs/formato-mondo.md`**

1. Nel blocco YAML di `game`, dopo `start_room: cortile`:
```yaml
  acts:                    # facoltativo: le parti del gioco, in ordine (vedi «Atti»)
    - name: secondo atto
      when: {flag: atto_due}
```
e nel finale di morte dell'esempio aggiungere `death: true` sotto la sua `when`.
2. Il paragrafo **Pericoli** diventa:
> **Pericoli.** Un finale non deve per forza essere una vittoria: una regola che attiva un flag e un finale con quel flag e `death: true` fanno morire il giocatore. Si può morire anche entrando in una stanza: `when: {all: [{player_in: sottotetto}, {not: {flag: asse_posata}}]}`. Nella Rocca la regola `salto_nel_pozzo` (`verb: salta`) attiva `caduto_nel_pozzo`. Il testo della regola racconta cosa succede, quello del finale lo chiude. Un pericolo va annunciato prima, in una descrizione: il pozzo è «profondo tre o quattro volte la tua altezza».
3. Dopo **Pericoli**, un paragrafo nuovo:
> **Atti.** In un'avventura lunga, `acts` divide il gioco in parti. Quando la condizione di un atto diventa vera per la prima volta (di solito il flag della regola che apre il piano nuovo), il gioco mette da parte lo stato. Dopo una morte si riprende da lì: nel web scrivendo «riprendi», nel terminale rispondendo sì alla domanda. Senza atti, dopo una morte si ricomincia da capo. `name` si legge dopo «dall'inizio del»: «secondo atto». Gli atti cominciano in ordine: il secondo solo dopo il primo.
4. Nella sezione `rules`, nel blocco YAML dopo `otherwise: …`:
```yaml
    otherwise_variants: []                      # facoltativo, come le variants: il testo che segue la partita
```
e nell'elenco «Come le usa il motore», nel punto sulla prima regola che corrisponde, dopo «Se il suo `when` è falso si mostra `otherwise`»: «(o la prima delle sue `otherwise_variants` la cui condizione vale)».
5. Nella sezione `characters`, nel blocco YAML dopo `location: scuderia`:
```yaml
    moves:                       # facoltativo: dove si trova quando una condizione vale
      - when: {flag: atto_due}
        room: biblioteca
```
e cambiare il commento di `location` in `# una stanza: dove sta quando nessuno spostamento vale`; poi un punto nell'elenco:
> - **Spostamenti**: `moves` dice dove si trova il personaggio mentre una condizione vale; vale il primo spostamento vero, altrimenti `location`. Si sposta solo così, con i flag: non si muove da solo col passare del tempo. Descrizione della stanza, dialoghi, `dai` e interprete seguono la sua posizione.
6. In **Condizioni**, la frase «Usate in `when` di uscite, varianti, regole, argomenti dei personaggi e finali» diventa «Usate in `when` di uscite, varianti, regole, argomenti e spostamenti dei personaggi, atti e finali».
7. In **Stato della partita**, l'elenco di cosa contiene `GameState` aggiunge: «se la partita è persa (una morte), quanti atti sono cominciati e lo stato all'inizio dell'ultimo».

- [ ] **Step 4: La spec e CLAUDE.md**

Nella spec (`docs/superpowers/specs/2026-09-29-valdimora-design.md`), sezione 5.2, sostituire il punto che comincia con «`Game.turn("riprendi")`» con:
> - `Game.turn("riprendi")` su una partita persa con checkpoint la riprende; su una partita finita, qualunque altra riga risponde «La partita è finita.» senza passare dall'LLM. L'invito a riprendere lo scrivono i front end: la pagina, con `resumable` (il nome dell'atto), «[Scrivi «riprendi» per ricominciare dall'inizio del secondo atto, oppure scegli «Nuova partita».]»; il terminale con la sua domanda.

In `CLAUDE.md`, in «Decisioni prese», dopo la voce **Pericoli**:
> - **Motore per Valdimora** (2026-09-29, branch `feature/inizia_l_Avventura`; spec in `docs/superpowers/specs/2026-09-29-valdimora-design.md`): tre aggiunte, nessuna al prompt. Personaggi che si spostano con le condizioni (`moves`, `Engine.character_room`). Atti (`game.acts`) e morti (`death: true` nei finali): quando comincia un atto il motore tiene da parte lo stato (`GameState.checkpoint`, con `act` e `lost`), e dopo una morte si riprende da lì (`Engine.resumable`/`resume`): nel web con «riprendi» (campo `resumable` nella risposta di `/api/turn`, avviso scritto dalla pagina), nel terminale con «Vuoi riprendere dall'inizio del secondo atto? (s/n)». Una partita finita non chiama più l'LLM. Il pozzo della Rocca è una morte, ma senza atti si ricomincia da capo. Le regole hanno anche `otherwise_variants`.

- [ ] **Step 5: Verifica finale**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tutto verde, e i test del modello vero saltati (`OLLAMA_TESTS` non impostato). Il prompt non è cambiato: controllare con
`git diff main --stat -- app/llm/` (atteso: nessun file) e `.venv/Scripts/python -m pytest tests/test_interpreter.py -q` verde (compreso il confronto con `tests/prompt_rocca.txt`).

Poi una partita nel terminale alla Rocca senza LLM, fino al pozzo:
```bash
printf '1\nsalta nel pozzo\nno\n' | LLM=off LLM_LOG=off COMMAND_LOG=off PYTHONIOENCODING=utf-8 .venv/Scripts/python -m app.cli | tail -6
```
Expected: la morte, poi «Vuoi giocare ancora? (s/n)» (nessuna domanda sulla ripresa) e «Alla prossima!».

- [ ] **Step 6: Commit**

```bash
git add data/worlds/rocca/gioco.yaml docs/formato-mondo.md CLAUDE.md docs/superpowers/specs/2026-09-29-valdimora-design.md tests/test_castello.py
git commit -m "Rocca: il pozzo è una morte; documentati spostamenti, atti e morti" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Poi chiedere all'utente se pubblicare il branch per la PR verso `main` (non pubblicarlo senza il suo sì).
