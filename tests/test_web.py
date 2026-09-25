"""The web interface: the page and the two endpoints, with the state kept by the client."""

import pytest
from fastapi.testclient import TestClient

from app.engine.engine import Engine
from app.engine.loader import load_world
from app.llm.client import FakeLLMClient
from app.main import WORLD_CHANGED, create_app


@pytest.fixture(scope="module")
def castle():
    return load_world()


@pytest.fixture
def client(castle) -> TestClient:
    return TestClient(create_app(Engine(castle), llm=None))


def test_the_castle_can_be_finished_through_http(client):
    reply = client.post("/api/new").json()
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
        reply = client.post("/api/turn", json={"line": line, "state": state}).json()
        state = reply["state"]

    assert reply["finished"] is True
    assert reply["text"].endswith("Sei libero.")


def new_game(client: TestClient) -> dict:
    return client.post("/api/new").json()


def turn(client: TestClient, line: str, state: dict) -> dict:
    response = client.post("/api/turn", json={"line": line, "state": state})
    assert response.status_code == 200
    return response.json()


def test_the_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>I.A.vventura nel Castello</title>" in response.text


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
    reply = new_game(TestClient(create_app(Engine(castle), llm=_UnavailableLLM())))

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
    llm = FakeLLMClient(json_replies=[{"verbo": "spingi", "bersaglio": "portone", "con": "nessuno"}])
    client = TestClient(create_app(Engine(castle), llm=llm))
    state = new_game(client)["state"]

    assert turn(client, "dai una spinta al portone", state)["text"] == "(spingi il portone)\nNon succede niente."


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


def test_overlong_lines_are_rejected(client):
    state = new_game(client)["state"]

    response = client.post("/api/turn", json={"line": "a" * 501, "state": state})

    assert response.status_code == 422


def test_replies_name_the_current_room_for_the_status_line(client):
    reply = new_game(client)

    assert reply["room"] == "Cortile"
    assert turn(client, "vai in cucina", reply["state"])["room"] == "Cucina"
