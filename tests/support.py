"""Test doubles and fresh-model factories for the offline test suite.

Nothing in this file touches the network or needs an API key. The fakes
stand in for the only seams the tests care about:

- ``FakeProvider`` replaces ``structured_llm``, so pipeline tests drive the
  real ``ChatPromptTemplate | provider`` composition and can assert on the
  exact messages that would have gone to Groq.
- Model factories return a fresh instance per call, so no test can leak a
  shared Pydantic object into another test's assertions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from prompt_optimizer.schemas import OptimizedPrompt, PromptAnalysis, PromptWeakness


def analysis(
    *,
    score: int = 55,
    weaknesses: list[PromptWeakness] | None = None,
    strengths: tuple[str, ...] = ("the intent is legible",),
) -> PromptAnalysis:
    """Return a fresh, valid PromptAnalysis with one weakness by default."""
    if weaknesses is None:
        weaknesses = [
            PromptWeakness(
                issue="no role is assigned",
                severity="critical",
                principle="role",
                suggestion="name a persona with a relevant expertise level",
            )
        ]
    return PromptAnalysis(
        score=score,
        weaknesses=weaknesses,
        strengths=list(strengths),
    )


def optimized(
    *,
    full_prompt: str = "You are a senior engineer. Summarise the attached report.",
    changes_made: tuple[str, ...] = ("assigned a role", "added an output format"),
    principles_applied: tuple[str, ...] = ("role", "output_format"),
) -> OptimizedPrompt:
    """Return a fresh, valid OptimizedPrompt."""
    return OptimizedPrompt(
        sections=[],
        full_prompt=full_prompt,
        changes_made=list(changes_made),
        principles_applied=list(principles_applied),
    )


# Lazy factories, so every response is a new instance even between tests.
DEFAULT_RESPONSES: Mapping[type[BaseModel], Callable[[], BaseModel]] = {
    PromptAnalysis: analysis,
    OptimizedPrompt: optimized,
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
class FakeProvider:
    """Stands in for ``structured_llm``, recording every call.

    When no canned response is registered for a schema, a fresh default
    instance is built from ``DEFAULT_RESPONSES``. Tests that want a
    specific shape pass their own mapping.
    """

    responses: Mapping[type[BaseModel], Callable[[], BaseModel]] | None = None
    calls: list[ProviderCall] = field(default_factory=list)

    def __call__(self, schema: type[BaseModel]) -> RunnableLambda:
        def respond(rendered: Any) -> BaseModel:
            factory = (self.responses or DEFAULT_RESPONSES).get(schema)
            assert factory is not None, f"no response registered for {schema.__name__}"
            self.calls.append(ProviderCall(schema, rendered.to_messages()))
            return factory()

        return RunnableLambda(respond)

    @property
    def only(self) -> ProviderCall:
        """The single recorded call; fails loudly if there isn't exactly one."""
        assert len(self.calls) == 1, f"expected 1 provider call, got {len(self.calls)}"
        return self.calls[0]

    @property
    def schemas(self) -> list[str]:
        return [call.schema.__name__ for call in self.calls]
