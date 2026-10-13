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
- Nei dialoghi i personaggi rispondono per argomenti, con testi d'autore: l'LLM sceglie solo
  personaggio e argomento, quindi non può mai dare la soluzione degli enigmi.

## Flusso di un turno
```
input giocatore
  → parser classico (comandi semplici: "nord", "prendi X", "inventario", "vai dall'orso")
  → se non riconosciuto: LLM interprete → Azione (JSON), controllata sulla frase (oggetti nominati,
    spostamento chiesto, argomento nominato), mostrata al giocatore tra parentesi
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
  `LLM_MODEL`, `LLM_LOG`, `LLM_LOG_FULL`, `COMMAND_LOG`. Se Ollama non risponde, il gioco avvisa e prosegue con i
  soli comandi semplici.
- Log delle chiamate (logger `app.llm`): il terminale lo scrive in `logs/llm.log` (esclusa da
  git; `LLM_LOG=off` per spegnerlo). Per ogni chiamata: messaggio inviato (`>>>`), risposta
  grezza (`<<<`), tempo e token di Ollama (anche quelli in cache), azione risultante o motivo del
  "non capito" (`===`). Il prompt di sistema solo quando cambia; lo schema no.
  Con `LLM_LOG_FULL=1` (2026-09-29) anche la richiesta esatta a Ollama, indentata come JSON e
  rimandabile con `curl`, e la sua risposta intera con i tempi (`load_duration`,
  `prompt_eval_duration`…): il logger passa a DEBUG e il client scrive quei due blocchi solo lì.
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
  main.py            # FastAPI: la pagina e tre endpoint (/api/adventures, /api/new, /api/turn)
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
  worlds/
    avventure.yaml   # le avventure del menu, nell'ordine in cui compaiono
    <id>/*.yaml      # un'avventura per cartella: stanze, oggetti, personaggi
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
  Mondo di esempio: la Rocca di Serravento in `data/worlds/rocca/`.

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
    pozzo). Un oggetto va **visto** prima di poterlo nominare: lo mostra la descrizione di un altro
    oggetto (`reveals`: esaminando il pozzo vedi la chiave), e `GameState.seen` se lo ricorda.
    Prima, "Non vedi niente del genere qui." e l'interprete non lo riceve. Poi parser e interprete
    lo ricevono dopo quelli a portata (`Engine.visible`); solo le regole agiscono su di lui, senza
    regola "Non ci arrivi.". `reveals` c'è solo sugli oggetti: sulle stanze si aggiungerà quando
    servirà ("in cima all'albero vedi un nido").
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
    Oggi è in `game.examples` della Rocca (`data/worlds/rocca/gioco.yaml`): il prompt è testa fissa
    + esempi del mondo + dialogo della cuoca, e `tests/prompt_rocca.txt` ne tiene la copia verificata.

- **Personaggi e dialoghi** (fase 6, 2026-09-25): sezione `characters` (formato in
  `docs/formato-mondo.md`), nella Rocca il pellegrino della scuderia (`data/worlds/rocca/personaggi.yaml`).
  - Si parla **per argomenti**, con testi d'autore: `parla con X` → `greeting`, `chiedi a X di Y`
    → testo dell'argomento, qualunque altra domanda → `unknown`. Scartate le risposte generate
    dal modello: con qwen2.5:3b su CPU tornerebbero i problemi del narratore.
  - Nell'`Action`, "chiedi" ha il personaggio come `target` e un campo `topic` (None: argomento
    che non conosce). Verbi in un enum a parte, `Conversation`: le regole non reagiscono.
  - Argomenti con `name` e `gender` (per "della torre"), `when` per nasconderli, `variants`,
    `effects` come le regole. Il pellegrino dà solo indizi: nessun effetto, niente scorciatoie
    (lo controlla `tests/test_castello.py`).
  - Nel prompt: le righe "Personaggi" e "Argomenti" solo se nella stanza c'è qualcuno; l'argomento
    va nel campo `con`, così lo schema della risposta resta lo stesso. "ciao" senza nessuno
    intorno: il modello risponde "parla", il gioco lo tratta come "altro".
  - Fuori da questa fase: personaggi che si spostano, dare o mostrare oggetti ("dai X a Y").

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
  - Prossimi pezzi: «dai X a qualcuno» (2), poi il draghetto raffreddato per bambini (3).

- **«dai X a qualcuno»** (fase 7, pezzo 2, 2026-09-26): verbo `dai` sugli oggetti; nella regola
  `target` è l'oggetto e `with` il personaggio. Si dà solo ciò che si porta, a un personaggio
  presente; «dai X» va all'unico presente. Senza regola risponde `refuses` del personaggio (o
  «Non sa che farsene.») e lo stato non cambia; un `dai` interpretato non chiede conferma.
  Nella Rocca nessuna regola `dai`: il pellegrino rifiuta.

- **Il draghetto raffreddato** (fase 7, pezzo 3, 2026-09-26): avventura per bambini dagli 8 anni in
  `data/worlds/draghetto/`, solo dati. Cinque luoghi intorno alla radura, tre enigmi (le more
  all'orso per il miele, il ramo per la piuma nel nido, prima il miele e poi la piuma al drago),
  il draghetto che dà indizi sempre più precisi, qualche regola-indizio per i regali sbagliati.
  Le uscite chiuse con un indizio portano a stanze in cui non si entra mai (`sentiero`, `chioma`),
  chiamate come le scrive un bambino («Casa», «Albero»): così «vai a casa» e «vai sull'albero»
  ricevono l'indizio col solo parser. Per lo stesso motivo i luoghi si chiamano «Quercia» e «Tana»:
  il parser vuole tutte le parole del nome. Testi senza aggettivi che diano un genere al giocatore.

- **Interprete più robusto, seconda parte** (2026-09-28, branch `interprete-robusto`): giocate le
  due avventure col modello vero e rilette le partite in `logs/comandi.jsonl`; le 44 frasi
  sbagliate (6 trovate dalla revisione) sono ora `test_sentences_found_while_playing` in
  `tests/test_ollama.py`.
  - Il modello sceglie da elenchi e, senza niente di adatto, sceglie a caso («mangio una mora» →
    prendi il sasso; «a cosa mi serve questa corda?» legava il gancio alla corda: enigma risolto da
    una domanda). Istruzioni ed esempi non bastavano: la risposta si **controlla sulla frase**
    (`interpreter._checked`). Un oggetto vale solo se la frase lo nomina (`parser.is_named`: nome o
    alias, anche con un'altra desinenza o, da cinque lettere, un errore di battitura che non tocchi
    la prima lettera: «lancio» non è «gancio»); un personaggio presente vale anche senza nome, ma
    solo per dai/usa e con un oggetto («gli do il miele»). Uno spostamento deve avere un verbo di
    moto (`MOVE_WORDS`), una direzione (non con una lettera sola: «e» è anche "e") o il nome proprio
    del luogo: un alias da solo non basta («mangio una mora» non va al roveto); poi vince la strada
    che la frase nomina, la sua direzione («salgo sul sasso»: su) o l'unica uscita nominata
    («attraverso il ponte»). Un argomento nominato vince su quello scelto; tra più argomenti,
    l'ultimo nominato («cosa serve per prendere la piuma?»).
  - Gioco (`game.py`), invece di «Non ho capito» o di una conferma sbagliata: «Non vedi niente del
    genere qui.» (nomina un oggetto che non è qui, se il nome non indica anche una cosa presente:
    «corda» è anche il rampino), «Non vedi nessuno del genere qui.» per ogni azione su chi è
    presente se la frase nomina solo qualcuno che non c'è («ciao orso» nella radura, «do le more al
    drago» nella tana: prima lo scambio con l'orso partiva da solo), ma una domanda su un suo
    argomento resta una domanda («conosci l'orso?»), «Qui non c'è nessuno con cui parlare.», «Sei già
    qui.» («torno dal draghetto» nella radura), «Non ho capito.» per un luogo più lontano se la
    direzione scelta non è il primo passo verso di lui («vai a casa» dalla quercia, se il modello
    dice su); se lo è, resta la conferma («vai dall'orso» dalla radura: «Vuoi andare a ovest?»,
    la tana è oltre il ruscello). Una domanda non capita («…?», o che comincia con perché,
    cosa, come…) che nomina un argomento del personaggio presente diventa quella domanda («mi dai
    il miele?»); un saluto che nomina un argomento anche («chi sei?», con l'alias «chi sei»).
  - **Alias delle stanze** (`rooms.X.aliases`), anche chi o cosa ci si trova: il parser capisce
    «torna dal drago», «vado dall'orso», «vai alle scuderie» (con più verbi di moto: torna, vado,
    entra, ritorna…), l'interprete vede «ovest (Tana: orso, grotta)», la conferma degli spostamenti
    li accetta. Nel parser anche «salgo», «scendo», «arrampicati» e «ecco X» (dai; non «tieni»,
    che vuol dire anche tenere in mano). La validazione rifiuta nomi e alias fatti solo di
    articoli e preposizioni, che nominerebbero qualunque frase. Nel log dei comandi, per una frase
    non capita, il dettaglio dice anche cosa ha risposto il gioco se non è «Non ho capito».
  - Prompt: solo l'esempio «a cosa serve questa chiavetta?» → esamina e tre ritocchi al glossario
    (ringraziare, leggi, ecco/tieni). Scartato un prompt più ricco (esempi di dialogo «ecco il
    mestolo», «grazie, arrivederci», gli alias spiegati nelle uscite): una frase nuova in più, ma
    di nuovo «butta/getta il rampino» sul portone e «come si esce» senza argomento.
  - Limiti noti (`KNOWN_LIMITS`, xfail): «busso alla porta», «sfondo la porta a calci», «afferra la
    ciave nel pozzo», «ti faccio il solletico… con la piuma», «guardo su nell'albero», e «aggancia
    la corda alla vera», che cambia da un giro all'altro. Nessuno cambia la partita: al massimo il
    gioco chiede conferma, dice «Non ho capito» o fa un'azione innocua («lascia la porta»: «Non ce
    l'hai.»). Scelto anche: «tieni, è per te» senza nominare
    l'oggetto non si capisce più (prima il modello indovinava, come indovinava a caso negli altri casi).

- **Difetti di testo trovati giocando** (2026-09-28, branch `difetti-di-testo`): le risposte del
  motore che si riferiscono all'oggetto si accordano col plurale («Ce le hai già.» per le more,
  «Non si possono prendere.» per i cespugli: `_PLURAL` in `engine.py`); i personaggi hanno
  `greeting_variants`, come le `variants` (l'orso dopo lo scambio non chiede più «chi va là?»);
  il ceppo della cucina è un arredo. Un oggetto nuovo nel mondo fa ricominciare una volta le
  partite salvate nel browser (`Engine.restore`).
- **Testi che seguono la partita** (2026-09-28, branch `testi-e-progressi`): anche il testo di
  un'uscita chiusa ha le sue varianti (`otherwise_variants`: salire sulla quercia col nido già
  vuoto). Nel draghetto il saluto dopo il miele, la quercia e le more chieste al draghetto,
  descrizione e more dell'orso dopo lo scambio; nella Rocca la cucina non promette più attrezzi
  sul ceppo (gli oggetti presenti li elenca il motore). Regola per chi scrive: un indizio che
  manda a fare qualcosa ha una variante per quando è fatto.
- **Pericoli** (2026-09-28, branch `pericoli`): nella Rocca chi salta nel pozzo muore e la partita
  finisce. Una morte è un finale come gli altri: la regola `salto_nel_pozzo` attiva
  `caduto_nel_pozzo`, e il finale con quel flag chiude con «Sei morto.». Nuovo verbo `salta`
  (saltare dentro qualcosa; senza regola «Non succede niente.»), che il parser riconosce da salta,
  salto, tuffati, buttati, gettati e lanciati. Nel glossario del prompt: `- salta: saltare, tuffarsi o
  buttarsi dentro qualcosa`. Un salto interpretato può uccidere, quindi ha due protezioni:
  - con un altro oggetto nominato, o scelto dal modello, è un lancio e diventa `usa` («lancio il
    rampino nel pozzo»);
  - senza una parola da salto (`JUMP_WORDS` in `interpreter.py`), il gioco chiede «Vuoi saltare nel
    pozzo?» («entro nel pozzo»).
  
  Un salto su un personaggio non si capisce. Nel terminale, a fine partita, vinta o persa, il gioco
  chiede «Vuoi giocare ancora?» e torna al menu. «Scendi nel pozzo» resta «giù», senza uscita:
  calarsi non è saltare. L'aiuto non elenca «salta», per non suggerire il pericolo.
  Col modello vero la riga nuova ha rotto due frasi, riparate senza toccare il prompt:
  - «salgo sul sasso» diventava `salta`: un salto senza parola da salto ma con una direzione
    («salgo», «scendo») torna uno spostamento;
  - «chiedo al vecchio come si esce da qui» perdeva l'argomento (3 volte su 3; col prompt di prima
    3 su 3 giuste): l'argomento `portone` del pellegrino ha gli alias `esce` e `uscire`.
- **Motore per Valdimora** (2026-09-29, branch `feature/inizia_l_Avventura`; spec in
  `docs/superpowers/specs/2026-09-29-valdimora-design.md`, piano in
  `docs/superpowers/plans/2026-09-29-motore-valdimora.md`): tre aggiunte, nessuna al prompt.
  - Personaggi che si spostano con le condizioni (`moves`, `Engine.character_room`).
  - Atti (`game.acts`) e morti (`death: true` nei finali): quando comincia un atto il motore tiene
    da parte lo stato (`GameState.checkpoint`, con `act` e `lost`), e dopo una morte si riprende da
    lì (`Engine.resumable`/`resume`). Nel web con «riprendi» (campo `resumable` nella risposta di
    `/api/turn`, avviso scritto dalla pagina), nel terminale con «Vuoi riprendere dall'inizio del
    secondo atto? (s/n)». Una partita finita non chiama più l'LLM. Il pozzo della Rocca è una
    morte, ma senza atti si ricomincia da capo.
  - Le regole hanno anche `otherwise_variants`, come le uscite.
- **Valdimora, atto 1** (2026-09-29, branch `feature/valdimora-atto-1`; piano in
  `docs/superpowers/plans/2026-09-29-valdimora-atto-1.md`): il pianterreno in `data/worlds/valdimora/`
  (`gioco.yaml`, `pianterreno.yaml`, `personaggi.yaml`), nel menu con un finale provvisorio sul flag
  `atto_due` (aprendo la porta dello scalone). La Loggia dello scalone è provvisoria. Oggetti degli
  atti futuri già piantati (forbici, tanica, fiammiferi, rosaio, porta della cantina).
  - Nomi propri: campo `article` su oggetti, personaggi e argomenti (`none`: «Ettore», «a Ettore»,
    «Qui c'è Agnese»; `definite`: «il dottor Ferri», mai «un dottor Ferri»). «ad» tra le parole che
    il parser ignora («dai il medaglione ad Agnese»).
  - Col modello vero, 17 frasi libere del pianterreno: 13 al primo giro. Le altre hanno mostrato
    difetti generali, corretti nel codice (il prompt non cambia): un alias che appartiene a un solo
    oggetto vale come il suo nome («grappa» per «bottiglia di grappa»: il modello a volte risponde
    con l'alias); leggere ed esaminare non hanno strumento, quindi l'oggetto nominato che il modello
    ha messo come strumento è quello letto («leggo il biglietto della contessa»); «inventario» con un
    oggetto nominato come bersaglio è un esame («frugo nella borsa del dottore»); un nome contenuto
    in quello di una cosa presente non vale come «altrove» («biglietto» in «biglietto della
    contessa»). E uno strumento che la frase non nomina, quando la frase nomina un solo altro
    oggetto, diventa un'**ipotesi** (`NotUnderstood.guess`): il gioco chiede «Vuoi usare il
    medaglione con la meridiana?» e la fa solo dopo un sì, perché anche una domanda nomina le cose
    («cosa c'è scritto sul biglietto, Livia?» dava la chiave dello scalone). «mostro/faccio vedere la
    lettera a Ettore» diventa una domanda sulla lettera, e Ettore chiede di vederla.
  - Parser: un nome non scavalca «con» (anche «col», «coi») se non lo contiene: «usa la chiave con la
    credenza» erano la sola «chiave della credenza»; «corda con gancio» della Rocca lo scavalca.
  - Dopo la revisione finale: la meridiana si apre solo dopo aver letto la busta (prima si saltava
    Ettore e la rivelazione); chi ha già la chiave si sente dire «usala», una chiave sbagliata «non
    entra»; il dottore addormentato non parla da sveglio; tutto ciò che le descrizioni nominano si
    esamina. Tolto un alias pericoloso: «leggio», che la tolleranza ai refusi faceva nominare da
    «leggo». Nella spec, gli indizi piantati nel primo atto da pagare dopo (il campanello col filo
    tagliato, la luce sotto il tetto, le lenzuola «A. V.»).
- **Dialoghi più naturali** (2026-09-30, branch `feature/dialoghi`; spec in
  `docs/superpowers/specs/2026-09-29-dialoghi-design.md`, piano in
  `docs/superpowers/plans/2026-09-29-dialoghi.md`): l'LLM resta solo interprete (un personaggio
  interpretato dal modello è stato scartato per gli stessi motivi del narratore; una prova di
  riformulazione è rimandata). Sette gesti sociali (saluto, congedo, grazie, scuse, come stai, chi
  sei, scortesia) con testi d'autore per gli otto personaggi (`Character.gestures`, risposte neutre
  di riserva); il parser riconosce le formule brevi, l'interprete le frasi libere con «parla» e il
  gesto in `con`. Il gioco ricorda cosa si è chiesto a chi (`GameState.asked`) per `again`, e
  l'ultimo interlocutore (`last_speaker`), a cui vanno gesti, domande e regali senza nome; è l'unica
  cosa che cambia anche con un'azione rifiutata. A Valdimora le opinioni reciproche (Agnese e
  Corrado si difendono a vicenda). «chiedi a Livia di Corrado» non prende più un argomento a caso.
  - Col modello vero, con «parla» qwen2.5:3b risponde «saluto» a quasi ogni gesto (5 frasi libere
    su 18 al primo giro). Riparato nel codice, il prompt non cambia più: le parole della frase
    decidono il gesto (`parser.gesture_said`: «perdonatemi», «chi siete», «addio», un insulto;
    l'ultimo detto vince), un'azione senza senso («dai» o «usa» senza oggetto) diventa il gesto
    che la frase dice, un congedo senza direzione né luogo non è uno spostamento («adesso vado, ci
    vediamo più tardi»). Poi 17 su 18; limite noto «siete una vecchia strega» («vecchia» è quasi
    «vecchio», alias di Ettore). «chi era il castellano?» ora dà «esamina il pellegrino», ma il
    turno risponde giusto (la domanda nomina l'argomento): il test è passato sul turno intero.
  - Dalla revisione finale: una domanda che nomina un argomento vince su qualunque gesto («scusate,
    cosa sapete della contessa?»); un insulto conta solo rivolto a qualcuno («sei…», «siete…», o poco
    più dell'insulto: «i draghi cattivi sputano fuoco?» è una domanda); con più personaggi e nessun
    nome né ultimo interlocutore presente, gesti e domande ricevono «A chi?» (`parser.ToWhom`,
    `NotUnderstood.to_whom`).
  - Minori della revisione (2026-09-30, branch `feature/dialoghi-minori`): la conferma di
    un'ipotesi viene prima del gesto detto; «chiamate il dottore» non è «chi sei» (solo «ti
    chiami», «vi chiamate», «tuo/vostro/suo nome»); una formula senza nessuno presente riceve
    «Qui non c'è nessuno con cui parlare.» dal parser; una domanda che non nomina argomenti ma dice
    un gesto è quel gesto («chiedi al pellegrino del suo nome», «chiedi scusa al custode»); l'orso,
    dopo lo scambio, ringrazia per le more. Lasciati: «chi era il castellano?» dall'interprete da
    solo (servirebbe ritoccare il prompt, il turno risponde giusto) e `engine.py` che usa `definite`.
- **Valdimora, atto 2** (2026-09-30, branch `feature/valdimora-atto-2`; decisioni nella spec,
  «Atto 2: decisioni prese al momento di costruirlo»; piano in
  `docs/superpowers/plans/2026-09-30-valdimora-atto-2.md`): il piano nobile in
  `data/worlds/valdimora/piano-nobile.yaml` (13 stanze e una provvisoria in cima alla scala di
  servizio), nel menu con un finale provvisorio sul flag `atto_tre`. Il primo `acts` («secondo
  atto», su `atto_due`): si muore cadendo dal balcone e si riprende dall'inizio dell'atto. Ettore,
  Livia, Corrado e Agnese salgono di sopra (`moves`), Ferri resta nel biliardo con la sua borsa; i
  loro testi seguono il posto e la partita. Le chiavi usate restano nella serratura. Tolti alcuni
  alias di una parola simili a parole comuni, per la tolleranza ai refusi («sete»/«siete»,
  «annate»/«andate», «cera»/«cerca», «cappelli»/«cappella»; poi la lista `COMMON_WORDS`, vedi sotto).
  Dati e test provati prima su una copia del mondo.
  - Col modello vero 142 su 150; gli altri 8 sono limiti noti. Trovati giocando: un oggetto dato dal
    modello per nome e per alias («bastone dal manico ricurvo», «bastone») mandava in errore il gioco
    (ora è un oggetto solo); prendere ciò che si ha già in mano, mentre la frase nomina un'altra sola
    cosa qui, diventa l'ipotesi «Vuoi usare la chiavetta di carica con il carillon?»; limite noto
    «infilo il medaglione nella cornice» (il modello dice «inventario», a volte «prendi», e allora il
    gioco chiede). Limite accettato: nella loggia «vado nel salone» da solo può dare «Sei già qui.»
    («salone» è quasi «scalone», alias della loggia).
  - Dalla revisione finale: un'azione capita dal modello che finirebbe con una morte viene chiesta
    prima («Vuoi spingere la balaustra?», `Game._would_kill`; i salti hanno già la loro regola); col
    bastone in mano prendere il vaso dà un indizio; tolti gli alias «fiori» (anche dei gigli
    dell'atto 1) e «conte», simili a «fuori» e «conti».
  - Minori della revisione (2026-10-01, branch `feature/valdimora-atto-2-minori`):
    - Le parole comuni non sono mai refusi (`parser.COMMON_WORDS`): «ho sete», «mi metto in mezzo»,
      «spegni la candela», «è il nostro segreto» non nominano più «seta», «mazzo», «segni», «nastro»
      (rispondevano «Non vedi niente del genere qui.»). Fuori dalla lista le parole che nominano con
      un'altra desinenza («esco» è «esce», l'argomento del pellegrino). «Altrove» si confronta sulle
      parole della frase: «accarezzo i velluti» nel boudoir non è il «velluto» del drappo. Con
      «vecchia» nella lista, «siete una vecchia strega» non è più un limite noto.
    - Le varianti di saluti, gesti e argomenti hanno il loro `again` (`SaidVariant`): prima una
      variante vinceva sempre e si ripeteva («Ce l'avete fatta!» a ogni saluto di Agnese); senza
      `again` si ripete, come «Il dottor Ferri russa.». Agnese, visto il medaglione, non lo chiede più.
    - Indizi con la variante «già fatto» (Corrado e il bastone, Livia e la scala di servizio, lo
      scalone, Ettore e il carillon, «su» con la chiave in tasca: «usala»); «chi è questa ragazza?»
      è il ritratto; «tira il cordone», «spingi il vaso», «salta nella valle» (una caduta); la
      boccetta sveglia per un momento il dottore addormentato. Riprendere ciò che si ha in mano
      «dal portagioie» non è più l'ipotesi «Vuoi usare…?».
    - Col modello vero «Ettore, chi è questa ragazza?» era «esamina il ritratto» (anche il ritratto ha
      l'alias «ragazza»): una domanda che nomina un solo personaggio presente e un suo argomento è
      quella domanda anche se il modello dice «esamina»; senza il nome resta l'esame.
    - Dalla revisione: uno sguardo non è un salto («lancio uno sguardo verso la valle», «getto
      un'occhiata»: con «sguardo», «occhiata», «occhio» un salto interpretato è un esame), altrimenti
      dal balcone si moriva subito. Lasciati: «morto» resta nella lista (non nomina più l'argomento
      «morte»); «ragazza» per Ettore è il ritratto anche se si parla di Agnese; un'ipotesi inutile se
      tra «da» e il nome c'è altro («dal fondo del portagioie»); «usa la boccetta col dottore» non
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
  - Dalla revisione finale: la trave sotto il lucernario è un arredo, e la corda si lega anche a
    lei («lego la corda alla trave»; un alias «trave» sul lucernario cambiava le risposte del
    modello e rompeva due frasi); nel terzo atto Livia non ha più le chiavi alla cintura, Ettore sa
    dov'è Agnese quando è di sotto e il suo indizio sulla lanterna la segue. Niente alias «tè» per
    la tisana: senza accento è «te». Rimandati: testi che invecchiano andando avanti nell'atto
    (Livia dopo la confessione, Corrado sull'eredità dopo le lettere, Agnese che si offre di
    scendere quando è già di sotto), «tetto» e «pioggia» nella stanza dell'orologio, gli alias
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
  - Dalla revisione finale: «tetro», «tento», «testo» sono parole comuni (col tetto nuovo «che
    posto tetro!» rispondeva «Non vedi niente del genere qui.» ovunque); una domanda non capita che
    due personaggi presenti sanno va a quello nominato, altrimenti «A chi?» («dove trovo il
    petrolio?» in cucina con Ettore e Agnese); Agnese non promette la tisana già bevuta né il
    petrolio già preso, e Corrado nell'archivio parla dello studio come di un altro posto; la corda
    si lega anche «al tetto». Lasciati: «(salta nel tetto)» (i salti hanno sempre «in»), due
    ritocchi di testo («farlo trent'anni fa» di Livia, la corda che «pende fin lassù»); le partite
    salvate nel terzo atto ricominciano (c'è un oggetto nuovo).
  - Limiti accettati: nello stenditoio e nel cortile «esamina il tetto» risponde «Non vedi niente
    del genere qui.» (è il tetto visto dalla stanza dell'orologio); «Agnese, mi date la tisana?» è
    un «dai» senza oggetto, come prima; «lego la corda al tetto» non è capita (il modello risponde
    «leggi la trave con la corda», e la frase non nomina la trave; così anche su main).

## Decisioni ancora aperte
- Mostrare oggetti ai personaggi («mostra X a Y»): per ora nessun enigma lo chiede.
- Hosting pubblico (es. PC di casa + Cloudflare Tunnel) — non prioritario.

## Comandi utili
```
# ambiente: Python 3.12 installato per l'utente (launcher `py`), ambiente virtuale in .venv
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install "pydantic>=2.11" "pyyaml>=6" "httpx>=0.27" "fastapi>=0.115" "uvicorn>=0.30" "pytest>=8"
.venv\Scripts\python -m pytest

