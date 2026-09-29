# Dialoghi più naturali — design

Data: 2026-09-29. Approvato in chat sezione per sezione; questo documento lo mette per iscritto.

## Obiettivo

L'utente vuole parlare con i personaggi in modo più naturale. Si è chiesto se l'LLM potesse
interpretare i personaggi: con qwen2.5:3b su CPU è la strada del narratore, già provata e scartata
(inventa, può rivelare gli indizi e il colpevole, 15-20 secondi a battuta). Si è scelto invece di
rendere più ricchi i dialoghi d'autore, lasciando l'LLM come solo interprete. Una prova di
riformulazione delle risposte con l'LLM resta un esperimento separato, da decidere più avanti.

Cosa ha deciso l'utente:

- **Tutte e tre le avventure**: i cinque personaggi di Valdimora, il pellegrino della Rocca, il
  draghetto e l'orso.
- **Sette gesti sociali**: saluto (c'è già), congedo, grazie, scuse, come stai, chi sei, scortesia.
  Niente complimenti, niente «sì»/«no» (sono le risposte alle domande di conferma).
- **Prima il parser, poi il modello**: le formule brevi le riconosce il parser; le frasi più libere
  vanno al modello, col verbo «parla» e il gesto nel campo `con`.
- **Risposte ripetute**: il gioco ricorda cosa si è già chiesto a chi; argomenti e gesti possono
  avere un testo `again` per la seconda volta.
- **L'ultimo personaggio con cui si è parlato** riceve i gesti e le domande senza nome, se è
  presente.
- **Le opinioni reciproche** dei personaggi di Valdimora, e i rimandi tra un argomento e l'altro.
- **La correzione del primo feedback**: «chiedi a Livia di Corrado» rispondeva su Ettore.

Criterio di riuscita: «grazie», «arrivederci», «come state?», «chi siete?», «scusate» e una
scortesia ricevono da ognuno degli otto personaggi una risposta nella sua voce, anche detti in
modi liberi; la seconda domanda sullo stesso argomento non ripete il testo identico (a Valdimora e
nella Rocca); nessun dialogo nuovo cambia la partita o rivela i segreti degli atti successivi;
`tests/test_ollama.py` resta verde, a parte i limiti noti.

## 1. Il meccanismo

### Il formato dei personaggi

```yaml
livia:
  greeting: …                       # c'è già: è il gesto «saluto»
  greeting_again: «Ancora voi.»     # nuovo, facoltativo: il saluto dalla seconda volta
  gestures:                         # nuovo, facoltativo: gli altri sei gesti
    congedo: {text: …}
    grazie:
      text: …
      again: …                      # facoltativo
    scuse: {text: …}
    come_stai:
      text: …
      variants: [{when: {flag: livia_chiave}, text: …}]   # facoltative, come per gli argomenti
    chi_sei: {text: …}
    scortesia: {text: …}
  topics:
    contessa:
      text: …
      again: …                      # nuovo, facoltativo
```

- Chiavi dei gesti: `congedo`, `grazie`, `scuse`, `come_stai`, `chi_sei`, `scortesia`. Il saluto
  resta `greeting` (con `greeting_variants` e ora `greeting_again`).
- **Quale testo vince**: la prima variante valida; altrimenti, se quel gesto o argomento è già
  stato usato con quel personaggio, `again`; altrimenti il testo.
- **Un gesto senza testo** riceve una risposta neutra col nome del personaggio («Livia annuisce.»,
  «Livia ti saluta con un cenno.»); «chi sei» senza testo risponde `unknown`. È una rete di
  sicurezza: i personaggi di oggi hanno tutti i sei gesti scritti.
- La validazione rifiuta un argomento con lo stesso nome di un gesto (servono distinti nel prompt).

### Lo stato della partita

Due campi nuovi di `GameState`, con valori predefiniti (i salvataggi di oggi restano validi):
`asked` (i gesti e gli argomenti già usati con ciascun personaggio) e `last_speaker` (l'ultimo
personaggio con cui si è parlato, a cui si è chiesto o dato qualcosa). `Engine.restore` rifiuta un
`last_speaker` che il mondo non ha più.

### L'azione

Il gesto viaggia nell'azione «parla» (`Action.gesture`, solo con «parla»; senza, è il saluto). Tra
parentesi e nelle domande di conferma si legge: «(congedati da Livia)», «(ringrazia Livia)»,
«(scusati con Livia)», «(chiedi a Livia come sta)», «(chiedi a Livia chi è)», «(sii scortese con
Livia)».

### Con chi si parla, senza nome

Gesti, domande e «dai X» senza personaggio vanno all'unico presente; se ce ne sono di più,
all'ultimo con cui si è parlato, se è presente; altrimenti «A chi?» (come oggi per «dai»).

### Il riconoscimento

- **Parser**: formule brevi, anche col nome o l'alias del personaggio all'inizio o alla fine
  («grazie, Livia», «Livia, grazie»), riconosciute prima di ogni altro comando: saluti («ciao»,
  «buongiorno», «buonasera», «salve»), grazie («grazie», «grazie mille», «vi ringrazio»…), congedi
  («arrivederci», «addio», «a dopo», «a presto», «buonanotte», «ci vediamo»), scuse («scusate»,
  «scusa», «perdonatemi», «mi dispiace»…), come stai («come state?», «come stai?», «come va?»,
  «tutto bene?»), chi sei («chi siete?», «chi sei?», «come vi chiamate?», «come ti chiami?») e
  qualche scortesia chiara («stupido», «idiota», «antipatica», «andate al diavolo»…). Se la frase
  nomina un argomento del personaggio, resta una domanda su quell'argomento.
- **Interprete**: il campo `con` di «parla» accetta anche i gesti (`saluto, congedo, grazie, scuse,
  come stai, chi sei, scortesia`, solo quando c'è qualcuno); nel prompt cambia la riga di «parla»,
  la spiegazione di `con` e si aggiunge un esempio di dialogo («grazie mille, signora»). Tutto
  `tests/test_ollama.py` va rigiocato; `tests/prompt_rocca.txt` si aggiorna dopo un giro verde.
- Un saluto che nomina un argomento diventa la domanda su quell'argomento (come oggi); gli altri
  gesti restano gesti («grazie per la chiave» è un grazie).

### La correzione di «chiedi a Livia di Corrado»

- **Gioco**: se il modello sceglie un argomento che la frase non nomina, mentre la frase nomina
  un'altra persona o un oggetto del gioco, la domanda è su quello: risponde `unknown`.
- **Parser**: «chiedi a X di Y», con Y una persona o un oggetto del gioco su cui X non ha argomenti
  (o non ancora), riceve `unknown` senza passare dall'LLM.

## 2. I contenuti

- **I gesti degli otto personaggi**, nella loro voce: a Valdimora registro del 1927 e il «voi»
  (Ettore commosso e protettivo, Livia secca, Corrado sarcastico, il dottore bonario e brillo, che
  addormentato russa e basta, Agnese dolce e un po' troppo interessata); il pellegrino saggio e
  ironico, col «tu»; il draghetto e l'orso affettuosi, per bambini, senza parole che diano un
  genere al giocatore, e che perdonano anche una scortesia.
- **Il pellegrino**: «chi sei?» e «come ti chiami?» passano dall'argomento «pellegrino» al gesto
  `chi_sei`; l'argomento resta per il viaggio.
- **Le opinioni reciproche a Valdimora**:

  | Chi | Di chi, in più | Cosa lascia intendere |
  |---|---|---|
  | Ettore | Ferri | «un buon medico, una volta» |
  | Livia | Corrado, Agnese, Ferri | disprezza Corrado; Agnese «troppo gentile», in giro a ore strane; Ferri firma ciò che gli dicono |
  | Corrado | Livia, Ettore, Agnese | di Agnese cambia discorso troppo in fretta |
  | Ferri | Corrado, Agnese | in debito con Corrado; Agnese «precisa con le gocce, annotava tutto» |
  | Agnese | Corrado, Ettore, Livia | difende Corrado un po' troppo; curiosa di cosa sa Ettore |

  Nessuno rivela un segreto degli atti successivi; chi fa attenzione nota che Agnese e Corrado si
  difendono a vicenda.
- **`again`** per gli argomenti di Valdimora e della Rocca che, ripetuti uguali, suonerebbero
  meccanici; nel draghetto no (per un bambino sentire di nuovo l'indizio aiuta).
- **Rimandi**: qualche argomento esistente si chiude con un rimando a chi sa di più; mai verso un
  luogo che non si può ancora raggiungere.
- Nessun gesto e nessun argomento nuovo ha effetti sulla partita.

## 3. Costruzione e prove

Un branch, `feature/dialoghi`, una PR. Compiti in ordine: la correzione di Livia e Corrado; la
memoria e `again`; i gesti nel motore e l'ultimo interlocutore; il parser; l'interprete e il prompt;
i contenuti di Valdimora; quelli della Rocca e del draghetto; il modello vero (una ventina di frasi
nuove, poi tutto `test_ollama.py`); documentazione e revisione finale.

Prove, oltre ai test di ogni pezzo: ognuno degli otto personaggi ha i sei gesti scritti (le
risposte di riserva non si vedono); nessun gesto e nessun argomento nuovo ha effetti; i salvataggi
di prima riprendono.

## Fuori ambito

- L'LLM che riformula le risposte nella voce del personaggio: esperimento separato, da misurare
  (tempi, invenzioni, indizi persi, italiano) prima di decidere.
- Complimenti, «sì» e «no» come gesti.
- Varianti per `unknown` e `refuses` (i testi si scrivono neutri dove servono).
