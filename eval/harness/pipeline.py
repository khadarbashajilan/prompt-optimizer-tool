"""Pipeline execution for eval: score, rewrite, rescore."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .rubric import RUBRIC_SECTIONS, sections_present


@dataclass
class Row:
    """Outcome for one prompt. `error` is set when any step failed."""

    id: str
    category: str
    before: int | None = None
    after: int | None = None
    lift: int | None = None
    coverage: float | None = None
    sections_found: list[str] | None = None
    error: str | None = None


def evaluate_one(item: dict, analyze: Callable, optimize: Callable) -> Row:
    """Run the three-step pipeline on one prompt, capturing failures."""
    row = Row(id=item["id"], category=item["category"])
    try:
        first = analyze(item["prompt"])
        rewrite = optimize(item["prompt"], first)
        second = analyze(rewrite.full_prompt)
    except Exception as error:  # one bad prompt must not sink a 24-prompt run
        row.error = f"{type(error).__name__}: {error}"
        return row

    found = sections_present([section.name for section in rewrite.sections], rewrite.full_prompt)
    row.before = first.score
    row.after = second.score
    row.lift = second.score - first.score
    row.sections_found = found
    row.coverage = len(found) / len(RUBRIC_SECTIONS)
    return row


def run_eval(
    items: list[dict],
    analyze: Callable,
    optimize: Callable,
    *,
    delay: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
    on_row: Callable[[Row], None] | None = None,
) -> list[Row]:
    """Evaluate every item in order, pausing `delay` seconds between prompts."""
    rows = []
    for index, item in enumerate(items):
        if index and delay:
            sleep(delay)
        row = evaluate_one(item, analyze, optimize)
        rows.append(row)
        if on_row:
            on_row(row)
    return rows
