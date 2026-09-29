# I.A.vventura nel Castello

Avventure testuali in stile anni '80/'90, giocabili dal browser: un castello per i grandi e un bosco fatato per i bambini.
Si gioca scrivendo in italiano naturale ("prendi la corda", "cala il secchio nel pozzo"):
un modello linguistico locale capisce le frasi, mentre un motore deterministico tiene le
regole del gioco e tutti i testi sono scritti a mano.

Liberamente ispirata ad «Avventura nel castello», l'avventura testuale di Enrico Colombini del
1982. Il castello, gli enigmi e i testi sono originali.

> **Stato:** in sviluppo. Sono pronte le prime cinque fasi: formato del mondo in YAML, motore
> di gioco, parser dei comandi semplici con testo fisso, LLM che interpreta le frasi libere,
> interfaccia web. Le avventure **si giocano dal browser o dal terminale**.

## Come funziona

Il **motore di gioco** è deterministico ed è l'unica fonte di verità sullo stato: stanze,
oggetti, inventario, porte, flag degli enigmi. L'**LLM non modifica mai lo stato** e ha un solo
ruolo: **interprete**. Trasforma la frase del giocatore in un'azione strutturata (JSON vincolato
da uno schema), che il motore poi valida ed esegue. Tutto ciò che il giocatore legge è testo
fisso, scritto dagli autori del mondo o dal motore: un modello piccolo, come narratore,
inventava eventi e a volte contraddiceva il gioco.

Un turno funziona così:

```
input del giocatore
  → parser classico (comandi semplici: "nord", "prendi X", "inventario")
  → se non riconosciuto: LLM interprete → azione (JSON), mostrata tra parentesi
  → motore: valida ed esegue → esito
  → testo fisso
```

