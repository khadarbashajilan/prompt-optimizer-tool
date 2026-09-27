"""Step 2 of the pipeline: rewrite a prompt using its analysis.

The analysis is passed in rather than recomputed, so the rewrite targets
the exact weaknesses that were found instead of re-guessing them.
"""

from langchain_core.prompts import ChatPromptTemplate

from llm import structured_llm
from principles import OPTIMIZER_SYSTEM_PROMPT
from schemas import OptimizedPrompt, PromptAnalysis

HUMAN_MESSAGE = "Original prompt:\n\n{original}\n\nAnalysis:\n{analysis}"


def optimize_prompt(prompt_text: str, analysis: PromptAnalysis) -> OptimizedPrompt:
    """Rewrite a prompt following the principles its analysis flagged.

    Args:
        prompt_text: The original raw prompt.
        analysis: The PromptAnalysis from analyze_prompt().

    Returns:
        An OptimizedPrompt with sections, full_prompt, changes_made,
        and principles_applied.

    Raises:
        MissingAPIKeyError: If no API key is configured.
        APIError: If the model call fails after retries.
    """
    chain = ChatPromptTemplate.from_messages([
        ("system", OPTIMIZER_SYSTEM_PROMPT),
        ("human", HUMAN_MESSAGE),
    ]) | structured_llm(OptimizedPrompt)

    return chain.invoke({
        "original": prompt_text,
        "analysis": analysis.model_dump_json(indent=2),
    })
