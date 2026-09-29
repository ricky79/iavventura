"""LLM clients: the Ollama HTTP protocol (against a fake server) and the fake client for tests."""

import json

import httpx
import pytest

from app.llm.client import FakeLLMClient, LLMError, OllamaClient

SCHEMA = {"type": "object", "properties": {"verbo": {"type": "string"}}, "required": ["verbo"]}


def ollama(handler) -> OllamaClient:
    return OllamaClient("http://ollama.test", "qwen2.5:3b", transport=httpx.MockTransport(handler))


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
    fake = FakeLLMClient(json_replies=[{"verbo": "usa"}, {"verbo": "apri"}])

    assert fake.complete_json("sistema", "frase", SCHEMA, max_tokens=60) == {"verbo": "usa"}
    assert fake.complete_json("sistema", "altra frase", SCHEMA, max_tokens=60) == {"verbo": "apri"}
    assert fake.calls == [("sistema", "frase"), ("sistema", "altra frase")]
    assert fake.unavailable_reason() is None


def test_fake_client_without_answers_fails_like_a_broken_llm():
    with pytest.raises(LLMError):
        FakeLLMClient().complete_json("s", "u", SCHEMA, max_tokens=60)


# --- Log of what goes to the model and what comes back ---------------------------------------------


def answering(content: str, **counters) -> OllamaClient:
    body = {"message": {"role": "assistant", "content": content}, "done": True, **counters}
    return ollama(lambda request: httpx.Response(200, json=body))


def test_each_call_logs_the_message_the_reply_and_the_counters(caplog):
    client = answering('{"verbo": "usa"}', prompt_eval_count=212, prompt_eval_cached_count=180, eval_count=21)

    with caplog.at_level("INFO", logger="app.llm"):
        client.complete_json("Sei l'interprete.", "Oggetti: pozzo\nFrase: cala la corda", SCHEMA, max_tokens=60)

    call = caplog.records[-1].getMessage()
    assert call.startswith("qwen2.5:3b  ")
    assert " s  prompt 212 token (180 in cache), risposta 21 token\n" in call
    assert call.endswith('>>> Oggetti: pozzo\n>>> Frase: cala la corda\n<<< {"verbo": "usa"}')


def test_missing_counters_are_shown_as_unknown(caplog):
    with caplog.at_level("INFO", logger="app.llm"):
        answering('{"verbo": "usa"}').complete_json("s", "u", SCHEMA, max_tokens=60)

    assert "prompt ? token (? in cache), risposta ? token" in caplog.records[-1].getMessage()


def test_the_system_prompt_is_logged_only_when_it_is_new(caplog):
    client = answering('{"verbo": "usa"}')

    with caplog.at_level("INFO", logger="app.llm"):
        client.complete_json("Sei l'interprete.\nTraduci.", "u1", SCHEMA, max_tokens=60)
        client.complete_json("Sei l'interprete.\nTraduci.", "u2", SCHEMA, max_tokens=60)
        client.complete_json("Nuovo prompt.", "u3", SCHEMA, max_tokens=60)

    system_logs = [record.getMessage() for record in caplog.records if "prompt di sistema" in record.getMessage()]
    assert system_logs == [
        "prompt di sistema:\n    Sei l'interprete.\n    Traduci.",
        "prompt di sistema:\n    Nuovo prompt.",
    ]


def test_a_failed_call_logs_the_message_and_the_error(caplog):
    client = answering("non è json")

    with caplog.at_level("INFO", logger="app.llm"), pytest.raises(LLMError):
        client.complete_json("s", "Frase: salta", SCHEMA, max_tokens=60)

    failure = caplog.records[-1]
    assert failure.levelname == "WARNING"
    assert ">>> Frase: salta\n" in failure.getMessage()
    assert "<<< non è json" in failure.getMessage()
    assert "the reply is not JSON" in failure.getMessage()


def test_an_unreachable_server_is_logged(caplog):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with caplog.at_level("INFO", logger="app.llm"), pytest.raises(LLMError):
        ollama(handler).complete_json("s", "Frase: salta", SCHEMA, max_tokens=60)

    assert "connection refused" in caplog.records[-1].getMessage()


# --- The full log (LLM_LOG_FULL=1: the logger at DEBUG) ---------------------------------------------


def logged_json(caplog, title: str) -> dict:
    """The JSON logged under `title`, indented by four spaces like the system prompt."""
    [message] = [record.getMessage() for record in caplog.records if record.getMessage().startswith(title)]
    first, *lines = message.splitlines()
    assert first == title
    assert all(line.startswith("    ") for line in lines)
    return json.loads("\n".join(lines))


def test_the_full_log_shows_the_request_exactly_as_sent_to_ollama(caplog):
    sent = []
    body = {"message": {"role": "assistant", "content": '{"verbo": "vai"}'}, "done": True}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=body)

    with caplog.at_level("DEBUG", logger="app.llm"):
        ollama(handler).complete_json("Sei l'interprete.\nVerbi:", "Frase: vai giù", SCHEMA, max_tokens=60)

    assert logged_json(caplog, "richiesta a Ollama:") == sent[0]
    assert "vai giù" in caplog.text  # readable: accents as they are, not escaped


def test_the_full_log_shows_the_whole_reply_of_ollama(caplog):
    client = answering('{"verbo": "usa"}', total_duration=5_500_000_000, load_duration=12_000_000, eval_count=21)

    with caplog.at_level("DEBUG", logger="app.llm"):
        client.complete_json("s", "u", SCHEMA, max_tokens=60)

    reply = logged_json(caplog, "risposta di Ollama:")
    assert reply["total_duration"] == 5_500_000_000
    assert reply["load_duration"] == 12_000_000
    assert reply["message"]["content"] == '{"verbo": "usa"}'


def test_the_usual_log_leaves_out_the_request_and_the_whole_reply(caplog):
    with caplog.at_level("INFO", logger="app.llm"):
        answering('{"verbo": "usa"}', total_duration=1).complete_json("s", "u", SCHEMA, max_tokens=60)

    assert "richiesta a Ollama" not in caplog.text
    assert "risposta di Ollama" not in caplog.text
    assert "num_ctx" not in caplog.text
