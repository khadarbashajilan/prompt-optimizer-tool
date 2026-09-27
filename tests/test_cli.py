"""Terminal presentation: how a score and a severity become a colour.

The mapping from numbers to terminal styling is pure and easy to break
silently, so the thresholds are pinned on both sides of each boundary.
"""

import pytest

from prompt_optimizer.cli import score_colour, severity_style


@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "green"), (70, "green"), (69, "yellow"), (40, "yellow"), (39, "red"), (0, "red")],
)
def test_score_colour_thresholds(score: int, expected: str) -> None:
    assert score_colour(score) == expected


def test_every_severity_has_a_style() -> None:
    for severity in ("critical", "major", "minor"):
        assert severity_style(severity)  # non-empty, and no KeyError
