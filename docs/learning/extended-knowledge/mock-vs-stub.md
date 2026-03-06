# Mock vs Stub — 扩展知识笔记

> 来源：Module 02 学习时，发现笔记第 1 讲里"全 Mock"的说法不够精确。
> 项目代码里两种用法都有，触发了对测试替身分类的深入讨论。
>
> 面试价值：体现你不只是"会写测试"，而是理解测试设计的精确语义。

---

## 测试替身（Test Double）的 5 种分类

Martin Fowler《Mocks Aren't Stubs》中的权威定义：

| 类型 | 作用 | 关心什么 |
|---|---|---|
| **Dummy** | 占位，从不被真正使用 | 什么都不关心 |
| **Fake** | 有真实实现但走捷径（如内存数据库） | 功能正确性 |
| **Stub** | 返回固定值，让代码能继续跑 | 返回值 |
| **Spy** | 在 Stub 基础上记录调用信息 | 返回值 + 部分调用记录 |
| **Mock** | 预设期望，验证交互是否发生 | 调用行为（次数、参数） |

日常工作中最常混淆的是 **Stub** 和 **Mock**。

---

## Stub vs Mock 的核心区别

| | Stub | Mock |
|---|---|---|
| 本质 | 控制**输入**（让代码能走下去） | 验证**行为**（交互是否发生） |
| 断言方向 | 断言最终**结果** | 断言**调用本身** |
| 失败原因 | 结果与预期不符 | 调用次数/参数与预期不符 |

---

## 对照项目代码

**纯 Stub** — `test_intent_classifier.py`

```python
mock_chain = mocker.MagicMock()
mock_chain.run.return_value = llm_response
mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)
result = classify_intent("帮我编译项目")
assert result["type"] == "action"   # 只断言最终结果
```

只关心"给我一个返回值让后续能跑"，没有验证 `_get_chain` 被调了几次。这是 **Stub**。

---

**Mock** — `test_api.py:42-43`

```python
mock_classify = mocker.patch("src.api.main.classify_intent", ...)
mock_answer = mocker.patch("src.api.main.answer_question")

mock_classify.assert_called_once()   # 验证调用行为 ← 这里变成 Mock
mock_answer.assert_not_called()      # 验证调用行为 ← 这里变成 Mock
```

有 `assert_called_once()` / `assert_not_called()` 才是真正的 **Mock**——验证的是"两个函数之间的交互协议"：action 场景下 classify 必须被调一次、answer 不能被调。

---

## 为什么大家都叫"mock"

混淆来自两处：

1. **Python 库命名**：`unittest.mock.MagicMock`、`pytest-mock` 全叫 mock，但用法上可以是 Stub
2. **口语惯例**："mock 掉依赖"通常泛指所有测试替身，包括 Stub

不必纠结用词，但理解背后的区别对设计测试有帮助：
- 大量使用 assert_called 验证行为 → 测试与实现耦合，重构时测试容易失败
- 只用 Stub 控制返回值、只断言结果 → 测试更稳定，更关注"做了什么"而非"怎么做的"

---

## 面试怎么用这部分知识

### 被问到"Mock 和 Stub 的区别"时

> "Stub 只提供返回值，让被测代码能运行到底，最终断言的是结果。
> Mock 在此基础上还验证调用行为——有没有被调、调了几次、传了什么参数。
>
> 项目里两种都有：`test_intent_classifier.py` patch `_get_chain` 工厂函数、只断言解析结果，是 Stub；
> `test_api.py` 里有 `mock_classify.assert_called_once()` 和 `mock_answer.assert_not_called()`，
> 验证的是 action 场景下两个函数的调用关系，是 Mock。"

### 被问到"你倾向于多用 Mock 还是 Stub"时

> "倾向于 Stub，原因是稳定性。Stub 只关心最终结果，内部实现怎么变不影响测试；
> Mock 验证了调用细节，一旦重构（比如把两次调用合并成一次），测试就要跟着改。
> Mock 真正有价值的场景是验证关键的交互协议，比如'action 场景下绝不能调 answer_question'，
> 这个约束如果靠 Stub+结果断言是表达不出来的。"
