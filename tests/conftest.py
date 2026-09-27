"""Shared fixtures for the offline test suite.

No test in this suite touches the network or needs an API key. The only
place that knows how to reach Groq is `structured_llm`, which analyzer.py
and optimizer.py import into their own namespace, so patching that name on
each module intercepts the provider without touching production code.

The stub still builds a real LangChain runnable, so the chain under test is
the same `ChatPromptTemplate | provider` composition the tool uses. That
means tests assert on the messages that *would* have been sent.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from prompt_optimizer import analyzer, optimizer
from prompt_optimizer.schemas import (
    OptimizedPrompt,
    PromptAnalysis,
    PromptWeakness,
)

SAMPLE_ANALYSIS = PromptAnalysis(
    score=55,
    strengths=["the intent is legible"],
    weaknesses=[
        PromptWeakness(
            issue="no role is assigned",
            severity="critical",
            principle="role",
            suggestion="name a persona with a relevant expertise level",
        )
    ],
)

SAMPLE_OPTIMIZED = OptimizedPrompt(
    sections=[],
    full_prompt="You are a senior engineer. Write a haiku about rain.",
    changes_made=["assigned a role", "added an output format"],
    principles_applied=["role", "output_format"],
)

RESPONSES: dict[type[BaseModel], BaseModel] = {
    PromptAnalysis: SAMPLE_ANALYSIS,
    OptimizedPrompt: SAMPLE_OPTIMIZED,
}


@dataclass
class ProviderCall:
    """One intercepted request to the provider seam."""

    schema: type[BaseModel]
    messages: list[BaseMessage]

    @property
    def system(self) -> str:
        return str(self.messages[0].content)

    @property
    def human(self) -> str:
        return str(self.messages[1].content)


@dataclass
class ProviderSpy:
    """Stands in for `structured_llm`, recording every call it receives."""

    calls: list[ProviderCall] = field(default_factory=list)

    def __call__(self, schema: type[BaseModel]) -> RunnableLambda:
        def respond(rendered: Any) -> BaseModel:
            self.calls.append(ProviderCall(schema, rendered.to_messages()))
            return RESPONSES[schema]

        return RunnableLambda(respond)

    @property
    def only(self) -> ProviderCall:
        assert len(self.calls) == 1, f"expected 1 provider call, got {len(self.calls)}"
        return self.calls[0]


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> ProviderSpy:
    """Intercept the provider seam for both pipeline steps."""
    spy = ProviderSpy()
    monkeypatch.setattr(analyzer, "structured_llm", spy)
    monkeypatch.setattr(optimizer, "structured_llm", spy)
    return spy
