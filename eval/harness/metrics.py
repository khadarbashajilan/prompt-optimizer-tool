"""Aggregation for eval results."""

from __future__ import annotations

import statistics
from collections.abc import Iterable

from .pipeline import Row


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _mean(values: Iterable[int | float]) -> float:
    return round(float(statistics.mean(values)), 1)


def summarize(rows: list[Row]) -> dict:
    """Aggregate rows into the headline numbers. Failed rows are excluded."""
    ok = [row for row in rows if row.error is None]
    summary: dict = {"n_total": len(rows), "n_ok": len(ok), "n_failed": len(rows) - len(ok)}
    if not ok:
        return summary

    lifts = [row.lift for row in ok]
    summary.update({
        "mean_before": _mean(row.before for row in ok),
        "mean_after": _mean(row.after for row in ok),
        "mean_lift": _mean(lifts),
        "median_lift": float(statistics.median(lifts)),
        "pct_improved": _pct(sum(lift > 0 for lift in lifts), len(ok)),
        "pct_unchanged": _pct(sum(lift == 0 for lift in lifts), len(ok)),
        "pct_regressed": _pct(sum(lift < 0 for lift in lifts), len(ok)),
        "mean_section_coverage_pct": round(100 * statistics.mean(row.coverage for row in ok), 1),
    })

    categories: dict[str, dict] = {}
    for name in dict.fromkeys(row.category for row in ok):
        group = [row for row in ok if row.category == name]
        group_lifts = [row.lift for row in group]
        categories[name] = {
            "n": len(group),
            "mean_before": _mean(row.before for row in group),
            "mean_after": _mean(row.after for row in group),
            "mean_lift": _mean(group_lifts),
            "pct_improved": _pct(sum(lift > 0 for lift in group_lifts), len(group)),
            "pct_regressed": _pct(sum(lift < 0 for lift in group_lifts), len(group)),
        }
    summary["by_category"] = categories
    return summary
