"""Model access and structured output, via LiteLLM.

The only place that knows how to talk to a provider. LiteLLM gives one
call signature for OpenAI, Anthropic, Gemini, Ollama and many others, so
switching provider is a change of model string, not of code.
"""

import json
from typing import Any, TypeVar

import litellm
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

from .config import (
    API_BASE,
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL,
    REQUEST_TIMEOUT,
    TEMPERATURE,
    ensure_credentials,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Silently ignore parameters a given provider does not support instead of
# failing the request; lets one set of settings work across providers.
litellm.drop_params = True

_ROLES = {"human": "user", "ai": "assistant", "system": "system"}


def _to_messages(prompt_value: Any) -> list[dict[str, str]]:
    """Convert a LangChain prompt value into LiteLLM chat messages."""
    messages: list[BaseMessage] = prompt_value.to_messages()
    return [
        {"role": _ROLES.get(message.type, "user"), "content": str(message.content)}
        for message in messages
    ]


def _supports_json_schema() -> bool:
    try:
        return bool(litellm.supports_response_schema(model=MODEL))
    except Exception:
        return False


def _complete(schema: type[SchemaT], messages: list[dict[str, str]]) -> SchemaT:
    ensure_credentials()

    if _supports_json_schema():
        response_format: Any = schema
    else:
        # Provider has no native schema enforcement: ask for JSON mode and
        # describe the schema in the prompt. Validation below still applies.
        response_format = {"type": "json_object"}
        instruction = (
            "Reply with a single JSON object matching this JSON Schema, "
            "and nothing else:\n" + json.dumps(schema.model_json_schema())
        )
        messages = [*messages, {"role": "system", "content": instruction}]

    response = litellm.completion(
        model=MODEL,
        messages=messages,
        response_format=response_format,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        num_retries=MAX_RETRIES,
        timeout=REQUEST_TIMEOUT,
        api_base=API_BASE,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise ValueError(
            "The model returned an empty reply. If it is a reasoning model, "
            "raise PLINT_MAX_TOKENS."
        )
    return schema.model_validate_json(content)


def structured_llm(schema: type[SchemaT]) -> Runnable[Any, SchemaT]:
    """Return a runnable that yields a validated instance of schema.

    Uses the provider's native JSON-schema mode where LiteLLM reports it
    is supported, and falls back to JSON mode plus an in-prompt schema
    otherwise. Either way the reply is validated with Pydantic.

    Args:
        schema: The Pydantic model the reply must conform to.

    Returns:
        A runnable accepting a prompt value and producing that model.
    """
    return RunnableLambda(lambda prompt_value: _complete(schema, _to_messages(prompt_value)))
