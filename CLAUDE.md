# Avventura testuale nel castello — note di progetto

## Obiettivo
Avventura testuale in stile anni '80/'90 ambientata in un castello, giocabile via web.
Il giocatore scrive in italiano naturale e può dialogare con i personaggi.
Il castello, gli enigmi e i personaggi sono **originali**: non copiare contenuti di giochi esistenti.

## Principio architetturale (non negoziabile)
- Il **motore di gioco è deterministico** ed è l'unica fonte di verità sullo stato (stanze, oggetti, inventario, porte, flag degli enigmi).
- L'**LLM non modifica mai lo stato** e ha **un solo ruolo: interprete**. Trasforma la frase
  del giocatore in un'azione strutturata (JSON vincolato da schema), che il motore valida.
- **Niente narratore LLM** (decisione del 2026-09-25): tutto ciò che il giocatore legge è testo
  fisso, scritto dagli autori del mondo o dal motore. Con qwen2.5:3b su CPU il narratore inventava
  eventi, a volte contraddiceva il motore e impiegava 9-17 s. Il tentativo è nel commit 09f4df0.
- Nei dialoghi, ogni personaggio ha un profilo con cosa sa e cosa può rivelare. L'LLM non deve mai dare la soluzione degli enigmi.

## Flusso di un turno
```
input giocatore
  → parser classico (comandi semplici: "nord", "prendi X", "inventario")
  → se non riconosciuto: LLM interprete → Azione (JSON), mostrata al giocatore tra parentesi
    (se il mondo non la prevede: "Vuoi usare X con Y?" e si esegue solo dopo un sì)
  → motore: valida ed esegue → Esito
  → testo fisso (app/engine/text.py)
```

## Stack
- Python 3.12, FastAPI, Pydantic v2, uvicorn, httpx (client per Ollama)
- Frontend: un solo HTML con JS/CSS minimale in stile console retrò, senza framework
- Dati del mondo in YAML (PyYAML), validati con modelli Pydantic al caricamento
- Test: pytest
- Persistenza: stato partita serializzato in JSON. Nel web lo tiene il browser (`localStorage`);
  SQLite solo se serviranno partite legate a un account e condivise tra dispositivi

## LLM
- Sviluppo: **Ollama in locale, solo CPU (niente GPU)**. Modello piccolo da 3-4B (es. famiglia Qwen o Llama, versione recente).
- In futuro, forse: API con piano gratuito o a pagamento. Il cambio deve richiedere solo configurazione.
- Astrazione `LLMClient` (`app/llm/client.py`), con un solo metodo per il modello: `complete_json`.
  - `OllamaClient` (API nativa `/api/chat`, output strutturato con `format`)
  - `FakeLLMClient` (risposte predefinite, per i test)
  - `OpenAICompatibleClient` (per provider esterni): rimandato a quando ne sceglieremo uno.
- Configurazione via variabili d'ambiente (`app/config.py`): `LLM` (ollama | off), `OLLAMA_URL`,
  `LLM_MODEL`, `LLM_LOG`, `COMMAND_LOG`. Se Ollama non risponde, il gioco avvisa e prosegue con i
  soli comandi semplici.
- Log delle chiamate (logger `app.llm`): il terminale lo scrive in `logs/llm.log` (esclusa da
  git; `LLM_LOG=off` per spegnerlo). Per ogni chiamata: messaggio inviato (`>>>`), risposta
  grezza (`<<<`), tempo e token di Ollama (anche quelli in cache), azione risultante o motivo del
  "non capito" (`===`). Il prompt di sistema solo quando cambia; lo schema mai.
- Log dei comandi andati male (logger `app.commands`): `logs/comandi.jsonl`, un oggetto JSON per
  riga, per terminale e web insieme (`COMMAND_LOG=off` per spegnerlo). Una riga per ogni frase non
  capita, "altro", azione rifiutata dal motore o richiesta di conferma, con ora, origine, stanza,
  frase, `da` (parser | llm), azione (con gli id), esito e dettaglio. Serve a trovare le frasi da
  sistemare.

