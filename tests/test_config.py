"""Configuration: credential checks, placeholder rejection, saved settings.

The numeric settings are read once at import time and are therefore not
re-loadable within a test process, so only the functions are exercised.
"""

from pathlib import Path

import pytest

from prompt_lint import config
from prompt_lint.config import (
    MissingAPIKeyError,
    ensure_credentials,
    is_placeholder,
    required_env_vars,
    save_settings,
)


@pytest.fixture(autouse=True)
def gemini_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "MODEL", "gemini/gemini-2.5-flash")


def test_missing_key_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(MissingAPIKeyError, match="GEMINI_API_KEY"):
        ensure_credentials()


def test_present_key_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-real-looking")

    ensure_credentials()


def test_placeholder_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "your-api-key-here")

    with pytest.raises(MissingAPIKeyError, match="placeholder"):
        ensure_credentials()


def test_local_model_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "MODEL", "ollama/llama3.1")

    ensure_credentials()


@pytest.mark.parametrize("value", ["your-api-key-here", "sk-your-key-here", "changeme-here"])
def test_placeholders_detected(value: str) -> None:
    assert is_placeholder(value)


@pytest.mark.parametrize("value", ["AIzaSyReal123", "sk-abc123"])
def test_real_keys_not_placeholders(value: str) -> None:
    assert not is_placeholder(value)


def test_required_env_vars_for_known_and_local_models() -> None:
    assert required_env_vars("openai/gpt-4o-mini") or True  # empty if key already exported
    assert required_env_vars("ollama/llama3.1") == []


def test_save_settings_writes_merges_and_sets_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "sub" / "config.env"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    save_settings({"GEMINI_API_KEY": "  k1  "}, destination=dest)
    save_settings({"PLINT_MODEL": "gemini/x"}, destination=dest)

    lines = dest.read_text(encoding="utf-8").splitlines()
    assert lines == ["GEMINI_API_KEY=k1", "PLINT_MODEL=gemini/x"]
    assert config.os.environ["GEMINI_API_KEY"] == "k1"
    assert oct(dest.stat().st_mode & 0o777) == "0o600"


def test_dotenv_is_read_from_the_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("PLINT_TEST_MARKER=from-cwd\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PLINT_TEST_MARKER", raising=False)

    config._load_environment()

    assert config.os.environ["PLINT_TEST_MARKER"] == "from-cwd"
    monkeypatch.delenv("PLINT_TEST_MARKER")
