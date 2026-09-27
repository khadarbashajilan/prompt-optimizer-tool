"""Where each run's rewritten prompt is written.

The clock is injected rather than read, so filenames are asserted exactly
instead of approximately.
"""

from datetime import datetime
from pathlib import Path

from prompt_optimizer.storage import new_output_path, write_output

STAMP = datetime(2026, 9, 27, 14, 32, 5)


def test_output_path_uses_date_and_time(tmp_path: Path) -> None:
    path = new_output_path(tmp_path, now=STAMP)

    assert path.name == "optimized-20260927-143205.md"
    assert path.parent == tmp_path


def test_same_second_runs_do_not_collide(tmp_path: Path) -> None:
    first = new_output_path(tmp_path, now=STAMP)
    write_output("first", first)
    second = new_output_path(tmp_path, now=STAMP)

    assert second != first
    assert second.name == "optimized-20260927-143205-2.md"


def test_write_output_creates_missing_folders(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "optimized-20260927-143205.md"
    write_output("hello", path)

    assert path.read_text(encoding="utf-8") == "hello"
