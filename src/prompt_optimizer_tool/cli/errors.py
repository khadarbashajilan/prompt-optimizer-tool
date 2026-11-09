"""User-facing error messages for the CLI."""

from groq import RateLimitError


def describe_error(error: Exception) -> str:
    """Turn a pipeline failure into a message a user can act on.

    Groq's free tier caps requests and tokens per minute and per day. The
    client already retried before this point, so a RateLimitError that
    reaches here means waiting is the only fix.
    """
    if isinstance(error, RateLimitError):
        wait = error.response.headers.get("retry-after")
        hint = f"Try again in about {wait} seconds." if wait else "Wait a minute and try again."
        return (
            "Groq rate limit reached (the free tier caps requests and tokens "
            f"per minute and per day). {hint}"
        )
    return str(error)
