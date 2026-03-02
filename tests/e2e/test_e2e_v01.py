# tests/e2e/test_e2e_v01.py

import subprocess
import time
import sys
import os
import httpx
import pytest

BASE_URL = "http://localhost:8000"
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")


@pytest.fixture(scope="module")
def api_server():
    """Start FastAPI server as subprocess, yield, then terminate."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for server to be ready
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


def test_health(api_server):
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_build_intent(api_server):
    r = httpx.post(f"{BASE_URL}/chat", json={"message": "帮我编译项目", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.build"
    assert data["requires_confirmation"] is False


def test_flash_intent(api_server):
    r = httpx.post(f"{BASE_URL}/chat", json={"message": "烧录固件", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "action"
    assert data["command"] == "hispark-studio.flash"
    assert data["requires_confirmation"] is True


def test_knowledge_qa(api_server):
    r = httpx.post(f"{BASE_URL}/chat", json={"message": "如何安装SDK？", "thread_id": "e2e"}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "answer"
    assert data.get("answer") and len(data["answer"]) > 0


def test_missing_message_field(api_server):
    r = httpx.post(f"{BASE_URL}/chat", json={"thread_id": "e2e"}, timeout=10)
    assert r.status_code == 422
