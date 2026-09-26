# Più avventure, «dai X a qualcuno» e il draghetto raffreddato — design

Data: 2026-09-26. Approvato in chat sezione per sezione; questo documento lo mette per iscritto.

## Obiettivo

All'ingresso il giocatore sceglie l'avventura: la Rocca di Serravento (quella che c'è già) oppure
un'avventura fantastica per bambini, facile. Stesso motore, stesso parser, stesso interprete: cambiano
solo i dati.

Cosa ha chiesto l'utente e cosa si è deciso:

- Bambini di **8-10 anni che giocano da soli**: testi brevi ma completi, 5 luoghi, 2-3 enigmi
  semplici, un personaggio che aiuta se gli chiedi.
- Storia: **il draghetto raffreddato** (bosco incantato, tono dolce, nessun pericolo).
- **Un salvataggio per avventura**, con un menu d'ingresso che dice se c'è una partita in corso.
- **Gli indizi li dà solo il draghetto**, che sta fermo nella radura (niente comando «indizio»,
  niente personaggi che si spostano).
- **«dai X a qualcuno»** entra in questo lavoro, in versione minima.
- Approccio A: un solo server con più mondi in cartelle separate.

Criterio di riuscita: dal browser (e dal terminale) si sceglie una delle due avventure, le partite
delle due restano separate, la Rocca si gioca esattamente come prima (anche con l'LLM:
`tests/test_ollama.py` tutto verde), e il draghetto si finisce anche scrivendo come un bambino.

## Scomposizione

Tre pezzi, in quest'ordine, ciascuno con il suo branch e la sua PR:

1. **Più avventure e menu d'ingresso** — nessun cambiamento di gioco; la Rocca resta com'è.
2. **«dai X a qualcuno»** — verbo nuovo; provato su un mondo di test e sul pellegrino.
3. **Il draghetto raffreddato** — dati YAML, test sul mondo, casi in `test_ollama.py`.

Il 2 viene prima del 3 perché il draghetto lo usa. Nel pezzo 1 `avventure.yaml` elenca solo `rocca`
(il menu ha una voce sola finché non arriva il pezzo 3, che aggiunge `draghetto` all'indice); i test
del pezzo 1 provano il caso con più mondi su un mondo minimo in `tests/`.

---

## 1. Più avventure e menu d'ingresso

### Dati

```
data/worlds/
  avventure.yaml        # adventures: [rocca, draghetto]  — ordine del menu
  rocca/                # i file di oggi (git mv da data/world/)
    gioco.yaml, stanze.yaml, oggetti.yaml, regole.yaml, personaggi.yaml
  draghetto/
    ...
```

- `avventure.yaml` elenca gli id (i nomi delle cartelle) nell'ordine del menu. Un mondo che non è
  nell'elenco non viene caricato: così se ne può preparare uno senza mostrarlo.
- `GameInfo` (sezione `game`) ha due campi nuovi:
  - `summary: Text` — **obbligatorio**, una o due righe per il menu.
  - `examples: Text | None` — facoltativo: esempi per l'interprete, scritti esattamente nel formato
    del prompt (righe `Oggetti:`, `Uscite:`, `Frase:` e JSON). Nella Rocca ci va il blocco del
    rampino, tolto dal codice.

### Caricamento (`app/engine/loader.py`)

- `load_world(directory)` resta com'è: carica una cartella.
- Nuovo `load_adventures(root: Path = WORLDS_DIR) -> dict[str, World]`, nell'ordine di
  `avventure.yaml`. Problemi raccolti tutti insieme, ognuno con l'id davanti
  (`draghetto: items.miele: …`); indice mancante, id duplicato o cartella inesistente sono problemi
  anche loro. Un mondo rotto blocca l'avvio, come oggi.
- I test che oggi chiamano `load_world()` senza argomenti caricano la Rocca con il percorso esplicito
  (`WORLDS_DIR / "rocca"`): niente mondo "predefinito" nascosto.

### Prompt dell'interprete (`app/llm/prompts.py`)

Il prompt di sistema si compone di tre parti:

1. **testa** (codice): istruzioni, glossario dei verbi, esempi generici sul mondo inventato
   (baule, chiavetta, biblioteca…);
2. **esempi del mondo** (`game.examples`, se ci sono);
3. **coda** (codice): l'esempio del dialogo con la cuoca.

`interpreter_system(examples: str | None) -> str`. Per la Rocca il risultato deve essere **identico
carattere per carattere** al prompt di oggi (un test lo confronta con una copia del testo attuale,
presa prima di spostare il rampino). Chi alterna le due avventure fa rileggere a Ollama solo la parte
dopo la testa.

`interpret()` riceve il prompt di sistema (o gli esempi) da `Game`, che lo prende dal suo mondo.

### Server (`app/main.py`)

- `create_app(engines: dict[str, Engine], llm)`: un `Engine` per mondo, nell'ordine del menu.
- `GET /api/adventures` → `[{id, title, summary}]`.
- `POST /api/new` con `{adventure}` → come oggi, più `title`.
- `POST /api/turn` con `{adventure, line, state, pending}` → come oggi.
- Id sconosciuto → **404**; la pagina lo tratta tornando al menu (e scarta quel salvataggio).
- `adventure` è obbligatorio nelle due POST.
- Log: nel log dei comandi (`logs/comandi.jsonl`) ogni riga ha il campo `avventura`; nel log
  dell'LLM la riga di inizio diventa `--- nuova partita (web): draghetto ---`.

### Pagina (`static/index.html`)

- **Menu** nella console, stile della preview approvata:

  ```
  Scegli la tua avventura:

   1. La Rocca di Serravento
      Un castello abbandonato, una bufera, un portone che non si riapre.
      (partita in corso)

   2. Il draghetto raffreddato
      Per bambini dagli 8 anni: aiuta un piccolo drago raffreddato a
      ritrovare il suo fuoco.
  ```

  Ogni voce si sceglie toccandola, oppure scrivendo il numero o una parola del titolo nella riga di
  comando. Una scelta che non corrisponde a niente: «Scrivi il numero dell'avventura.»
  Una partita finita conta come nessuna partita in corso: sceglierla ne inizia una nuova.
- **Titolo in alto**: sul menu «I.A.vventura»; dentro un'avventura, il suo `title`. Il titolo della
  scheda del browser segue lo stesso criterio. La presentazione (ispirata ad «Avventura nel castello»
  di Enrico Colombini, frasi capite anche da un'intelligenza artificiale) va sul menu.
- **Riga di stato**:
  - in partita: stanza, mosse, **Avventure** (torna al menu subito, non si perde niente),
    **Nuova partita** (con la conferma di oggi, ricomincia l'avventura in corso), colori;
  - sul menu: «Scegli un'avventura», colori.
- **Salvataggi** nel `localStorage`:
  - `castle-adventure.save.<id>`: lo stesso oggetto di oggi (`state`, `room`, `finished`, `lines`,
    `pending`), uno per avventura;
  - `castle-adventure.adventure`: l'ultima avventura giocata;
  - all'apertura: se l'ultima avventura ha una partita in corso si riprende lì, come oggi; altrimenti
    il menu;
  - **migrazione**: se c'è il vecchio `castle-adventure.save` e non c'è `castle-adventure.save.rocca`,
    diventa il salvataggio della Rocca (e l'ultima avventura giocata), poi la chiave vecchia si toglie.
  - Ogni lettura e scrittura resta dentro `try/catch`, come oggi.
- Il colore resta com'è (`castle-adventure.color`), comune a tutte le avventure.

### Terminale (`app/cli.py`)

`python -m app.cli` mostra lo stesso menu numerato (senza «partita in corso»: il terminale non salva)
e chiede la scelta; numero o parola del titolo; una risposta che non va fa ripetere la domanda.
Poi la partita come oggi; «fine» chiude il programma.

### Test

- Loader: ordine di `avventure.yaml`; indice mancante, id duplicato, cartella inesistente; errori con
  l'id davanti; `summary` obbligatorio.
- Prompt: composizione nelle tre parti; prompt della Rocca invariato.
- Web: `/api/adventures`; nuova partita e turni con `adventure`; id sconosciuto → 404; ogni mondo si
  finisce via HTTP.
- Terminale: scelta per numero, per parola, scelta sbagliata ripetuta.
- Pagina: nessun test JS (come oggi); prova a mano nel browser — menu, scelta, «Avventure», «Nuova
  partita», due partite separate, migrazione del vecchio salvataggio, id sconosciuto.
- Documentazione: `docs/formato-mondo.md` (`summary`, `examples`, cartelle e indice) e `CLAUDE.md`.

---

## 2. «dai X a qualcuno»

### Modello

- `Verb.GIVE = "dai"`, tra i verbi sugli oggetti: le regole ci reagiscono.
- Azione: `dai`, `target` = l'oggetto, `with` = il personaggio.
- In YAML: `trigger: {verb: dai, target: miele, with: draghetto}`.
- Validazione (`app/engine/validation.py`): in un trigger `dai` il `target` è un oggetto e il `with`
  un personaggio; negli altri verbi i trigger continuano a nominare solo oggetti.
- `Character.refuses: Text | None`: la risposta del personaggio a un `dai` che nessuna regola
  prevede.

### Motore

Per `dai` il motore riconosce da solo quale dei due id è il personaggio (quello che è in
`world.characters`): l'ordine rovesciato («dai al drago il miele», o il modello che scambia i campi)
funziona lo stesso. Poi, prima delle regole:

- il personaggio deve essere qui → altrimenti `NOBODY_HERE`;
- l'oggetto dev'essere nell'inventario → altrimenti `DONT_HAVE` («Non ce l'hai.»).

Con una regola: come tutte le altre (`when`, `otherwise`, `effects`, `text`). Senza regola:
`refuses` del personaggio, oppure `NOT_WANTED = "Non sa che farsene."`; stato invariato.

- «usa il miele con il draghetto» ricade sulla regola `dai` sugli stessi due, grazie alla ricaduta di
  `usa` che c'è già in `_find_rule`.
- `Engine.expects`: un `dai` è sempre previsto (come prendi e lascia), quindi un `dai` interpretato
  non chiede conferma; si vede comunque «(dai il miele al draghetto)».

### Parser

- Verbi: `dai`, `dà`, `porgi`, `offri`, `regala`, `consegna`.
- Forme: «VERBO X a/al/allo/alla/all'/ai/agli/alle Y» e «VERBO a… Y X».
- «dai» è anche una parola vuota (da + i): come **prima** parola è il verbo, altrove resta vuota.
  Lo stesso per «dà», che senza accenti diventa «da».

### Testo (`app/engine/text.py`)

- Infinito «dare» (per «Vuoi dare il miele al draghetto?»).
- In `_complements`, per `dai`: «il miele al draghetto» con `articulated("a", personaggio)`, che
  esiste già.
- `HELP` in `app/game.py`: una riga «dai X a Y».

### Interprete

- Glossario: `- dai: dare, porgere, offrire un oggetto a un personaggio`.
- Schema invariato: `bersaglio` = l'oggetto, `con` = il personaggio (gli enum contengono già oggetti e
  personaggi in tutti e due i campi).
- `_to_action`: per `dai` servono un oggetto e un personaggio tra i nomi elencati, in qualunque
  ordine.
- Un esempio nella coda («le porgo il mestolo» con la cuoca) **solo se** i test col modello vero lo
  chiedono.
- Il glossario cambia il prompt anche per la Rocca: si rifà tutto `tests/test_ollama.py` (oggi 25 su
  25), più casi nuovi per «dai» sul pellegrino («offri la corda al vecchio»).

### Rocca

Nessuna regola `dai`. Il pellegrino riceve un `refuses`: «Tienilo tu, figliolo: a me basta il
bastone.»

### Test

- Motore: con regola; senza regola (con e senza `refuses`); oggetto non portato; personaggio assente;
  ordine rovesciato; `usa X con personaggio` che ricade su `dai`; `expects`.
- Validazione: `dai` con un non-personaggio in `with`; un altro verbo che nomina un personaggio.
- Parser: ogni verbo; le due forme; «dai» come prima parola e come parola vuota.
- Testo: «dai il miele al draghetto», «Vuoi dare…?», le preposizioni articolate.
- Interprete e gioco con il client finto; `test_ollama.py` completo.

### Fuori ambito

«mostra»; personaggi che danno oggetti di loro iniziativa (un argomento con `give` lo fa già);
personaggi che si spostano.

---

## 3. Il draghetto raffreddato

### Storia

Stai raccogliendo funghi ai margini del Bosco Fatato quando senti uno starnuto enorme. In una radura
trovi un draghetto verde con il naso rosso e gli occhi lucidi: il raffreddore gli ha spento il fuoco,
e senza il calduccio nella pancia le sue ali restano fredde. Non riesce a volare fino a casa, sulla
Montagna Rossa. Decidi di aiutarlo.

Finale: dopo il miele e il solletico, un ETCIÙ con una fiammata; il fuoco è tornato, le ali si
scaldano, il draghetto ti porta in volo sopra il bosco fino a casa.

### Mappa

```
                 Vecchia quercia
                      |
Tana dell'orso — Ruscello — Radura — Roveto
                              |
                     (sentiero di casa: chiuso)
```

| id | Luogo | Contenuto |
|---|---|---|
| `radura` | Radura (inizio) | il draghetto, su un sasso coperto di muschio; `sud` chiuso: «Non puoi lasciare il draghetto da solo proprio adesso!» |
| `roveto` | Roveto | cespugli (arredo) e le **more** (si prendono) |
| `ruscello` | Ruscello | un **ramo** lungo e dritto; ponticello verso la tana |
| `tana` | Tana dell'orso | l'**orso Tobia** e il suo vasetto di miele |
| `quercia` | Vecchia quercia | il **nido** in alto (arredo) con la **piuma**; `su` chiuso: «I rami più bassi sono troppo in alto per te.» |

### Enigmi

1. **Scambio**: `dai more a orso` → togli le more, ti dà il **vasetto di miele** (alias: miele,
   vasetto).
2. **Nido**: la piuma è fuori gioco (`location: null`) con
   `visible_from: {room: quercia, when: {not: {flag: piuma_presa}}}`, come la chiave nel pozzo, e la
   rivela l'esame della quercia o del nido (`reveals`). «prendi la piuma» → «Non ci arrivi.». Trigger equivalenti: `usa ramo con nido`,
   `usa ramo con piuma`, `prendi piuma con ramo` → ti dà la piuma («con la punta del ramo dai un
   colpetto al nido: la piuma volteggia giù e la prendi al volo»).
3. **Cura, in due passi**:
   - `dai miele a draghetto` → togli il miele, flag `gola_guarita`;
   - `dai piuma a draghetto` (e, per ricaduta, `usa piuma con draghetto`) con `when: gola_guarita`
     → flag `fuoco_tornato`, e il finale (`endings: when flag fuoco_tornato`);
   - senza `gola_guarita`, `otherwise`: dal naso esce solo un filo di fumo, «La gola mi brucia ancora
     troppo…» — un indizio, non un errore; la piuma resta al giocatore.

Niente vicoli ciechi: nessun oggetto si perde per sbaglio, tutto si può lasciare e riprendere.

### Personaggi

- **draghetto** (radura): parla e risponde per argomenti — fuoco/raffreddore, miele, orso,
  piuma/solletico, casa, bosco. Ogni risposta indica la strada senza dare la soluzione («L'orso Tobia
  ha sempre del miele… ma è goloso, vorrà qualcosa in cambio.»). `variants` secondo i progressi (dopo
  il miele: «Ora mi manca solo uno starnuto bello forte!»). Nessun effetto, come il pellegrino.
  `refuses` per gli oggetti che non servono.
- **orso** (tana, alias Tobia): serve solo per lo scambio; saluto, poche battute, `refuses` («L'orso
  annusa e sbuffa: non è una cosa da mangiare.»).

### Stile

Seconda persona, frasi brevi, parole semplici, descrizioni di 2-4 frasi; nessun pericolo, un po' di
umorismo (gli starnuti, l'orso goloso). Riassunto per il menu: «Per bambini dagli 8 anni: aiuta un
piccolo drago raffreddato a ritrovare il suo fuoco.» Tutto originale.

### Test

- `tests/test_draghetto.py`: la partita si finisce; ogni soluzione alternativa del nido funziona;
  piuma prima del miele non chiude il gioco e lascia la piuma al giocatore; le more si possono
  lasciare e riprendere; il draghetto non ha effetti; il sentiero a sud resta chiuso.
- Il mondo passa la validazione (già garantito dal caricamento nei test).
- `tests/test_ollama.py`, frasi da bambino (ognuna con il suo test sul client finto): «do le more
  all'orso», «faccio il solletico al drago con la piuma», «stacco la piuma col bastone», «salgo
  sull'albero», «ciao draghetto», «come posso aiutarti?», «gli do il miele».
- `game.examples` del draghetto parte vuoto; si aggiunge un esempio solo per un caso che fallisce, e
  ogni aggiunta si verifica su tutto `test_ollama.py`.

---

## Rischi

- **Prompt**: la riga di «dai» nel glossario può spostare casi della Rocca che oggi passano. Si
  verifica con `test_ollama.py` completo prima della PR; se serve si prova la riga in punti diversi
  del glossario (con `interpreter.INTERPRETER_SYSTEM` sostituito in uno script, come già fatto).
- **Frasi da bambino**: errori di battitura e frasi lunghe andranno spesso all'LLM; «Non ho capito.»
  sarà più frequente che nella Rocca. I casi trovati giocando diventano test (regola del progetto) e
  finiscono nel log dei comandi.
- **Migrazione del salvataggio**: se va storta si perde la partita in corso nella Rocca, niente di
  più; la si prova a mano.
