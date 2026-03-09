"""Unit tests for POST /chat/stream SSE endpoint (F18).

Uses httpx.AsyncClient with ASGITransport to test the async streaming
endpoint without a real HTTP server.  classify_intent and _get_qa_chain
are mocked so no real LLM or embedding calls are made.
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


async def _make_astream(*tokens):
    """Helper: returns an async generator that yields the given tokens."""

    async def _gen(input_, config=None):
        for token in tokens:
            yield token

    return _gen


# ---------------------------------------------------------------------------
# Scenario 1 – answer intent yields delta events + [DONE]
# ---------------------------------------------------------------------------


async def test_stream_answer_yields_deltas(mocker):
    """Answer intent: 3 token deltas + [DONE]; content is concatenated correctly."""
    mocker.patch("src.api.main.classify_intent", return_value={"type": "answer"})

    async def _astream(input_, config=None):
        for token in ["Hello", " world", "!"]:
            yield token

    mock_chain = mocker.MagicMock()
    mock_chain.astream = _astream
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat/stream", json={"message": "test", "thread_id": "t1"}
        ) as response:
            assert response.status_code == 200
            raw_lines = []
            async for line in response.aiter_lines():
                if line:
                    raw_lines.append(line)

    data_lines = [l for l in raw_lines if l.startswith("data: ")]
    assert data_lines[-1] == "data: [DONE]"

    delta_events = [json.loads(l[6:]) for l in data_lines[:-1]]
    assert len(delta_events) == 3
    full_text = "".join(e["delta"] for e in delta_events)
    assert full_text == "Hello world!"
    for e in delta_events:
        assert e["thread_id"] == "t1"


# ---------------------------------------------------------------------------
# Scenario 2 – action intent yields single action event + [DONE]
# ---------------------------------------------------------------------------


async def test_stream_action_single_event(mocker):
    """Action intent: one action event with full fields + [DONE]; astream not called."""
    mocker.patch(
        "src.api.main.classify_intent",
        return_value={
            "type": "action",
            "command": "hispark-studio.build",
            "requires_confirmation": False,
            "description": "编译项目",
            "args": {},
        },
    )
    mock_chain = mocker.MagicMock()
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat/stream", json={"message": "编译", "thread_id": "t2"}
        ) as response:
            assert response.status_code == 200
            raw_lines = []
            async for line in response.aiter_lines():
                if line:
                    raw_lines.append(line)

    data_lines = [l for l in raw_lines if l.startswith("data: ")]
    assert len(data_lines) == 2  # action event + [DONE]
    assert data_lines[-1] == "data: [DONE]"

    action_event = json.loads(data_lines[0][6:])
    assert action_event["type"] == "action"
    assert action_event["command"] == "hispark-studio.build"
    assert action_event["thread_id"] == "t2"
    assert action_event["requires_confirmation"] is False
    assert action_event["description"] == "编译项目"

    # astream must NOT have been called for an action intent
    mock_chain.astream.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 3 – Content-Type header is text/event-stream
# ---------------------------------------------------------------------------


async def test_stream_content_type(mocker):
    """Response Content-Type must include text/event-stream."""
    mocker.patch("src.api.main.classify_intent", return_value={"type": "answer"})

    async def _astream(input_, config=None):
        yield "token"

    mock_chain = mocker.MagicMock()
    mock_chain.astream = _astream
    mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat/stream", json={"message": "test", "thread_id": "t3"}
        ) as response:
            assert "text/event-stream" in response.headers["content-type"]
