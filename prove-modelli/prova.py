"""Prova un modello sui prompt più difficili per l'interprete (prompt-difficili.json).

Manda a ogni caso la stessa richiesta del gioco (prompt di sistema, messaggio, schema JSON) e
confronta la risposta con quelle accettate. Solo la libreria standard: si lancia anche fuori dal
progetto.

    python prove-modelli/prova.py --model qwen2.5:7b
    python prove-modelli/prova.py --model llama3.2:3b --casi pozzo        # solo i casi con «pozzo»
    python prove-modelli/prova.py --api openai --url https://api.example.com/v1 --model nome --chiave-env MIA_CHIAVE

Con --api ollama usa /api/chat con `format`, come il gioco; con --api openai un endpoint compatibile
(/chat/completions con `response_format` json_schema).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CASES_FILE = HERE / "prompt-difficili.json"

# Con questi verbi la posizione conta; con gli altri bersaglio e strumento si possono scambiare,
# come nel motore (le regole accettano i due oggetti in qualunque ordine).
_ORDERED = {"vai", "chiedi", "parla"}


def matches(reply: dict, expected: dict) -> bool:
    if not _same(reply.get("verbo"), expected["verbo"]):
        return False
    pair = (reply.get("bersaglio"), reply.get("con"))
    wanted = (expected["bersaglio"], expected["con"])
    if _same(pair[0], wanted[0]) and _same(pair[1], wanted[1]):
        return True
    return expected["verbo"] not in _ORDERED and _same(pair[0], wanted[1]) and _same(pair[1], wanted[0])


def _same(value, wanted: str) -> bool:
    return wanted == "*" or value == wanted


def ask_ollama(url: str, model: str, case: dict, system: str, options: dict) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "format": case["schema"],
        "keep_alive": "30m",
        "options": options,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": case["utente"]}],
    }
    body = _post(f"{url.rstrip('/')}/api/chat", payload, {})
    return json.loads(body["message"]["content"])


def ask_openai(url: str, model: str, case: dict, system: str, options: dict, key: str | None) -> dict:
    schema = {**case["schema"], "additionalProperties": False}
    payload = {
        "model": model,
        "temperature": options["temperature"],
        "max_tokens": options["num_predict"],
        "response_format": {"type": "json_schema", "json_schema": {"name": "azione", "schema": schema, "strict": True}},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": case["utente"]}],
    }
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    body = _post(f"{url.rstrip('/')}/chat/completions", payload, headers)
    return json.loads(body["choices"][0]["message"]["content"])


def _post(url: str, payload: dict, headers: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--url", help="predefinito: http://127.0.0.1:11434 per ollama")
    parser.add_argument("--chiave-env", help="variabile d'ambiente con la chiave dell'API (per --api openai)")
    parser.add_argument("--casi", help="solo i casi la cui frase o il cui id contiene questo testo")
    parser.add_argument("--salva", type=Path, help="scrive qui le risposte, in JSON")
    args = parser.parse_args()

    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    cases = [c for c in data["casi"] if not args.casi or args.casi.lower() in (c["frase"] + c["id"]).lower()]
    url = args.url or ("http://127.0.0.1:11434" if args.api == "ollama" else None)
    if url is None:
        parser.error("con --api openai serve --url")
    key = os.environ.get(args.chiave_env) if args.chiave_env else None

    results, passed, total_time = [], 0, 0.0
    for case in cases:
        system = data["sistema"][case["avventura"]]
        start = time.perf_counter()
        try:
            if args.api == "ollama":
                reply = ask_ollama(url, args.model, case, system, data["opzioni"])
            else:
                reply = ask_openai(url, args.model, case, system, data["opzioni"], key)
            error = None
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as exc:
            reply, error = None, str(exc)
        elapsed = time.perf_counter() - start
        total_time += elapsed
        ok = isinstance(reply, dict) and any(matches(reply, e) for e in case["attese"])
        passed += ok
        shown = json.dumps(reply, ensure_ascii=False) if error is None else f"ERRORE: {error}"
        print(f"{'OK' if ok else 'NO'}  {elapsed:5.1f}s  [{case['id']}] {case['frase']}\n           -> {shown}")
        if not ok:
            print(f"           attese: {' | '.join(json.dumps(e, ensure_ascii=False) for e in case['attese'])}")
        results.append({"id": case["id"], "frase": case["frase"], "risposta": reply, "errore": error, "ok": ok, "secondi": round(elapsed, 1)})

    print(f"\n{args.model}: {passed} su {len(cases)} giusti, {total_time:.0f} s in tutto")
    if args.salva:
        args.salva.write_text(json.dumps({"modello": args.model, "risultati": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
