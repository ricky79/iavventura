# Avventura nel castello

Un'avventura testuale in stile anni '80/'90, ambientata in un castello e giocabile dal browser.
Si gioca scrivendo in italiano naturale ("prendi la corda", "cala il secchio nel pozzo"):
un modello linguistico locale capisce le frasi, mentre un motore deterministico tiene le
regole del gioco e tutti i testi sono scritti a mano.

Il castello, gli enigmi e i personaggi sono originali.

> **Stato:** in sviluppo. Sono pronte le prime quattro fasi: formato del mondo in YAML, motore
> di gioco, parser dei comandi semplici con testo fisso, LLM che interpreta le frasi libere.
> Il castello **si gioca già dal terminale**; l'interfaccia web arriverà nella prossima fase.

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

## Il mondo di esempio

**La Rocca di Serravento**: sorpreso dalla bufera, il giocatore si rifugia in una rocca
abbandonata e il portone gli si richiude alle spalle. Deve trovare un'altra via d'uscita.

Il mondo è descritto in file YAML in `data/world/` (stanze, oggetti, regole degli enigmi,
finali). Il formato è documentato in [`docs/formato-mondo.md`](docs/formato-mondo.md): basta
quello per scrivere un nuovo castello senza toccare il codice. Al caricamento il mondo viene
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
.venv\Scripts\python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "pytest>=8"
```

Su Linux o macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "pytest>=8"
```

## Come si gioca

Dal terminale, nella cartella del progetto:

```powershell
.venv\Scripts\python -m app.cli
```

Il gioco capisce subito i comandi semplici, con o senza articoli:

| Per… | Scrivi |
|---|---|
| muoverti | `nord`, `sud`, `est`, `ovest`, `su`, `giù` (anche `n`, `s`, `e`, `o`, `vai a nord`) |
| guardarti intorno | `guarda` |
| vedere cosa porti | `inventario` (anche `i`) |
| agire sugli oggetti | `esamina X` (anche `x X`), `prendi X`, `lascia X`, `apri X`, `chiudi X`, `leggi X`, `spingi X`, `tira X` |
| combinare due oggetti | `usa X con Y`, `apri X con Y` |
| aiuto / terminare | `aiuto` / `fine` |

Le frasi più libere ("dai un'occhiata al pozzo", "metti giù la corda") passano all'LLM, se
Ollama è acceso: il gioco mostra tra parentesi come le ha capite, poi risponde. Ogni frase
libera richiede qualche secondo su CPU (4-7 s nelle nostre prove; la prima, che carica il
modello, fino a 20 s).

Configurazione, con variabili d'ambiente:

| Variabile | Valore predefinito | Significato |
|---|---|---|
| `LLM` | `ollama` | `off` per giocare senza LLM |
| `OLLAMA_URL` | `http://localhost:11434` | dove risponde Ollama |
| `LLM_MODEL` | `qwen2.5:3b` | il modello da usare |

## Sviluppo

Eseguire i test:

```powershell
.venv\Scripts\python -m pytest
```

I test col modello vero (Ollama acceso) sono saltati per default; si lanciano così:

```powershell
$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s
```

Controllare che il mondo in `data/world/` sia valido:

```powershell
.venv\Scripts\python -c "from app.engine.loader import load_world; print(load_world().game.title)"
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
data/world/         # il castello di esempio
docs/               # documentazione del formato e delle regole
tests/              # test pytest
```

## Prossime fasi

1. ~~Formato del mondo, modelli e castello di esempio~~
2. ~~Motore di gioco: esecuzione delle azioni, regole e condizioni~~
3. ~~Parser classico dei comandi semplici, testo fisso e gioco da terminale~~
4. ~~LLM interprete delle frasi libere (Ollama)~~
5. Interfaccia web in stile console retrò
6. Personaggi e dialoghi
