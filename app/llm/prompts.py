"""The interpreter's prompt, in Italian. The fixed part always comes first, so Ollama can reuse it
from its cache; only the last lines change from turn to turn. Keep it short: on CPU, reading the
prompt is the slowest part of a call.
"""

from collections.abc import Sequence

from app.engine.models import Item

INTERPRETER_SYSTEM = """\
Sei l'interprete di un'avventura testuale. Traduci la frase del giocatore in un'azione.
Verbi:
- esamina: guardare, osservare o controllare un oggetto
- prendi: prendere, raccogliere
- lascia: posare, mettere giù, buttare
- usa: usare un oggetto con un altro, legarli, calarne uno in un altro
- apri, chiudi, spingi, tira, leggi
- vai: spostarsi in una direzione
- guarda: guardarsi intorno
- inventario: controllare cosa si ha con sé
- altro: la frase non è un'azione di gioco
bersaglio: l'oggetto su cui si agisce; con "vai", la direzione.
con: l'oggetto usato per compiere l'azione, altrimenti "nessuno".
Scegli solo tra gli oggetti elencati; tra parentesi ci sono gli altri nomi con cui si chiamano.

Esempi
Oggetti: baule; chiavetta d'ottone (chiavetta); finestra della cucina (finestra); finestrone
Frase: provo ad aprire il baule usando la chiavetta
{"verbo": "apri", "bersaglio": "baule", "con": "chiavetta d'ottone"}
Frase: chiudi la finestra
{"verbo": "chiudi", "bersaglio": "finestra della cucina", "con": "nessuno"}
Frase: torno indietro verso sud
{"verbo": "vai", "bersaglio": "sud", "con": "nessuno"}
Frase: buongiorno, che ore sono?
{"verbo": "altro", "bersaglio": "nessuno", "con": "nessuno"}"""


def interpreter_user(sentence: str, in_reach: Sequence[Item]) -> str:
    """Items in reach with their aliases, then the sentence."""
    items = "; ".join(f"{item.name} ({', '.join(item.aliases)})" if item.aliases else item.name for item in in_reach)
    return f"Oggetti: {items or 'nessuno'}\nFrase: {sentence}"
