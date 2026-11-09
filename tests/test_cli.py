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

from prompt_optimizer_tool import cli
from prompt_optimizer_tool.config import MissingAPIKeyError
from prompt_optimizer_tool.principles import PRINCIPLES

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


def test_list_renders_every_principle(runner: CliRunner) -> None:
    result = runner.invoke(cli.cli, ["list"])

    assert result.exit_code == 0, result.output
    flat_output = " ".join(result.output.split())
    assert "Prompt Engineering Principles" in flat_output
    for key in PRINCIPLES:
        assert key in flat_output


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


def rate_limit_error(retry_after: str | None) -> Exception:
    import httpx
    from groq import RateLimitError

    headers = {"retry-after": retry_after} if retry_after else {}
    response = httpx.Response(
        429, headers=headers, request=httpx.Request("POST", "https://api.groq.com")
    )
    return RateLimitError("429 raw payload", response=response, body=None)


@pytest.mark.parametrize("step", ["analysis_error", "optimize_error"])
def test_rate_limit_is_explained_with_the_wait_time(
    runner: CliRunner, pipeline, tmp_path: Path, step: str
) -> None:
    setattr(pipeline, step, rate_limit_error("42"))

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "free tier" in result.output
    assert "42 seconds" in result.output
    assert "429 raw payload" not in result.output
    assert written(tmp_path) == []


def test_rate_limit_without_retry_after_still_gives_advice(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    pipeline.analysis_error = rate_limit_error(None)

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert "Wait a minute" in result.output


def test_setup_saves_key_interactively(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "config.env"
    monkeypatch.setattr(cli, "save_api_key", lambda key: dest)

    result = runner.invoke(cli.cli, ["setup"], input="gsk_new_secret_key\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert str(dest) in result.output


def test_setup_rejects_empty_key(runner: CliRunner) -> None:
    result = runner.invoke(cli.cli, ["setup"], input="\n")

    assert result.exit_code == 1
    assert "No API key provided" in result.output


def test_setup_rejects_placeholder_key(runner: CliRunner) -> None:
    result = runner.invoke(cli.cli, ["setup"], input="your-groq-api-key-here\n")

    assert result.exit_code == 1
    assert "Placeholder keys cannot be used" in result.output
