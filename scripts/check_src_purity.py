"""check_src_purity.py — 检查生产代码（src/）不含测试专用代码。

用法：
    python scripts/check_src_purity.py          # 检查，有问题则以非零退出码退出
    python scripts/check_src_purity.py --fix    # 仅报告，不自动修复（需人工处理）

可加入 CI 流程或 pre-commit hook：
    python scripts/check_src_purity.py || exit 1

背景：
    2026-03-04 事故：_ChainWrapper 作为 pytest-mock 的 testing seam 混入了 src/。
    本脚本自动检测类似问题，不依赖人工记忆或 LLM 上下文。
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "backend" / "src"

# 类/函数文档字符串里出现这些词，说明它为测试而存在
TEST_KEYWORDS = {"mock", "patch", "pytest", "mocker", "testing seam", "unit test"}

# 类名里出现这些模式，说明它可能是测试包装
SUSPICIOUS_CLASS_PATTERNS = {"wrapper", "stub", "fake", "spy"}

issues: list[str] = []


def check_file(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        class_name = node.name
        docstring = ast.get_docstring(node) or ""

        # 规则 1：类文档字符串里出现测试关键词
        docstring_lower = docstring.lower()
        matched_keywords = [kw for kw in TEST_KEYWORDS if kw in docstring_lower]
        if matched_keywords:
            issues.append(
                f"{path.relative_to(ROOT)}:{node.lineno} "
                f"类 `{class_name}` 的文档字符串包含测试关键词: {matched_keywords}"
            )

        # 规则 2：类名本身包含可疑模式（不区分大小写）
        name_lower = class_name.lower()
        matched_patterns = [p for p in SUSPICIOUS_CLASS_PATTERNS if p in name_lower]
        if matched_patterns:
            issues.append(
                f"{path.relative_to(ROOT)}:{node.lineno} "
                f"类名 `{class_name}` 包含可疑模式（可能是测试替身）: {matched_patterns}"
            )


def main() -> int:
    if not SRC_DIR.exists():
        print(f"[ERROR] src 目录不存在: {SRC_DIR}")
        return 2

    for py_file in SRC_DIR.rglob("*.py"):
        check_file(py_file)

    if issues:
        print("[FAIL] src/ purity issues found:\n")
        for issue in issues:
            print(f"  - {issue}")
        print(
            "\nPlease check if the above classes exist only for testing."
            "\nCorrect approach: use factory functions or dependency injection."
            "\nSee: docs/incidents/2026-03-04-chain-wrapper-in-production.md"
        )
        return 1

    file_count = len(list(SRC_DIR.rglob("*.py")))
    print(f"[OK] src/ purity check passed ({file_count} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
