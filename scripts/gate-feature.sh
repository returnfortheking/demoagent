#!/usr/bin/env bash
# gate-feature.sh — Feature 提交的完整质量门禁
# 由 commit-msg hook 在检测到 feat(Fxx): 时自动调用
# 也可手动执行：bash scripts/gate-feature.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "╔══════════════════════════════════════╗"
echo "║  Feature Commit Quality Gate         ║"
echo "╚══════════════════════════════════════╝"

echo "[1/6] src purity..."
python scripts/check_src_purity.py

echo "[2/6] test layer boundaries..."
python scripts/check_test_layers.py

echo "[3/6] contract assertions (warning only)..."
python scripts/check_contract_assertions.py

echo "[4/6] unit tests..."
cd "$ROOT/backend" && pytest tests/unit -x -q

echo "[5/6] integration tests..."
cd "$ROOT/backend" && pytest tests/integration -x -q

echo "[6/6] E2E (extension + webview)..."
cd "$ROOT/extension" && E2E_MODE=gate npm run test:e2e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  All 6 gates passed.                 ║"
echo "╚══════════════════════════════════════╝"
