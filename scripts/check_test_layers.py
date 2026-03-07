"""check_test_layers.py — 检查测试分层边界：unit/ 目录禁止出现 integration 标记。

用法：
    python scripts/check_test_layers.py

背景：
    审计发现 backend/tests/unit/test_qa_chain.py 含 @pytest.mark.integration，
    导致"快速反馈层"掺入慢速外部依赖测试，本脚本自动检测此类边界混入。
"""

import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
UNIT_DIR = ROOT / "backend" / "tests" / "unit"

INTEGRATION_PATTERN = re.compile(r"@pytest\.mark\.integration")

issues: list[str] = []


def check_file(path: Path) -> None:
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if INTEGRATION_PATTERN.search(line):
            issues.append(
                f"{path.relative_to(ROOT)}:{lineno}  "
                f"unit/ 目录中出现 @pytest.mark.integration"
            )


def main() -> int:
    if not UNIT_DIR.exists():
        print(f"[ERROR] unit 测试目录不存在: {UNIT_DIR}")
        return 2

    for py_file in UNIT_DIR.rglob("*.py"):
        check_file(py_file)

    if issues:
        print("[FAIL] Test layer boundary violations:\n")
        for issue in issues:
            print(f"  - {issue}")
        print(
            "\n请将 integration 标记的测试移至 backend/tests/integration/ 目录，"
            "\n或移除 @pytest.mark.integration 标记（如该测试确实是纯单元测试）。"
        )
        return 1

    file_count = len(list(UNIT_DIR.rglob("*.py")))
    print(f"[OK] Test layer check passed ({file_count} files in unit/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
