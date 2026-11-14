"""User-facing error messages for the CLI."""

import litellm


def describe_error(error: Exception) -> str:
    """Turn a pipeline failure into a message a user can act on.

    LiteLLM already retried before this point, so a RateLimitError that
    reaches here means waiting is the only fix.
    """
    if isinstance(error, litellm.RateLimitError):
        response = getattr(error, "response", None)
        wait = response.headers.get("retry-after") if response is not None else None
        hint = f"Try again in about {wait} seconds." if wait else "Wait a minute and try again."
        return f"Rate limit reached. {hint}"
    if isinstance(error, litellm.AuthenticationError):
        return "The provider rejected your API key. Re-run `plint setup`."
    return str(error)
