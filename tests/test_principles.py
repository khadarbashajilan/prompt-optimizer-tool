"""The principle table: single source of truth for the three consumers.

The dict keys, the PrincipleKey Literal, and both generated system prompts
must never drift apart. These tests pin all three views to each other.
"""

from prompt_optimizer_tool.principles import (
    ANALYSIS_SYSTEM_PROMPT,
    OPTIMIZER_SYSTEM_PROMPT,
    PRINCIPLES,
    PrincipleKey,
    principle_name,
)


def test_table_keys_match_the_declared_literal() -> None:
    assert set(PRINCIPLES) == set(PrincipleKey.__args__)


def test_every_principle_is_fully_populated() -> None:
    for key, principle in PRINCIPLES.items():
        for attribute in ("name", "description", "analysis", "rewrite"):
            assert getattr(principle, attribute).strip(), f"{key}.{attribute} is empty"


def test_both_system_prompts_render_every_principle() -> None:
    for system, attribute in (
        (ANALYSIS_SYSTEM_PROMPT, "analysis"),
        (OPTIMIZER_SYSTEM_PROMPT, "rewrite"),
    ):
        for key, principle in PRINCIPLES.items():
            assert key in system, f"{key} missing from {attribute} prompt"
            assert getattr(principle, attribute) in system


def test_principle_names_resolve_and_fall_back_to_the_key() -> None:
    assert principle_name("role") == PRINCIPLES["role"].name
    assert principle_name("not-a-real-key") == "not-a-real-key"
