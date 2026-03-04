"""Intent classifier using LangChain LLMChain (legacy, non-LCEL).

The module uses lazy initialization: ``_chain`` is NOT created at import time.
It is built on the first call to ``_get_chain()``.  This means importing the
module never triggers real LLM API calls, which allows unit tests to mock
``src.chains.intent_classifier._get_chain`` without any network side-effects.
"""

import json

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from src.config import get_llm

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
你是 HiSpark Studio VS Code 插件的智能助手，负责判断用户的意图。

可用命令列表：
- hispark-studio.build        编译项目            requires_confirmation=false
- hispark-studio.rebuild      重新编译            requires_confirmation=false
- hispark-studio.clean        清理项目            requires_confirmation=false
- hispark-studio.flash        烧录固件            requires_confirmation=true
- hispark-studio.stackAnalysis 栈分析             requires_confirmation=false
- hispark-studio.imageAnalysis 镜像分析           requires_confirmation=false
- stopBuild                   停止编译            requires_confirmation=false
- portionOfBurn               部分烧录            requires_confirmation=true

判断规则：
1. 若用户意图对应上方某条命令，返回：
   {{"type": "action", "command": "<命令名>", "requires_confirmation": <true|false>, "description": "<简短中文描述>"}}
2. 若用户意图是提问、咨询、或与上方命令无关，返回：
   {{"type": "answer"}}

严格要求（必须遵守）：
- 只输出纯 JSON，绝对不要使用 Markdown 代码块（不要输出 ```json 或 ```）。
- 不要在 JSON 前后添加任何文字、前缀、后缀或说明。
- 第一个字符必须是 {{，最后一个字符必须是 }}。

用户输入：{message}
"""

_prompt = PromptTemplate(input_variables=["message"], template=_PROMPT_TEMPLATE)

# ---------------------------------------------------------------------------
# Lazy-initialized module-level chain
# ---------------------------------------------------------------------------

_chain: LLMChain | None = None


def _get_chain() -> LLMChain:
    """Return the module-level LLMChain, building it on first access.

    The chain is constructed lazily so that importing this module does not
    trigger any LLM API calls.  Subsequent calls return the cached instance.
    """
    global _chain
    if _chain is None:
        _chain = LLMChain(llm=get_llm(), prompt=_prompt)
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
        ValueError: If the LLM response cannot be parsed as valid JSON, or if
            the JSON string does not start with ``{`` (i.e. there is a
            leading prefix).
    """
    raw: str = _get_chain().run(message=message)
    stripped = raw.strip()

    # Strip markdown code fences if the LLM wrapped the JSON in them.
    # Both ```json\n...\n``` and ```\n...\n``` are handled.
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove the opening fence line (```json or ```)
        lines = lines[1:]
        # Remove the closing fence line if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    # Reject anything that does not look like a bare JSON object.
    if not stripped.startswith("{"):
        raise ValueError(
            f"LLM response is not a bare JSON object. Got: {raw!r}"
        )

    try:
        result = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM response could not be parsed as JSON. Got: {raw!r}"
        ) from exc

    return result
