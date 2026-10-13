r"""Builds prompt-difficili.json: the exact requests the game sends for the hardest sentences.

    .venv\Scripts\python prove-modelli/genera.py
    .venv\Scripts\python prove-modelli/genera.py --risposte risultati.json   # with a model's answers (prova.py --salva)
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine.engine import Engine  # noqa: E402
from app.engine.loader import WORLDS_DIR, load_world  # noqa: E402
from app.engine.parser import parse  # noqa: E402
from app.llm.client import LLMError  # noqa: E402
from app.llm.interpreter import MAX_TOKENS, interpret  # noqa: E402
from app.llm.client import OllamaClient  # noqa: E402

WORLDS = {name: load_world(WORLDS_DIR / name) for name in ("rocca", "draghetto", "valdimora")}
A3 = ("atto_due", "busta_data", "atto_tre")


class Recorder:
    def __init__(self):
        self.request = None

    def complete_json(self, system, user, schema, max_tokens, temperature=0):
        self.request = (system, user, schema)
        raise LLMError("recorded")

    def unavailable_reason(self):
        return None


def E(verbo, bersaglio="nessuno", con="nessuno"):
    return (verbo, bersaglio, con)


# (avventura, stanza, in mano, flag, visti, frase, perché è difficile, risposte accettate)
CASES = [
    # --- La Rocca di Serravento
    ("rocca", "cortile", ("corda_con_gancio",), (), ("chiave_torre",), "usa il rampino per recuperare la chiave dal pozzo",
     "Frase con lo scopo: senza l'esempio nel prompt il modello sceglieva il portone.",
     [E("usa", "corda_con_gancio", "pozzo"), E("prendi", "chiave_torre", "corda_con_gancio"), E("usa", "corda_con_gancio", "chiave_torre")]),
    ("rocca", "cortile", ("corda_con_gancio",), (), ("chiave_torre",), "provo a ripescare la chiave nel pozzo col rampino",
     "Frase con lo scopo, come sopra.",
     [E("usa", "corda_con_gancio", "pozzo"), E("prendi", "chiave_torre", "corda_con_gancio"), E("usa", "corda_con_gancio", "chiave_torre")]),
    ("rocca", "cortile", ("corda_con_gancio",), (), (), "butta il rampino nel pozzo",
     "«Buttare» è nel glossario sotto «lascia»: qwen risponde lascia, ma buttare una cosa in un'altra è usarle insieme.",
     [E("usa", "corda_con_gancio", "pozzo")]),
    ("rocca", "cortile", ("corda_con_gancio",), (), (), "lancio il rampino nel pozzo",
     "Non è un salto: lanciare una cosa dentro un'altra è usarle insieme.",
     [E("usa", "corda_con_gancio", "pozzo")]),
    ("rocca", "cortile", ("corda_con_gancio",), (), (), "aggancia la corda alla vera di pietra",
     "«vera» è un alias del pozzo; instabile con qwen.",
     [E("usa", "corda_con_gancio", "pozzo")]),
    ("rocca", "cortile", ("corda_con_gancio",), (), ("chiave_torre",), "afferra la ciave nel pozzo",
     "Refuso e oggetto in vista ma non a portata: qwen mette il pozzo come strumento.",
     [E("prendi", "chiave_torre"), E("prendi", "chiave_torre", "corda_con_gancio")]),
    ("rocca", "cortile", ("corda",), (), (), "bene ora utilizza la corda che hai preso nella scuderia e legala alla vera del pozzo",
     "Frase lunga, con un luogo che non c'entra.",
     [E("usa", "corda", "pozzo")]),
    ("rocca", "scuderia", ("gancio",), (), (), "a cosa mi serve questa corda?",
     "Una domanda, non un'azione: qwen legava il gancio alla corda e risolveva l'enigma.",
     [E("esamina", "corda")]),
    ("rocca", "scuderia", (), (), (), "vai in cucina",
     "La cucina non è tra le uscite (è oltre il cortile): qwen sceglieva una direzione a caso.",
     [E("vai", "nessuno")]),
    ("rocca", "cortile", (), (), (), "vado nella cantina",
     "Un luogo che non esiste: la risposta giusta è «nessuno».",
     [E("vai", "nessuno")]),
    ("rocca", "cortile", (), (), (), "busso alla porta della torre",
     "Nessun verbo per bussare: qwen dice «tira».",
     [E("altro"), E("esamina", "porta_torre")]),
    ("rocca", "cortile", (), (), (), "sfondo la porta a calci",
     "qwen risponde «lascia la porta».",
     [E("apri", "porta_torre"), E("spingi", "porta_torre")]),
    ("rocca", "cortile", (), (), (), "mi butto nel pozzo",
     "«Buttarsi» è saltare; «buttare» invece è lasciare.",
     [E("salta", "pozzo")]),
    ("rocca", "cortile", (), (), (), "guardo giù nel pozzo",
     "Guardare giù non è un salto né uno spostamento.",
     [E("esamina", "pozzo")]),
    ("rocca", "scuderia", (), (), (), "chi era il castellano?",
     "Domanda su un argomento («rocca») nominato solo dal contenuto: qwen dice «esamina il pellegrino».",
     [E("chiedi", "pellegrino", "t:rocca")]),
    ("rocca", "scuderia", (), (), (), "chiedo al vecchio come si esce da qui",
     "L'argomento «portone» si capisce solo da «si esce» (alias «esce»).",
     [E("chiedi", "pellegrino", "t:portone")]),
    ("rocca", "scuderia", (), (), (), "gli chiedo se ha fame",
     "Domanda su un argomento che il personaggio non ha: «con» deve essere «nessuno».",
     [E("chiedi", "pellegrino", "nessuno")]),
    ("rocca", "scuderia", (), (), (), "sei proprio un vecchio brontolone",
     "Gesto: qwen risponde «saluto» a quasi ogni gesto.",
     [E("parla", "pellegrino", "scortesia")]),
    ("rocca", "scuderia", (), (), (), "addio, e buona fortuna",
     "Gesto di congedo, non uno spostamento.",
     [E("parla", "pellegrino", "congedo")]),
    # --- Il draghetto raffreddato
    ("draghetto", "radura", (), (), (), "mangio una mora",
     "Le more non sono qui: qwen sceglieva un oggetto a caso (prendi il sasso).",
     [E("altro")]),
    ("draghetto", "quercia", ("ramo",), (), (), "salgo sull'albero",
     "«su», non «sud».",
     [E("vai", "su")]),
    ("draghetto", "quercia", ("ramo",), (), ("piuma",), "stacco la piuma col bastone",
     "«bastone» è un alias del ramo; senza l'esempio della mela qwen perdeva lo strumento.",
     [E("usa", "ramo", "piuma"), E("prendi", "piuma", "ramo")]),
    ("draghetto", "quercia", ("ramo",), (), (), "guardo su nell'albero",
     "«guarda su» è guardarsi intorno, non la quercia.",
     [E("esamina", "quercia"), E("esamina", "nido")]),
    ("draghetto", "radura", ("ramo", "piuma"), ("gola_guarita",), (), "ti faccio il solletico sul naso con la piuma",
     "Il personaggio è solo «ti»: qwen lo perde.",
     [E("usa", "piuma", "draghetto")]),
    ("draghetto", "ruscello", (), (), (), "attraverso il ponte",
     "Il ponte porta alla tana: la direzione si capisce dall'uscita.",
     [E("vai", "dir:tana")]),
    ("draghetto", "quercia", (), (), (), "vai a casa",
     "Casa è più lontana: dalla quercia non c'è un'uscita che ci porti.",
     [E("vai", "nessuno")]),
    ("draghetto", "radura", (), (), (), "vai dall orso",
     "La tana è oltre il ruscello (ovest): va bene il primo passo o «nessuno».",
     [E("vai", "dir:ruscello"), E("vai", "nessuno")]),
    ("draghetto", "radura", (), (), (), "salgo sul sasso",
     "Non c'è un'uscita «su» nella radura: non è uno spostamento né un salto.",
     [E("esamina", "sasso"), E("altro"), E("vai", "nessuno")]),
    ("draghetto", "radura", (), (), (), "ciao orso",
     "L'orso non è qui: il draghetto non va salutato al suo posto.",
     [E("altro"), E("parla", "nessuno", "saluto")]),
    ("draghetto", "tana", ("more",), (), (), "ecco le more",
     "«ecco» è dare, al solo personaggio presente.",
     [E("dai", "more", "orso")]),
    ("draghetto", "tana", ("more",), (), (), "mi dai il tuo miele?",
     "Una domanda con «dai»: chi dà è l'orso, non il giocatore.",
     [E("chiedi", "orso", "t:miele")]),
    ("draghetto", "radura", (), (), (), "conosci l'orso?",
     "L'orso è un argomento, non un personaggio presente.",
     [E("chiedi", "draghetto", "t:orso")]),
    ("draghetto", "radura", (), (), (), "perche hai il naso rosso",
     "Domanda senza punto interrogativo né accento.",
     [E("chiedi", "draghetto", "t:raffreddore")]),
    ("draghetto", "radura", (), (), (), "sei un drago cattivo",
     "Gesto (scortesia), non una domanda.",
     [E("parla", "draghetto", "scortesia")]),
    ("draghetto", "radura", (), (), (), "i draghi cattivi sputano fuoco?",
     "Domanda che contiene un insulto: resta una domanda.",
     [E("chiedi", "draghetto", "*")]),
    ("draghetto", "tana", (), (), (), "scusami tanto, orso",
     "Gesto di scuse.",
     [E("parla", "orso", "scuse")]),
    # --- La Stella di Valdimora
    ("valdimora", "stanza_maggiordomo", ("busta",), ("busta_data",), (), "leggo il biglietto della contessa",
     "qwen metteva un altro oggetto nominato come strumento.",
     [E("leggi", "busta")]),
    ("valdimora", "biliardo", (), ("ferri_addormentato",), (), "frugo nella borsa del dottore",
     "qwen rispondeva «inventario».",
     [E("esamina", "borsa"), E("apri", "borsa")]),
    ("valdimora", "stanza_maggiordomo", ("busta",), (), (), "faccio vedere la lettera a Ettore",
     "Non c'è un verbo per mostrare: va bene dare o chiedere della lettera.",
     [E("dai", "busta", "ettore"), E("chiedi", "ettore", "t:lettera")]),
    ("valdimora", "galleria", (), ("atto_due", "ritratto_scoperto"), (), "Ettore, chi è questa ragazza?",
     "Anche il ritratto ha l'alias «ragazza»: qwen dice «esamina il ritratto».",
     [E("chiedi", "ettore", "t:ritratto")]),
    ("valdimora", "galleria", (), ("atto_due", "ritratto_scoperto"), (), "infilo il medaglione nella cornice",
     "La cornice è il ritratto: qwen dice «inventario» o «prendi il medaglione».",
     [E("usa", "medaglione", "ritratto")]),
    ("valdimora", "camera_clara", (), (*A3, "camera_clara_aperta"), (), "infilo il medaglione nel tetto della casa delle bambole",
     "Ogni nome in più nella stanza cambiava la risposta in «inventario».",
     [E("usa", "medaglione", "casa_bambole")]),
    ("valdimora", "camera_clara", (), (*A3, "camera_clara_aperta"), (), "metto il medaglione nell'incavo",
     "«incavo» è un alias della casa delle bambole.",
     [E("usa", "medaglione", "casa_bambole")]),
    ("valdimora", "camera_clara", ("lettere_clara",), (*A3, "camera_clara_aperta"), (), "leggo le lettere della contessa",
     "«lettere» non è la lettera della contessa (che è altrove).",
     [E("leggi", "lettere_clara")]),
    ("valdimora", "camera_agnese", (), (*A3, "agnese_in_cucina"), (), "guardo sotto il materasso",
     "Il materasso è del letto di Agnese.",
     [E("esamina", "letto_agnese")]),
    ("valdimora", "stanza_orologio", ("corda",), A3, (), "lego la corda alla trave",
     "«lego» non è «leggo».",
     [E("usa", "corda", "trave_lucernario"), E("usa", "corda", "lucernario")]),
    ("valdimora", "stanza_orologio", ("corda",), A3, (), "lego la corda al tetto",
     "qwen risponde «leggi la trave con la corda».",
     [E("usa", "corda", "trave_lucernario"), E("usa", "corda", "lucernario"), E("usa", "corda", "tetto_visto")]),
    ("valdimora", "stanza_orologio", (), A3, (), "esco dal lucernario sul tetto",
     "Uno spostamento verso il tetto, non un salto.",
     [E("vai", "dir:tetto")]),
    ("valdimora", "cucina", ("lanterna",), (*A3, "lanterna_piena"), (), "accendo la lanterna con un fiammifero",
     "qwen sceglieva il focolare come strumento.",
     [E("usa", "lanterna", "fiammiferi")]),
    ("valdimora", "balcone", (), ("atto_due",), (), "mi appoggio alla balaustra",
     "Spingere la balaustra uccide: appoggiarsi non è spingere.",
     [E("esamina", "balaustra"), E("altro")]),
    ("valdimora", "balcone", (), ("atto_due",), (), "lancio uno sguardo verso la valle",
     "Uno sguardo non è un salto nella valle.",
     [E("esamina", "valle"), E("guarda")]),
    ("valdimora", "galleria", (), ("atto_due",), (), "ho sete",
     "Non è un'azione di gioco («sete» assomiglia a «seta»).",
     [E("altro")]),
    ("valdimora", "ufficio_governante", (), (), (), "chiedo a Livia di Corrado",
     "Argomento che è anche il nome di un altro personaggio.",
     [E("chiedi", "livia", "t:corrado")]),
    ("valdimora", "ufficio_governante", (), (), (), "e voi chi siete, di preciso?",
     "Gesto «chi sei», col «voi» di cortesia.",
     [E("parla", "livia", "chi sei")]),
    ("valdimora", "ufficio_governante", (), (), (), "siete una vecchia strega",
     "Insulto col «voi».",
     [E("parla", "livia", "scortesia")]),
    ("valdimora", "cappella", (), (), (), "perdonatemi se vi disturbo",
     "Gesto di scuse.",
     [E("parla", "agnese", "scuse")]),
    ("valdimora", "cappella", (), (), (), "adesso vado, ci vediamo più tardi",
     "Congedo, non uno spostamento.",
     [E("parla", "agnese", "congedo")]),
    ("valdimora", "stanza_maggiordomo", (), (), (), "scusate, cosa sapete della contessa?",
     "Una domanda dietro le parole di un gesto.",
     [E("chiedi", "ettore", "t:contessa")]),
    ("valdimora", "corridoio_servitu", (), A3, (), "Agnese, mi faresti una camomilla?",
     "La camomilla è l'argomento «tisana».",
     [E("chiedi", "agnese", "t:tisana")]),
    ("valdimora", "cucina", (), (*A3, "agnese_in_cucina"), (), "dove trovo il petrolio?",
     "Due personaggi presenti, nessuno nominato: va bene chiederlo a uno dei due (tanica o lanterna).",
     [E("chiedi", "*", "t:tanica"), E("chiedi", "*", "t:lanterna")]),
    ("valdimora", "camera_livia", ("fotografia",), A3, (), "mostro la fotografia di mia madre a Livia",
     "Mostrare: va bene dare o chiedere della fotografia.",
     [E("dai", "fotografia", "livia"), E("chiedi", "livia", "t:fotografia")]),
]  # fmt: skip


def resolve(token, world, engine, state):
    if token in ("*", "nessuno") or token in ("su", "giù", "nord", "sud", "est", "ovest"):
        return token
    if token.startswith("t:"):
        topic = token[2:]
        return next(c.topics[topic].name for c in world.characters.values() if topic in c.topics)
    if token.startswith("dir:"):
        room = token[4:]
        return next(direction.value for direction, exit_ in world.rooms[state.current_room].exits.items() if exit_.to == room)
    if token in world.items:
        return world.items[token].name
    if token in world.characters:
        return world.characters[token].name
    return token  # a gesture label, a verb


def setup(world_name, room, carried, flags, seen):
    world = WORLDS[world_name]
    engine = Engine(world)
    state, _ = engine.new_game()
    state.current_room = room
    state.visited.add(room)
    for item_id in carried:
        state.item_locations[item_id] = "inventory"
    if "corda_con_gancio" in carried:
        state.item_locations["corda"] = state.item_locations["gancio"] = None
    state.flags.update(flags)
    state.seen.update(seen)
    return world, engine, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--risposte", type=Path, action="append", default=[], help="a file written by prova.py --salva")
    args = parser.parse_args()
    answers = [json.loads(path.read_text(encoding="utf-8")) for path in args.risposte]
    systems, out = {}, []
    for n, (world_name, room, carried, flags, seen, sentence, why, accepted) in enumerate(CASES, 1):
        world, engine, state = setup(world_name, room, carried, flags, seen)
        near = engine.in_reach(state) + engine.visible(state)
        exits = engine.known_exits(state)
        characters = engine.characters_here(state)
        parsed = parse(sentence, world, near, exits, characters, state.last_speaker)
        if parsed is not None:
            print(f"skipped, the parser understands it: {sentence!r}")
            continue
        recorder = Recorder()
        interpret(recorder, sentence, near, exits, characters, world.game.examples)
        system, user, schema = recorder.request
        assert systems.setdefault(world_name, system) == system
        attese = []
        for verbo, bersaglio, con in accepted:
            e = {k: resolve(v, world, engine, state) for k, v in (("verbo", verbo), ("bersaglio", bersaglio), ("con", con))}
            for field in ("verbo", "bersaglio", "con"):
                assert e[field] == "*" or e[field] in schema["properties"][field]["enum"], f"{sentence!r}: {field}={e[field]!r} not in enum"
            attese.append(e)
        out.append({
            "id": f"{len(out) + 1:02d}-{world_name}",
            "avventura": world_name,
            "stanza": room,
            "frase": sentence,
            "perche": why,
            "utente": user,
            "schema": schema,
            "attese": attese,
        })
        for run in answers:
            found = next((r for r in run["risultati"] if r["frase"] == sentence), None)
            if found is not None:
                out[-1][run["modello"]] = found["risposta"]
    data = {
        "descrizione": (
            "Le frasi più difficili per l'interprete, trovate giocando e nei test col modello vero "
            "(tests/test_ollama.py). Per ogni caso c'è la richiesta esatta del gioco: il prompt di sistema "
            "dell'avventura (in «sistema»), il messaggio («utente») e lo schema JSON della risposta. "
            "«attese» sono le risposte accettate; con i verbi diversi da vai, chiedi e parla bersaglio e "
            "con si possono scambiare, «*» va bene qualunque valore. Col nome di un modello (es. «qwen2.5:3b») "
            "la sua risposta grezza, prima dei controlli del gioco sulla frase. Si prova un modello con prova.py."
        ),
        "opzioni": {"temperature": 0, "num_predict": MAX_TOKENS, "num_ctx": OllamaClient.NUM_CTX},
        "sistema": systems,
        "casi": out,
    }
    path = Path(__file__).resolve().parent / "prompt-difficili.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(out)} casi in {path}")


if __name__ == "__main__":
    main()
