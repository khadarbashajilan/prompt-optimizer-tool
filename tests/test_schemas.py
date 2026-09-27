"""The Pydantic contracts, which double as the structured-output schema.

Groq's strict mode forces every reply through these, so a constraint that
is not tested here is a constraint nothing enforces at runtime either.
"""

import pytest

from prompt_optimizer.principles import PRINCIPLES
from prompt_optimizer.schemas import OptimizedPrompt, PromptAnalysis, PromptWeakness


def test_score_must_be_within_range() -> None:
    with pytest.raises(ValueError):
        PromptAnalysis(score=101, weaknesses=[], strengths=[])
    with pytest.raises(ValueError):
        PromptAnalysis(score=-1, weaknesses=[], strengths=[])


def test_severity_rejects_undeclared_values() -> None:
    """Strict mode should make this impossible from the LLM, but validate anyway."""
    with pytest.raises(ValueError):
        PromptWeakness(
            issue="x", severity="catastrophic", principle="role", suggestion="y"
        )


def test_principle_field_rejects_undeclared_keys() -> None:
    with pytest.raises(ValueError):
        PromptWeakness(
            issue="x", severity="minor", principle="vibes", suggestion="y"
        )


def test_principles_applied_resolves_to_real_principles() -> None:
    """Regression test.

    The LLM used to return names like "1. Role and Persona Definition" while
    the lookup table was keyed by "role", so the Principles Applied panel
    silently rendered nothing. Keys are now enforced by the schema, so every
    returned value must resolve.
    """
    optimized = OptimizedPrompt(
        sections=[],
        full_prompt="rewritten",
        changes_made=["added a role"],
        principles_applied=["role", "output_format"],
    )
    for key in optimized.principles_applied:
        assert PRINCIPLES[key].name
