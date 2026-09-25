# Formato del mondo (YAML)

Guida per chi scrive stanze, oggetti ed enigmi. I modelli che la applicano sono in
`app/engine/models.py`; i controlli tra le varie parti sono in `app/engine/validation.py`.
L'esempio completo è la Rocca di Serravento in `data/world/`.

## File

- Il mondo sta in `data/world/*.yaml`. Il loader legge tutti i file e ne unisce le sezioni.
- Sezioni ammesse: `game`, `rooms`, `items`, `rules`. Un file può contenerne quante vuole e
  una sezione può continuare in più file. La divisione attuale (gioco, stanze, oggetti,
  regole) è solo una convenzione.
- `game` compare una sola volta. Lo stesso id non può essere definito in due file.

## Id, chiavi e testi

- Ogni stanza, oggetto e regola è identificato dalla sua **chiave**, cioè l'id: minuscole,
  cifre e `_`, iniziale una lettera (`chiave_torre`). Non si scrive un campo `id`.
- Chiavi dello schema in inglese (`description`, `exits`…); id, testi e direzioni in italiano.
- Nessun campo sconosciuto è ammesso: un refuso come `descripton` è un errore.
- Testi lunghi: meglio lo stile `>` di YAML, che permette anche i due punti nel testo.
- Attenzione: in YAML una chiave scritta `on`, `off`, `yes` o `no` senza virgolette diventa un
  booleano. Il loader la rifiuta segnalando file e riga.

## `game`

```yaml
game:
  title: La Rocca di Serravento
  intro: Testo mostrato all'inizio.
  start_room: cortile
  endings:                 # almeno uno; vale il primo la cui condizione è vera
    - when: {player_in: torre}
      text: Testo finale.
```

## `rooms`

```yaml
rooms:
  cortile:
    name: Cortile
    description: Testo della stanza. Cita gli arredi, non gli oggetti trasportabili.
    variants:                # facoltativo: la prima valida sostituisce description
      - when: {flag: torre_aperta}
        text: Testo alternativo.
    exits:                   # nord, sud, est, ovest, su, giù
      ovest: {to: cucina}
      nord:
        to: torre
        when: {flag: torre_aperta}              # facoltativo: senza, l'uscita è sempre libera
        otherwise: La porta è chiusa a chiave.  # mostrato se la condizione è falsa
```

Le uscite sono a senso unico: per tornare indietro serve l'uscita opposta nell'altra stanza.

**Andare in una stanza per nome.** Il giocatore può scrivere "vai in cucina" invece di "ovest"
se conosce la stanza di destinazione: l'ha già visitata, oppure la descrizione che sta leggendo
la nomina (tutte le parole del nome, esclusi articoli e preposizioni: "Sala del trono" richiede
sia "sala" sia "trono"). Le stanze mai viste e mai nominate restano sconosciute, così un nome
indovinato non rivela dove si trovano. Consiglio per chi scrive: nelle descrizioni nomina le
stanze vicine con il loro nome ("A ovest una porta bassa dà sulla cucina").

## `items`

```yaml
items:
  gancio:
    name: gancio da macellaio    # nome canonico: unico in tutto il mondo
    gender: m                    # genere del nome: m oppure f
    plural: false                # facoltativo: true per nomi plurali (attrezzi, chiavi)
    aliases: [gancio, uncino]    # altri nomi; possono coincidere con quelli di altri oggetti
    description: Testo mostrato quando lo si esamina.
    location: cucina             # una stanza, inventory, oppure null
    scenery: false               # true = arredo: non si prende e non viene elencato
    variants: []                 # come per le stanze
    visible_from:                # facoltativo: si vede da una stanza, ma non ci si arriva
      room: cortile
      when: {not: {flag: chiave_pescata}}   # facoltativo
    reveals: []                  # facoltativo: oggetti lontani che la sua descrizione mostra
```

- `location: inventory`: l'oggetto parte nelle mani del giocatore.
- `location: null`: l'oggetto parte **fuori gioco** ed entra solo tramite un effetto `give` o
  `place` (per esempio il risultato di una combinazione).
- `gender` e `plural` servono agli articoli, che il gioco calcola da solo con le regole
  dell'italiano: il gancio / un gancio, lo specchio / uno specchio, l'ascia / un'ascia,
  la corda / una corda, gli attrezzi / degli attrezzi.