Il modello gira in locale con [Ollama](https://ollama.com), anche solo su CPU: per questo i
prompt sono brevi e tutto ciò che il parser sa gestire non passa dall'LLM.

## Le avventure

**La Rocca di Serravento**: sorpreso dalla bufera, il giocatore si rifugia in una rocca
abbandonata e il portone gli si richiude alle spalle. Deve trovare un'altra via d'uscita.

**Il draghetto raffreddato**, per bambini dagli 8 anni: nel Bosco Fatato un draghetto ha perso
il fuoco per colpa di un raffreddore e non riesce più a volare fino a casa. Bisogna aiutarlo, con
l'orso Tobia, un nido in cima a una quercia e gli indizi del draghetto stesso.

Ogni avventura è descritta in file YAML in una cartella di `data/worlds/` (stanze, oggetti,
regole degli enigmi, personaggi, finali), e `data/worlds/avventure.yaml` dà l'ordine del menu.
Il formato è documentato in [`docs/formato-mondo.md`](docs/formato-mondo.md): basta
quello per scrivere una nuova avventura senza toccare il codice. Al caricamento il mondo viene
controllato a fondo (riferimenti, flag mai attivati, stanze irraggiungibili…) e tutti gli errori
vengono mostrati insieme, con il punto esatto in cui correggerli.

Il motore riceve azioni già strutturate (verbo, oggetti, direzione), applica le regole del mondo
e restituisce un esito: il testo da mostrare, la stanza in cui si trova il giocatore e,
all'ultima mossa, il finale. Cosa fanno i verbi e come scattano le regole è spiegato nello
stesso documento del formato.

## Requisiti

- Python 3.12
- Per le frasi libere: [Ollama](https://ollama.com) con il modello `qwen2.5:3b`
  (`ollama pull qwen2.5:3b`, circa 2 GB). Basta la CPU. Senza Ollama il gioco funziona lo
  stesso, con i soli comandi semplici.

## Installazione

Su Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "fastapi>=0.115" "uvicorn>=0.30" "pytest>=8"
```

Su Linux o macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "fastapi>=0.115" "uvicorn>=0.30" "pytest>=8"
```

## Come si gioca

**Nel browser**: avvia il server dalla cartella del progetto e apri <http://127.0.0.1:8000>.

```powershell
.venv\Scripts\python -m app.main
```

All'inizio scegli l'avventura dal menu: toccandola, oppure scrivendo il numero o il nome.
Ogni avventura si salva da sola nel browser (`localStorage`): ricaricando la pagina riprendi da
dove eri. Il server non tiene nessuna partita, quindi riavviarlo non perde niente; ogni browser ha
le sue. Nella riga di stato in basso, «Avventure» torna al menu senza perdere niente e «Nuova
partita» ricomincia da capo l'avventura in corso, dopo una conferma. Se nel frattempo il mondo è
cambiato (stanze o oggetti diversi nei file YAML), la partita salvata ricomincia. Sempre nella riga
in basso scegli il colore dello schermo, fosfori verdi o ambra, come i monitor dell'epoca; la
scelta resta anche per le partite successive.

**Nel terminale**:

```powershell
.venv\Scripts\python -m app.cli
```

Anche nel terminale si comincia scegliendo l'avventura.

I due modi usano lo stesso motore e possono essere usati insieme, ognuno con la sua partita.

Il gioco capisce subito i comandi semplici, con o senza articoli:

| Per… | Scrivi |
|---|---|
| muoverti | `nord`, `sud`, `est`, `ovest`, `su`, `giù` (anche `n`, `s`, `e`, `o`, `vai a nord`), oppure `vai in cucina` per una stanza che conosci |
| guardarti intorno | `guarda` |
| vedere cosa porti | `inventario` (anche `i`) |
| agire sugli oggetti | `esamina X` (anche `x X`), `prendi X`, `lascia X`, `apri X`, `chiudi X`, `leggi X`, `spingi X`, `tira X` |
| combinare due oggetti | `usa X con Y`, `apri X con Y` |
| parlare con i personaggi | `parla con X` (anche `saluta X`), `chiedi a X di Y` |
| aiuto / terminare | `aiuto` / `fine` (nel terminale) |

Le frasi più libere ("dai un'occhiata al pozzo", "metti giù la corda") passano all'LLM, se
Ollama è acceso: il gioco mostra tra parentesi come le ha capite, poi risponde. Ogni frase
libera richiede qualche secondo su CPU (4-7 s nelle nostre prove; la prima, che carica il
modello, fino a 20 s).

Anche ai personaggi si può parlare liberamente ("pellegrino, cosa sai della torre?"): l'LLM
sceglie solo a chi ti rivolgi e di cosa chiedi, la risposta è sempre un testo scritto per il
gioco. Così nessun personaggio può inventare fatti o svelare la soluzione.

Configurazione, con variabili d'ambiente:

| Variabile | Valore predefinito | Significato |
|---|---|---|
| `LLM` | `ollama` | `off` per giocare senza LLM |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | dove risponde Ollama (meglio `127.0.0.1` di `localhost`: su Windows `localhost` rallenta ogni connessione di circa 2 s) |
| `LLM_MODEL` | `qwen2.5:3b` | il modello da usare |
| `LLM_LOG` | `logs/llm.log` (terminale), `logs/llm-web.log` (browser) | file dove finisce ciò che viene passato al modello e ciò che torna; `off` per non scriverlo |
| `LLM_LOG_FULL` | `0` | `1` per scrivere nel log anche la richiesta intera mandata a Ollama (schema e opzioni compresi) e la sua risposta intera |

Il log dell'LLM riporta, per ogni frase libera, gli oggetti e la frase inviati (`>>>`), la
risposta del modello (`<<<`), i tempi e i token, e com'è stata tradotta in azione (`===`). Il
prompt di sistema compare una volta sola, all'inizio. Con `LLM_LOG_FULL=1` ogni chiamata ha
anche la richiesta esatta (si può rimandare a Ollama così com'è, per esempio con
`curl http://127.0.0.1:11434/api/chat --data-binary @richiesta.json`) e la risposta intera, con i
tempi di Ollama (`load_duration`, `prompt_eval_duration`, `eval_duration`, in nanosecondi).

## Sviluppo

Eseguire i test:

```powershell
.venv\Scripts\python -m pytest
```

I test col modello vero (Ollama acceso) sono saltati per default; si lanciano così:

```powershell
$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s
```

Controllare che le avventure in `data/worlds/` siano valide:

```powershell
.venv\Scripts\python -c "from app.engine.loader import load_adventures; print([w.game.title for w in load_adventures().values()])"
```

Se il mondo contiene errori, il comando li elenca tutti.

## Struttura

```
app/
  engine/
    models.py       # modelli Pydantic: mondo, stato della partita, azione ed esito
    loader.py       # lettura dei file YAML e validazione
    validation.py   # controlli incrociati (riferimenti, flag, raggiungibilità)
    engine.py       # il motore: esegue le azioni e aggiorna lo stato
    parser.py       # comandi semplici in italiano -> azioni
    text.py         # articoli e testo fisso degli esiti
  llm/
    client.py       # client per il modello (Ollama) e client finto per i test
    interpreter.py  # frase libera -> azione
    prompts.py      # il prompt dell'interprete
  config.py         # variabili d'ambiente
  game.py           # un turno: parser, interprete, motore, testo
  cli.py            # la partita nel terminale
  main.py           # la partita nel browser: server FastAPI
static/index.html   # la pagina del gioco
data/worlds/        # le avventure: una cartella ciascuna, e l'indice del menu
docs/               # documentazione del formato e delle regole
tests/              # test pytest
```

## Prossime fasi

1. ~~Formato del mondo, modelli e castello di esempio~~
2. ~~Motore di gioco: esecuzione delle azioni, regole e condizioni~~
3. ~~Parser classico dei comandi semplici, testo fisso e gioco da terminale~~
4. ~~LLM interprete delle frasi libere (Ollama)~~
5. ~~Interfaccia web in stile console retrò~~
6. ~~Personaggi e dialoghi~~
