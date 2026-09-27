"""Deciding where each run's rewritten prompt is stored.

Every run gets its own file so results never overwrite each other. The
filename is the date and time of the run, which keeps saved files sorting
chronologically and makes the right one easy to find later.
"""

from datetime import datetime
from pathlib import Path

from .config import DEFAULT_OUTPUT_DIR

TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def new_output_path(
    directory: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    now: datetime | None = None,
) -> Path:
    """Build a fresh, unique path for one run's output.

    Two runs inside the same second would otherwise collide, so a counter
    is appended until the name is free.

    Args:
        directory: Folder to write into. Created later by write_output().
        now: Timestamp to embed. Defaults to the current time. Injectable
            so tests get predictable names.

    Returns:
        A path like saved/optimized-20260927-143205.md.
    """
    folder = Path(directory)
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
    candidate = folder / f"optimized-{stamp}.md"

    counter = 2
    while candidate.exists():
        candidate = folder / f"optimized-{stamp}-{counter}.md"
        counter += 1

    return candidate


def write_output(prompt: str, path: Path) -> Path:
    """Write the rewritten prompt to path, creating parent folders.

    Args:
        prompt: The full rewritten prompt text.
        path: Destination file, normally from new_output_path().

    Returns:
        The path written to.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return path
