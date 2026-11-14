"""Rich terminal rendering for the CLI.

All visual concerns live here: the shared console, the colour mappings,
and the three report panels/tables. `cli.py` only decides what to render.
"""

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ..principles import PRINCIPLES, principle_name
from ..schemas import OptimizedPrompt, PromptAnalysis, Severity

THEME = Theme({
    "brand": "bold cyan",
    "good": "bold green",
    "warn": "bold yellow",
    "bad": "bold red",
})

console = Console(theme=THEME)


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
    console.print(Rule("[bold brand]Prompt Engineering Principles[/]", style="brand"))
    table = Table(
        box=box.SIMPLE,
        title_style="bold cyan",
    )
    table.add_column("Key", style="bold green")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    for key, principle in PRINCIPLES.items():
        table.add_row(key, principle.name, principle.description)
    console.print(table)
