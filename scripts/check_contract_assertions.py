"""check_contract_assertions.py — 检查 TypeScript 客户端是否存在裸类型断言。

用法：
    python scripts/check_contract_assertions.py     # 仅 warning，不阻断

背景：
    审计发现 ApiClient.ts parseResponse 使用 `raw as ChatResponse` 直接断言，
    缺少运行时结构校验，接口漂移时测试不会及时报错。
    此检查仅输出 warning，修复方向是引入 zod 等运行时校验（v0.2 契约门禁后考虑）。
"""

import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGET_FILE = ROOT / "extension" / "src" / "client" / "ApiClient.ts"

# 匹配 return 语句末尾的裸断言：return xxx as DomainType
# 排除内部转换用途（as Record<...>、as string[] 等带泛型或小写的形式）
BARE_ASSERTION = re.compile(r"\breturn\b.+\bas\s+([A-Z][A-Za-z]+)\s*;")

warnings: list[str] = []


def check_file(path: Path) -> None:
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        for match in BARE_ASSERTION.finditer(line):
            warnings.append(
                f"{path.relative_to(ROOT)}:{lineno}  "
                f"裸类型断言 `as {match.group(1)}`，缺少运行时结构校验"
            )


def main() -> int:
    if not TARGET_FILE.exists():
        print(f"[SKIP] 目标文件不存在: {TARGET_FILE}")
        return 0

    check_file(TARGET_FILE)

    if warnings:
        print("[WARN] Contract assertion risks (not blocking):\n")
        for w in warnings:
            print(f"  - {w}")
        print(
            "\n建议：引入 zod 对 parseResponse 返回值做运行时结构校验，"
            "\n防止接口漂移时测试误判通过。"
        )
    else:
        print("[OK] No bare type assertions found in ApiClient.ts")

    return 0  # warning only，不阻断门禁


if __name__ == "__main__":
    sys.exit(main())
