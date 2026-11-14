"""LiteLLM boundary: message conversion, schema path, JSON fallback."""

import json
from types import SimpleNamespace

import pytest
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from prompt_lint import llm


class Out(BaseModel):
    answer: str


def reply(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    recorded: list[dict] = []
    monkeypatch.setattr(llm, "ensure_credentials", lambda: None)

    def fake_completion(**kwargs):
        recorded.append(kwargs)
        return reply(json.dumps({"answer": "hi"}))

    monkeypatch.setattr(llm.litellm, "completion", fake_completion)
    return recorded


def run(text: str = "hello"):
    chain = ChatPromptTemplate.from_messages([("system", "sys"), ("human", "{x}")]) | llm.structured_llm(Out)
    return chain.invoke({"x": text})


def test_native_schema_path(calls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm.litellm, "supports_response_schema", lambda model: True)

    assert run().answer == "hi"
    call = calls[0]
    assert call["response_format"] is Out
    assert call["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]


def test_json_mode_fallback_adds_schema_instruction(calls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm.litellm, "supports_response_schema", lambda model: False)

    assert run().answer == "hi"
    call = calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in call["messages"][-1]["content"]


def test_empty_reply_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm, "ensure_credentials", lambda: None)
    monkeypatch.setattr(llm.litellm, "supports_response_schema", lambda model: True)
    monkeypatch.setattr(llm.litellm, "completion", lambda **kw: reply(None))

    with pytest.raises(ValueError, match="empty reply"):
        run()


def test_invalid_json_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm, "ensure_credentials", lambda: None)
    monkeypatch.setattr(llm.litellm, "supports_response_schema", lambda model: True)
    monkeypatch.setattr(llm.litellm, "completion", lambda **kw: reply('{"wrong": 1}'))

    with pytest.raises(ValueError):
        run()
