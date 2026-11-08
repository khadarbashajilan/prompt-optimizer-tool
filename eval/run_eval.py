"""Measure how much the optimizer improves prompts, using the tool itself.

For every prompt in prompts.jsonl the harness runs:

    analyze(original)  ->  optimize(original, analysis)  ->  analyze(rewrite)

and reports the change in score, plus how many of the six structural
sections (role, objective, context, instructions, constraints,
output_format) the rewrite contains.

HONEST FRAMING: the scorer and the rewriter are the same model, so the
score lift is a self-consistency proxy, not an independent measure of
quality. The section coverage is the one objective, model-free number here.

Usage (needs GROQ_API_KEY and network access):

    uv run python eval/run_eval.py
    uv run python eval/run_eval.py --limit 4 --delay 3 --out eval/results
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

# The six sections a well-formed rewrite is expected to contain.
RUBRIC_SECTIONS = (
    "role",
    "objective",
    "context",
    "instructions",
    "constraints",
    "output_format",
)

DEFAULT_PROMPTS = Path(__file__).with_name("prompts.jsonl")
DEFAULT_OUT = Path(__file__).with_name("results")
STAMP_FORMAT = "%Y%m%d-%H%M%S"

# Matches a rubric label at the start of a line, in either form:
#   "## Objective", "### Output format"   (markdown heading, colon optional)
#   "Role:", "**Constraints**:", "output_format:"   (label with a colon)
_NAMES = "|".join(s.replace("_", "[ _]") for s in RUBRIC_SECTIONS)
_LABEL = re.compile(
    rf"^[ \t]*(?:#+[ \t]*(?P<h>{_NAMES})[ \t]*:?[ \t]*$"
    rf"|(?:\*\*|__)?(?P<l>{_NAMES})(?:\*\*|__)?[ \t]*:)",
    re.IGNORECASE | re.MULTILINE,
)


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


def load_prompts(path: Path) -> list[dict]:
    """Read a JSONL file of {id, category, prompt}; blank lines are skipped.

    Raises:
        ValueError: If a line is not valid JSON or lacks a required field.
    """
    items = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: invalid JSON ({error.msg})") from error
        missing = {"id", "category", "prompt"} - item.keys()
        if missing:
            raise ValueError(f"{path}:{number}: missing {sorted(missing)}")
        items.append(item)
    return items


def sections_present(section_names: list[str], full_prompt: str) -> list[str]:
    """Return which rubric sections a rewrite contains, in rubric order.

    A section counts if the model labelled one with that name, or if the
    prompt text itself has a line starting with the label (``Role:``,
    ``## Objective``, ``**Output format**:`` ...). Model-free and
    deterministic, so it does not inherit the scorer's bias.
    """
    found = {name.strip().lower().replace(" ", "_") for name in section_names}
    for match in _LABEL.finditer(full_prompt):
        found.add((match.group("h") or match.group("l")).lower().replace(" ", "_"))
    return [s for s in RUBRIC_SECTIONS if s in found]


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

    found = sections_present([s.name for s in rewrite.sections], rewrite.full_prompt)
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


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def summarize(rows: list[Row]) -> dict:
    """Aggregate rows into the headline numbers. Failed rows are excluded."""
    ok = [r for r in rows if r.error is None]
    summary: dict = {"n_total": len(rows), "n_ok": len(ok), "n_failed": len(rows) - len(ok)}
    if not ok:
        return summary

    lifts = [r.lift for r in ok]
    summary.update({
        "mean_before": round(float(statistics.mean(r.before for r in ok)), 1),
        "mean_after": round(float(statistics.mean(r.after for r in ok)), 1),
        "mean_lift": round(float(statistics.mean(lifts)), 1),
        "median_lift": float(statistics.median(lifts)),
        "pct_improved": _pct(sum(l > 0 for l in lifts), len(ok)),
        "pct_unchanged": _pct(sum(l == 0 for l in lifts), len(ok)),
        "pct_regressed": _pct(sum(l < 0 for l in lifts), len(ok)),
        "mean_section_coverage_pct": round(100 * statistics.mean(r.coverage for r in ok), 1),
    })

    categories: dict[str, dict] = {}
    for name in dict.fromkeys(r.category for r in ok):
        group = [r for r in ok if r.category == name]
        categories[name] = {
            "n": len(group),
            "mean_before": round(float(statistics.mean(r.before for r in group)), 1),
            "mean_after": round(float(statistics.mean(r.after for r in group)), 1),
            "mean_lift": round(float(statistics.mean(r.lift for r in group)), 1),
            "pct_improved": _pct(sum(r.lift > 0 for r in group), len(group)),
            "pct_regressed": _pct(sum(r.lift < 0 for r in group), len(group)),
        }
    summary["by_category"] = categories
    return summary


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
        for name, c in summary["by_category"].items():
            lines.append(
                f"| {name} | {c['n']} | {c['mean_before']} | {c['mean_after']} | "
                f"{c['mean_lift']:+} | {c['pct_improved']}% | {c['pct_regressed']}% |"
            )
        lines += ["", "## Per prompt", "", "| ID | Before | After | Lift | Sections |", "|---|---|---|---|---|"]
        for r in rows:
            if r.error is None:
                lines.append(
                    f"| {r.id} | {r.before} | {r.after} | {r.lift:+} | "
                    f"{len(r.sections_found)}/{len(RUBRIC_SECTIONS)} |"
                )
    failed = [r for r in rows if r.error]
    if failed:
        lines += ["", "## Failures", ""]
        lines += [f"- `{r.id}`: {r.error}" for r in failed]
    return "\n".join(lines) + "\n"


def write_results(rows: list[Row], summary: dict, out_dir: Path, model: str = "",
                  now: datetime | None = None) -> tuple[Path, Path]:
    """Write <stamp>.json and <stamp>.md into out_dir; return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime(STAMP_FORMAT)
    json_path = out_dir / f"{stamp}.json"
    md_path = out_dir / f"{stamp}.md"
    payload = {"model": model, "summary": summary, "rows": [asdict(r) for r in rows]}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(rows, summary, model), encoding="utf-8")
    return json_path, md_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate prompt-optimizer on a prompt set.")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS, help="JSONL prompt file.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N prompts.")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds to pause between prompts (free-tier rate limits).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Results folder.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Imported here so --help and the unit tests never need an API key.
    from prompt_optimizer_tool.analyzer import analyze_prompt
    from prompt_optimizer_tool.config import MODEL, MissingAPIKeyError, api_key
    from prompt_optimizer_tool.optimizer import optimize_prompt

    try:
        api_key()
    except MissingAPIKeyError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    items = load_prompts(args.prompts)
    if args.limit is not None:
        items = items[: args.limit]
    if not items:
        print("No prompts to run.", file=sys.stderr)
        return 1

    def progress(row: Row) -> None:
        status = row.error or f"{row.before} -> {row.after} ({row.lift:+})"
        print(f"[{row.id}] {status}", flush=True)

    rows = run_eval(items, analyze_prompt, optimize_prompt, delay=args.delay, on_row=progress)
    summary = summarize(rows)
    json_path, md_path = write_results(rows, summary, args.out, MODEL)
    print(f"\nWrote {json_path}\nWrote {md_path}")
    return 0 if summary["n_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
