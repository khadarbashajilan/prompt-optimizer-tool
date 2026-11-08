"""End-to-end CLI behaviour: input, exit codes, file writing, output.

The CLI is the product's contract. These tests use CliRunner with the two
LLM steps faked, so everything from argument parsing to the file on disk
is real while no network is touched.

Exit codes are the point of cases 2-4: a failure that still exits 0 lies
to scripts and to run.sh, which checks `|| echo "Optimize failed."`.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from prompt_optimizer import cli
from prompt_optimizer.config import MissingAPIKeyError

from support import optimized

RAW = "write code in python to fetch api data"
AWKWARD = "summarise {this} and   keep  spacing\n\nexactly"


def written(tmp_path: Path) -> list[Path]:
    return sorted(tmp_path.glob("*.md"))


def test_success_saves_the_rewrite_and_exits_zero(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "55/100" in result.output
    assert "Saved to" in result.output
    files = written(tmp_path)
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == optimized().full_prompt


def test_argument_prompt_reaches_the_pipeline_verbatim(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    result = runner.invoke(cli.cli, ["optimize", AWKWARD, "--out", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert pipeline.prompt == AWKWARD


def test_file_prompt_reaches_the_pipeline_verbatim(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    source = tmp_path / "prompt.txt"
    source.write_text(AWKWARD, encoding="utf-8")

    result = runner.invoke(
        cli.cli, ["optimize", "--file", str(source), "--out", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert pipeline.prompt == AWKWARD


def test_stdin_prompt_reaches_the_pipeline_verbatim(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    """Piped input must not lose leading or trailing whitespace."""
    result = runner.invoke(
        cli.cli, ["optimize", "--out", str(tmp_path)], input=f"  {AWKWARD}  \n"
    )

    assert result.exit_code == 0, result.output
    assert pipeline.prompt == f"  {AWKWARD}  \n"


def test_empty_input_is_a_usage_error_not_a_silent_success(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    result = runner.invoke(cli.cli, ["optimize", "--out", str(tmp_path)], input="")

    assert result.exit_code == 2
    assert "No prompt" in result.output
    assert pipeline.prompts == []
    assert written(tmp_path) == []


def test_analysis_failure_exits_non_zero_and_writes_nothing(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    pipeline.analysis_error = RuntimeError("groq is down")

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "groq is down" in result.output
    assert written(tmp_path) == []


def test_optimization_failure_exits_non_zero_and_writes_nothing(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    pipeline.optimize_error = RuntimeError("rewrite blew up")

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "rewrite blew up" in result.output
    assert written(tmp_path) == []


def test_missing_api_key_failure_exits_non_zero(
    runner: CliRunner, pipeline, placeholder_error, tmp_path: Path
) -> None:
    pipeline.analysis_error = placeholder_error

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "GROQ_API_KEY" in result.output
    assert written(tmp_path) == []


def test_out_folder_is_honoured(runner: CliRunner, pipeline, tmp_path: Path) -> None:
    out = tmp_path / "custom"

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(out)])

    assert result.exit_code == 0, result.output
    files = list(out.glob("*.md"))
    assert len(files) == 1
    assert written(tmp_path) == []


def test_score_colour_thresholds() -> None:
    """Pure mapping: both sides of every boundary."""
    assert cli.score_colour(100) == "green"
    assert cli.score_colour(70) == "green"
    assert cli.score_colour(69) == "yellow"
    assert cli.score_colour(40) == "yellow"
    assert cli.score_colour(39) == "red"
    assert cli.score_colour(0) == "red"


def test_every_severity_has_a_style() -> None:
    for severity in ("critical", "major", "minor"):
        assert cli.severity_style(severity)
