"""Integration tests for Zhipu LLM connectivity.

These tests make real API calls to the ZhipuAI service.
Run with: pytest tests/integration/test_llm_real.py -v -m integration
"""

import os

import pytest

from src.config import get_llm
from src.chains.intent_classifier import classify_intent
from src.chains.qa_chain import answer_question


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


# ---------------------------------------------------------------------------
# F04 RAG answer quality integration tests (real LLM + embedding calls)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_rag_sdk_download_url():
    """验证 RAG 能从文档中检索出 WS63 SDK 的具体下载地址。

    The sample_docs.md fixture contains the exact git clone URL with 'gitee'
    and 'fbb_ws63', so the RAG answer must include both keywords.
    """
    answer = answer_question("WS63的SDK从哪里下载？", session_id="integration-test")
    assert "gitee" in answer, (
        f"Expected 'gitee' in answer, got: {answer!r}"
    )
    assert "fbb_ws63" in answer, (
        f"Expected 'fbb_ws63' in answer, got: {answer!r}"
    )


@pytest.mark.integration
def test_rag_toolchain_env_variable():
    """验证 RAG 能从文档中检索出工具链安装后添加的环境变量名称。

    The sample_docs.md fixture explicitly states that HISPARK_TOOL_PATH is
    added to the user environment after toolchain download completes.
    """
    answer = answer_question("工具链安装完成后会添加什么环境变量？", session_id="integration-test")
    assert "HISPARK_TOOL_PATH" in answer, (
        f"Expected 'HISPARK_TOOL_PATH' in answer, got: {answer!r}"
    )


@pytest.mark.integration
def test_rag_sdk_series():
    """验证 RAG 能从文档中检索出支持下载的 SDK 系列（WS63 和 BS2X）。

    The sample_docs.md fixture states that both WS63 and BS2X SDK series
    are available for download through the HiSpark Studio plugin.
    """
    answer = answer_question("HiSpark支持下载哪些系列的SDK？", session_id="integration-test")
    assert "WS63" in answer, (
        f"Expected 'WS63' in answer, got: {answer!r}"
    )
    assert "BS2X" in answer, (
        f"Expected 'BS2X' in answer, got: {answer!r}"
    )


@pytest.mark.integration
def test_rag_toolchain_path_restriction():
    """验证 RAG 能从文档中检索出工具链文件夹路径的约束条件。

    The sample_docs.md fixture states that the toolchain folder path must
    not contain Chinese characters or spaces — at least one of these two
    keywords must appear in the answer.
    """
    answer = answer_question("工具链文件夹路径有什么限制？", session_id="integration-test")
    has_chinese_keyword = "中文" in answer
    has_space_keyword = "空格" in answer
    assert has_chinese_keyword or has_space_keyword, (
        f"Expected '中文' or '空格' in answer, got: {answer!r}"
    )
