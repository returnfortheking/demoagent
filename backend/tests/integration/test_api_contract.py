"""API contract tests for /chat and /chat/stream endpoints (F21).

Tests make real LLM calls with a real FastAPI server managed by a pytest
fixture (subprocess.Popen + health check).  The fixture is shared with
test_e2e_v01 but runs on port 8003 to avoid conflicts.

Run with:
  pytest tests/integration/test_api_contract.py -v -m integration
"""

import json
import os
import subprocess
import sys
import time

import httpx
import pytest

BASE_URL = "http://localhost:8003"
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


@pytest.fixture(scope="module")
def api_server_contract():
    """Start FastAPI server on port 8003, yield, then terminate."""
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--port",
            "8003",
            "--host",
            "127.0.0.1",
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("FastAPI server failed to start within 30 seconds")

    yield proc

    proc.terminate()
    proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# /health契约
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_contract_health(api_server_contract):
    """GET /health → 200, body == {"status": "ok"}"""
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /chat 契约
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_contract_action_response_fields(api_server_contract):
    """action 意图响应字段类型和状态码。"""
    r = httpx.post(
        f"{BASE_URL}/chat",
        json={"message": "帮我编译项目", "thread_id": "contract-test"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "action"
    assert isinstance(data["command"], str)
    assert isinstance(data["requires_confirmation"], bool)
    assert isinstance(data["description"], str)
    assert isinstance(data["args"], dict)


@pytest.mark.integration
def test_contract_answer_response_fields(api_server_contract):
    """answer 意图响应字段类型和状态码。"""
    r = httpx.post(
        f"{BASE_URL}/chat",
        json={"message": "如何查看栈分析结果？", "thread_id": "contract-test"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "answer"
    assert isinstance(data["answer"], str) and len(data["answer"]) > 0
    assert isinstance(data["sources"], list)


@pytest.mark.integration
def test_contract_missing_message_returns_422(api_server_contract):
    """缺少 message 字段 → HTTP 422"""
    r = httpx.post(f"{BASE_URL}/chat", json={"thread_id": "contract-test"}, timeout=10)
    assert r.status_code == 422


@pytest.mark.integration
def test_contract_missing_thread_id_returns_422(api_server_contract):
    """缺少 thread_id 字段 → HTTP 422"""
    r = httpx.post(f"{BASE_URL}/chat", json={"message": "test"}, timeout=10)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /chat/stream 契约
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_contract_stream_content_type(api_server_contract):
    """Content-Type header 必须包含 text/event-stream"""
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat/stream",
        json={"message": "帮我编译项目", "thread_id": "contract-stream"},
        timeout=30,
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]


@pytest.mark.integration
def test_contract_stream_delta_contains_thread_id(api_server_contract):
    """所有 delta 事件都包含 thread_id 字段，且与请求一致。"""
    thread_id = "contract-stream-tid"
    lines = []
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat/stream",
        json={"message": "HiSpark支持哪些芯片？", "thread_id": thread_id},
        timeout=60,
    ) as r:
        for line in r.iter_lines():
            if line:
                lines.append(line)

    delta_lines = [
        l for l in lines if l.startswith("data: ") and l != "data: [DONE]"
    ]
    assert len(delta_lines) >= 1, "Expected at least one delta event"
    for dl in delta_lines:
        event = json.loads(dl[6:])
        assert event.get("thread_id") == thread_id, (
            f"Expected thread_id={thread_id!r} in event: {event}"
        )


@pytest.mark.integration
def test_contract_stream_ends_with_done(api_server_contract):
    """流以 data: [DONE] 作为最后一条非空行终止。"""
    lines = []
    with httpx.stream(
        "POST",
        f"{BASE_URL}/chat/stream",
        json={"message": "编译项目", "thread_id": "contract-stream-done"},
        timeout=60,
    ) as r:
        for line in r.iter_lines():
            if line:
                lines.append(line)

    assert lines, "Expected at least one SSE line"
    assert lines[-1] == "data: [DONE]", (
        f"Last line must be 'data: [DONE]', got: {lines[-1]!r}"
    )
