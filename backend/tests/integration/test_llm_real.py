"""Integration tests for Zhipu LLM connectivity.

These tests make real API calls to the ZhipuAI service.
Run with: pytest tests/integration/test_llm_real.py -v -m integration
"""

import os

import pytest

from src.config import get_llm
from src.chains.intent_classifier import classify_intent


@pytest.mark.integration
def test_llm_normal_invoke():
    """Test that a normal LLM call returns a non-empty string response."""
    llm = get_llm()
    response = llm.invoke("用一句话介绍你自己")
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.integration
def test_llm_invalid_key_raises(monkeypatch):
    """Test that an invalid API key causes an exception to be raised.

    Uses monkeypatch to temporarily set ZHIPU_API_KEY to an invalid value.
    The environment variable is automatically restored after the test.
    """
    monkeypatch.setenv("ZHIPU_API_KEY", "invalid_key_xxx")
    llm = get_llm()
    with pytest.raises(Exception):
        llm.invoke("test")


# ---------------------------------------------------------------------------
# F03 intent classifier integration tests (real LLM calls)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_classify_intent_build_real():
    """Real LLM call: '帮我编译项目' should map to hispark-studio.build."""
    result = classify_intent("帮我编译项目")
    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.build"


@pytest.mark.integration
def test_classify_intent_flash_real():
    """Real LLM call: '烧录固件' should map to hispark-studio.flash."""
    result = classify_intent("烧录固件")
    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.flash"


@pytest.mark.integration
def test_classify_intent_answer_real():
    """Real LLM call: knowledge question should return type='answer'."""
    result = classify_intent("如何查看栈分析结果？")
    assert result["type"] == "answer"