.venv\Scripts\python -m app.cli      # giocare nel terminale: prima il menu delle avventure (con Ollama acceso, anche frasi libere)
$env:LLM="off"                       # giocare senza LLM

$env:OLLAMA_TESTS=1; .venv\Scripts\python -m pytest tests/test_ollama.py -v -s   # test col modello vero

ollama pull qwen2.5:3b
.venv\Scripts\python -m app.main          # giocare nel browser: http://127.0.0.1:8000

.venv\Scripts\python prove-modelli/prova.py --model qwen2.5:7b   # un altro modello sulle 60 frasi più difficili (prove-modelli/README.md)
```


### Risultati dei test (qwen2.5:3b su CPU, Windows)
- Ambiente di sviluppo: Windows, PowerShell.
- Velocità misurate: generazione ~6-7 token/s, lettura prompt ~30 token/s.
  Con la parte fissa del prompt in testa, Ollama la tiene in cache (dal log: ~460 token su ~470
  già in cache): il grosso del tempo è generare i 25-30 token della risposta JSON.
- Interprete (fase 4): 4-7 s per frase; la prima chiamata 15-20 s (caricamento del modello,
  poi tenuto in memoria con `keep_alive: 30m`). `tests/test_ollama.py`: 25 su 25.
  - Output strutturato con `format` (schema JSON), `temperature: 0`, `num_predict: 60`, `num_ctx: 2048`.
  - Campi: `verbo`, `bersaglio` (su cosa si agisce; per "vai" la direzione), `con` (cosa si usa;
    "nessuno" se assente; con "chiedi" l'argomento). Enum generati a ogni turno: verbi del
    motore + `altro` (non è un'azione); nomi degli oggetti a portata o in vista e dei personaggi
    presenti + direzioni + `nessuno`; in `con` anche gli argomenti.
  - Nel prompt: glossario dei verbi (senza, il modello usava "usa" per quasi tutto), oggetti con
    gli alias tra parentesi (senza, confondeva "porta" con "portone"), esempi su un mondo
    inventato, poi quello del rampino, poi un dialogo con la cuoca.
  - Scambiare bersaglio e strumento non è un problema: le regole accettano i due oggetti in
    qualunque ordine.
  - Frasi con lo scopo ("usa il rampino per recuperare la chiave dal pozzo"): senza esempio il
    modello ripiega su un oggetto a caso, spesso il portone, anche con la chiave nell'enum.
    Aggiungere istruzioni non aiutava; un esempio generico (baule e monete) nemmeno. L'esempio
    del rampino ripara la frase e le sue varianti.
  - "butta/getta il rampino nel pozzo": il modello risponde `lascia` con i due oggetti giusti,
    anche spostando "buttare" sotto `usa` nel glossario (e "lancia la corda nel pozzo"
    peggiorava). Ripara l'interprete: `lascia X con Y` diventa `usa X con Y`, perché buttare una
    cosa in un'altra è usarle insieme. "vai in cucina" dalla scuderia (la cucina è oltre il
    cortile) diventa "ovest": lo ferma la conferma sugli spostamenti.
  - Il modello è fragile: ogni riga in più nel prompt sposta altri casi. Con l'esempio del rampino
    (in fondo o dentro il blocco di esempi) "vado nella cantina" va a ovest: da qui la conferma
    sugli spostamenti non nominati. Mettere la chiave in vista nell'enum, senza l'esempio, rompeva
    invece "cala il rampino giù nel pozzo". Ogni modifica al prompt va verificata su tutto
    `tests/test_ollama.py` (oggi 183 su 191, ~2040 s: i 36 casi di prima, gli 8 dei pericoli, i 17
    del primo atto di Valdimora, le 20 frasi dei dialoghi e le 24 del terzo atto tutti, 11 delle 12
    dei suoi minori, 28 delle 29 frasi del secondo atto e 39 delle 45 frasi trovate giocando; le
    altre 8 sono limiti noti, e «infilo il medaglione nella cornice» a volte passa).
  - Il modello non è del tutto deterministico: con lo stesso prompt e `temperature: 0`, 2 o 3 frasi
    su 70 cambiano risposta da un giro all'altro (la cache di Ollama?). Un caso che passa una volta
    sola non dimostra niente.
  - Dialoghi (fase 6): senza l'esempio del dialogo, "chi era il castellano?" diventava "altro";
    con l'esempio prima di quello del rampino, "getta il rampino nel pozzo" andava al portone.
    In fondo funziona tutto. Con il dialogo nel prompt, "vai in cucina" dalla scuderia risponde
    "nessuno" (quindi "Non ho capito.") invece di "ovest". Per provare varianti del prompt senza
    toccare il codice basta sostituire in uno script `interpreter.interpreter_system`, oppure le
    costanti `_HEAD` e `_DIALOGUE` di `app/llm/prompts.py`.
  - «dai» (fase 7): è bastata la riga `- dai: dare, porgere, offrire un oggetto a un personaggio`
    dopo `chiedi` nel glossario, senza esempi: 28 su 28 al primo giro, e «dai un'occhiata al
    pozzo» resta un esame. Spesso il modello mette il personaggio in `bersaglio` e l'oggetto in
    `con` («offri la corda al vecchio»): nessun problema, il motore riconosce chi è il personaggio.
  - Draghetto (fase 7): senza esempi 8 frasi su 9; «salgo sull'albero» andava a sud (il modello
    confondeva «su» con «sud»). Con un esempio della scala («salgo in cima alla scala» → su)
    «stacco la piuma col bastone» perdeva lo strumento; aggiungendo quello della mela fatta cadere
    col bastone, 9 su 9. Gli esempi stanno in `game.examples` del draghetto, quindi il prompt della
    Rocca non cambia. «dai un'occhiata al draghetto» resta un esame, anche col draghetto presente.
- Narratore: provato e scartato (vedi sopra), anche con temperatura 0.2 e senza descrizioni.