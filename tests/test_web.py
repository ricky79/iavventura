"""The web interface: the page, the list of the adventures and the game endpoints, with the state
kept by the client."""

import pytest
from fastapi.testclient import TestClient

from app.engine.engine import Engine
from app.engine.loader import WORLDS_DIR, load_adventures, load_world
from app.engine.models import World
from app.llm.client import FakeLLMClient
from app.main import UNKNOWN_ADVENTURE, WORLD_CHANGED, create_app


@pytest.fixture(scope="module")
def castle():
    return load_world(WORLDS_DIR / "rocca")


@pytest.fixture
def client(castle) -> TestClient:
    return TestClient(create_app({"rocca": Engine(castle)}, llm=None))


@pytest.fixture
def two(castle, world_data) -> TestClient:
    """The castle and the small test world, in this order."""
    engines = {"rocca": Engine(castle), "prova": Engine(World.model_validate(world_data))}
    return TestClient(create_app(engines, llm=None))


def new_game(client: TestClient, adventure: str = "rocca") -> dict:
    response = client.post("/api/new", json={"adventure": adventure})
    assert response.status_code == 200
    return response.json()


def turn(client: TestClient, line: str, state, adventure: str = "rocca", pending=None) -> dict:
    response = client.post("/api/turn", json={"adventure": adventure, "line": line, "state": state, "pending": pending})
    assert response.status_code == 200
    return response.json()


def test_the_castle_can_be_finished_through_http(client):
    reply = new_game(client)
    state = reply["state"]
    commands = [
        "vai in cucina",
        "prendi il gancio",
        "est",
        "est",
        "prendi la corda",
        "usa la corda con il gancio",
        "ovest",
        "usa il rampino con il pozzo",
        "apri la porta con la chiave",
        "nord",
    ]

    for line in commands:
        reply = turn(client, line, state)
        state = reply["state"]

    assert reply["finished"] is True
    assert reply["text"].endswith("Sei libero.")


def test_the_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>I.A.vventura</title>" in response.text
    assert "/api/adventures" in response.text


def test_a_new_game_starts_with_intro_first_room_and_state(client):
    reply = new_game(client)

    assert reply["text"].startswith("La bufera ti ha sorpreso")
    assert "\n\nCortile\n" in reply["text"]
    assert reply["state"]["current_room"] == "cortile"
    assert reply["notice"] is None


class _UnavailableLLM(FakeLLMClient):
    def unavailable_reason(self):
        return "Ollama non risponde su http://localhost:11434."


def test_a_new_game_warns_when_the_llm_is_not_available(castle):
    reply = new_game(TestClient(create_app({"rocca": Engine(castle)}, llm=_UnavailableLLM())))

    assert reply["notice"] == "Ollama non risponde su http://localhost:11434. Si gioca con i soli comandi semplici."


def test_a_turn_returns_the_answer_and_the_new_state(client):
    state = new_game(client)["state"]

    reply = turn(client, "vai in cucina", state)

    assert reply["text"].startswith("Cucina\n")
    assert reply["state"]["current_room"] == "cucina"
    assert reply["state"]["turns"] == 1
    assert reply["finished"] is False
    assert reply["restarted"] is False


def test_free_sentences_go_to_the_llm(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "esamina", "bersaglio": "portone", "con": "nessuno"}])
    client = TestClient(create_app({"rocca": Engine(castle)}, llm=llm))
    state = new_game(client)["state"]

    reply = turn(client, "dai un'occhiata al portone", state)

    assert reply["text"] == f"(esamina il portone)\n{castle.items['portone'].description}"
    assert reply["pending"] is None


