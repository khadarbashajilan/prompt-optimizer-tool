"""Offline tests. No API key and no network needed.

These cover the pure logic that the terminal UI depends on: severity
colours, score thresholds, principle lookups, filename generation, and the
schema constraints that the LLM reply is forced to satisfy.
"""

from datetime import datetime
from pathlib import Path

import pytest

from prompt_optimizer.cli import score_colour, severity_style
from prompt_optimizer.principles import PRINCIPLES, PrincipleKey, principle_name
from prompt_optimizer.schemas import OptimizedPrompt, PromptAnalysis, PromptWeakness
from prompt_optimizer.storage import new_output_path, write_output


# --- score and severity presentation -------------------------------------

@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "green"), (70, "green"), (69, "yellow"), (40, "yellow"), (39, "red"), (0, "red")],
)
def test_score_colour_thresholds(score: int, expected: str) -> None:
    assert score_colour(score) == expected


def test_every_severity_has_a_style() -> None:
    for severity in ("critical", "major", "minor"):
        assert severity_style(severity)  # non-empty, and no KeyError


# --- principles ----------------------------------------------------------

def test_principle_keys_match_the_declared_literal() -> None:
    """The dict keys and the PrincipleKey Literal must not drift apart."""
    assert set(PRINCIPLES) == set(PrincipleKey.__args__)


def test_every_principle_is_fully_populated() -> None:
    for key, principle in PRINCIPLES.items():
        for field in ("name", "description", "analysis", "rewrite"):
            assert getattr(principle, field).strip(), f"{key} has an empty {field}"


def test_principle_name_falls_back_to_the_key() -> None:
    assert principle_name("role") == PRINCIPLES["role"].name
    assert principle_name("not-a-real-key") == "not-a-real-key"


# --- schemas -------------------------------------------------------------

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


# --- storage -------------------------------------------------------------

def test_output_path_uses_date_and_time(tmp_path: Path) -> None:
    now = datetime(2026, 9, 27, 14, 32, 5)
    path = new_output_path(tmp_path, now=now)

    assert path.name == "optimized-20260927-143205.md"
    assert path.parent == tmp_path


def test_same_second_runs_do_not_collide(tmp_path: Path) -> None:
    now = datetime(2026, 9, 27, 14, 32, 5)
    first = new_output_path(tmp_path, now=now)
    write_output("first", first)
    second = new_output_path(tmp_path, now=now)

    assert second != first
    assert second.name == "optimized-20260927-143205-2.md"


def test_write_output_creates_missing_folders(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "optimized-20260927-143205.md"
    write_output("hello", path)

    assert path.read_text(encoding="utf-8") == "hello"
