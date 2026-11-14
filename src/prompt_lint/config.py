"""Configuration values, loaded once, in one place.

Every knob the tool exposes lives here so the rest of the code never
touches os.environ or magic numbers. Each value can be overridden with an
environment variable, which makes experiments (different model, higher
temperature) possible without editing code.
"""

import os
from pathlib import Path

import dotenv

ENV_PREFIX = "PLINT_"
LEGACY_ENV_PREFIX = "PROMPT_OPTIMIZER_"  # pre-rename names, still honoured
USER_CONFIG_DIR = Path.home() / ".plint"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.env"
LEGACY_CONFIG_FILE = Path.home() / ".prompt-optimizer" / "config.env"


class MissingAPIKeyError(RuntimeError):
    """Raised when the selected model's credentials are missing or fake."""


def is_placeholder(value: str) -> bool:
    """True for template values such as 'your-api-key-here'."""
    lowered = value.strip().lower()
    return lowered.startswith("your-") or lowered.endswith("-here") or "your-key" in lowered


def _load_environment() -> None:
    """Load `.env` files once, before any setting is read.

    The working-directory `.env` is loaded first, then the user config if
    it exists. Values already present in the environment win, which is
    python-dotenv's default and keeps shell exports authoritative.
    """
    # usecwd=True: without it python-dotenv searches from this file's folder
    # (site-packages when installed) and never sees the user's own .env.
    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    for config_file in (USER_CONFIG_FILE, LEGACY_CONFIG_FILE):
        if config_file.exists():
            dotenv.load_dotenv(config_file)


def _env_raw(name: str) -> str | None:
    """Read PLINT_<name>, falling back to the pre-rename PROMPT_OPTIMIZER_ one."""
    return os.getenv(f"{ENV_PREFIX}{name}") or os.getenv(f"{LEGACY_ENV_PREFIX}{name}")


def _env_str(name: str, default: str) -> str:
    return _env_raw(name) or default


def _env_float(name: str, default: float) -> float:
    return float(_env_raw(name) or default)


def _env_int(name: str, default: int) -> int:
    return int(_env_raw(name) or default)


_load_environment()

# LiteLLM model string: "<provider>/<model>", e.g. "gemini/gemini-2.5-flash",
# "openai/gpt-4o-mini", "anthropic/claude-sonnet-4-5", "ollama/llama3.1".
# The model must support structured (JSON) output for best results.
MODEL = _env_str("MODEL", "gemini/gemini-2.5-flash")

# Optional custom endpoint (Ollama, vLLM, an OpenAI-compatible gateway...).
API_BASE = _env_raw("API_BASE")

# 0.5-0.7 balances variety and consistency for rewriting.
TEMPERATURE = _env_float("TEMPERATURE", 0.6)

# Low provider defaults truncate long rewrites mid-sentence, which breaks
# schema validation. Reasoning models also spend hidden tokens against this
# budget, so 8192 leaves headroom.
MAX_TOKENS = _env_int("MAX_TOKENS", 8192)

# Retries on rate limiting (HTTP 429) and transient network errors.
MAX_RETRIES = _env_int("MAX_RETRIES", 3)

# Per-request ceiling in seconds, so a stalled call cannot hang the terminal.
REQUEST_TIMEOUT = _env_float("TIMEOUT", 60.0)

# Folder that holds one file per run. Overridable per run with --out.
DEFAULT_OUTPUT_DIR = _env_str("OUTPUT_DIR", "saved")


def _credential_keys(names: list[str]) -> list[str]:
    """Drop endpoint settings (e.g. OLLAMA_API_BASE); they have local defaults."""
    return [n for n in names if not n.endswith(("_API_BASE", "_BASE_URL"))]


def required_env_vars(model: str = "") -> list[str]:
    """Names of environment variables the model still needs, per LiteLLM."""
    import litellm

    try:
        info = litellm.validate_environment(model=model or MODEL)
    except Exception:
        return []
    return _credential_keys(info.get("missing_keys", []))


def save_settings(values: dict[str, str], destination: Path = USER_CONFIG_FILE) -> Path:
    """Merge values into the user config file (mode 600) and the environment.

    Args:
        values: Environment variable names mapped to their values.
        destination: Where to write. Defaults to USER_CONFIG_FILE.

    Returns:
        The path of the written file.
    """
    existing: dict[str, str] = {}
    if destination.exists():
        existing = {
            k: v for k, v in dotenv.dotenv_values(destination).items() if v is not None
        }
    existing.update({k: v.strip() for k, v in values.items()})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(f"{k}={v}\n" for k, v in existing.items()), encoding="utf-8"
    )
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    for key, value in values.items():
        os.environ[key] = value.strip()
    return destination


def ensure_credentials() -> None:
    """Check the credentials the configured model needs are present.

    Raises:
        MissingAPIKeyError: If a required variable is unset, or still a
            template placeholder.
    """
    import litellm

    try:
        info = litellm.validate_environment(model=MODEL)
    except Exception:
        return  # unknown model: let the provider report the problem
    missing = _credential_keys(info.get("missing_keys", []))
    if not info.get("keys_in_environment", True) and missing:
        names = ", ".join(missing)
        raise MissingAPIKeyError(
            f"{names} not found for model '{MODEL}'. Configure it with:\n"
            "  plint setup\n"
            "or set it in a .env file or export it:\n"
            f"  export {missing[0]}='your-key-here'"
        )
    name = f"{MODEL.split('/')[0].upper()}_API_KEY"
    if is_placeholder(os.getenv(name, "")):
        raise MissingAPIKeyError(
            f"{name} is still a placeholder value. Replace it with a real key."
        )
