# 事故复盘：测试代码混入生产代码

- **日期**：2026-03-04
- **严重程度**：中（功能正常，但违反公司代码规范）
- **发现方式**：代码学习复盘（学习 Module 02 pytest 时，作者主动审查代码）
- **修复 commit**：`8d4a998`

---

## 起因

v0.1 开发期间，TDD 流程里测试先行。`test_intent_classifier.py` 要求 patch `_chain.run`，
但 `LLMChain` 继承自 Pydantic v2 `BaseModel`，其实例禁止 `setattr`/`delattr`，
导致 `mocker.patch("...._chain.run", ...)` 失败。

**当时的决策**：为了让测试通过，在生产代码 `intent_classifier.py` 里加了 `_ChainWrapper` 类：

```python
class _ChainWrapper:
    """Thin wrapper around LLMChain to allow attribute-level mocking."""
    def __init__(self, llm_chain: LLMChain) -> None:
        self._llm_chain = llm_chain
    def run(self, **kwargs) -> str:
        return self._llm_chain.run(**kwargs)
```

同样的问题在 `qa_chain.py` 里也存在，`_ChainWrapper` 被同样地引入了。

---

## 问题

`_ChainWrapper` 没有任何业务价值，它存在的唯一原因是让 pytest-mock 能工作。
这违反了"生产代码不得包含测试专用代码"的原则。

---

## 经过

1. 作者学习 Module 02 第 6 讲（`_ChainWrapper` 模式）时，理解了它的设计意图
2. 作者提问："这部分代码在真实生产环境里会使用吗？"
3. 分析后确认：不会，它是 Testing Seam，不应出现在 `src/` 下
4. 作者确认："我们公司不允许把本地测试用的代码放到生产代码里"，要求修复

---

## 修复方案

将两个文件统一改为**工厂函数（Factory Function）模式**，与 `qa_chain.py` 已有模式一致：

**`intent_classifier.py`**
- 删除 `_ChainWrapper` 类
- 新增 `_get_chain()` 懒加载工厂函数
- `classify_intent()` 改为调用 `_get_chain().run(...)`

**`qa_chain.py`**
- 删除 `_ChainWrapper` 类
- `_get_qa_chain()` 直接返回 `RetrievalQA` 实例（不再包装）
- `_qa_chain` 类型从 `Optional[_ChainWrapper]` 改为 `RetrievalQA | None`

**`test_intent_classifier.py`**
- patch 目标从 `_chain.run` 改为 `_get_chain`，与 `test_qa_chain.py` 的模式统一

**额外收益**：`intent_classifier.py` 从 import 时创建 LLM 连接（eager）改为首次调用时创建（lazy），
启动更快，与 `qa_chain.py` 风格一致。

---

## 测试结果

```
单元测试：14/14 passed
集成测试：10/10 passed
Gradio 手动验收：通过
```

---

## 根本原因分析

| 层级 | 原因 |
|---|---|
| 直接原因 | 遇到 Pydantic v2 patch 限制时，选择了"加包装类"而非"重新设计可测性" |
| 深层原因 | 没有在设计时考虑 Testing Seam 是否应出现在生产代码里 |
| 流程原因 | 缺少对"生产代码纯净性"的自动检查，依赖人工审查发现 |

---

## 规避措施

见 `scripts/check_src_purity.py`，已加入项目。

**设计原则（补充到 CLAUDE.md）**：
- 生产代码（`src/`）里不得出现任何为测试而存在的类、函数或注释
- 遇到 Pydantic v2 / 第三方库 patch 限制时，正确解法是工厂函数或依赖注入，而不是包装类
