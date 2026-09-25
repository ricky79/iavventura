"""Configuration from environment variables: switching model or provider is only configuration."""

import pytest

from app.config import Settings, make_client
from app.llm.client import OllamaClient


def test_defaults_use_the_local_ollama_with_the_small_qwen():
    settings = Settings.from_env({})

    assert settings == Settings(llm="ollama", ollama_url="http://localhost:11434", model="qwen2.5:3b")


def test_environment_variables_override_the_defaults():
    settings = Settings.from_env({"LLM": "OFF", "OLLAMA_URL": "http://pc-di-casa:11434", "LLM_MODEL": "llama3.2:3b"})

    assert settings == Settings(llm="off", ollama_url="http://pc-di-casa:11434", model="llama3.2:3b")


def test_an_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="ollama, off"):
        Settings.from_env({"LLM": "gpt"})


def test_ollama_settings_make_an_ollama_client():
    client = make_client(Settings(llm="ollama", ollama_url="http://pc-di-casa:11434/", model="llama3.2:3b"))

    assert isinstance(client, OllamaClient)
    assert client.base_url == "http://pc-di-casa:11434"
    assert client.model == "llama3.2:3b"


def test_llm_off_means_no_client():
    assert make_client(Settings(llm="off")) is None