- Il nome e gli alias si scrivono senza articolo: "gancio da macellaio", non "il gancio".
- Gli alias possono ripetersi: dopo la combinazione, "corda" deve indicare la corda con gancio.
- `visible_from`: l'oggetto **si vede ma non si raggiunge** (la chiave in fondo al pozzo). Dalla
  stanza indicata, finché la condizione è vera e l'oggetto non è a portata, il giocatore lo può
  nominare, e parser e interprete lo riconoscono, ma **solo dopo averlo visto** (vedi `reveals`):
  prima, il motore risponde "Non vedi niente del genere qui.". Solo le regole agiscono su di lui:
  senza una regola il motore risponde "Non ci arrivi.". Tipicamente l'oggetto parte fuori gioco
  e una regola lo consegna (`give`), attivando il flag che lo toglie dalla vista.
- `reveals`: gli oggetti lontani che la descrizione di questo oggetto mostra. Quando il giocatore
  lo esamina, li vede, e da allora può nominarli:
  ```yaml
  pozzo:
    reveals: [chiave_torre]    # esaminando il pozzo vedi la chiave in fondo
  ```
  Vale solo per la descrizione: una regola su "esamina" che la sostituisce non rivela niente.

**Come il parser riconosce gli oggetti.** Nel comando del giocatore articoli e preposizioni
(il, la, con, sul, nella…) vengono ignorati, e così anche nei nomi: "usa la corda con gancio
nel pozzo" confronta le parole "corda gancio pozzo". Il parser sceglie:
- prima gli oggetti **a portata o in vista**, e fra questi il nome o alias più lungo: se la corda con
  gancio è fuori gioco, "usa la corda con il gancio" indica la corda e il gancio separati;
- se due oggetti a portata rispondono alle stesse parole, chiede "Quale intendi: …?";
- un oggetto non a portata arriva al motore, che risponde "Non vedi niente del genere qui."
  (senza chiedere quale, per non svelare oggetti che il giocatore non ha ancora visto).

## `rules`

Una regola dice cosa succede quando il giocatore compie un'azione precisa.

```yaml
rules:
  pesca_chiave:
    trigger: {verb: usa, target: pozzo, with: corda_con_gancio}
    when: {not: {flag: chiave_pescata}}         # facoltativo
    otherwise: Nel pozzo non c'è più niente.    # facoltativo: se when è falso
    effects:
      - give: chiave_torre
      - set_flag: chiave_pescata
    text: Testo dell'esito.
```

- `verb`: uno fra esamina, prendi, lascia, usa, apri, chiudi, spingi, tira, leggi.
- `target` e `with` sono id di oggetti; `with` è facoltativo.
- `trigger` può essere anche una **lista** di azioni equivalenti, quando lo stesso enigma si
  risolve in più modi. Ciascuna fa scattare la regola:
  ```yaml
  trigger:
    - {verb: usa, target: pozzo, with: corda_con_gancio}
    - {verb: prendi, target: chiave_torre, with: corda_con_gancio}
  ```
- Una regola senza effetti è una semplice risposta. Serve per gli indizi, come calare nel pozzo
  la corda senza gancio.

**Come le usa il motore:**
- gli oggetti dell'azione devono essere a portata, cioè nell'inventario o nella stanza (arredi
  compresi), oppure in vista (`visible_from`); altrimenti il motore risponde "Non vedi niente del
  genere qui.". Su un oggetto in vista agiscono solo le regole: senza, "Non ci arrivi.";
- `target` e `with` valgono in qualunque ordine: "usa corda con gancio" = "usa gancio con corda";
- una regola senza `with` scatta solo per azioni senza strumento, e viceversa;
- vale la prima regola che corrisponde, nell'ordine dei file. Se il suo `when` è falso si mostra
  `otherwise` (oppure "Non succede niente.") e lo stato non cambia: le regole successive non
  vengono provate;
- **"usa X con Y"** è il verbo generico dei giocatori: se nessuna regola `usa` corrisponde, vale
  la prima regola di qualunque verbo sugli stessi due oggetti. Così "usa la chiave con la porta"
  fa scattare `apri: porta_torre con chiave_torre` senza scrivere una regola doppia;
- una regola **sostituisce** il comportamento predefinito del verbo (vedi sotto): una regola su
  "prendi X" che deve dare l'oggetto al giocatore lo fa con `give: X`.

