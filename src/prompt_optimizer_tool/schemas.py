"""Pydantic models describing what the LLM is allowed to return.

These schemas double as validation and as the contract for Groq's strict
structured output, so the fields below are the tool's real API. Enumerated
fields use Literal rather than str: that way the LLM cannot invent a
severity the terminal does not know how to colour, and it cannot return a
principle name the code is unable to look up.
"""

from typing import Literal

from pydantic import BaseModel, Field

from .principles import PrincipleKey

Severity = Literal["critical", "major", "minor"]


class PromptWeakness(BaseModel):
    """A single problem found in a prompt."""

    issue: str = Field(description="What's wrong with the prompt")
    severity: Severity = Field(description="How serious: critical, major, or minor")
    principle: PrincipleKey = Field(description="Key of the prompting principle violated")
    suggestion: str = Field(description="How to fix it")


class PromptSection(BaseModel):
    """One labelled block of a rewritten prompt."""

    name: str = Field(description="Section name, e.g. role, objective, constraints")
    content: str = Field(description="The rewritten content of this section")


class PromptAnalysis(BaseModel):
    """Result of analyzing a prompt for quality."""

    score: int = Field(ge=0, le=100, description="Overall quality score 0-100")
    weaknesses: list[PromptWeakness] = Field(description="Identified issues")
    strengths: list[str] = Field(description="What the prompt does well")


class OptimizedPrompt(BaseModel):
    """A prompt that has been rewritten following best practices."""

    sections: list[PromptSection] = Field(
        description=(
            "Structured prompt sections: role, objective, context, instructions, "
            "constraints, output_format. Only the ones that are relevant."
        )
    )
    full_prompt: str = Field(description="The complete rewritten prompt")
    changes_made: list[str] = Field(description="Summary of what was improved")
    principles_applied: list[PrincipleKey] = Field(
        description="Keys of the principles that were used"
    )