def test_the_action_asked_about_travels_with_the_state(castle):
    llm = FakeLLMClient(json_replies=[{"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}])
    client = TestClient(create_app({"rocca": Engine(castle)}, llm=llm))
    state = new_game(client)["state"]

    asked = turn(client, "dai una spinta al portone", state)
    answered = client.post(
        "/api/turn", json={"adventure": "rocca", "line": "sì", "state": asked["state"], "pending": asked["pending"]}
    )

    assert asked["text"] == "Vuoi spingere il portone?"
    assert asked["pending"] == {"verb": "spingi", "target": "portone", "with": None, "direction": None, "topic": None}
    assert answered.json()["text"] == "Non succede niente."
    assert answered.json()["pending"] is None


def test_a_broken_pending_action_is_ignored(client):
    state = new_game(client)["state"]

    response = client.post("/api/turn", json={"adventure": "rocca", "line": "sì", "state": state, "pending": {"verb": "vola"}})

    assert response.status_code == 200
    assert response.json()["state"]["turns"] == 0


def test_an_empty_line_changes_nothing(client):
    state = new_game(client)["state"]

    reply = turn(client, "   ", state)

    assert reply["text"] == ""
    assert reply["state"] == state


@pytest.mark.parametrize(
    "state",
    [{"current_room": "cantina"}, "stato", None],
    ids=["from another world", "not a state", "missing"],
)
def test_a_state_that_does_not_fit_the_world_restarts_the_game(client, state):
    reply = turn(client, "nord", state)

    assert reply["restarted"] is True
    assert reply["text"].startswith(f"{WORLD_CHANGED}\n\nLa bufera ti ha sorpreso")
    assert reply["state"]["current_room"] == "cortile"
    assert reply["state"]["turns"] == 0


def test_a_finished_game_stays_finished(client):
    state = new_game(client)["state"]
    state["finished"] = True

    reply = turn(client, "guarda", state)

    assert reply["text"] == "La partita è finita."
    assert reply["finished"] is True
    assert reply["resumable"] is None


@pytest.fixture
def two_acts(acts_world) -> TestClient:
    return TestClient(create_app({"prova": Engine(World.model_validate(acts_world))}, llm=None))


def test_after_a_death_the_game_goes_on_from_the_last_act(two_acts):
    state = new_game(two_acts, "prova")["state"]
    state = turn(two_acts, "tira la leva", state, "prova")["state"]

    dead = turn(two_acts, "salta sulla leva", state, "prova")
    again = turn(two_acts, "riprendi", dead["state"], "prova")

    assert (dead["finished"], dead["resumable"]) == (True, "secondo atto")
    assert again["text"].startswith("Riprendi dall'inizio del secondo atto.")
    assert (again["finished"], again["resumable"]) == (False, None)
    assert again["state"]["checkpoint"]["flags"] == ["porta_aperta"]


def test_the_page_offers_to_go_on_after_a_death(client):
    page = client.get("/").text

    assert "reply.resumable" in page
    assert "Scrivi «riprendi» per ricominciare dall'inizio del" in page


def test_overlong_lines_are_rejected(client):
    state = new_game(client)["state"]

    response = client.post("/api/turn", json={"adventure": "rocca", "line": "a" * 501, "state": state})

    assert response.status_code == 422


def test_replies_name_the_current_room_for_the_status_line(client):
    reply = new_game(client)

    assert reply["room"] == "Cortile"
    assert turn(client, "vai in cucina", reply["state"])["room"] == "Cucina"


# --- Several adventures ------------------------------------------------------------------------------


def test_the_adventures_are_listed_in_the_order_of_the_menu(two):
    assert two.get("/api/adventures").json() == [
        {
            "id": "rocca",
            "title": "La Rocca di Serravento",
            "summary": "Un castello abbandonato, una bufera, un portone che non si riapre.",
        },
        {"id": "prova", "title": "Prova", "summary": "Un mondo di prova."},
    ]


def test_each_adventure_plays_its_own_world(two):
    castle = new_game(two, "rocca")
    test = new_game(two, "prova")

    assert (castle["title"], castle["state"]["current_room"]) == ("La Rocca di Serravento", "cortile")
    assert (test["title"], test["state"]["current_room"]) == ("Prova", "atrio")
    assert turn(two, "tira la leva", test["state"], "prova")["text"] == "Clac! Qualcosa cade ai tuoi piedi."


def test_a_state_goes_with_its_own_adventure(two):
    castle = new_game(two, "rocca")

    reply = turn(two, "guarda", castle["state"], "prova")

    assert reply["restarted"] is True
    assert reply["text"].startswith(f"{WORLD_CHANGED}\n\nInizio.")
    assert reply["state"]["current_room"] == "atrio"


@pytest.mark.parametrize(
    "url, body",
    [("/api/new", {"adventure": "atlantide"}), ("/api/turn", {"adventure": "atlantide", "line": "guarda", "state": None})],
    ids=["new", "turn"],
)
def test_an_unknown_adventure_is_not_found(two, url, body):
    response = two.post(url, json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": UNKNOWN_ADVENTURE}


@pytest.mark.parametrize("url", ["/api/new", "/api/turn"])
def test_the_adventure_is_required(two, url):
    assert two.post(url, json={"line": "guarda", "state": None}).status_code == 422


def test_the_browser_checks_the_page_with_the_server_every_time(client):
    # Without it the browser kept the old page after an update, and the old page no longer fits the API.
    assert client.get("/").headers["cache-control"] == "no-cache"


def test_the_dragon_adventure_can_be_finished_through_http():
    worlds = load_adventures()
    client = TestClient(create_app({adventure_id: Engine(world) for adventure_id, world in worlds.items()}, llm=None))
    reply = new_game(client, "draghetto")
    commands = [
        "est", "prendi le more", "ovest", "ovest", "prendi il ramo", "ovest", "dai le more all'orso",
        "est", "est", "nord", "usa il ramo con il nido", "sud", "dai il miele al draghetto",
        "dai la piuma al draghetto",
    ]  # fmt: skip

    for line in commands:
        reply = turn(client, line, reply["state"], "draghetto")

    assert reply["finished"] is True
    assert reply["text"].endswith("Che avventura!")
    assert [a["id"] for a in client.get("/api/adventures").json()] == ["rocca", "draghetto", "valdimora"]