### Vincoli dovuti alla CPU
- Prompt **corti**: passa solo gli oggetti a portata (con i loro alias), mai il mondo intero.
- Preferire l'output strutturato con schema JSON al tool calling (più affidabile sui modelli piccoli).
- Ridurre le chiamate: tutto ciò che il parser classico sa gestire non passa dall'LLM.
- Non cambiare l'inizio del prompt di sistema senza motivo: Ollama lo tiene in cache, e un
  prefisso nuovo costa ~10 s in più alla prima chiamata.

## Struttura proposta
```
app/
  main.py            # FastAPI: la pagina e due endpoint (/api/new, /api/turn)
  config.py          # variabili d'ambiente
  game.py            # un turno: parser → interprete LLM → motore → testo fisso
  cli.py             # la partita nel terminale
  engine/
    models.py        # Pydantic: Mondo, Stanza, Oggetto, Personaggio, Azione, Esito, StatoPartita
    loader.py        # caricamento e validazione YAML
    validation.py    # controlli incrociati sul mondo (riferimenti, flag, raggiungibilità)
    engine.py        # esecuzione azioni, regole, condizioni
    parser.py        # parser classico dei comandi semplici
    text.py          # articoli e testo fisso degli esiti
  llm/
    client.py        # interfaccia LLMClient + implementazioni
    interpreter.py   # frase → Azione
    prompts.py
  storage/
    saves.py
data/
  world/*.yaml       # stanze, oggetti, personaggi
static/
  index.html
tests/
```

## Convenzioni
- Codice e identificatori in inglese; testi di gioco, prompt e commenti rivolti al giocatore in italiano.
- Il motore non importa nulla da `llm/`: deve essere testabile senza modello.
- Ogni regola o enigma nuovo va accompagnato da un test sul motore.
- Una frase libera che il modello sbaglia giocando diventa un caso di `tests/test_ollama.py`,
  con il test sul client finto accanto (`tests/test_interpreter.py` o `tests/test_game.py`).
- Nessun costo di infrastruttura: niente servizi a pagamento senza chiedere.

## Decisioni prese
- **Formato YAML del mondo** (fase 1, 2026-09-25): descritto in `docs/formato-mondo.md`.
  Mondo di esempio: la Rocca di Serravento in `data/world/`.
- **Personaggi e dialoghi rimandati** (decisione del 2026-09-25): li affronteremo in una fase
  successiva. Per ora il formato del mondo non li prevede; andranno aggiunti con il loro profilo
  (cosa sanno, cosa possono rivelare) quando lavoreremo sui dialoghi.

- **Motore di gioco** (fase 2, 2026-09-25): `Engine` in `app/engine/engine.py`.
  - Schema dell'Azione (`Action` in `models.py`): un solo modello piatto `verb`, `target`,
    `with`, `direction`, con gli **id** degli oggetti. `verb` è un `Verb` (verbi sugli oggetti,
    a cui reagiscono le regole) o un `Command` (`vai`, `guarda`, `inventario`).
    Da nomi e alias agli id ci pensa il parser (fase 3), usando `Engine.in_reach`.
  - `usa X con Y` senza una regola `usa` ricade sulla prima regola di qualunque verbo sugli
    stessi due oggetti.
  - I messaggi del motore non nominano l'oggetto ("Fatto.", "Non si può prendere."): articoli e
    genere si decidono nella fase 3, insieme al testo di stanze e inventario.
  - Regole e comportamento predefinito dei verbi: in `docs/formato-mondo.md`.
- **Parser, testo fisso e terminale** (fase 3, 2026-09-25):
  - `app/engine/parser.py`: comandi semplici → `Action`, `Ambiguous` o `None`. È severo: una
    parola sconosciuta rende la frase non capita, e le frasi libere andranno all'LLM (fase 4).
    Riconoscimento degli oggetti descritto in `docs/formato-mondo.md`.
  - Oggetti con `gender` (m/f, obbligatorio) e `plural` (facoltativo): gli articoli si calcolano
    in `app/engine/text.py`, che trasforma anche l'esito in testo fisso (stanza con "Qui vedi…"
    e "Uscite: …", inventario, finale).
  - Se il nome è ambiguo il gioco chiede "Quale intendi: …?" e il giocatore riscrive il comando
    intero (non si ricorda l'azione a metà: da riprendere con l'interfaccia web).
  - `app/cli.py`: partita nel terminale. `fine` ed `esci` chiedono conferma, perché "esci" può
    anche voler dire "esci dalla stanza".
