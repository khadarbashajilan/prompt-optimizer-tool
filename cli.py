"""Command-line entry point: argument parsing and terminal output.

This module only handles presentation and input gathering. It calls
analyzer and optimizer, then renders whatever comes back. The one piece of
real logic here is score_colour and severity_style, which map a number or a
severity onto a terminal colour.
"""

import sys
from pathlib import Path

import click
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from analyzer import analyze_prompt
from config import DEFAULT_OUTPUT_DIR, MissingAPIKeyError
from optimizer import optimize_prompt
from principles import PRINCIPLES, principle_name
from schemas import OptimizedPrompt, PromptAnalysis, Severity
from storage import new_output_path, write_output

console = Console()

USAGE_HINT = """Usage: prompt-optimizer optimize [PROMPT]
   or: prompt-optimizer optimize --file prompt.txt
   or: cat prompt.txt | prompt-optimizer optimize"""


def score_colour(score: int) -> str:
    """Return the terminal colour for a 0-100 quality score."""
    if score >= 70:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


def severity_style(severity: Severity) -> str:
    """Return the terminal style for a weakness severity."""
    return {
        "critical": "bold red",
        "major": "yellow",
        "minor": "dim",
    }[severity]


def render_analysis(analysis: PromptAnalysis) -> None:
    """Print the score, strengths, and weaknesses tables."""
    colour = score_colour(analysis.score)
    console.print(Panel(
        Text(f"{analysis.score}/100", style=f"bold {colour}", justify="center"),
        title="Quality Score",
        border_style=colour,
        width=20,
    ))

    if analysis.strengths:
        strengths = Table(
            box=box.SIMPLE,
            title="Strengths",
            title_style="bold green",
            border_style="green",
        )
        strengths.add_column()
        for strength in analysis.strengths:
            strengths.add_row(f"  {strength}")
        console.print(strengths)

    if analysis.weaknesses:
        table = Table(
            box=box.SIMPLE,
            title="Weaknesses and Improvements",
            title_style="bold yellow",
            border_style="yellow",
        )
        table.add_column("Issue", style="bold red")
        table.add_column("Severity", style="bold")
        table.add_column("Principle", style="blue")
        table.add_column("Suggestion")
        for weakness in analysis.weaknesses:
            table.add_row(
                weakness.issue,
                Text(weakness.severity, style=severity_style(weakness.severity)),
                principle_name(weakness.principle),
                weakness.suggestion,
            )
        console.print(table)


def render_optimized(optimized: OptimizedPrompt) -> None:
    """Print the changes, the rewritten prompt, and the principles used."""
    changes = "\n".join(f"  + {change}" for change in optimized.changes_made)
    console.print(Panel(
        changes,
        title="Changes Made",
        border_style="green",
        width=60,
    ))

    console.print(Panel(
        Markdown(optimized.full_prompt),
        title="Optimized Prompt",
        border_style="cyan",
        subtitle="Copy the markdown section above",
    ))

    applied = [
        Panel(
            f"[bold]{PRINCIPLES[key].name}[/bold]\n  {PRINCIPLES[key].description}",
            border_style="dim",
            width=50,
        )
        for key in dict.fromkeys(optimized.principles_applied)
    ]
    if applied:
        console.print(Columns(applied, title="Principles Applied"))


def render_principles() -> None:
    """Print the table of all prompting principles."""
    table = Table(
        box=box.SIMPLE,
        title="Prompt Engineering Principles",
        title_style="bold cyan",
    )
    table.add_column("Key", style="bold green")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    for key, principle in PRINCIPLES.items():
        table.add_row(key, principle.name, principle.description)
    console.print(table)


def read_prompt(prompt: str | None, filepath: str | None) -> str | None:
    """Resolve the prompt from a file, an argument, or stdin.

    Args:
        prompt: The prompt given as a positional argument, if any.
        filepath: Path given via --file, if any.

    Returns:
        The prompt text, or None if nothing was supplied. In that case the
        usage hint has already been printed.
    """
    if filepath:
        return Path(filepath).read_text(encoding="utf-8")

    if prompt:
        return prompt

    # Only treat stdin as a source when it is a pipe, otherwise an
    # interactive terminal would block waiting for input.
    if not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            return piped

    click.echo(USAGE_HINT)
    return None


def run(prompt: str, output_dir: str) -> Path | None:
    """Analyze, then optimize, then render and save the result.

    Args:
        prompt: The raw prompt text.
        output_dir: Folder to write the rewritten prompt into.

    Returns:
        The file the rewrite was saved to, or None if a step failed.
    """
    console.print(Panel(prompt, title="Original Prompt", border_style="bright_black"))

    try:
        with console.status("Analyzing prompt..."):
            analysis = analyze_prompt(prompt)
    except MissingAPIKeyError as error:
        console.print(f"[red]Error:[/red] {error}")
        return None
    except Exception as error:
        console.print(f"[red]API Error:[/red] {error}")
        return None

    console.print()
    render_analysis(analysis)
    console.print()

    try:
        with console.status("Optimizing prompt..."):
            optimized = optimize_prompt(prompt, analysis)
    except Exception as error:
        console.print(f"[red]Optimization Error:[/red] {error}")
        return None

    render_optimized(optimized)

    path = write_output(optimized.full_prompt, new_output_path(output_dir))
    console.print(f"\n[green]Saved to[/green] [bold]{path}[/bold]")
    return path


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Prompt Optimizer — analyze and rewrite prompts following best practices.

    Analyzes a prompt against 10 engineering principles, scores it 0-100,
    identifies weaknesses, and rewrites it into a structured prompt.

    Input sources:
        [PROMPT] argument, --file PATH, or pipe from stdin.

    Examples:

        prompt-optimizer optimize "write code to fetch API data"

        prompt-optimizer optimize --file prompt.txt

        echo "explain AI" | prompt-optimizer optimize
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()


@cli.command()
@click.argument("prompt", required=False)
@click.option("--file", "-f", "filepath", type=click.Path(exists=True, dir_okay=False),
              help="Read the prompt from a file.")
@click.option("--out", "output_dir", default=DEFAULT_OUTPUT_DIR, show_default=True,
              help="Folder to save the rewritten prompt into.")
def optimize(prompt: str | None, filepath: str | None, output_dir: str) -> None:
    """Analyze and optimize a prompt, then save the result.

    Accepts input as an argument, from a file, or via stdin pipe. Every run
    is saved to its own timestamped file in the output folder.
    """
    if not (text := read_prompt(prompt, filepath)):
        return
    run(text, output_dir)


@cli.command(name="list")
def list_principles() -> None:
    """List all available prompting principles."""
    render_principles()


if __name__ == "__main__":
    cli()
