"""Command-line entry point: argument parsing and terminal output.

This module only handles presentation and input gathering. It calls
analyzer and optimizer, then renders whatever comes back. The one piece of
real logic here is score_colour and severity_style, which map a number or a
severity onto a terminal colour.
"""

import sys
from pathlib import Path
from typing import Any, Callable

import click
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.traceback import install as install_traceback

from ..analyzer import analyze_prompt
from ..config import DEFAULT_OUTPUT_DIR, MissingAPIKeyError, PLACEHOLDER_KEYS, save_api_key
from ..optimizer import optimize_prompt
from ..storage import new_output_path, write_output
from .errors import describe_error
from .ui import (
    console,
    render_analysis,
    render_optimized,
    render_principles,
    score_colour,
    severity_style,
)

USAGE_HINT = """Usage: prompt-optimizer optimize [PROMPT]
   or: prompt-optimizer optimize --file prompt.txt
   or: cat prompt.txt | prompt-optimizer optimize"""


def read_prompt(prompt: str | None, filepath: str | None) -> str:
    """Resolve the prompt from a file, an argument, or stdin.

    Args:
        prompt: The prompt given as a positional argument, if any.
        filepath: Path given via --file, if any.

    Returns:
        The prompt text, preserved exactly as given, whatever the source.

    Raises:
        click.UsageError: If no source produced any non-empty text.
    """
    if filepath:
        return Path(filepath).read_text(encoding="utf-8")

    if prompt:
        return prompt

    # Only treat stdin as a source when it is a pipe, otherwise an
    # interactive terminal would block waiting for input. Whitespace is
    # preserved: leading or trailing newlines can be meaningful in prompts.
    if not sys.stdin.isatty():
        piped = sys.stdin.read()
        if piped.strip():
            return piped

    raise click.UsageError(f"No prompt text was given.\n{USAGE_HINT}")


def _run_step(description: str, step: Callable[[], Any]) -> Any:
    """Run one pipeline step under an indeterminate progress spinner."""
    with Progress(
        SpinnerColumn(style="brand"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description, total=None)
        result = step()
        progress.update(task, completed=1)
        return result


def run(prompt: str, output_dir: str) -> Path | None:
    """Analyze, then optimize, then render and save the result.

    Args:
        prompt: The raw prompt text.
        output_dir: Folder to write the rewritten prompt into.

    Returns:
        The file the rewrite was saved to, or None if a step failed.
    """
    console.print(Panel(prompt, title="Original Prompt", border_style="bright_black"))
    console.print(Rule(style="dim"))

    try:
        analysis = _run_step("[bold cyan]Analyzing prompt...", lambda: analyze_prompt(prompt))
    except MissingAPIKeyError as error:
        console.print(f"[bad]Error:[/bad] {error}")
        return None
    except Exception as error:
        console.print(f"[bad]API Error:[/bad] {describe_error(error)}")
        return None

    render_analysis(analysis)
    console.print()

    try:
        optimized = _run_step("[bold green]Optimizing prompt...", lambda: optimize_prompt(prompt, analysis))
    except Exception as error:
        console.print(f"[bad]Optimization Error:[/bad] {describe_error(error)}")
        return None

    render_optimized(optimized)

    path = write_output(optimized.full_prompt, new_output_path(output_dir))
    console.print(f"\n[good]Saved to[/good] [bold]{path}[/bold]")
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
    install_traceback(console=console, show_locals=False)
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

    Raises:
        SystemExit: Status 1 if a pipeline step failed, so callers and
            scripts can rely on the exit status. Missing input raises
            click.UsageError (status 2) instead.
    """
    text = read_prompt(prompt, filepath)
    if run(text, output_dir) is None:
        sys.exit(1)


@cli.command(name="list")
def list_principles() -> None:
    """List all available prompting principles."""
    render_principles()


@cli.command(name="setup")
def setup() -> None:
    """Configure your Groq API key interactively."""
    console.print(Panel(
        "A free Groq API key is required (no credit card needed).\n"
        "Get your key at: [bold cyan]https://console.groq.com/keys[/bold cyan]",
        title="[brand]Prompt Optimizer Setup[/brand]",
        border_style="cyan",
    ))
    key = click.prompt("Enter your Groq API key", default="", hide_input=True, show_default=False).strip()
    if not key:
        console.print("[bad]Error:[/bad] No API key provided.")
        sys.exit(1)
    if key in PLACEHOLDER_KEYS:
        console.print("[bad]Error:[/bad] Placeholder keys cannot be used.")
        sys.exit(1)

    path = save_api_key(key)
    console.print(f"[good]Success![/good] API key saved to [bold]{path}[/bold]")