- **LLM interprete** (fase 4, 2026-09-25):
  - `app/game.py`: `Game.turn(riga) → testo`, usato dal terminale e poi dal web. L'LLM entra solo
    se il parser non capisce; l'azione interpretata compare tra parentesi, "(usa la corda con il
    pozzo)", così il giocatore vede subito se il modello ha frainteso.
  - Se il modello non risponde o risponde qualcosa senza senso: "Non ho capito."
  - Test col modello vero in `tests/test_ollama.py`, saltati per default (`OLLAMA_TESTS=1`).
- **Andare in una stanza per nome** (2026-09-25): `Engine.known_exits` dà le uscite con la
  destinazione solo se il giocatore la conosce (visitata, o nominata nella descrizione attuale).
  Il parser capisce "vai in cucina"; l'LLM riceve "Uscite: nord (Torre), est (Scuderia), …" e,
  per un luogo che non è tra le uscite, risponde `bersaglio: nessuno` ("Non ho capito.").
  Senza le uscite nel prompt il modello tirava a indovinare la direzione.
- **Interfaccia web** (fase 5, 2026-09-25): `app/main.py` + `static/index.html`.
  - Server **senza memoria**: il browser tiene stato e testo a schermo nel `localStorage` e manda
    lo stato con ogni riga; il server lo controlla (`Engine.restore`), gioca il turno con `Game` e
    restituisce testo, stato, nome della stanza e `finished`. Una richiesta per turno, niente SSE.
  - Stato che non va più bene per il mondo (stanze o oggetti cambiati): "Il mondo è cambiato
    dall'ultimo salvataggio: la partita ricomincia." Se sono cambiati solo i testi, si continua.
  - Stato non firmato: con un giocatore solo, barare non danneggia nessuno. Firma HMAC se il
    gioco diventerà pubblico.
  - Pagina: console a fosfori (verdi o ambra), una sola dimensione di carattere, titolo sempre
    visibile in alto, riga di stato in video invertito in fondo (stanza, mosse, colore,
    «Nuova partita» con conferma nella pagina, niente `confirm()`).
  - Il web scrive il log dell'LLM in `logs/llm-web.log`; la disponibilità di Ollama si ricontrolla
    a ogni nuova partita.
  - `OLLAMA_URL` predefinito `http://127.0.0.1:11434`: con `localhost`, su Windows, ogni nuova
    connessione costava ~2 s (prova prima IPv6).

