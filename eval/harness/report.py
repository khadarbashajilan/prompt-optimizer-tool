"""Markdown/JSON result rendering for eval."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .pipeline import Row
from .rubric import RUBRIC_SECTIONS


def render_markdown(rows: list[Row], summary: dict, model: str = "") -> str:
    """Render the summary and per-prompt table as GitHub-flavoured markdown."""
    lines = ["# Evaluation results", ""]
    if model:
        lines += [f"Model: `{model}`", ""]
    lines += [
        "> Same-model proxy: the model that rewrites a prompt also scores it, "
        "so lift measures self-consistency, not independent quality. "
        "Section coverage is model-free.",
        "",
        f"Prompts: {summary['n_ok']} scored, {summary['n_failed']} failed, "
        f"{summary['n_total']} total.",
        "",
    ]
    if summary["n_ok"]:
        lines += [
            "| Metric | Value |",
            "|---|---|",
            f"| Mean score before | {summary['mean_before']} |",
            f"| Mean score after | {summary['mean_after']} |",
            f"| Mean lift | {summary['mean_lift']:+} |",
            f"| Median lift | {summary['median_lift']:+} |",
            f"| Improved | {summary['pct_improved']}% |",
            f"| Unchanged | {summary['pct_unchanged']}% |",
            f"| Regressed | {summary['pct_regressed']}% |",
            f"| Rubric section coverage | {summary['mean_section_coverage_pct']}% |",
            "",
            "## By category",
            "",
            "| Category | N | Before | After | Mean lift | Improved | Regressed |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, category in summary["by_category"].items():
            lines.append(
                f"| {name} | {category['n']} | {category['mean_before']} | {category['mean_after']} | "
                f"{category['mean_lift']:+} | {category['pct_improved']}% | {category['pct_regressed']}% |"
            )
        lines += ["", "## Per prompt", "", "| ID | Before | After | Lift | Sections |", "|---|---|---|---|---|"]
        for row in rows:
            if row.error is None:
                lines.append(
                    f"| {row.id} | {row.before} | {row.after} | {row.lift:+} | "
                    f"{len(row.sections_found)}/{len(RUBRIC_SECTIONS)} |"
                )
    failed = [row for row in rows if row.error]
    if failed:
        lines += ["", "## Failures", ""]
        lines += [f"- `{row.id}`: {row.error}" for row in failed]
    return "\n".join(lines) + "\n"


def write_results(
    rows: list[Row],
    summary: dict,
    out_dir: Path,
    model: str = "",
    now: datetime | None = None,
    stamp_format: str = "%Y%m%d-%H%M%S",
) -> tuple[Path, Path]:
    """Write <stamp>.json and <stamp>.md into out_dir; return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime(stamp_format)
    json_path = out_dir / f"{stamp}.json"
    md_path = out_dir / f"{stamp}.md"
    payload = {"model": model, "summary": summary, "rows": [asdict(row) for row in rows]}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(rows, summary, model), encoding="utf-8")
    return json_path, md_path
