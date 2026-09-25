# Avventura testuale nel castello — note di progetto

## Obiettivo
Avventura testuale in stile anni '80/'90 ambientata in un castello, giocabile via web.
Il giocatore scrive in italiano naturale e può dialogare con i personaggi.
Il castello, gli enigmi e i personaggi sono **originali**: non copiare contenuti di giochi esistenti.

## Principio architetturale (non negoziabile)
- Il **motore di gioco è deterministico** ed è l'unica fonte di verità sullo stato (stanze, oggetti, inventario, porte, flag degli enigmi).
- L'**LLM non modifica mai lo stato**. Ha solo due ruoli:
  1. **Interprete**: trasforma la frase del giocatore in un'azione strutturata (JSON validato con Pydantic).
  2. **Narratore**: riceve l'esito calcolato dal motore e lo racconta. Non inventa oggetti, uscite o eventi.
- Nei dialoghi, ogni personaggio ha un profilo con cosa sa e cosa può rivelare. L'LLM non deve mai dare la soluzione degli enigmi.

## Flusso di un turno
```
input giocatore
  → parser classico (comandi semplici: "nord", "prendi X", "inventario")
  → se non riconosciuto: LLM interprete → Azione (JSON)
  → motore: valida ed esegue → Esito
  → narrazione: testo fisso (stanze già viste, casi semplici) oppure LLM narratore
  → streaming al client
```

## Stack
- Python 3.12, FastAPI, Pydantic v2, uvicorn
- Frontend: un solo HTML con JS/CSS minimale in stile console retrò, senza framework
- Streaming verso il client con SSE
- Dati del mondo in YAML (PyYAML), validati con modelli Pydantic al caricamento
- Test: pytest
- Persistenza: stato partita serializzato in JSON; SQLite quando serviranno più utenti

## LLM
- Sviluppo: **Ollama in locale, solo CPU (niente GPU)**. Modello piccolo da 3-4B (es. famiglia Qwen o Llama, versione recente).
- In futuro, forse: API con piano gratuito o a pagamento. Il cambio deve richiedere solo configurazione.
- Astrazione `LLMClient` con implementazioni:
  - `OllamaClient` (usa l'output strutturato con schema JSON per l'interprete)
  - `OpenAICompatibleClient` (per provider esterni)
  - `FakeLLMClient` (risposte predefinite, per i test)
- Configurazione via variabili d'ambiente (URL, modello, chiave).

### Vincoli dovuti alla CPU
- Prompt **corti**: passa solo la stanza corrente, gli oggetti visibili, le uscite e l'inventario, mai il mondo intero.
- Preferire l'output strutturato con schema JSON al tool calling (più affidabile sui modelli piccoli).
- Risposte del narratore brevi (2-4 frasi), sempre in streaming.
- Ridurre le chiamate: tutto ciò che il parser classico o il testo fisso sanno gestire non passa dall'LLM.

## Struttura proposta
```
app/
  main.py            # FastAPI: endpoint, SSE, file statici
  engine/
    models.py        # Pydantic: Mondo, Stanza, Oggetto, Personaggio, Azione, Esito, StatoPartita
    loader.py        # caricamento e validazione YAML
    validation.py    # controlli incrociati sul mondo (riferimenti, flag, raggiungibilità)
    engine.py        # esecuzione azioni, regole, condizioni
    parser.py        # parser classico dei comandi semplici
  llm/
    client.py        # interfaccia LLMClient + implementazioni
    interpreter.py   # frase → Azione
    narrator.py      # Esito → testo
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

## Decisioni ancora aperte
- Articoli e genere degli oggetti, per scrivere "Qui vedi una corda" (fase 3).
- Hosting pubblico (es. PC di casa + Cloudflare Tunnel) — non prioritario.

## Comandi utili
```
# ambiente: Python 3.12 installato per l'utente (launcher `py`), ambiente virtuale in .venv
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install "pydantic>=2.11" "pyyaml>=6" "pytest>=8"
.venv\Scripts\python -m pytest

ollama pull <modello>
uvicorn app.main:app --reload
```


### Risultati dei test (qwen2.5:3b su CPU, Windows)
- Ambiente di sviluppo: Windows, PowerShell.
- Velocità misurate: generazione ~7 token/s, lettura prompt ~30 token/s.
  La lettura del prompt è il collo di bottiglia: prompt minimi, parte fissa in testa (cache).
- Interprete: output strutturato con `format` (schema JSON), `temperature: 0`, `num_predict: 60`.
  - Campi: `verbo`, `bersaglio` (su cosa si agisce), `con` (cosa si usa; "nessuno" se assente).
  - `verbo` vincolato con enum ai verbi supportati.
  - `bersaglio` e `con` vincolati con enum agli oggetti visibili + inventario, generati dal motore a ogni turno.
  - Due esempi few-shot nel prompt di sistema: senza, il modello scambiava bersaglio e strumento.
- Narratore: `num_predict` ~150, temperatura più alta, sempre in streaming.
- Il motore valida ogni azione; se non ha senso prova a invertire bersaglio/con o chiede chiarimenti.