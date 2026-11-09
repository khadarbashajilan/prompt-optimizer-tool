"""Measure how much the optimizer improves prompts, using the tool itself.

For every prompt in data/prompts.jsonl the harness runs:

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
import sys
from datetime import datetime
from pathlib import Path

from harness.metrics import summarize
from harness.pipeline import Row, evaluate_one, run_eval
from harness.prompt_io import load_prompts
from harness.report import render_markdown, write_results
from harness.rubric import RUBRIC_SECTIONS, sections_present

DEFAULT_PROMPTS = Path(__file__).with_name("data") / "prompts.jsonl"
DEFAULT_OUT = Path(__file__).with_name("results")
STAMP_FORMAT = "%Y%m%d-%H%M%S"

__all__ = [
    "DEFAULT_OUT",
    "DEFAULT_PROMPTS",
    "RUBRIC_SECTIONS",
    "Row",
    "STAMP_FORMAT",
    "evaluate_one",
    "load_prompts",
    "main",
    "parse_args",
    "render_markdown",
    "run_eval",
    "sections_present",
    "summarize",
    "write_results",
]


def _write_results(
    rows: list[Row],
    summary: dict,
    out_dir: Path,
    model: str = "",
    now: datetime | None = None,
):
    return write_results(rows, summary, out_dir, model, now, stamp_format=STAMP_FORMAT)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate prompt-optimizer on a prompt set.")
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS, help="JSONL prompt file.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N prompts.")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to pause between prompts (free-tier rate limits).",
    )
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
    json_path, md_path = _write_results(rows, summary, args.out, MODEL)
    print(f"\nWrote {json_path}\nWrote {md_path}")
    return 0 if summary["n_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
