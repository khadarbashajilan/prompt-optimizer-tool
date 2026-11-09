"""Prompt-set loading for eval."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_PROMPT_FIELDS = {"id", "category", "prompt"}


def load_prompts(path: Path) -> list[dict]:
    """Read a JSONL file of {id, category, prompt}; blank lines are skipped.

    Raises:
        ValueError: If a line is not valid JSON or lacks a required field.
    """
    items = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{number}: invalid JSON ({error.msg})") from error
        missing = REQUIRED_PROMPT_FIELDS - item.keys()
        if missing:
            raise ValueError(f"{path}:{number}: missing {sorted(missing)}")
        items.append(item)
    return items
