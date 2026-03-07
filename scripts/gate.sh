#!/usr/bin/env bash
# gate.sh — 普通提交的轻量质量门禁（src purity + 分层检查 + unit tests）
# 用法：bash scripts/gate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Quality Gate (light) ==="

echo "[1/3] src purity..."
python scripts/check_src_purity.py

echo "[2/3] test layer boundaries..."
python scripts/check_test_layers.py

echo "[3/3] unit tests..."
cd "$ROOT/backend" && pytest tests/unit -x -q

echo ""
echo "[OK] Light gate passed."
