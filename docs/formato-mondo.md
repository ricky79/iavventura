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

## `items`

```yaml
items:
  gancio:
    name: gancio da macellaio    # nome canonico: unico in tutto il mondo
    aliases: [gancio, uncino]    # altri nomi; possono coincidere con quelli di altri oggetti
    description: Testo mostrato quando lo si esamina.
    location: cucina             # una stanza, inventory, oppure null
    scenery: false               # true = arredo: non si prende e non viene elencato
    variants: []                 # come per le stanze
```

- `location: inventory`: l'oggetto parte nelle mani del giocatore.
- `location: null`: l'oggetto parte **fuori gioco** ed entra solo tramite un effetto `give` o
  `place` (per esempio il risultato di una combinazione).
- Gli alias possono ripetersi: dopo la combinazione, "corda" deve indicare la corda con gancio.
  Il motore sceglierà in base a ciò che il giocatore ha a portata.

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

- `verb`: uno fra esamina, prendi, lascia, usa, apri, chiudi, spingi, tira, leggi
  (elenco provvisorio, da confermare con lo schema dell'Azione).
- `target` e `with` sono id di oggetti; `with` è facoltativo.
- Una regola senza effetti è una semplice risposta. Serve per gli indizi, come calare nel pozzo
  la corda senza gancio.

**Come le userà il motore** (fase 2, da confermare quando lo scriveremo):
- `target` e `with` valgono in qualunque ordine: "usa corda con gancio" = "usa gancio con corda";
- una regola senza `with` scatta solo per azioni senza strumento;
- gli oggetti del trigger devono essere a portata: nell'inventario o nella stanza;
- vale la prima regola che corrisponde. Se il suo `when` è falso si mostra `otherwise`, oppure
  una risposta generica del motore.

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
  stanze irraggiungibili dall'inizio; nomi canonici duplicati (maiuscole comprese).

## Stato della partita

`GameState` (in `models.py`) contiene tutto ciò che cambia durante la partita: stanza corrente,
posizione di ogni oggetto, flag attivi, stanze visitate, turni, fine partita.
`GameState.new(world)` crea lo stato iniziale, che si salva e rilegge in JSON.
Il mondo invece è immutabile.
