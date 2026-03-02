"""Integration tests for Zhipu LLM connectivity.

These tests make real API calls to the ZhipuAI service.
Run with: pytest tests/integration/test_llm_real.py -v -m integration
"""

import os

import pytest

from src.config import get_llm


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
