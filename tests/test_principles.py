"""The principle table, and the two system prompts generated from it.

principles.py is the single source of truth: the `list` command, the
analysis prompt, and the rewrite prompt are all rendered from PRINCIPLES.
These tests guard the table's internal consistency, which is what keeps
that generation honest.
"""

from prompt_optimizer.principles import (
    ANALYSIS_SYSTEM_PROMPT,
    OPTIMIZER_SYSTEM_PROMPT,
    PRINCIPLES,
    PrincipleKey,
    principle_name,
)


def test_principle_keys_match_the_declared_literal() -> None:
    """The dict keys and the PrincipleKey Literal must not drift apart."""
    assert set(PRINCIPLES) == set(PrincipleKey.__args__)


def test_every_principle_is_fully_populated() -> None:
    for key, principle in PRINCIPLES.items():
        for field in ("name", "description", "analysis", "rewrite"):
            assert getattr(principle, field).strip(), f"{key} has an empty {field}"


def test_principle_name_falls_back_to_the_key() -> None:
    assert principle_name("role") == PRINCIPLES["role"].name
    assert principle_name("not-a-real-key") == "not-a-real-key"


def test_both_system_prompts_render_every_principle() -> None:
    """The two prompts are generated, so this proves the generation ran.

    A principle added to the table but not rendered into a prompt would
    be invisible to the model while still looking correct in `list`.
    """
    for prompt, field in (
        (ANALYSIS_SYSTEM_PROMPT, "analysis"),
        (OPTIMIZER_SYSTEM_PROMPT, "rewrite"),
    ):
        for key, principle in PRINCIPLES.items():
            assert key in prompt, f"{key} missing from a system prompt"
            assert getattr(principle, field) in prompt
