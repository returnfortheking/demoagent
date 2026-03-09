# 计划文档编写规范

参考基准：`docs/plans/2026-03-02-v0.1-plan.md`

---

## 核心原则

**计划 = 描述 WHAT，不描述 HOW**

---

## 禁止项

| 禁止 | 正确替代 |
|------|---------|
| 写完整 Python/TypeScript 实现代码 | 写接口签名 + 行为规约（文字） |
| 写完整测试文件代码 | 写测试场景表格（输入 → 期望） |
| 在验收步骤里写代码 | 只写 bash 命令 + 预期输出 |

---

## 各节标准格式

**接口定义** — 伪代码/文字，只写签名和契约：
```
function_name(param: type) -> return_type
  - 行为说明
  - 异常说明
```

**单元测试场景** — 表格：
```
| # | 场景 | Mock/输入 | 期望结果 |
```

**验收** — 只写命令：
```bash
pytest tests/unit/xxx.py -v
# 预期: N 个 PASSED
```

**Commit** — 一行 conventional commit message

---

## 检查清单（生成后自查）

- [ ] 没有出现超过 3 行的 Python/TypeScript 代码块
- [ ] 测试场景用表格，不用代码
- [ ] 验收只有命令，没有函数定义
