# Formato del mondo (YAML)

Guida per chi scrive stanze, oggetti ed enigmi. I modelli che la applicano sono in
`app/engine/models.py`; i controlli tra le varie parti sono in `app/engine/validation.py`.
Gli esempi completi sono la Rocca di Serravento (`data/worlds/rocca/`) e il draghetto raffreddato
(`data/worlds/draghetto/`), che usa anche `dai` e le uscite chiuse con un indizio.

## File

- Ogni avventura sta in una cartella `data/worlds/<id>/`: l'id è il nome della cartella. Il loader
  legge tutti i file `.yaml` della cartella e ne unisce le sezioni.
- `data/worlds/avventure.yaml` elenca le avventure nell'ordine del menu (`adventures: [rocca]`).
  Una cartella che non è nell'elenco non viene caricata: così se ne può preparare una senza
  mostrarla. Gli errori di un'avventura portano il suo id davanti (`rocca: items.pozzo: …`).
- Sezioni ammesse: `game`, `rooms`, `items`, `rules`, `characters`. Un file può contenerne quante
  vuole e una sezione può continuare in più file. La divisione attuale (gioco, stanze, oggetti,
  regole, personaggi) è solo una convenzione.
- `game` compare una sola volta. Lo stesso id non può essere definito in due file.

## Id, chiavi e testi

- Ogni stanza, oggetto, regola e personaggio (e ogni argomento di un personaggio) è identificato
  dalla sua **chiave**, cioè l'id: minuscole, cifre e `_`, iniziale una lettera (`chiave_torre`).
  Non si scrive un campo `id`.
- Chiavi dello schema in inglese (`description`, `exits`…); id, testi e direzioni in italiano.
- Nessun campo sconosciuto è ammesso: un refuso come `descripton` è un errore.
- Testi lunghi: meglio lo stile `>` di YAML, che permette anche i due punti nel testo.
- Attenzione: in YAML una chiave scritta `on`, `off`, `yes` o `no` senza virgolette diventa un
  booleano. Il loader la rifiuta segnalando file e riga.

## `game`

```yaml
game:
  title: La Rocca di Serravento
  summary: Una o due righe per il menu delle avventure.
  examples: |-             # facoltativo: esempi per l'interprete LLM (vedi sotto)
    Oggetti: …
  intro: Testo mostrato all'inizio.
  start_room: cortile
  acts:                    # facoltativo: le parti del gioco, in ordine (vedi «Atti»)
    - name: secondo atto
      when: {flag: atto_due}
  endings:                 # almeno uno; vale il primo la cui condizione è vera
    - when: {player_in: torre}
      text: Testo finale.
    - when: {flag: caduto_nel_pozzo}   # anche una morte è un finale
      death: true                      # facoltativo: è una morte (vedi «Pericoli»)
      text: … Sei morto.
```

`examples` sono esempi per l'interprete, scritti come nel prompt (`app/llm/prompts.py`): righe
`Oggetti:`, `Uscite:`, `Frase:` e la risposta JSON. Si mettono solo per una frase che il modello
sbaglia giocando, e ogni modifica va verificata su tutto `tests/test_ollama.py`. Nella Rocca c'è
la frase del rampino.

**Pericoli.** Un finale non deve per forza essere una vittoria: una regola che attiva un flag e un
finale con quel flag e `death: true` fanno morire il giocatore, e la partita finisce (nel web si
ricomincia con «Nuova partita», nel terminale il gioco chiede «Vuoi giocare ancora?»; se il mondo
ha degli atti, prima si può riprendere dall'inizio dell'ultimo). Si può morire anche entrando in
una stanza: `when: {all: [{player_in: sottotetto}, {not: {flag: asse_posata}}]}`. Nella Rocca la
regola `salto_nel_pozzo` (`verb: salta`) attiva `caduto_nel_pozzo`. Il testo della regola racconta
cosa succede, quello del finale lo chiude. Un pericolo va annunciato prima, in una descrizione: il
pozzo è «profondo tre o quattro volte la tua altezza».

