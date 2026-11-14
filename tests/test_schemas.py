"""The Pydantic contracts, which double as the structured-output schema.

Strict structured output forces every reply through these models, so a constraint
that is not validated here is a constraint nothing enforces at runtime.
"""

import pytest

from prompt_lint.principles import PRINCIPLES
from prompt_lint.schemas import OptimizedPrompt, PromptAnalysis, PromptWeakness

from support import analysis, optimized


@pytest.mark.parametrize("score", [-1, 101])
def test_score_outside_bounds_is_rejected(score: int) -> None:
    with pytest.raises(ValueError):
        analysis(score=score)


@pytest.mark.parametrize("score", [0, 100])
def test_score_boundary_values_are_accepted(score: int) -> None:
    assert analysis(score=score).score == score


def test_severity_rejects_undeclared_values() -> None:
    with pytest.raises(ValueError):
        PromptWeakness(
            issue="x", severity="catastrophic", principle="role", suggestion="y"
        )


def test_principle_field_rejects_undeclared_keys() -> None:
    with pytest.raises(ValueError):
        PromptWeakness(issue="x", severity="minor", principle="vibes", suggestion="y")


def test_principles_applied_only_contains_real_principles() -> None:
    """Regression guard: the model once returned display names, not keys,
    and the Principles Applied panel then rendered nothing silently."""
    result = optimized(principles_applied=["role", "output_format"])

    for key in result.principles_applied:
        assert key in PRINCIPLES


def test_optimized_rejects_unknown_principle_keys() -> None:
    with pytest.raises(ValueError):
        optimized(principles_applied=["vibes"])


def test_analysis_without_weaknesses_or_strengths_is_valid():
    """Regression: the model omits empty lists for a strong prompt."""
    result = PromptAnalysis.model_validate({"score": 92})
    assert result.weaknesses == [] and result.strengths == []
