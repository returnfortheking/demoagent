"""Unit tests for the FastAPI /chat endpoint (F05).

All tests use FastAPI TestClient and mock both chain functions so no real
LLM calls are made.

Mock targets:
  - src.api.main.classify_intent
  - src.api.main.answer_question
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Scenario 1 – build intent (action, no confirmation required)
# ---------------------------------------------------------------------------
def test_chat_build_intent(mocker):
    """classify_intent returns build action; answer_question must not be called."""
    mock_classify = mocker.patch(
        "src.api.main.classify_intent",
        return_value={
            "type": "action",
            "command": "hispark-studio.build",
            "requires_confirmation": False,
            "description": "编译项目",
        },
    )
    mock_answer = mocker.patch("src.api.main.answer_question")

    response = client.post("/chat", json={"message": "帮我编译项目", "thread_id": "t1"})

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.build"
    assert data["requires_confirmation"] is False
    mock_classify.assert_called_once()
    mock_answer.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 2 – flash intent (action, confirmation required)
# ---------------------------------------------------------------------------
def test_chat_flash_intent(mocker):
    """classify_intent returns flash action with requires_confirmation=True."""
    mock_classify = mocker.patch(
        "src.api.main.classify_intent",
        return_value={
            "type": "action",
            "command": "hispark-studio.flash",
            "requires_confirmation": True,
            "description": "烧录固件",
        },
    )
    mock_answer = mocker.patch("src.api.main.answer_question")

    response = client.post("/chat", json={"message": "烧录固件", "thread_id": "t2"})

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.flash"
    assert data["requires_confirmation"] is True
    mock_classify.assert_called_once()
    mock_answer.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3 – knowledge Q&A (answer type)
# ---------------------------------------------------------------------------
def test_chat_knowledge_qa(mocker):
    """classify_intent returns answer type; answer_question is called and its result returned."""
    mocker.patch(
        "src.api.main.classify_intent",
        return_value={"type": "answer"},
    )
    mocker.patch(
        "src.api.main.answer_question",
        return_value="BS21支持蓝牙和Wi-Fi双模通信。",
    )

    response = client.post(
        "/chat", json={"message": "BS21支持哪些通信协议？", "thread_id": "t3"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "answer"
    assert data["answer"]  # non-empty
    assert data["sources"] == []


# ---------------------------------------------------------------------------
# Scenario 4 – missing message field → 422
# ---------------------------------------------------------------------------
def test_chat_missing_message():
    """Request without 'message' field must return 422 Unprocessable Entity."""
    response = client.post("/chat", json={"thread_id": "t4"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 5 – missing thread_id field → 422
# ---------------------------------------------------------------------------
def test_chat_missing_thread_id():
    """Request without 'thread_id' field must return 422 Unprocessable Entity."""
    response = client.post("/chat", json={"message": "帮我编译"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scenario 6 – health check
# ---------------------------------------------------------------------------
def test_health_check():
    """GET /health must return 200 with status=ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
