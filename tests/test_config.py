"""Configuration: key resolution and placeholder rejection.

These tests only exercise ``api_key()``; the numeric settings are read once
at import time and are therefore not re-loadable within a test process.
"""

import pytest

from prompt_optimizer.config import MissingAPIKeyError, api_key


def test_returns_a_stripped_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "  gsk_real-key  ")

    assert api_key() == "gsk_real-key"


def test_missing_key_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(MissingAPIKeyError, match="GROQ_API_KEY"):
        api_key()


def test_blank_key_is_a_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "   ")

    with pytest.raises(MissingAPIKeyError, match="not found"):
        api_key()


def test_dotenv_example_placeholder_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "your-groq-api-key-here")

    with pytest.raises(MissingAPIKeyError, match="placeholder"):
        api_key()


def test_docstring_style_placeholder_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_your-key-here")

    with pytest.raises(MissingAPIKeyError, match="placeholder"):
        api_key()


def test_a_real_looking_key_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_1a2b3c")

    assert api_key() == "gsk_1a2b3c"
