"""LLM clients: the Ollama HTTP protocol (against a fake server) and the fake client for tests."""

import json

import httpx
import pytest

from app.llm.client import FakeLLMClient, LLMError, OllamaClient

SCHEMA = {"type": "object", "properties": {"verbo": {"type": "string"}}, "required": ["verbo"]}


def ollama(handler) -> OllamaClient:
    return OllamaClient("http://ollama.test", "qwen2.5:3b", transport=httpx.MockTransport(handler))


def ndjson(*chunks: dict) -> bytes:
    return "".join(json.dumps(chunk) + "\n" for chunk in chunks).encode()


# --- Structured output ---------------------------------------------------------------------


def test_complete_json_sends_schema_and_options_and_parses_the_reply():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"message": {"role": "assistant", "content": '{"verbo": "usa"}'}, "done": True})

    reply = ollama(handler).complete_json("Sei l'interprete.", "cala la corda", SCHEMA, max_tokens=60)

    assert reply == {"verbo": "usa"}
    [request] = requests
    assert request.method == "POST"
    assert request.url == "http://ollama.test/api/chat"
    assert json.loads(request.content) == {
        "model": "qwen2.5:3b",
        "stream": False,
        "format": SCHEMA,
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 60, "num_ctx": 2048},
        "messages": [
            {"role": "system", "content": "Sei l'interprete."},
            {"role": "user", "content": "cala la corda"},
        ],
    }


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"message": {"content": "non è json"}}),
        httpx.Response(200, json={"message": {"content": "[1, 2]"}}),
        httpx.Response(200, json={"error": "model not found"}),
        httpx.Response(500, text="boom"),
    ],
    ids=["not json", "not an object", "error field", "http error"],
)
def test_complete_json_turns_bad_replies_into_llm_errors(response):
    with pytest.raises(LLMError):
        ollama(lambda request: response).complete_json("s", "u", SCHEMA, max_tokens=60)


def test_unreachable_server_is_an_llm_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMError):
        ollama(handler).complete_json("s", "u", SCHEMA, max_tokens=60)


# --- Streaming ---------------------------------------------------------------------------------


def test_stream_text_yields_the_pieces_as_they_arrive():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = ndjson(
            {"message": {"content": "Il pozzo "}, "done": False},
            {"message": {"content": ""}, "done": False},
            {"message": {"content": "è di pietra."}, "done": False},
            {"message": {"content": ""}, "done": True, "eval_count": 5},
        )
        return httpx.Response(200, content=body)

    pieces = list(ollama(handler).stream_text("Sei il narratore.", "Esito: ...", max_tokens=100, temperature=0.7))

    assert pieces == ["Il pozzo ", "è di pietra."]
    payload = json.loads(requests[0].content)
    assert payload["stream"] is True
    assert "format" not in payload
    assert payload["options"] == {"temperature": 0.7, "num_predict": 100, "num_ctx": 2048}


def test_an_error_in_the_stream_is_an_llm_error():
    body = ndjson({"message": {"content": "Il pozzo "}, "done": False}, {"error": "out of memory"})
    stream = ollama(lambda request: httpx.Response(200, content=body)).stream_text("s", "u", 100, 0.7)

    assert next(stream) == "Il pozzo "
    with pytest.raises(LLMError):
        next(stream)


# --- Availability --------------------------------------------------------------------------------


def tags(*names: str) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"name": name, "model": name} for name in names]})


def test_available_when_the_model_is_pulled():
    assert ollama(lambda request: tags("llama3.2:3b", "qwen2.5:3b")).unavailable_reason() is None


def test_a_model_without_tag_means_latest():
    client = OllamaClient("http://ollama.test", "qwen2.5", transport=httpx.MockTransport(lambda r: tags("qwen2.5:latest")))

    assert client.unavailable_reason() is None


def test_unavailable_when_the_model_is_missing():
    reason = ollama(lambda request: tags("llama3.2:3b")).unavailable_reason()

    assert "ollama pull qwen2.5:3b" in reason


def test_unavailable_when_ollama_does_not_answer():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    assert "http://ollama.test" in ollama(handler).unavailable_reason()


# --- Fake client ----------------------------------------------------------------------------------


def test_fake_client_replays_its_answers_and_records_the_calls():
    fake = FakeLLMClient(json_replies=[{"verbo": "usa"}], text_replies=["Il pozzo è di pietra."])

    assert fake.complete_json("sistema", "frase", SCHEMA, max_tokens=60) == {"verbo": "usa"}
    assert "".join(fake.stream_text("narratore", "fatti", max_tokens=100, temperature=0.7)) == "Il pozzo è di pietra."
    assert fake.calls == [("json", "sistema", "frase"), ("text", "narratore", "fatti")]
    assert fake.unavailable_reason() is None


def test_fake_client_without_answers_fails_like_a_broken_llm():
    fake = FakeLLMClient()

    with pytest.raises(LLMError):
        fake.complete_json("s", "u", SCHEMA, max_tokens=60)
    with pytest.raises(LLMError):
        list(fake.stream_text("s", "u", max_tokens=100, temperature=0.7))
