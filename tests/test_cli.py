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

from prompt_lint import cli
from prompt_lint.config import MissingAPIKeyError
from prompt_lint.principles import PRINCIPLES

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
    pipeline.analysis_error = RuntimeError("provider is down")

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "provider is down" in result.output
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
    assert "API_KEY" in result.output
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
    from litellm import RateLimitError

    headers = {"retry-after": retry_after} if retry_after else {}
    response = httpx.Response(
        429, headers=headers, request=httpx.Request("POST", "https://api.example.com")
    )
    return RateLimitError("429 raw payload", llm_provider="test", model="m", response=response)


@pytest.mark.parametrize("step", ["analysis_error", "optimize_error"])
def test_rate_limit_is_explained_with_the_wait_time(
    runner: CliRunner, pipeline, tmp_path: Path, step: str
) -> None:
    setattr(pipeline, step, rate_limit_error("42"))

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "Rate limit" in result.output
    assert "42 seconds" in result.output
    assert "429 raw payload" not in result.output
    assert written(tmp_path) == []


def test_rate_limit_without_retry_after_still_gives_advice(
    runner: CliRunner, pipeline, tmp_path: Path
) -> None:
    pipeline.analysis_error = rate_limit_error(None)

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert "Wait a minute" in result.output


def test_setup_saves_model_and_key(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "config.env"
    saved: dict = {}
    monkeypatch.setattr(cli, "required_env_vars", lambda model: ["OPENAI_API_KEY"])
    monkeypatch.setattr(cli, "save_settings", lambda values: saved.update(values) or dest)

    result = runner.invoke(cli.cli, ["setup"], input="openai/gpt-4o-mini\nsk_new_secret\n")

    assert result.exit_code == 0
    assert "Success!" in result.output
    assert saved == {"PLINT_MODEL": "openai/gpt-4o-mini", "OPENAI_API_KEY": "sk_new_secret"}


def test_setup_local_model_needs_no_key(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "required_env_vars", lambda model: [])
    monkeypatch.setattr(cli, "save_settings", lambda values: tmp_path / "c.env")

    result = runner.invoke(cli.cli, ["setup"], input="ollama/llama3.1\n")

    assert result.exit_code == 0
    assert "No API key needed" in result.output


def test_setup_rejects_empty_key(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "required_env_vars", lambda model: ["OPENAI_API_KEY"])

    result = runner.invoke(cli.cli, ["setup"], input="openai/gpt-4o-mini\n\n")

    assert result.exit_code == 1
    assert "No API key provided" in result.output


def test_setup_rejects_placeholder_key(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "required_env_vars", lambda model: ["OPENAI_API_KEY"])

    result = runner.invoke(cli.cli, ["setup"], input="openai/gpt-4o-mini\nyour-api-key-here\n")

    assert result.exit_code == 1
    assert "Placeholder keys cannot be used" in result.output


def test_authentication_error_points_to_setup(runner: CliRunner, pipeline, tmp_path: Path) -> None:
    from litellm import AuthenticationError

    pipeline.analysis_error = AuthenticationError("bad key", llm_provider="test", model="m")

    result = runner.invoke(cli.cli, ["optimize", RAW, "--out", str(tmp_path)])

    assert result.exit_code == 1
    assert "plint setup" in result.output


def test_bare_prompt_defaults_to_optimize(runner: CliRunner, pipeline, tmp_path: Path) -> None:
    result = runner.invoke(cli.cli, [RAW, "--out", str(tmp_path)])

    assert result.exit_code == 0
    assert pipeline.prompts == [RAW]


def test_bare_file_option_defaults_to_optimize(runner: CliRunner, pipeline, tmp_path: Path) -> None:
    source = tmp_path / "p.txt"
    source.write_text(RAW, encoding="utf-8")

    result = runner.invoke(cli.cli, ["--file", str(source), "--out", str(tmp_path)])

    assert result.exit_code == 0
    assert pipeline.prompts == [RAW]


def test_subcommands_still_work(runner: CliRunner) -> None:
    assert runner.invoke(cli.cli, ["list"]).exit_code == 0
    assert "optimize" in runner.invoke(cli.cli, ["--help"]).output
