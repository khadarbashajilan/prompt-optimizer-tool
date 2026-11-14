"""Fixtures for the offline test suite.

Fixtures only — every reusable double or factory lives in support.py.

Two seams are patched, at the two boundaries the tests exercise:

- ``provider`` replaces ``structured_llm`` inside analyzer and optimizer,
  so pipeline tests run the real chain composition without a network.
- ``pipeline`` replaces ``analyze_prompt``/``optimize_prompt`` inside the
  cli module, so CLI tests cover argument parsing through file writing
  with the two LLM steps stubbed out.

Production code is never modified by the tests themselves; patches are
undone by monkeypatch.
"""

from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner

from prompt_lint import analyzer, cli, optimizer
from prompt_lint.config import MissingAPIKeyError
from prompt_lint.schemas import PromptAnalysis

from support import FakeProvider, analysis, optimized


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    """Intercept the provider seam used by both pipeline steps."""
    fake = FakeProvider()
    monkeypatch.setattr(analyzer, "structured_llm", fake)
    monkeypatch.setattr(optimizer, "structured_llm", fake)
    return fake


@dataclass
class FakePipeline:
    """Stands in for the two LLM steps the CLI drives.

    Records every prompt and analysis it receives. Set ``analysis_error``
    or ``optimize_error`` to simulate a provider failure at either step.
    """

    analysis_error: Exception | None = None
    optimize_error: Exception | None = None
    prompts: list[str] = field(default_factory=list)
    analyses: list[PromptAnalysis] = field(default_factory=list)

    def analyze_prompt(self, prompt_text: str) -> PromptAnalysis:
        """Record the prompt and return a canned analysis (or raise)."""
        self.prompts.append(prompt_text)
        if self.analysis_error:
            raise self.analysis_error
        return analysis()

    def optimize_prompt(self, prompt_text: str, received: PromptAnalysis) -> PromptAnalysis:
        """Record the forwarded analysis and return a canned rewrite (or raise)."""
        self.analyses.append(received)
        if self.optimize_error:
            raise self.optimize_error
        return optimized()

    @property
    def prompt(self) -> str:
        """The single prompt the pipeline received."""
        assert len(self.prompts) == 1, f"expected 1 prompt, got {len(self.prompts)}"
        return self.prompts[0]


@pytest.fixture
def runner() -> CliRunner:
    """Click's test runner; output is captured plain (Rich renders no ANSI)."""
    return CliRunner()


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> FakePipeline:
    """Intercept the LLM steps at the CLI boundary."""
    fake = FakePipeline()
    monkeypatch.setattr(cli, "analyze_prompt", fake.analyze_prompt)
    monkeypatch.setattr(cli, "optimize_prompt", fake.optimize_prompt)
    return fake


@pytest.fixture
def placeholder_error() -> MissingAPIKeyError:
    """The actionable error a placeholder key must produce."""
    return MissingAPIKeyError(
        "GEMINI_API_KEY is still a placeholder value. Replace it with a real key."
    )
