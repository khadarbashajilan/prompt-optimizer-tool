"""Configuration values, loaded once, in one place.

Every knob the tool exposes lives here so the rest of the code never
touches os.environ or magic numbers. Each value can be overridden with an
environment variable, which makes experiments (different model, higher
temperature) possible without editing code.
"""

import os
from pathlib import Path

import dotenv

USER_CONFIG_DIR = Path.home() / ".prompt-optimizer"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.env"

# Reads .env from the working directory first, then user config if present.
dotenv.load_dotenv()
if USER_CONFIG_FILE.exists():
    dotenv.load_dotenv(USER_CONFIG_FILE)


class MissingAPIKeyError(RuntimeError):
    """Raised when no usable Groq API key can be found."""


# Values that look like a key but are just the committed templates. They
# pass any non-empty check and only fail at the provider, minutes later.
PLACEHOLDER_KEYS = frozenset({
    "your-groq-api-key-here",   # .env.example before this change
    "gsk_your-key-here",        # from the message older versions printed
})


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


# The only Groq model on the free tier that supports Structured Outputs in
# strict mode, so the reply is always valid against our Pydantic schemas.
MODEL = _env_str("PROMPT_OPTIMIZER_MODEL", "openai/gpt-oss-20b")

# Groq recommends 0.5-0.7 for gpt-oss. Lower values make it repeat itself.
TEMPERATURE = _env_float("PROMPT_OPTIMIZER_TEMPERATURE", 0.6)

# Groq's own default of 1024 tokens truncates long rewrites mid-sentence,
# which breaks the strict-schema decode. gpt-oss is a reasoning model whose
# hidden reasoning tokens count against this budget; at 4096 a long prompt
# occasionally used it all and returned an empty reply, so 8192 gives headroom.
MAX_TOKENS = _env_int("PROMPT_OPTIMIZER_MAX_TOKENS", 8192)

# 3 attempts total. Handles the free tier's rate limiting (HTTP 429) and
# transient network errors.
MAX_RETRIES = _env_int("PROMPT_OPTIMIZER_MAX_RETRIES", 3)

# Per-request ceiling in seconds, so a stalled call cannot hang the terminal.
REQUEST_TIMEOUT = _env_float("PROMPT_OPTIMIZER_TIMEOUT", 60.0)

# Folder that holds one file per run. Overridable per run with --out.
DEFAULT_OUTPUT_DIR = _env_str("PROMPT_OPTIMIZER_OUTPUT_DIR", "saved")


def save_api_key(key: str, destination: Path = USER_CONFIG_FILE) -> Path:
    """Save key to the user config file with restricted permissions.

    Args:
        key: The Groq API key to store.
        destination: Where to write. Defaults to USER_CONFIG_FILE.

    Returns:
        The path of the written file.
    """
    clean_key = key.strip()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"GROQ_API_KEY={clean_key}\n", encoding="utf-8")
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    os.environ["GROQ_API_KEY"] = clean_key
    return destination


def api_key() -> str:
    """Return the Groq API key from the environment.

    Returns:
        The value of GROQ_API_KEY.

    Raises:
        MissingAPIKeyError: If the variable is unset, empty, or one of the
            known template placeholders.
    """
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise MissingAPIKeyError(
            "GROQ_API_KEY not found. Configure it with:\n"
            "  prompt-optimizer setup\n"
            "or set it in .env file or export it:\n"
            "  export GROQ_API_KEY='your-key-here'"
        )
    if key in PLACEHOLDER_KEYS:
        raise MissingAPIKeyError(
            "GROQ_API_KEY is still the placeholder from .env.example. "
            "Replace it with a real key: https://console.groq.com/keys"
        )
    return key
