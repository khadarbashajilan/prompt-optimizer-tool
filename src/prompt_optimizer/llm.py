"""Model construction and structured output.

The only place that knows how to talk to Groq. Both analysis and
optimization go through here, which is what lets them evolve
independently while sharing one client configuration.
"""

from typing import TypeVar

from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel

from .config import (
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL,
    REQUEST_TIMEOUT,
    TEMPERATURE,
    api_key,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def get_llm() -> ChatGroq:
    """Build a Groq chat model from the settings in config.

    Returns:
        A ChatGroq instance ready to invoke.

    Raises:
        MissingAPIKeyError: If GROQ_API_KEY is unset or empty.
    """
    return ChatGroq(
        model=MODEL,
        groq_api_key=api_key(),
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        max_retries=MAX_RETRIES,
        request_timeout=REQUEST_TIMEOUT,
    )


def structured_llm(schema: type[SchemaT]) -> Runnable[dict, SchemaT]:
    """Wrap the model so every reply is a validated instance of schema.

    Uses Groq Structured Outputs in strict mode rather than tool calling:
    gpt-oss does not support tool use together with Structured Outputs,
    and strict mode guarantees schema-valid JSON via constrained decoding.

    A side benefit of constrained decoding is that Literal fields, such as
    severity or principle keys, can only ever come back as declared values.

    Args:
        schema: The Pydantic model the reply must conform to.

    Returns:
        A runnable that yields instances of that model.
    """
    return get_llm().with_structured_output(schema, method="json_schema", strict=True)
