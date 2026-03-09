"""Unit tests for the qa_chain module (v0.2 LCEL + RunnableWithMessageHistory).

Tests mock `src.chains.qa_chain._get_qa_chain` so no real LLM or embedding
calls are made.  The chain now wraps a LCEL pipeline with RunnableWithMessageHistory,
so mock.invoke() returns a string directly (StrOutputParser is already applied).
"""

import pytest

from src.chains.qa_chain import answer_question, get_session_history, _session_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_session(session_id: str) -> None:
    """Remove a session from the in-memory store before each test."""
    _session_store.pop(session_id, None)


# ---------------------------------------------------------------------------
# Scenario 1 – answer_question returns a non-empty string
# ---------------------------------------------------------------------------
def test_answer_question_returns_string(mocker):
    """answer_question must return a non-empty string."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = "BS21 芯片支持Wi-Fi和蓝牙"
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    result = answer_question("BS21 支持哪些无线协议？", session_id="s1")

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Scenario 2 – invoke called with correct question and session_id
# ---------------------------------------------------------------------------
def test_answer_question_calls_invoke_with_session_id(mocker):
    """answer_question must call chain.invoke with question dict and session_id config."""
    mock_chain = mocker.MagicMock()
    mock_chain.invoke.return_value = "任意回答内容"
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    question = "如何下载 BS22 的 SDK？"
    answer_question(question, session_id="session-abc")

    mock_chain.invoke.assert_called_once_with(
        {"question": question},
        config={"configurable": {"session_id": "session-abc"}},
    )


# ---------------------------------------------------------------------------
# Scenario 3 – multi-turn: get_session_history accumulates messages
# ---------------------------------------------------------------------------
def test_get_session_history_accumulates_across_calls():
    """Same session_id returns the same ChatMessageHistory object with accumulated messages."""
    session_id = "test-multi-turn-99"
    _clear_session(session_id)

    h1 = get_session_history(session_id)
    h1.add_user_message("BS21支持Wi-Fi吗?")
    h1.add_ai_message("支持Wi-Fi")

    h2 = get_session_history(session_id)

    assert h2 is h1, "Same session_id must return the same history object"
    assert len(h2.messages) == 2

    _clear_session(session_id)
