"""The ten prompting principles: one data table, no prompt text.

This module is the single source of truth for the rules. `prompts.py`
builds both system prompts from `PRINCIPLES`, and the `list` command
renders the table directly.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Principle:
    """One prompting rule, in every form the tool needs.

    Attributes:
        name: Human-readable title, shown in the terminal.
        description: One-line plain-English summary, shown to the user.
        analysis: How the grader should interrogate the prompt for this.
        rewrite: What the rewriter should do about it.
    """

    name: str
    description: str
    analysis: str
    rewrite: str


# Declared beside the table below on purpose: the keys and the Literal are
# two views of the same thing, and keeping them adjacent makes drift obvious.
PrincipleKey = Literal[
    "role",
    "objective",
    "context",
    "instructions",
    "constraints",
    "output_format",
    "examples",
    "chain_of_thought",
    "success_criteria",
    "specificity",
]

PRINCIPLES: dict[PrincipleKey, Principle] = {
    "role": Principle(
        name="Role and Persona Definition",
        description="Set tone and expertise level by naming who the model should be.",
        analysis="does it assign a clear persona?",
        rewrite="define a specific role or persona, including relevant expertise and experience level",
    ),
    "objective": Principle(
        name="Clear Objective",
        description="State the single, specific goal up front.",
        analysis="is the goal specific and upfront?",
        rewrite="begin with a concise one-sentence statement of the primary goal or task",
    ),
    "context": Principle(
        name="Context Provision",
        description="Give background, audience, and environment so the answer fits.",
        analysis="is sufficient background given?",
        rewrite="include necessary background, target audience, environment, and any relevant situational details",
    ),
    "instructions": Principle(
        name="Step-by-Step Instructions",
        description="Break complex tasks into a clear sequence of actions.",
        analysis="are complex tasks broken down?",
        rewrite="break down the task into clear, sequential steps or a numbered checklist",
    ),
    "constraints": Principle(
        name="Constraints and Rules",
        description="Set boundaries: what to include, exclude, and avoid.",
        analysis="are boundaries and rules explicit?",
        rewrite="define hard rules: exclusions, boundaries, tone limits, length constraints, and uncertainty handling",
    ),
    "output_format": Principle(
        name="Output Format Specification",
        description="Say exactly how the response should be structured.",
        analysis="is the response structure defined?",
        rewrite="specify the exact output structure: format, sections, length, and style",
    ),
    "examples": Principle(
        name="Few-Shot Examples",
        description="Demonstrate the desired pattern with examples.",
        analysis="are examples provided when helpful?",
        rewrite="include 1-3 concrete examples showing the expected input-to-output transformation",
    ),
    "chain_of_thought": Principle(
        name="Chain of Thought",
        description="Ask for reasoning before the answer on multi-step problems.",
        analysis="is reasoning requested for complex tasks?",
        rewrite="for complex tasks, instruct the model to think through the problem step by step before answering",
    ),
    "success_criteria": Principle(
        name="Success Criteria",
        description="Define what a good response looks like.",
        analysis="is what good looks like defined?",
        rewrite="state measurable criteria for a successful response: what must be included, what quality bar to meet",
    ),
    "specificity": Principle(
        name="Specific and Actionable Language",
        description="Replace vague qualifiers with precise, measurable terms.",
        analysis="is the language precise?",
        rewrite="use precise, concrete language; avoid subjective qualifiers and quantify where possible",
    ),
}


def principle_name(key: PrincipleKey) -> str:
    """Return the human-readable title for a principle key.

    Args:
        key: One of the keys in PRINCIPLES.

    Returns:
        The display name, or the key itself if it is not recognised.
    """
    principle = PRINCIPLES.get(key)
    return principle.name if principle else key

