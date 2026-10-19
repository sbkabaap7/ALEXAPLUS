import pytest

from backend.app import ollama


def test_general_answer_provider_must_be_loopback(monkeypatch):
    monkeypatch.setattr(ollama.settings, 'ollama_base_url', 'https://example.com')
    with pytest.raises(ValueError, match='local HTTP'):
        ollama._base_url()
