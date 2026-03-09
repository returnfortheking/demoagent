"""Intent classifier using LCEL (v0.2).

The chain is a simple pipe: prompt | llm | JsonOutputParser().
JsonOutputParser handles markdown fences and prefix text internally via regex,
which makes the output more robust than v0.1's manual JSON parsing.

The module uses lazy initialization: ``_chain`` is NOT created at import time.
It is built on the first call to ``_get_chain()``.  This means importing the
module never triggers real LLM API calls, which allows unit tests to mock
``src.chains.intent_classifier._get_chain`` without any network side-effects.
"""

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import get_llm
from src.prompts.intent_v1 import INTENT_PROMPT_TEMPLATE

# ---------------------------------------------------------------------------
# Lazy-initialized module-level chain
# ---------------------------------------------------------------------------

_chain = None


def _get_chain():
    """Return the module-level LCEL chain, building it on first access."""
    global _chain
    if _chain is None:
        prompt = ChatPromptTemplate.from_template(INTENT_PROMPT_TEMPLATE)
        _chain = prompt | get_llm() | JsonOutputParser()
    return _chain


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_intent(message: str) -> dict:
    """Classify the user's intent using the LLM.

    Args:
        message: The natural-language message from the user.

    Returns:
        A dict with at minimum ``{"type": "action", ...}`` or
        ``{"type": "answer"}``.

    Raises:
        ValueError: If the chain raises OutputParserException, or if the
            returned dict has a type field other than "action" or "answer".
    """
    try:
        result: dict = _get_chain().invoke({"message": message})
    except OutputParserException as exc:
        raise ValueError(f"Intent parsing failed: {exc}") from exc

    if result.get("type") not in ("action", "answer"):
        raise ValueError(f"Unexpected intent type: {result.get('type')!r}")

    return result
