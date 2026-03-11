"""E2E streaming integration tests for POST /chat/stream (F20).

Starts a real FastAPI server on a free port (auto-selected to avoid Windows
reserved port ranges) and makes real LLM + embedding calls.
Run standalone with:
  pytest tests/e2e/test_e2e_v02_stream.py -v -m integration
"""

import json
import os
import socket
import subprocess
import sys
import time

import httpx
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")


def _get_free_port() -> int:
    """Return an available TCP port chosen by the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_server_v02():
    """Start FastAPI server on a free port, yield base_url, then terminate."""
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.api.main:app",
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
        ],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            r = httpx.get(f"{base_url}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("FastAPI server failed to start within 30 seconds")

    yield base_url

    proc.terminate()
    proc.wait(timeout=10)


def _collect_sse_lines(url: str, payload: dict) -> list[str]:
    """POST to url, collect all non-empty SSE data lines from the stream."""
    lines = []
    with httpx.stream("POST", url, json=payload, timeout=60) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Scenario 1 – knowledge Q&A streaming
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_stream_knowledge_qa(api_server_v02):
    """知识问答流: status=200, Content-Type=text/event-stream, ≥1 delta事件, 最后为 [DONE]"""
    base_url = api_server_v02
    lines = _collect_sse_lines(
        f"{base_url}/chat/stream",
        {"message": "HiSpark Studio支持哪些芯片型号？", "thread_id": "e2e-stream-v02-qa"},
    )

    assert lines, "Expected at least one SSE line"
    assert lines[-1] == "data: [DONE]", f"Last line must be 'data: [DONE]', got: {lines[-1]!r}"

    delta_lines = [l for l in lines[:-1] if l.startswith("data: ")]
    assert len(delta_lines) >= 1, "Expected at least one delta event before [DONE]"

    for dl in delta_lines:
        event = json.loads(dl[6:])
        assert "delta" in event, f"delta field missing in event: {event}"
        assert "thread_id" in event, f"thread_id missing in event: {event}"


# ---------------------------------------------------------------------------
# Scenario 2 – action intent streaming
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_stream_action_intent(api_server_v02):
    """action意图流: 一条 type=action 事件, command 以 hispark-studio. 开头, 最后为 [DONE]"""
    base_url = api_server_v02
    lines = _collect_sse_lines(
        f"{base_url}/chat/stream",
        {"message": "帮我编译项目", "thread_id": "e2e-stream-v02-action"},
    )

    assert lines, "Expected at least one SSE line"
    assert lines[-1] == "data: [DONE]", f"Last line must be 'data: [DONE]', got: {lines[-1]!r}"

    data_lines = [l for l in lines[:-1] if l.startswith("data: ")]
    assert len(data_lines) == 1, (
        f"Expected exactly one action event before [DONE], got {len(data_lines)}: {data_lines}"
    )

    event = json.loads(data_lines[0][6:])
    assert event.get("type") == "action", f"Expected type=action, got: {event}"
    assert str(event.get("command", "")).startswith("hispark-studio."), (
        f"command must start with 'hispark-studio.', got: {event.get('command')!r}"
    )
    assert "thread_id" in event, f"thread_id missing in event: {event}"