**Atti.** In un'avventura lunga, `acts` divide il gioco in parti. Quando la condizione di un atto
diventa vera per la prima volta (di solito il flag della regola che apre il piano nuovo), il gioco
mette da parte lo stato. Dopo una morte si riprende da lì: nel web scrivendo «riprendi», nel
terminale rispondendo sì alla domanda. Senza atti, dopo una morte si ricomincia da capo. `name` si
legge dopo «dall'inizio del»: «secondo atto». Gli atti cominciano in ordine: il secondo solo dopo il
primo.

## `rooms`

```yaml
rooms:
  cortile:
    name: Cortile
    aliases: [pozzo]         # facoltativo: altri nomi del luogo, anche chi o cosa ci si trova
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
        otherwise_variants: []                  # facoltativo, come le variants: il testo che segue la partita
```

Le uscite sono a senso unico: per tornare indietro serve l'uscita opposta nell'altra stanza.

**Andare in una stanza per nome.** Il giocatore può scrivere "vai in cucina" invece di "ovest"
se conosce la stanza di destinazione: l'ha già visitata, oppure la descrizione che sta leggendo
la nomina (tutte le parole del nome, esclusi articoli e preposizioni: "Sala del trono" richiede
sia "sala" sia "trono"). Le stanze mai viste e mai nominate restano sconosciute, così un nome
indovinato non rivela dove si trovano. Consiglio per chi scrive: nelle descrizioni nomina le
stanze vicine con il loro nome ("A ovest una porta bassa dà sulla cucina").

Gli `aliases` di una stanza valgono come il nome, sempre solo per una stanza conosciuta: con
`aliases: [orso, grotta]` sulla tana, "vado dall'orso" porta alla tana se è una delle uscite.
Servono per chi o cosa si trova nel luogo ("torna dal drago", "torna al pozzo") e per i nomi che
il giocatore usa davvero ("scuderie", "stalla"). Anche l'interprete li riceve, nelle uscite:
"ovest (Tana: orso, grotta)". Lo stesso alias può stare su più stanze: il ponte che unisce il
ruscello e la tana è un alias di tutte e due, così "attraverso il ponte" va dall'altra parte.

## `items`

```yaml
items:
  gancio:
    name: gancio da macellaio    # nome canonico: unico in tutto il mondo
    gender: m                    # genere del nome: m oppure f
    plural: false                # facoltativo: true per nomi plurali (attrezzi, chiavi)
    article: definite            # facoltativo: definite (sempre l'articolo determinativo) o none (nessun articolo)
    aliases: [gancio, uncino]    # altri nomi; possono coincidere con quelli di altri oggetti
    hidden_aliases: []           # facoltativo: altri nomi che il modello non vede (vedi sotto)
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
- `article` per i nomi propri: `none` per un nome di persona, che non vuole articolo («Ettore»,
  «a Ettore», «di Livia», «Qui c'è Agnese»); `definite` per un titolo o una cosa unica, che vuole
  sempre il determinativo («il dottor Ferri», «Qui c'è il dottor Ferri», mai «un dottor Ferri»).
  Vale anche per i personaggi e per i loro argomenti («chiedi a Ettore di Livia»).
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

**E l'interprete.** Anche per le frasi libere un oggetto vale solo se la frase lo nomina, con il
nome o un alias (tollerando un'altra desinenza e un errore di battitura: "chiavi", "ciave"): il
modello sceglie da un elenco, e senza niente di adatto sceglie a caso. Quindi negli alias vanno le
parole che il giocatore usa davvero ("vera" per il pozzo): una frase che nomina l'oggetto con una
parola che non c'è riceve "Non ho capito.", e finisce in `logs/comandi.jsonl`. Le parole comuni
(`COMMON_WORDS` in `app/engine/parser.py`: "sete", "metto", "nostro"…) non sono mai refusi, quindi
"ho sete" non nomina la "seta". Un alias di una parola sola vicino a una parola comune che non è
nella lista va evitato, oppure la parola va aggiunta alla lista ("fuori" nominava i "fiori").

**Alias nascosti al modello.** Il modello riceve l'elenco degli oggetti con i loro alias, e ogni nome
in più cambia le sue risposte anche alle altre frasi della stanza: nella camera di Clara, «incavo»
sulla casa delle bambole faceva diventare «inventario» la frase «infilo il medaglione nel tetto della
casa delle bambole». Un nome che serve solo perché il parser e i controlli riconoscano una parola
delle descrizioni va quindi in `hidden_aliases`: vale come gli alias per il parser, per i controlli
sulle risposte del modello e per «Non vedi niente del genere qui.», ma il modello non lo vede. Il
modello non lo sceglierà mai da solo; se però sceglie l'oggetto per un'altra via (la «casetta»), la
frase che usa il nome nascosto è valida.

## `rules`

Una regola dice cosa succede quando il giocatore compie un'azione precisa.

```yaml
rules:
  pesca_chiave:
    trigger: {verb: usa, target: pozzo, with: corda_con_gancio}
    when: {not: {flag: chiave_pescata}}         # facoltativo
    otherwise: Nel pozzo non c'è più niente.    # facoltativo: se when è falso
    otherwise_variants: []                      # facoltativo, come le variants: il testo che segue la partita
    effects:
      - give: chiave_torre
      - set_flag: chiave_pescata
    text: Testo dell'esito.
