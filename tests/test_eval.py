"""Offline tests for the eval harness (eval/run_eval.py).

The harness takes the analyze/optimize callables as arguments, so these
tests drive the real aggregation, rendering and file-writing code with
scripted stand-ins. No network, no API key.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

import run_eval
from run_eval import (
    RUBRIC_SECTIONS,
    Row,
    evaluate_one,
    load_prompts,
    render_markdown,
    run_eval as run_all,
    sections_present,
    summarize,
    write_results,
)
from support import analysis, optimized
from prompt_optimizer_tool.schemas import PromptSection

ITEM = {"id": "t-1", "category": "coding", "prompt": "do the thing"}
PROMPTS_FILE = Path(run_eval.__file__).with_name("prompts.jsonl")


def scripted(scores: list[int], full_prompt: str = "Role: x\nObjective: y"):
    """Return (analyze, optimize) fakes; analyze yields `scores` in order."""
    queue = iter(scores)
    return (
        lambda prompt: analysis(score=next(queue)),
        lambda prompt, found: optimized(full_prompt=full_prompt),
    )


class TestShippedPromptSet:
    def test_has_24_prompts_in_six_categories_of_four(self):
        items = load_prompts(PROMPTS_FILE)
        assert len(items) == 24
        counts: dict[str, int] = {}
        for item in items:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        assert sorted(counts.values()) == [4] * 6

    def test_ids_are_unique(self):
        ids = [item["id"] for item in load_prompts(PROMPTS_FILE)]
        assert len(ids) == len(set(ids))


class TestLoadPrompts:
    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "p.jsonl"
        path.write_text(json.dumps(ITEM) + "\n\n", encoding="utf-8")
        assert load_prompts(path) == [ITEM]

    def test_invalid_json_names_the_line(self, tmp_path):
        path = tmp_path / "p.jsonl"
        path.write_text(json.dumps(ITEM) + "\n{oops\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"p\.jsonl:2: invalid JSON"):
            load_prompts(path)

    def test_missing_field_is_reported(self, tmp_path):
        path = tmp_path / "p.jsonl"
        path.write_text('{"id": "a", "category": "c"}\n', encoding="utf-8")
        with pytest.raises(ValueError, match="missing.*prompt"):
            load_prompts(path)


class TestSectionsPresent:
    def test_uses_model_section_names(self):
        assert sections_present(["Role", "output format"], "") == ["role", "output_format"]

    def test_detects_labels_in_prompt_text(self):
        text = "Role: analyst\n## Objective\nDo it\n**Constraints**: none\nOutput format: json"
        assert sections_present([], text) == ["role", "objective", "constraints", "output_format"]

    def test_mid_sentence_mentions_do_not_count(self):
        assert sections_present([], "Please define the role of the user in context.") == []

    def test_result_follows_rubric_order(self):
        found = sections_present(["output_format", "role"], "")
        assert found == [s for s in RUBRIC_SECTIONS if s in found]


class TestEvaluateOne:
    def test_computes_lift_and_coverage(self):
        analyze, optimize = scripted([40, 70], "Role: a\nObjective: b\nContext: c")
        row = evaluate_one(ITEM, analyze, optimize)
        assert (row.before, row.after, row.lift) == (40, 70, 30)
        assert row.coverage == 0.5
        assert row.error is None

    def test_negative_lift_is_kept(self):
        analyze, optimize = scripted([80, 60])
        assert evaluate_one(ITEM, analyze, optimize).lift == -20

    def test_rewrite_is_what_gets_rescored(self):
        seen = []

        def analyze(prompt):
            seen.append(prompt)
            return analysis()

        evaluate_one(ITEM, analyze, lambda p, a: optimized(full_prompt="REWRITE"))
        assert seen == ["do the thing", "REWRITE"]

    @pytest.mark.parametrize("failing", ["first", "optimize", "second"])
    def test_failure_at_any_step_becomes_an_error_row(self, failing):
        calls = {"n": 0}

        def analyze(prompt):
            calls["n"] += 1
            if failing == "first" and calls["n"] == 1 or failing == "second" and calls["n"] == 2:
                raise RuntimeError("rate limited")
            return analysis()

        def optimize(prompt, found):
            if failing == "optimize":
                raise RuntimeError("rate limited")
            return optimized()

        row = evaluate_one(ITEM, analyze, optimize)
        assert row.error == "RuntimeError: rate limited"
        assert row.lift is None


class TestRunEval:
    def test_one_failure_does_not_stop_the_run(self):
        items = [dict(ITEM, id=f"t-{i}") for i in range(3)]
        calls = {"n": 0}

        def analyze(prompt):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return analysis()

        rows = run_all(items, analyze, lambda p, a: optimized())
        assert [r.error is None for r in rows] == [False, True, True]

    def test_delay_applies_between_prompts_only(self):
        sleeps = []
        analyze, optimize = scripted([50] * 6)
        run_all([ITEM] * 3, analyze, optimize, delay=1.5, sleep=sleeps.append)
        assert sleeps == [1.5, 1.5]

    def test_no_sleep_when_delay_is_zero(self):
        sleeps = []
        analyze, optimize = scripted([50] * 4)
        run_all([ITEM] * 2, analyze, optimize, sleep=sleeps.append)
        assert sleeps == []

    def test_on_row_called_per_prompt(self):
        seen = []
        analyze, optimize = scripted([50] * 4)
        run_all([ITEM] * 2, analyze, optimize, on_row=seen.append)
        assert len(seen) == 2


def row(category, before, after, coverage=1.0):
    return Row(id="x", category=category, before=before, after=after,
               lift=after - before, coverage=coverage, sections_found=list(RUBRIC_SECTIONS))


class TestSummarize:
    def test_headline_numbers(self):
        rows = [row("a", 40, 80), row("a", 50, 50), row("b", 90, 70), row("b", 60, 70)]
        s = summarize(rows)
        assert s["n_ok"] == 4 and s["n_failed"] == 0
        assert s["mean_lift"] == 7.5            # (40 + 0 - 20 + 10) / 4
        assert s["median_lift"] == 5.0          # median of [-20, 0, 10, 40]
        assert (s["pct_improved"], s["pct_unchanged"], s["pct_regressed"]) == (50.0, 25.0, 25.0)
        assert s["mean_before"] == 60.0 and s["mean_after"] == 67.5

    def test_coverage_is_averaged_as_a_percentage(self):
        s = summarize([row("a", 1, 2, coverage=1.0), row("a", 1, 2, coverage=0.5)])
        assert s["mean_section_coverage_pct"] == 75.0

    def test_groups_by_category_in_first_seen_order(self):
        s = summarize([row("b", 10, 30), row("a", 10, 20), row("b", 10, 10)])
        assert list(s["by_category"]) == ["b", "a"]
        assert s["by_category"]["b"]["n"] == 2
        assert s["by_category"]["b"]["mean_lift"] == 10.0

    def test_failed_rows_are_excluded_but_counted(self):
        failed = Row(id="f", category="a", error="X: y")
        s = summarize([row("a", 10, 20), failed])
        assert (s["n_total"], s["n_ok"], s["n_failed"]) == (2, 1, 1)
        assert s["mean_lift"] == 10.0

    def test_all_failed_has_no_metrics(self):
        s = summarize([Row(id="f", category="a", error="X: y")])
        assert s == {"n_total": 1, "n_ok": 0, "n_failed": 1}


class TestRenderAndWrite:
    def test_markdown_contains_framing_metrics_and_failures(self):
        rows = [row("a", 40, 60), Row(id="bad", category="a", error="RuntimeError: nope")]
        text = render_markdown(rows, summarize(rows), model="m-1")
        assert "Same-model proxy" in text
        assert "`m-1`" in text
        assert "| Mean lift | +20.0 |" in text
        assert "`bad`: RuntimeError: nope" in text

    def test_markdown_with_no_successes_still_renders(self):
        rows = [Row(id="bad", category="a", error="E: x")]
        text = render_markdown(rows, summarize(rows))
        assert "0 scored, 1 failed" in text
        assert "Mean lift" not in text

    def test_write_results_creates_both_files(self, tmp_path):
        rows = [row("a", 40, 60)]
        json_path, md_path = write_results(
            rows, summarize(rows), tmp_path / "nested", "m-1",
            now=datetime(2026, 11, 8, 9, 30, 5),
        )
        assert json_path.name == "20261108-093005.json"
        assert md_path.name == "20261108-093005.md"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["model"] == "m-1"
        assert payload["summary"]["mean_lift"] == 20.0
        assert payload["rows"][0]["lift"] == 20


class TestMain:
    def test_refuses_to_run_without_a_key(self, monkeypatch, capsys):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        assert run_eval.main(["--limit", "1"]) == 1
        assert "GROQ_API_KEY" in capsys.readouterr().err

    def test_end_to_end_with_fake_pipeline(self, monkeypatch, tmp_path, capsys, provider):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_real_looking_key")
        code = run_eval.main(["--limit", "2", "--delay", "0", "--out", str(tmp_path)])
        assert code == 0
        assert len(list(tmp_path.glob("*.json"))) == 1
        assert len(list(tmp_path.glob("*.md"))) == 1
        assert "[coding-01]" in capsys.readouterr().out

    def test_empty_prompt_file_fails(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_real_looking_key")
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        assert run_eval.main(["--prompts", str(empty), "--out", str(tmp_path)]) == 1
        assert "No prompts" in capsys.readouterr().err