- **Interprete più robusto** (2026-09-25, dopo il bug del rampino: "usa il rampino per
  recuperare la chiave dal pozzo" diventava "usa il portone"). Il pozzo era nell'enum: la causa era
  la frase con lo scopo, che il modello da 3B non sa agganciare all'oggetto giusto.
  - **Più soluzioni per un enigma**: `trigger` di una regola può essere una lista di azioni
    equivalenti (`pesca_chiave`: "usa pozzo con corda con gancio" e "prendi chiave con corda con
    gancio").
  - **Oggetti in vista ma non a portata**: campo `visible_from: {room, when}` (la chiave in fondo al
    pozzo). Parser e interprete li ricevono dopo quelli a portata (`Engine.visible`); solo le regole
    agiscono su di loro, senza regola "Non ci arrivi.".
  - **Alias**: c'erano già (`aliases`, anche per gli arredi, che sono oggetti con `scenery: true`),
    mostrati al modello tra parentesi e riconosciuti dal parser.
  - **"altro"**: il modello lo sceglie quando la frase non è un'azione di gioco; lo stato non cambia
    e il gioco risponde con un testo fisso ("Non sembra un'azione del gioco. Scrivi «aiuto»…"),
    non con un narratore. L'interprete restituisce l'`Action` oppure `NotUnderstood` col motivo.
  - **Conferma**: un'azione interpretata dall'LLM che il mondo non prevede (`Engine.expects`:
    nessuna regola, e non è esamina/prendi/lascia senza strumento) non si esegue, il gioco chiede
    "Vuoi usare la corda con gancio con il portone?". Anche uno spostamento interpretato che la
    frase non nomina (né direzione né stanza): "vado in cantina" → "Vuoi andare a ovest?".
    "sì"/"certo"/"ok" eseguono, "no" annulla, altro è un comando nuovo ("s" e "n" restano sud e
    nord). Le azioni del parser non chiedono mai conferma: il giocatore ha scritto proprio quello.
  - **Azione in sospeso**: `Game.pending`; nel web viaggia accanto allo stato (campo `pending` di
    richiesta e risposta, tenuto dal browser), non dentro `GameState`, che resta solo del motore.
    Lo stesso meccanismo potrà servire a rispondere a "Quale intendi: …?".
  - **Esempio nel prompt**: la frase del rampino, in fondo agli esempi (vedi i risultati sotto).
    Lega il prompt fisso alla Rocca: quando ci sarà un secondo mondo, gli esempi andranno nel suo
    YAML.

## Decisioni ancora aperte
- Dialoghi con i personaggi: senza narratore LLM, le risposte saranno testi d'autore (l'LLM
  potrebbe solo scegliere l'argomento), oppure servirà un modello più capace.
- Hosting pubblico (es. PC di casa + Cloudflare Tunnel) — non prioritario.

## Comandi utili
```
# ambiente: Python 3.12 installato per l'utente (launcher `py`), ambiente virtuale in .venv
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "fastapi>=0.115" "uvicorn>=0.30" "pytest>=8"
.venv\Scripts\python -m pytest

.venv\Scripts\python -m app.cli      # giocare nel terminale (con Ollama acceso, anche frasi libere)
$env:LLM="off"                       # giocare senza LLM

$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s   # test col modello vero

ollama pull qwen2.5:3b
.venv\Scripts\python -m app.main          # giocare nel browser: http://127.0.0.1:8000
```


### Risultati dei test (qwen2.5:3b su CPU, Windows)
- Ambiente di sviluppo: Windows, PowerShell.
- Velocità misurate: generazione ~6-7 token/s, lettura prompt ~30 token/s.
  Con la parte fissa del prompt in testa, Ollama la tiene in cache (dal log: ~460 token su ~470
  già in cache): il grosso del tempo è generare i 25-30 token della risposta JSON.
- Interprete (fase 4): 4-7 s per frase; la prima chiamata 15-20 s (caricamento del modello,
  poi tenuto in memoria con `keep_alive: 30m`). `tests/test_ollama.py`: 16 su 16.
  - Output strutturato con `format` (schema JSON), `temperature: 0`, `num_predict: 60`, `num_ctx: 2048`.
  - Campi: `verbo`, `bersaglio` (su cosa si agisce; per "vai" la direzione), `con` (cosa si usa;
    "nessuno" se assente). Enum generati a ogni turno: verbi del motore + `altro` (non è
    un'azione); nomi degli oggetti a portata o in vista + direzioni + `nessuno`.
  - Nel prompt: glossario dei verbi (senza, il modello usava "usa" per quasi tutto), oggetti con
    gli alias tra parentesi (senza, confondeva "porta" con "portone"), esempi su un mondo
    inventato, più quello del rampino in fondo.
  - Scambiare bersaglio e strumento non è un problema: le regole accettano i due oggetti in
    qualunque ordine.
  - Frasi con lo scopo ("usa il rampino per recuperare la chiave dal pozzo"): senza esempio il
    modello ripiega su un oggetto a caso, spesso il portone, anche con la chiave nell'enum.
    Aggiungere istruzioni non aiutava; un esempio generico (baule e monete) nemmeno. L'esempio
    del rampino ripara la frase e le sue varianti.
  - Il modello è fragile: ogni riga in più nel prompt sposta altri casi. Con l'esempio del rampino
    (in fondo o dentro il blocco di esempi) "vado nella cantina" va a ovest: da qui la conferma
    sugli spostamenti non nominati. Mettere la chiave in vista nell'enum, senza l'esempio, rompeva
    invece "cala il rampino giù nel pozzo". Ogni modifica al prompt va verificata su tutto
    `tests/test_ollama.py` (oggi 16 su 16, ~85 s).
- Narratore: provato e scartato (vedi sopra), anche con temperatura 0.2 e senza descrizioni.