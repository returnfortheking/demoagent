"""Unit tests for the intent_classifier module.

Tests use mocking on `src.chains.intent_classifier._get_chain` so no real
LLM calls are made.  All five scenarios must pass before and after the
implementation is written.
"""

import json

import pytest

from src.chains.intent_classifier import classify_intent


# ---------------------------------------------------------------------------
# Scenario 1 – build intent (action, no confirmation required)
# ---------------------------------------------------------------------------
def test_classify_intent_build_action(mocker):
    """LLM returns valid JSON for a build command."""
    llm_response = json.dumps(
        {
            "type": "action",
            "command": "hispark-studio.build",
            "requires_confirmation": False,
            "description": "编译项目",
        }
    )
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = llm_response
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("帮我编译项目")

    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.build"
    assert result["requires_confirmation"] is False


# ---------------------------------------------------------------------------
# Scenario 2 – flash intent (action, confirmation required)
# ---------------------------------------------------------------------------
def test_classify_intent_flash_action(mocker):
    """LLM returns valid JSON for a flash command that requires confirmation."""
    llm_response = json.dumps(
        {
            "type": "action",
            "command": "hispark-studio.flash",
            "requires_confirmation": True,
            "description": "烧录固件",
        }
    )
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = llm_response
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("烧录固件")

    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.flash"
    assert result["requires_confirmation"] is True


# ---------------------------------------------------------------------------
# Scenario 3 – knowledge Q&A (answer type)
# ---------------------------------------------------------------------------
def test_classify_intent_answer(mocker):
    """LLM returns valid JSON for a knowledge Q&A intent."""
    llm_response = json.dumps({"type": "answer"})
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = llm_response
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    result = classify_intent("如何查看栈分析结果？")

    assert result["type"] == "answer"
    assert "command" not in result
    assert "requires_confirmation" not in result


# ---------------------------------------------------------------------------
# Scenario 4 – LLM returns plain text (must raise ValueError)
# ---------------------------------------------------------------------------
def test_classify_intent_plain_text_raises(mocker):
    """LLM returns plain text; classify_intent must raise ValueError."""
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = "对不起，我不明白"
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    with pytest.raises(ValueError):
        classify_intent("随便说点什么")


# ---------------------------------------------------------------------------
# Scenario 5 – LLM returns JSON with a leading prefix (must raise ValueError)
# ---------------------------------------------------------------------------
def test_classify_intent_prefixed_json_raises(mocker):
    """LLM returns a string with a non-JSON prefix; must raise ValueError."""
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = '好的！{"type": "answer"}'
    mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)

    with pytest.raises(ValueError):
        classify_intent("随便说点什么")
