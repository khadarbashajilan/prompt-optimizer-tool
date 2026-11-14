"""Step 1 of the pipeline: score a prompt and list what is wrong with it.

Kept deliberately thin. It builds a chain, invokes it once, and returns the
result, so the interesting behaviour lives in prompts.py and the model
setup in llm.py.
"""

from langchain_core.prompts import ChatPromptTemplate

from .llm import structured_llm
from .prompts import ANALYSIS_HUMAN_TEMPLATE, ANALYSIS_SYSTEM_PROMPT
from .schemas import PromptAnalysis


def analyze_prompt(prompt_text: str) -> PromptAnalysis:
    """Analyze a prompt and return a structured quality assessment.

    Args:
        prompt_text: The raw prompt text to analyze.

    Returns:
        A PromptAnalysis with score, weaknesses, and strengths.

    Raises:
        MissingAPIKeyError: If no API key is configured.
        APIError: If the model call fails after retries.
    """
    chain = ChatPromptTemplate.from_messages([
        ("system", ANALYSIS_SYSTEM_PROMPT),
        ("human", ANALYSIS_HUMAN_TEMPLATE),
    ]) | structured_llm(PromptAnalysis)

    return chain.invoke({"prompt": prompt_text})
