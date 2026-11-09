"""Rubric constants and model-free section detection for eval."""

from __future__ import annotations

import re

# The six sections a well-formed rewrite is expected to contain.
RUBRIC_SECTIONS = (
    "role",
    "objective",
    "context",
    "instructions",
    "constraints",
    "output_format",
)

# Matches a rubric label at the start of a line, in either form:
#   "## Objective", "### Output format"   (markdown heading, colon optional)
#   "Role:", "**Constraints**:", "output_format:"   (label with a colon)
_NAMES = "|".join(section.replace("_", "[ _]") for section in RUBRIC_SECTIONS)
_LABEL = re.compile(
    rf"^[ \t]*(?:#+[ \t]*(?P<h>{_NAMES})[ \t]*:?[ \t]*$"
    rf"|(?:\*\*|__)?(?P<l>{_NAMES})(?:\*\*|__)?[ \t]*:)",
    re.IGNORECASE | re.MULTILINE,
)


def _normalize_section(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def sections_present(section_names: list[str], full_prompt: str) -> list[str]:
    """Return which rubric sections a rewrite contains, in rubric order.

    A section counts if the model labelled one with that name, or if the
    prompt text itself has a line starting with the label (``Role:``,
    ``## Objective``, ``**Output format**:`` ...). Model-free and
    deterministic, so it does not inherit the scorer's bias.
    """
    found = {_normalize_section(name) for name in section_names}
    for match in _LABEL.finditer(full_prompt):
        found.add(_normalize_section(match.group("h") or match.group("l")))
    return [section for section in RUBRIC_SECTIONS if section in found]