**Senza regole**, i verbi fanno così (lo strumento, se c'è, viene ignorato):

| Verbo | Comportamento predefinito |
|---|---|
| esamina | mostra la descrizione dell'oggetto, con la variante valida |
| prendi | mette l'oggetto nell'inventario; rifiuta gli arredi e gli oggetti che hai già |
| lascia | posa l'oggetto nella stanza; rifiuta gli oggetti che non hai |
| apri, chiudi, leggi | "Non si può aprire." / "Non si può chiudere." / "Non c'è niente da leggere." |
| usa, spingi, tira | "Non succede niente." |

I messaggi del motore non nominano mai l'oggetto, così non servono articolo e genere.

**Azioni non previste.** Se una frase libera, interpretata dall'LLM, diventa un'azione a cui
nessuna regola reagisce (tranne esamina, prendi e lascia senza strumento, che fanno qualcosa da
sole), il gioco non la esegue subito ma chiede conferma: "Vuoi usare la corda con gancio con il
portone?". Il modello potrebbe aver frainteso. Lo stesso per uno spostamento interpretato verso
una direzione che la frase non nomina, né con la direzione né con la stanza in cui porta ("vado
in cantina" → "Vuoi andare a ovest?"). Le azioni scritte con i comandi semplici si eseguono
senza domande. Per chi scrive: le azioni che i giocatori tenteranno davvero meritano una
regola, anche solo un indizio.

## Condizioni

Usate in `when` di uscite, varianti, regole e finali. Ogni condizione ha **una sola chiave**.

| Condizione | Vera quando |
|---|---|
| `{flag: nome}` | il flag è attivo |
| `{has: oggetto}` | l'oggetto è nell'inventario |
| `{player_in: stanza}` | il giocatore è in quella stanza |
| `{all: [c1, c2]}` | tutte le condizioni sono vere |
| `{any: [c1, c2]}` | almeno una è vera |
| `{not: c}` | la condizione è falsa |

Una lista equivale a `all`: `when: [{flag: a}, {has: chiave}]`.

## Effetti

| Effetto | Cosa fa |
|---|---|
| `{give: oggetto}` | porta l'oggetto nell'inventario, ovunque fosse |
| `{remove: oggetto}` | toglie l'oggetto dal gioco |
| `{place: {item: oggetto, room: stanza}}` | mette l'oggetto in una stanza |
| `{set_flag: nome}` / `{clear_flag: nome}` | attiva / disattiva un flag |

## Flag

Vero/falso, tutti falsi a inizio partita, senza dichiarazione. Un flag letto in una condizione
deve essere attivato da almeno un `set_flag`: così i refusi vengono scoperti al caricamento.

## Controlli al caricamento

Tutti gli errori vengono raccolti e mostrati insieme, ciascuno con il percorso
(`rooms.cortile.exits.nord.to: unknown room 'torree'`) oppure con file e riga per quelli YAML.

- YAML: sintassi, chiavi duplicate, chiavi non testuali, id duplicati tra file, `game` unico.
- Struttura: campi sconosciuti o mancanti, tipi, id, direzioni, verbi, condizioni ed effetti.
- Riferimenti: stanza iniziale, uscite, posizioni, oggetti e stanze citati in trigger,
  condizioni ed effetti devono esistere; `inventory` non può essere l'id di una stanza.
- Coerenza: flag letti ma mai attivati; oggetti fuori gioco che nessun effetto fa entrare;
  oggetti con `visible_from` che nessun `reveals` mostra; stanze irraggiungibili dall'inizio;
  nomi canonici duplicati (maiuscole comprese).

## Stato della partita

`GameState` (in `models.py`) contiene tutto ciò che cambia durante la partita: stanza corrente,
posizione di ogni oggetto, flag attivi, stanze visitate, oggetti lontani già visti, turni, fine
partita.
`GameState.new(world)` crea lo stato iniziale, che si salva e rilegge in JSON.
Il mondo invece è immutabile.

Solo il motore (`app/engine/engine.py`) modifica lo stato. Ogni azione, anche se rifiutata,
conta come un turno; dopo ogni azione il primo finale la cui condizione è vera chiude la
partita. Le uscite chiuse mostrano il loro `otherwise`, oppure "Non puoi andare da quella parte."
