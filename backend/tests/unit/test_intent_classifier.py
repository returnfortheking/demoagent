"""Unit tests for the intent_classifier module (v0.2 LCEL).

Tests mock `src.chains.intent_classifier._get_chain` so no real LLM calls
are made.  The chain now uses LCEL + JsonOutputParser, so the mock stub
returns a dict from `.invoke()` (not a JSON string from `.run()`).
"""

import pytest
from langchain_core.exceptions import OutputParserException

from src.chains.intent_classifier import classify_intent


# ---------------------------------------------------------------------------
# Scenario 1 – build intent (action, no confirmation required)
# ---------------------------------------------------------------------------
def test_classify_intent_build_action(mocker):
    """Chain returns build action dict."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = {
        "type": "action",
        "command": "hispark-studio.build",
        "requires_confirmation": False,
        "description": "编译项目",
    }
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("帮我编译项目")

    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.build"
    assert result["requires_confirmation"] is False


# ---------------------------------------------------------------------------
# Scenario 2 – flash intent (action, confirmation required)
# ---------------------------------------------------------------------------
def test_classify_intent_flash_action(mocker):
    """Chain returns flash action dict with requires_confirmation=True."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = {
        "type": "action",
        "command": "hispark-studio.flash",
        "requires_confirmation": True,
        "description": "烧录固件",
    }
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("烧录固件")

    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.flash"
    assert result["requires_confirmation"] is True


# ---------------------------------------------------------------------------
# Scenario 3 – knowledge Q&A (answer type)
# ---------------------------------------------------------------------------
def test_classify_intent_answer(mocker):
    """Chain returns answer type dict; no command field present."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = {"type": "answer"}
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("如何查看栈分析结果？")

    assert result["type"] == "answer"
    assert "command" not in result
    assert "requires_confirmation" not in result


# ---------------------------------------------------------------------------
# Scenario 4 – OutputParserException → ValueError
# ---------------------------------------------------------------------------
def test_classify_intent_parser_exception_raises(mocker):
    """OutputParserException from chain is re-raised as ValueError."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.side_effect = OutputParserException("parse error")
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    with pytest.raises(ValueError):
        classify_intent("随便说点什么")


# ---------------------------------------------------------------------------
# Scenario 5 – unknown type field → ValueError
# ---------------------------------------------------------------------------
def test_classify_intent_unknown_type_raises(mocker):
    """Chain returns dict with unknown type; classify_intent must raise ValueError."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = {"type": "unknown"}
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    with pytest.raises(ValueError):
        classify_intent("随便说点什么")


# ---------------------------------------------------------------------------
# Scenario 6 – prefixed JSON (behavior change from v0.1)
# ---------------------------------------------------------------------------
def test_classify_intent_prefixed_json_succeeds(mocker):
    """v0.2 behavior: JsonOutputParser handles prefix internally; no longer raises.

    In v0.1, '好的！{"type": "answer"}' would raise ValueError because the
    raw string did not start with '{'.  In v0.2, JsonOutputParser extracts
    the JSON via regex, so the chain returns a clean dict — no exception.
    """
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = {"type": "answer"}
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("随便说点什么")

    assert result["type"] == "answer"
