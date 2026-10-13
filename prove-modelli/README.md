# Prove di altri modelli per l'interprete

Qui ci sono le 60 frasi più difficili per l'interprete. Servono a capire se un altro modello capisce
il giocatore meglio di qwen2.5:3b, senza giocare. Riferimento: **qwen2.5:3b fa 14 su 60** (il gioco
poi ne ripara molte con i controlli sulla frase, ma qui conta solo la risposta del modello).

## Come si lancia

Dalla cartella del progetto, in PowerShell, con Ollama acceso:

```
ollama pull qwen2.5:7b                                          # una volta: scarica il modello da provare
.venv\Scripts\python prove-modelli/prova.py --model qwen2.5:7b
```

Ci vogliono alcuni minuti (con qwen2.5:3b su CPU circa 10). Alla fine stampa
`qwen2.5:7b: N su 60 giusti`.

Altre forme utili:

```
# solo alcune frasi: quelle il cui testo o id contiene la parola
.venv\Scripts\python prove-modelli/prova.py --model qwen2.5:7b --casi pozzo
.venv\Scripts\python prove-modelli/prova.py --model qwen2.5:7b --casi valdimora

# salvare le risposte, per confrontarle o aggiungerle al file (vedi sotto)
.venv\Scripts\python prove-modelli/prova.py --model qwen2.5:7b --salva prove-modelli/risultati-7b.json

# un servizio compatibile con l'API di OpenAI (/chat/completions con response_format json_schema)
$env:MIA_CHIAVE = "..."
.venv\Scripts\python prove-modelli/prova.py --api openai --url https://api.provider.com/v1 --model nome-modello --chiave-env MIA_CHIAVE
```

`prova.py` usa solo la libreria standard: funziona anche con un Python qualunque, fuori da `.venv`.
Se Ollama non è su `http://127.0.0.1:11434`, aggiungi `--url`.

## Come si legge il risultato

Una riga per frase:

```
OK   14.1s  [52-valdimora] chiedo a Livia di Corrado
           -> {"verbo": "chiedi", "bersaglio": "Livia", "con": "Corrado"}
NO    6.3s  [18-rocca] sei proprio un vecchio brontolone
           -> {"verbo": "parla", "bersaglio": "pellegrino", "con": "saluto"}
           attese: {"verbo": "parla", "bersaglio": "pellegrino", "con": "scortesia"}
```

Con i verbi diversi da `vai`, `chiedi` e `parla`, `bersaglio` e `con` si possono scambiare (come nel
motore); `*` nelle attese accetta qualunque valore.

Il modello non è del tutto deterministico: un caso che passa una volta sola non dimostra niente.
Conta anche il tempo: nel gioco ogni frase libera aspetta il modello.

## Cosa c'è nel file

`prompt-difficili.json` ha, per ogni caso, la richiesta esatta che il gioco manda al modello:

- `sistema`: il prompt di sistema, uno per avventura (`rocca`, `draghetto`, `valdimora`);
- `utente`: il messaggio del turno (oggetti, personaggi, argomenti, uscite e la frase);
- `schema`: lo schema JSON della risposta, con gli elenchi di quel turno;
- `attese`: le risposte accettate;
- `perche`: cosa rende la frase difficile;
- `qwen2.5:3b`: la risposta grezza di qwen2.5:3b su CPU (il giro intero è in `risultati-3b.json`).

`opzioni` sono quelle del gioco: `temperature: 0`, `num_predict: 60`, `num_ctx: 2048`.

## Rigenerare il file

I prompt vengono dal codice e dai mondi del momento in cui il file è stato generato: se cambiano
il prompt (`app/llm/prompts.py`) o i mondi, va rigenerato. I casi (stanza, oggetti in mano, flag,
frase, risposte accettate) stanno in `genera.py`, nella lista `CASES`: lì si aggiungono frasi nuove.

```
.venv\Scripts\python prove-modelli/genera.py
.venv\Scripts\python prove-modelli/genera.py --risposte prove-modelli/risultati-3b.json --risposte prove-modelli/risultati-7b.json
```

`--risposte` (anche più di uno) aggiunge a ogni caso la risposta di un modello, da un file scritto da
`prova.py --salva`. Senza, le risposte di qwen2.5:3b spariscono dal file. Se sono cambiati i prompt,
quelle vecchie non valgono più: rilancia prima `prova.py --model qwen2.5:3b --salva
prove-modelli/risultati-3b.json`.
