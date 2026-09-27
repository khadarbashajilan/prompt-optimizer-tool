"""The optimize step: it must consume the analysis, not recompute it.

optimizer.py claims in its docstring that the analysis is "passed in
rather than recomputed, so the rewrite targets the exact weaknesses that
were found instead of re-guessing them." Nothing protected that, so a
refactor could have quietly reintroduced a second analysis call and
doubled both the latency and the cost of every run.
"""

import json

from prompt_optimizer.optimizer import optimize_prompt
from prompt_optimizer.principles import PRINCIPLES, PrincipleKey
from prompt_optimizer.schemas import OptimizedPrompt, PromptAnalysis, PromptWeakness

from conftest import SAMPLE_ANALYSIS, SAMPLE_OPTIMIZED, ProviderSpy

RAW = "write code in python to fetch api data"


def test_requests_the_optimized_prompt_contract(provider: ProviderSpy) -> None:
    optimize_prompt(RAW, SAMPLE_ANALYSIS)
    assert provider.only.schema is OptimizedPrompt


def test_does_not_re_analyze(provider: ProviderSpy) -> None:
    """The regression guard.

    optimize_prompt is handed a finished analysis. It must make exactly
    one provider call, for OptimizedPrompt. Two calls would mean the
    grader was re-run: double the tokens, double the latency, and a
    second opinion that can contradict the weaknesses it was given.
    """
    optimize_prompt(RAW, SAMPLE_ANALYSIS)

    requested = [call.schema.__name__ for call in provider.calls]
    assert requested == ["OptimizedPrompt"], requested


def test_analysis_travels_as_machine_readable_json(provider: ProviderSpy) -> None:
    """The rewriter gets structured data, not prose.

    The weaknesses have to survive as fields, otherwise the rewriter is
    pattern-matching on English and the score/severity link is lost.
    """
    optimize_prompt(RAW, SAMPLE_ANALYSIS)
    human = provider.only.human

    assert "Analysis:" in human
    payload = json.loads(human[human.index("Analysis:") + len("Analysis:"):].strip())

    assert payload["score"] == 55
    assert payload["weaknesses"][0]["principle"] == "role"
    assert payload["weaknesses"][0]["severity"] == "critical"


def test_rewriter_sees_the_flagged_principles_by_name(provider: ProviderSpy) -> None:
    optimize_prompt(RAW, SAMPLE_ANALYSIS)
    system = provider.only.system

    for key in PrincipleKey.__args__:
        assert key in system, f"{key} missing from the rewrite system prompt"
        assert PRINCIPLES[key].rewrite in system


def test_original_prompt_travels_untouched(provider: ProviderSpy) -> None:
    awkward = "refactor {module} -> keep {backwards} compat"
    optimize_prompt(awkward, SAMPLE_ANALYSIS)

    assert awkward in provider.only.human
    assert provider.only.human.startswith("Original prompt:")


def test_returns_the_validated_rewrite(provider: ProviderSpy) -> None:
    result = optimize_prompt(RAW, SAMPLE_ANALYSIS)

    assert result is SAMPLE_OPTIMIZED
    assert isinstance(result, OptimizedPrompt)
    assert result.full_prompt.startswith("You are a senior engineer.")


def test_reported_principles_all_resolve(provider: ProviderSpy) -> None:
    """A principle key the terminal cannot look up renders as a blank
    panel, so every value must resolve against the table."""
    result = optimize_prompt(RAW, SAMPLE_ANALYSIS)

    for key in result.principles_applied:
        assert key in PRINCIPLES
        assert PRINCIPLES[key].name


def test_forwards_a_different_analysis_verbatim(provider: ProviderSpy) -> None:
    """Guards against the step being hardwired to the fixture's sample.

    A weak, unrelated analysis must be the one that reaches the model.
    """
    other = PromptAnalysis(
        score=8,
        weaknesses=[
            PromptWeakness(
                issue="no measurable success criteria",
                severity="minor",
                principle="success_criteria",
                suggestion="state what a good answer must contain",
            )
        ],
        strengths=[],
    )
    optimize_prompt(RAW, other)
    human = provider.only.human
    payload = json.loads(human[human.index("Analysis:") + len("Analysis:"):].strip())

    assert payload["score"] == 8
    assert payload["weaknesses"][0]["principle"] == "success_criteria"
    assert "no measurable success criteria" in human
