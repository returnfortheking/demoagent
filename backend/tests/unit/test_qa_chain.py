"""Unit tests for the qa_chain module.

Test 1: answer_question returns a non-empty string (mocked _get_qa_chain).

Test 2: answer_question calls chain.run exactly once with the question text
         (mocked _get_qa_chain).

Mock strategy
-------------
Because ``_qa_chain`` is now lazily initialized (None at import time), patching
``src.chains.qa_chain._qa_chain.run`` would fail — the attribute is None until
the first real call.  Instead, we patch ``src.chains.qa_chain._get_qa_chain``
to return a MagicMock that has a ``run`` method.  This completely bypasses
chain construction (no embedding or LLM calls) while still exercising the
``answer_question`` code path.

Note: build_retriever integration test (requires real ZhipuAI API) lives in
      backend/tests/integration/test_qa_chain.py
"""

import pytest

from src.chains.qa_chain import answer_question


# ---------------------------------------------------------------------------
# Scenario 1 – answer_question returns a non-empty string
# ---------------------------------------------------------------------------
def test_answer_question_returns_string(mocker):
    """answer_question must return a non-empty string.

    Patches _get_qa_chain so no real LLM or embedding calls are made.
    """
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = "BS21 芯片支持Wi-Fi和蓝牙"
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    result = answer_question("BS21 支持哪些无线协议？")

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Scenario 3 – answer_question calls chain.run with the question text
# ---------------------------------------------------------------------------
def test_answer_question_calls_run_with_question(mocker):
    """answer_question must call chain.run exactly once with the question.

    Verifies that the question text is passed through to the underlying chain.
    Patches _get_qa_chain so no real LLM or embedding calls are made.
    """
    mock_chain = mocker.MagicMock()
    mock_chain.run.return_value = "任意回答内容"
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    question = "如何下载 BS22 的 SDK？"
    answer_question(question)

    mock_chain.run.assert_called_once()
    call_args = mock_chain.run.call_args
    # The question text must appear in either positional or keyword arguments
    all_args = list(call_args.args) + list(call_args.kwargs.values())
    assert any(question in str(arg) for arg in all_args), (
        f"Expected question '{question}' to be in call args, got: {call_args}"
    )