```

- `verb`: uno fra esamina, prendi, lascia, usa, apri, chiudi, spingi, tira, leggi, dai, salta
  (saltare dentro qualcosa: `trigger: {verb: salta, target: pozzo}`).
- `target` e `with` sono id di oggetti; `with` è facoltativo. Con `dai`, invece, `target` è
  l'oggetto e `with` il personaggio che lo riceve, obbligatorio:
  `trigger: {verb: dai, target: miele, with: draghetto}`.
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
  `otherwise` (o la prima delle sue `otherwise_variants` la cui condizione vale; altrimenti "Non
  succede niente.") e lo stato non cambia: le regole successive non vengono provate;
- **"usa X con Y"** è il verbo generico dei giocatori: se nessuna regola `usa` corrisponde, vale
  la prima regola di qualunque verbo sugli stessi due oggetti. Così "usa la chiave con la porta"
  fa scattare `apri: porta_torre con chiave_torre` senza scrivere una regola doppia;
- una frase libera come "butta la moneta nella fessura" arriva come "usa": l'interprete
  trasforma `lascia X con Y` in `usa X con Y`, quindi basta la regola `usa`;
- una regola **sostituisce** il comportamento predefinito del verbo (vedi sotto): una regola su
  "prendi X" che deve dare l'oggetto al giocatore lo fa con `give: X`.

**Senza regole**, i verbi fanno così (lo strumento, se c'è, viene ignorato):

| Verbo | Comportamento predefinito |
|---|---|
| esamina | mostra la descrizione dell'oggetto, con la variante valida |
| prendi | mette l'oggetto nell'inventario; rifiuta gli arredi e gli oggetti che hai già |
| lascia | posa l'oggetto nella stanza; rifiuta gli oggetti che non hai |
| apri, chiudi, leggi | "Non si può aprire." / "Non si può chiudere." / "Non c'è niente da leggere." |
| usa, spingi, tira, salta | "Non succede niente." |
| dai | il personaggio risponde `refuses`, o "Non sa che farsene."; l'oggetto resta al giocatore |

I messaggi del motore non nominano mai l'oggetto, così non servono articolo e genere.

**Azioni non previste.** Se una frase libera, interpretata dall'LLM, diventa un'azione a cui
nessuna regola reagisce (tranne esamina, prendi e lascia senza strumento, che fanno qualcosa da
sole), il gioco non la esegue subito ma chiede conferma: "Vuoi usare la corda con gancio con il
portone?". Il modello potrebbe aver frainteso. Lo stesso per uno spostamento interpretato verso
una direzione che la frase non nomina, né con la direzione né con la stanza in cui porta ("vado
in cantina" → "Vuoi andare a ovest?"). E per un salto, che può uccidere, se la frase non ha una
parola da salto (salta, tuffo, mi butto…): "entro nel pozzo" → "Vuoi saltare nel pozzo?"; se
invece nomina un altro oggetto, è un lancio ("lancio il rampino nel pozzo" diventa "usa").
Le azioni scritte con i comandi semplici si eseguono senza domande ("salta nel pozzo",
"buttati nel pozzo"). Per chi scrive: le azioni che i giocatori tenteranno davvero meritano una
regola, anche solo un indizio.

## `characters`

```yaml
characters:
  pellegrino:
    name: pellegrino             # nome canonico: unico tra oggetti e personaggi
    gender: m
    plural: false                # facoltativo
    article: none                # facoltativo: none per un nome di persona, definite per un titolo
    aliases: [viandante, vecchio]
    description: Testo mostrato quando lo si esamina.
    variants: []                 # come per le stanze
    location: scuderia           # una stanza: dove sta quando nessuno spostamento vale
    moves:                       # facoltativo: dove si trova quando una condizione vale
      - when: {flag: atto_due}
        room: biblioteca
    greeting: Risposta a "parla con il pellegrino".
    greeting_variants:           # facoltativo, come le variants: il saluto che segue la partita
      - when: {flag: torre_vista}
        text: Il saluto quando la condizione vale.
        again: …                 # facoltativo: questa variante dalla seconda volta
    greeting_again: …            # facoltativo: il saluto dalla seconda volta
    unknown: Risposta a una domanda su qualcosa che non conosce.
    refuses: Risposta a "dai X al pellegrino" se nessuna regola lo prevede (facoltativo).
    gestures:                    # facoltativo: congedo, grazie, scuse, come_stai, chi_sei, scortesia
      grazie:
        text: Risposta a «grazie».
        variants: []             # come greeting_variants, anche con again
        again: …                 # facoltativo: dalla seconda volta
    topics:
      torre:
        name: torre              # unico tra gli argomenti del personaggio
        gender: f                # serve all'articolo: "chiedi al pellegrino della torre"
        aliases: [mura]
        when: {flag: torre_vista}   # facoltativo: finché è falsa, l'argomento è sconosciuto
        text: Risposta.
        variants: []             # come greeting_variants, anche con again
        again: …                 # facoltativo: la risposta dalla seconda volta
        effects: []              # facoltativo, come per le regole
