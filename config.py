"""Configuration values, loaded once, in one place.

Every knob the tool exposes lives here so the rest of the code never
touches os.environ or magic numbers. Each value can be overridden with an
environment variable, which makes experiments (different model, higher
temperature) possible without editing code.
"""

import os

import dotenv

# Reads .env from the working directory. Must run before any getenv below
# that expects a value from that file.
dotenv.load_dotenv()


class MissingAPIKeyError(RuntimeError):
    """Raised when no Groq API key can be found."""


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
# which breaks the strict-schema decode. 4096 leaves room for a full prompt.
MAX_TOKENS = _env_int("PROMPT_OPTIMIZER_MAX_TOKENS", 4096)

# 3 attempts total. Handles the free tier's rate limiting (HTTP 429) and
# transient network errors.
MAX_RETRIES = _env_int("PROMPT_OPTIMIZER_MAX_RETRIES", 3)

# Per-request ceiling in seconds, so a stalled call cannot hang the terminal.
REQUEST_TIMEOUT = _env_float("PROMPT_OPTIMIZER_TIMEOUT", 60.0)

# Folder that holds one file per run. Overridable per run with --out.
DEFAULT_OUTPUT_DIR = _env_str("PROMPT_OPTIMIZER_OUTPUT_DIR", "saved")


def api_key() -> str:
    """Return the Groq API key from the environment.

    Returns:
        The value of GROQ_API_KEY.

    Raises:
        MissingAPIKeyError: If the variable is unset or empty.
    """
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise MissingAPIKeyError(
            "GROQ_API_KEY not found. Set it in .env file or export it:\n"
            "  export GROQ_API_KEY='your-key-here'"
        )
    return key
