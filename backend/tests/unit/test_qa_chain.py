"""Unit tests for the qa_chain module.

Test 1: build_retriever returns a non-None object with get_relevant_documents method.
         This test makes a real embedding API call to ZhipuAI (requires ZHIPU_API_KEY).

Test 2: answer_question returns a non-empty string (mocked _qa_chain.run).

Test 3: answer_question calls _qa_chain.run exactly once with the question text.
"""

import pytest

from src.chains.qa_chain import answer_question, build_retriever


# ---------------------------------------------------------------------------
# Scenario 1 – build_retriever returns a valid retriever object
# ---------------------------------------------------------------------------
def test_build_retriever_returns_non_none():
    """build_retriever must return a non-None object that has get_relevant_documents.

    This test makes a real call to the ZhipuAI embedding-3 API.
    Requires a valid ZHIPU_API_KEY in the .env file.
    """
    docs = [
        "BS21 芯片支持 Wi-Fi 和蓝牙双模，适用于智能家居场景。",
        "BS20 芯片适用于低功耗 IoT 场景，内置 RISC-V 处理器。",
        "烧录固件前需连接 USB 数据线并选择正确的串口号。",
    ]

    retriever = build_retriever(docs)

    assert retriever is not None
    assert hasattr(retriever, "get_relevant_documents")


# ---------------------------------------------------------------------------
# Scenario 2 – answer_question returns a non-empty string
# ---------------------------------------------------------------------------
def test_answer_question_returns_string(mocker):
    """answer_question must return a non-empty string.

    Mocks _qa_chain.run so no real LLM or embedding calls are made.
    """
    mock_answer = "BS21 芯片支持Wi-Fi和蓝牙"
    mocker.patch("src.chains.qa_chain._qa_chain.run", return_value=mock_answer)

    result = answer_question("BS21 支持哪些无线协议？")

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Scenario 3 – answer_question calls chain.run with the question text
# ---------------------------------------------------------------------------
def test_answer_question_calls_run_with_question(mocker):
    """answer_question must call _qa_chain.run exactly once with the question.

    Verifies that the question text is passed through to the underlying chain.
    """
    mock_run = mocker.patch(
        "src.chains.qa_chain._qa_chain.run", return_value="任意回答内容"
    )

    question = "如何下载 BS22 的 SDK？"
    answer_question(question)

    mock_run.assert_called_once()
    call_args = mock_run.call_args
    # The question text must appear in either positional or keyword arguments
    all_args = list(call_args.args) + list(call_args.kwargs.values())
    assert any(question in str(arg) for arg in all_args), (
        f"Expected question '{question}' to be in call args, got: {call_args}"
    )