```

- **Si parla per argomenti**, come nelle avventure degli anni '80: `parla con X` (anche `saluta X`)
  risponde con `greeting`, `chiedi a X di Y` (anche `domanda a X di Y`) con il testo
  dell'argomento. `chiedi della torre` si rivolge all'unico personaggio presente. Le frasi libere
  ("pellegrino, cosa sai della torre?") passano all'LLM, che sceglie solo il personaggio e uno degli
  argomenti che conosce: **le risposte sono sempre i testi scritti qui**.
- La descrizione della stanza elenca i personaggi presenti: "Qui c'è un pellegrino."
- `greeting_variants`: la prima con la condizione vera sostituisce `greeting`, così il saluto
  segue la partita (l'orso, dopo lo scambio, non chiede più "chi va là?").
- **I gesti**: oltre al saluto, il personaggio risponde a congedi, ringraziamenti, scuse, «come
  stai?», «chi sei?» e scortesie con i testi di `gestures`. Le formule brevi («grazie», «arrivederci,
  Livia», «come state?») le capisce il parser; le frasi più libere l'interprete, col verbo «parla» e
  il gesto nel campo `con`. Il modello tende a rispondere «saluto» per qualunque gesto, quindi le
  parole della frase decidono («perdonatemi se vi disturbo» è una scusa, «grazie e arrivederci» un
  congedo; un insulto solo se rivolto a qualcuno: «sei un drago cattivo», non «i draghi cattivi
  sputano fuoco?»), e un'azione senza senso diventa il gesto che la frase dice («ti ringrazio tanto,
  draghetto»). Un gesto senza testo riceve una risposta neutra col nome del personaggio («Livia
  annuisce.»); «chi sei?» senza testo risponde `unknown`. Una formula che è proprio il nome o un alias
  di un argomento resta la domanda su quell'argomento; tra le frasi libere, una domanda che nomina un
  argomento è quella domanda qualunque sia il gesto («scusate, cosa sapete della contessa?»), e fuori
  dalle domande solo il saluto che nomina un argomento diventa la domanda su quell'argomento («grazie
  per la chiave» è un grazie). Un argomento non può chiamarsi come un gesto.
- **Le risposte ripetute**: il gioco ricorda i gesti e gli argomenti già usati con ciascun
  personaggio; dalla seconda volta vale `again`, se c'è, a meno che una variante sia vera (una novità
  della partita vince sempre). Anche una variante ha il suo `again`, dalla seconda volta che si dice
  proprio lei: Agnese saluta «Ce l'avete fatta!» una volta sola. Senza `again` la variante si ripete,
  come serve a ciò che descrive uno stato («Il dottor Ferri russa.»). Il gioco ricorda le varianti
  per posizione: aggiungerle, toglierle o riordinarle sposta il loro `again` nelle partite salvate.
  Nelle avventure per bambini meglio senza: sentire di nuovo l'indizio aiuta.
- **A chi, senza nome**: gesti, domande e «dai X» senza personaggio vanno all'unico presente, o a
  quello con cui si è parlato per ultimo (anche solo una domanda senza risposta o un regalo
  rifiutato) se è ancora lì; altrimenti «A chi?».
- «chiedi a X di Y», con Y un oggetto o un altro personaggio che non nomina nessun argomento di X,
  riceve `unknown`.
- Un argomento si riconosce dal nome o da un alias. Un alias può ripetere il nome di un oggetto
  ("chiave di ferro"): se l'LLM sceglie l'oggetto per una domanda, la risposta è quella dell'argomento.
- Nelle frasi libere un argomento nominato vince su quello scelto dall'LLM, e una domanda che il
  modello non capisce ("mi dai il miele?", anche senza "?" se comincia con perché, cosa, come…)
  riceve la risposta dell'argomento che nomina. Così un alias può essere anche una frase breve
  che i giocatori scrivono davvero: `[serve, successo]` sul raffreddore risponde a "cosa ti serve?"
  e "cosa ti è successo?". Il nome
  del personaggio non conta come argomento ("pellegrino, cosa sai della torre?" parla della torre).
- Una domanda su un argomento sconosciuto (con `when` falsa, o che non c'è) riceve `unknown` e
  non cambia la partita. Finisce in `logs/comandi.jsonl`: mostra cosa chiedono i giocatori.
- `effects` si applicano ogni volta che si chiede dell'argomento; per un effetto solo la prima
  volta, basta un `when` su un flag. Un personaggio che dà solo indizi non ne ha.
- I personaggi si possono esaminare; "prendi" risponde "Non si può prendere.", gli altri verbi non
  fanno niente.
- **Spostamenti**: `moves` dice dove si trova il personaggio mentre una condizione vale; vale il
  primo spostamento vero, altrimenti `location`. Si sposta solo così, con i flag: non si muove da
  solo col passare del tempo. Descrizione della stanza, dialoghi, `dai` e interprete seguono la sua
  posizione.
- **Dare**: `dai X a Y` (anche porgi, offri, regala, consegna, "ecco X"). Si dà solo ciò che si
  porta con sé, a un personaggio presente; "dai X" senza nome va all'unico personaggio presente, o
  a quello con cui si è parlato per ultimo se è lì ("A chi?" altrimenti). Una regola `verb: dai`
  decide cosa succede; senza regola il personaggio risponde `refuses` e la partita non cambia. "usa X con il personaggio" ricade sulla stessa regola.
  Una frase libera che nomina solo un personaggio che non c'è ("do le more al drago" nella tana)
  riceve "Non vedi nessuno del genere qui.": non va a chi è presente.

## Condizioni

Usate in `when` di uscite, varianti, regole, argomenti e spostamenti dei personaggi, atti e finali. Ogni condizione ha **una sola chiave**.

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
  nomi canonici duplicati (maiuscole comprese) tra oggetti e personaggi, e tra gli argomenti di
  un personaggio; personaggi con lo stesso id di un oggetto. Condizioni ed effetti degli
  argomenti si controllano come quelli delle regole.

## Stato della partita

`GameState` (in `models.py`) contiene tutto ciò che cambia durante la partita: stanza corrente,
posizione di ogni oggetto, flag attivi, stanze visitate, oggetti lontani già visti, gesti e
argomenti già usati con ciascun personaggio, l'ultimo personaggio con cui si è parlato, turni, fine
partita; se la partita è persa (una morte), quanti atti sono cominciati e lo stato all'inizio
dell'ultimo.
`GameState.new(world)` crea lo stato iniziale, che si salva e rilegge in JSON.
Il mondo invece è immutabile.

Solo il motore (`app/engine/engine.py`) modifica lo stato. Ogni azione, anche se rifiutata,
conta come un turno; dopo ogni azione il primo finale la cui condizione è vera chiude la
partita. Le uscite chiuse mostrano il loro `otherwise`, oppure "Non puoi andare da quella parte."
