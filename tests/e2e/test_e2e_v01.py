# tests/e2e/test_e2e_v01.py

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
def api_server():
    """Start FastAPI server on a free port, yield base_url, then terminate."""
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", str(port), "--host", "127.0.0.1"],
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


def test_health(api_server):
    r = httpx.get(f"{api_server}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_build_intent(api_server):
    r = httpx.post(f"{api_server}/chat", json={"message": "帮我编译项目", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.build"
    assert data["requires_confirmation"] is False


def test_flash_intent(api_server):
    r = httpx.post(f"{api_server}/chat", json={"message": "烧录固件", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.flash"
    assert data["requires_confirmation"] is True


def test_knowledge_qa(api_server):
    r = httpx.post(f"{api_server}/chat", json={"message": "如何安装SDK？", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "answer"
    assert data.get("answer") and len(data["answer"]) > 0


def test_missing_message_field(api_server):
    r = httpx.post(f"{api_server}/chat", json={"thread_id": "e2e"}, timeout=10)
    assert r.status_code == 422
