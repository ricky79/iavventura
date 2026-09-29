"""The interpreter's prompt, in Italian. The fixed part always comes first, so Ollama can reuse it
from its cache; only the last lines change from turn to turn. The examples of a world come from its
YAML (`game.examples`): the Rocca's is the grapple. Keep it short: on CPU, reading the
prompt is the slowest part of a call.
"""

from collections.abc import Iterable, Sequence

from app.engine.models import Character, Direction, Item, Room, Topic

_HEAD = """\
Sei l'interprete di un'avventura testuale. Traduci la frase del giocatore in un'azione.
Verbi:
- esamina: guardare, osservare o controllare un oggetto
- prendi: prendere, raccogliere
- lascia: posare, mettere giù, buttare
- usa: usare un oggetto con un altro, legarli, calarne uno in un altro
- apri, chiudi, spingi, tira
- leggi: leggere uno scritto
- parla: salutare un personaggio, ringraziarlo, rivolgergli la parola
- chiedi: fare una domanda a un personaggio
- dai: dare, porgere, offrire un oggetto a un personaggio (anche "ecco", "tieni")
- salta: saltare, tuffarsi o buttarsi dentro qualcosa
- vai: spostarsi in una direzione o verso una delle uscite elencate
- guarda: guardarsi intorno
- inventario: controllare cosa si ha con sé
- altro: la frase non è un'azione di gioco
bersaglio: l'oggetto o il personaggio su cui si agisce; con "vai", la direzione dell'uscita, \
oppure "nessuno" se il luogo non è tra le uscite.
con: l'oggetto usato per compiere l'azione, altrimenti "nessuno"; con "chiedi", l'argomento \
della domanda, oppure "nessuno" se non è tra gli argomenti.
Scegli solo tra gli oggetti, i personaggi e gli argomenti elencati; tra parentesi ci sono gli \
altri nomi con cui si chiamano.
Per le uscite, tra parentesi c'è il luogo in cui portano, se è noto.

Esempi
Oggetti: baule; chiavetta d'ottone (chiavetta); finestra della cucina (finestra); finestrone
Uscite: nord (Biblioteca), sud
Frase: provo ad aprire il baule usando la chiavetta
{"verbo": "apri", "bersaglio": "baule", "con": "chiavetta d'ottone"}
Frase: chiudi la finestra
{"verbo": "chiudi", "bersaglio": "finestra della cucina", "con": "nessuno"}
Frase: a cosa serve questa chiavetta?
{"verbo": "esamina", "bersaglio": "chiavetta d'ottone", "con": "nessuno"}
Frase: torno indietro verso sud
{"verbo": "vai", "bersaglio": "sud", "con": "nessuno"}
Frase: torno in biblioteca
{"verbo": "vai", "bersaglio": "nord", "con": "nessuno"}
Frase: vado in cantina
{"verbo": "vai", "bersaglio": "nessuno", "con": "nessuno"}
Frase: buongiorno, che ore sono?
{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}"""

# Last, after the world's examples: anywhere before the grapple, "getta il rampino nel pozzo" went
# to the door (qwen2.5:3b).
_DIALOGUE = """\
Oggetti: mestolo
Personaggi: cuoca (donna)
Argomenti: cantina (scantinato); cena
Uscite: est
Frase: buongiorno, signora
{"verbo": "parla", "bersaglio": "cuoca", "con": "nessuno"}
Frase: cosa sai dello scantinato?
{"verbo": "chiedi", "bersaglio": "cuoca", "con": "cantina"}
Frase: le chiedo se ha visto il re
{"verbo": "chiedi", "bersaglio": "cuoca", "con": "nessuno"}"""


def interpreter_system(examples: str | None = None) -> str:
    """The fixed part of the prompt: instructions and generic examples, then the world's own examples
    (`game.examples`, in the same format), then the dialogue. It doesn't change from turn to turn,
    so Ollama keeps it in its cache."""
    return "\n".join(part for part in (_HEAD, examples, _DIALOGUE) if part)


def interpreter_user(
    sentence: str,
    in_reach: Sequence[Item],
    exits: Sequence[tuple[Direction, Room | None]] = (),
    characters: Sequence[tuple[Character, Sequence[Topic]]] = (),
) -> str:
    """Items in reach with their aliases; the characters here and their topics, only if there is
    someone; exits with the rooms the player knows; then the sentence."""
    lines = [f"Oggetti: {_names(in_reach) or 'nessuno'}"]
    if characters:
        topics = {topic.name: topic for _, known in characters for topic in known}.values()
        lines += [
            f"Personaggi: {_names(character for character, _ in characters)}",
            f"Argomenti: {_names(topics) or 'nessuno'}",
        ]
    ways = ", ".join(f"{direction} ({_place(room)})" if room else direction for direction, room in exits)
    lines += [f"Uscite: {ways or 'nessuna'}", f"Frase: {sentence}"]
    return "\n".join(lines)


def _place(room: Room) -> str:
    """"Tana: orso, grotta": the room with its other names."""
    return f"{room.name}: {', '.join(room.aliases)}" if room.aliases else room.name


def _names(things: Iterable[Item | Character | Topic]) -> str:
    """"pozzo; corda con gancio (corda, gancio, rampino)": each name with its aliases."""
    return "; ".join(f"{thing.name} ({', '.join(thing.aliases)})" if thing.aliases else thing.name for thing in things)
