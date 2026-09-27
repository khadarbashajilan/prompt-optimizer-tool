"""The ten prompting principles, and the LLM instructions built from them.

This module is the single source of truth for the rules. The `list` command,
the analysis prompt, and the optimization prompt are all generated from
`PRINCIPLES`, so a rule can no longer be edited in one place and forgotten
in the other two.
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


def _numbered(items: list[str]) -> str:
    """Render a 1-based numbered list for embedding in a prompt."""
    return "\n".join(f"{i}. {text}" for i, text in enumerate(items, start=1))


def _analysis_checklist() -> str:
    """Build the per-principle checklist for the grader."""
    return _numbered(
        f"{key} ({p.name}) — {p.analysis}"
        for key, p in PRINCIPLES.items()
    )


def _rewrite_checklist() -> str:
    """Build the per-principle checklist for the rewriter."""
    return _numbered(
        f"{key} ({p.name}) — {p.rewrite}"
        for key, p in PRINCIPLES.items()
    )


ANALYSIS_SYSTEM_PROMPT = f"""You are an expert prompt engineering analyst. \
Your job is to analyze prompts for quality and identify weaknesses.

Evaluate the given prompt against these principles:
{_analysis_checklist()}

Return:
- score: an integer 0-100 for overall prompt quality.
- weaknesses: each with the issue, a severity of critical, major, or minor, \
the principle key it violates, and a concrete suggestion for fixing it.
- strengths: what the prompt already does well. An empty list is fine."""

OPTIMIZER_SYSTEM_PROMPT = f"""You are an expert prompt optimization engineer. \
Your job is to rewrite prompts following all established prompt engineering \
best practices.

Given the original prompt and its analysis, produce an optimized version \
structured with clear sections.

Apply these principles as needed, using only the ones that genuinely fit:
{_rewrite_checklist()}

Return:
- sections: labelled blocks of the rewrite. Common names are role, \
objective, context, instructions, constraints, output_format. Include only \
the ones that are relevant.
- full_prompt: the complete rewritten prompt as one self-contained string, \
ready to paste into a chat window.
- changes_made: a list summarising each improvement applied.
- principles_applied: the principle keys from the list above that you used."""
