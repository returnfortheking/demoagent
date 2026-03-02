"""v0.1 Baseline Evaluation Script (F13).

Self-contained script that:
  1. Starts uvicorn as a subprocess (cwd = backend/).
  2. Waits for the /health endpoint to become ready.
  3. POSTs each operation_qa item to /chat and compares the response.
  4. Prints per-item results (pass/fail) and an overall summary.
  5. Saves a JSON report to docs/evaluation/results/v0.1-baseline.json.
  6. Terminates uvicorn before exiting.

Run from backend/:
    python scripts/eval_v01_baseline.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# This script lives at: <project>/backend/scripts/eval_v01_baseline.py
SCRIPT_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = SCRIPT_DIR.parent                       # backend/
PROJECT_ROOT = BACKEND_DIR.parent                     # project root

DATASET_PATH = PROJECT_ROOT / "docs" / "evaluation" / "dataset.json"
RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "v0.1-baseline.json"

API_BASE = "http://localhost:8000"
CHAT_URL = f"{API_BASE}/chat"
HEALTH_URL = f"{API_BASE}/health"

STARTUP_TIMEOUT = 30   # seconds to wait for uvicorn to become ready
STARTUP_POLL    = 0.5  # seconds between health-check polls
REQUEST_TIMEOUT = 30   # seconds per /chat call


# ---------------------------------------------------------------------------
# Uvicorn lifecycle helpers
# ---------------------------------------------------------------------------

def start_uvicorn() -> subprocess.Popen:
    """Start uvicorn as a background subprocess.

    We run it from BACKEND_DIR so that ``src.*`` imports resolve correctly.
    stdout/stderr are inherited so the user can see startup logs.
    """
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--log-level", "warning",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        # Let log output flow to the terminal so the user can see it
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_ready(timeout: float = STARTUP_TIMEOUT, poll: float = STARTUP_POLL) -> bool:
    """Poll /health until the server responds 200 or we time out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(HEALTH_URL, timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(poll)
    return False


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------

def run_evaluation(items: list[dict]) -> list[dict]:
    """Send each item to /chat and return a list of result dicts."""
    results = []
    for item in items:
        item_id       = item["id"]
        user_input    = item["input"]
        expected_type = item["expected_type"]
        expected_cmd  = item.get("expected_command", "")

        predicted_type = ""
        predicted_cmd  = ""
        match          = False
        error          = None

        try:
            resp = httpx.post(
                CHAT_URL,
                json={"message": user_input, "thread_id": "eval"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            predicted_type = data.get("type", "")
            predicted_cmd  = data.get("command", "")

            # Matching rules:
            #   - type must match always
            #   - if expected_type == "action", command must also match
            type_ok    = predicted_type == expected_type
            command_ok = (expected_type != "action") or (predicted_cmd == expected_cmd)
            match      = type_ok and command_ok

        except Exception as exc:
            error = str(exc)

        # Console output — use ASCII markers to stay compatible with Windows GBK console
        mark = "[PASS]" if match else "[FAIL]"
        print(
            f"  {mark} [{item_id}] {user_input!r}\n"
            f"       expected : type={expected_type!r}  command={expected_cmd!r}\n"
            f"       predicted: type={predicted_type!r}  command={predicted_cmd!r}"
            + (f"\n       ERROR    : {error}" if error else "")
        )

        result: dict = {
            "id":               item_id,
            "input":            user_input,
            "expected_type":    expected_type,
            "expected_command": expected_cmd,
            "predicted_type":   predicted_type,
            "predicted_command": predicted_cmd,
            "match":            match,
        }
        if error:
            result["error"] = error
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # -- Load dataset --------------------------------------------------------
    if not DATASET_PATH.exists():
        print(f"ERROR: dataset not found at {DATASET_PATH}", file=sys.stderr)
        return 1

    with DATASET_PATH.open(encoding="utf-8") as f:
        dataset = json.load(f)

    items: list[dict] = dataset.get("operation_qa", [])
    if not items:
        print("ERROR: no operation_qa items in dataset", file=sys.stderr)
        return 1

    print(f"Loaded {len(items)} operation_qa items from {DATASET_PATH}")

    # -- Start uvicorn -------------------------------------------------------
    print("\nStarting uvicorn (src.api.main:app) on port 8000 ...")
    proc = start_uvicorn()

    try:
        print(f"Waiting up to {STARTUP_TIMEOUT}s for server to become ready ...")
        if not wait_for_ready():
            print("ERROR: server did not become ready in time.", file=sys.stderr)
            proc.terminate()
            return 1
        print("Server is ready.\n")

        # -- Run evaluation --------------------------------------------------
        print("=" * 60)
        print("Running evaluation ...")
        print("=" * 60)
        results = run_evaluation(items)

    finally:
        # Always shut down uvicorn
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("\nuvicorn terminated.")

    # -- Summary -------------------------------------------------------------
    total   = len(results)
    correct = sum(1 for r in results if r["match"])
    rate    = correct / total if total else 0.0

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total items      : {total}")
    print(f"  Correct          : {correct}")
    print(f"  command_match_rate: {rate:.2%}")
    print("=" * 60)

    # -- Save report ---------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "version":            "v0.1",
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "total":              total,
        "correct":            correct,
        "command_match_rate": round(rate, 4),
        "results":            results,
    }

    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
