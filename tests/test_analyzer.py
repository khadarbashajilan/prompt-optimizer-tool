"""The analyze step: what would be sent to Groq, and what comes back.

These never call the model. The provider seam is intercepted, so the chain
under test is the real one and the assertions are on the exact messages
that would have gone over the wire.
"""

from prompt_optimizer.analyzer import analyze_prompt
from prompt_optimizer.principles import PRINCIPLES, PrincipleKey
from prompt_optimizer.schemas import PromptAnalysis

from conftest import SAMPLE_ANALYSIS, ProviderSpy

RAW = "write code in python to fetch api data"


def test_requests_the_prompt_analysis_contract(provider: ProviderSpy) -> None:
    analyze_prompt(RAW)
    assert provider.only.schema is PromptAnalysis


def test_every_principle_reaches_the_system_prompt(provider: ProviderSpy) -> None:
    """Ties the generated prompt to the table it is generated from.

    principles.py builds ANALYSIS_SYSTEM_PROMPT from PRINCIPLES, so a
    principle added to the table but not rendered would be silently
    invisible to the grader. This fails if that drift ever comes back.
    """
    analyze_prompt(RAW)
    system = provider.only.system

    for key in PrincipleKey.__args__:
        assert key in system, f"{key} missing from the analysis system prompt"
        assert PRINCIPLES[key].analysis in system


def test_raw_prompt_reaches_the_model_verbatim(provider: ProviderSpy) -> None:
    """Templating must not mangle braces, whitespace, or newlines."""
    awkward = "summarise {this} and [that]\n\n  keep  spacing  {intact}"
    analyze_prompt(awkward)

    assert awkward in provider.only.human
    assert provider.only.human.startswith("Analyze this prompt:")


def test_returns_the_parsed_analysis(provider: ProviderSpy) -> None:
    result = analyze_prompt(RAW)

    assert result is SAMPLE_ANALYSIS
    assert result.score == 55
    assert result.weaknesses[0].principle == "role"


def test_result_is_a_validated_model_not_a_dict(provider: ProviderSpy) -> None:
    """Proves the step returns a real schema instance, so the terminal
    can rely on attribute access and Literal fields stay typed."""
    result = analyze_prompt(RAW)

    assert isinstance(result, PromptAnalysis)
    assert isinstance(result.weaknesses[0].severity, str)
    assert result.model_dump()["score"] == 55
