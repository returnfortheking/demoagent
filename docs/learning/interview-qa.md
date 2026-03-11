# hispark-ai-agent 项目实战面试问答

> 记录项目开发中涉及的面试题、我的作答和标准答案，持续更新。
> 格式：❌我的答案（问题分析）→ ✅标准答案 → 💡记忆要点

---

## v0.2：LCEL 与 RunnableWithMessageHistory

### Q1 `RunnableWithMessageHistory` 的 `input_messages_key` bug：根因是什么？为什么单元测试发现不了？

**❌ 我的答案**
> 根因是 input 这个属性导致 history 这个接口返回值发生了变化。在调用时出现了类型不匹配报错。单元测试里，由于默认 rag 模块运行成功，没有实际调用真实 RAG 接口，所以没发现这个错误。

**问题分析**
- "history 接口返回值发生了变化"——定位偏了。变化的不是 history 的返回值，而是**框架把传给 base_chain 的 question 值改了**
- 根因要说清楚变换链路：字符串 → `[HumanMessage]` → 流到 retriever → tiktoken 崩
- 单元测试发现不了的原因方向对，但可以说得更具体

**✅ 标准答案**

根因：`input_messages_key="question"` 告诉框架"question 是用户消息"，框架把 question 的值从字符串包装成 `[HumanMessage("...")]`，再传给 base_chain。

完整变换链路：
```
你传入:   {"question": "帮我编译项目"}  ← 字符串
框架处理: input_messages_key="question"
→ question 值被包装成 [HumanMessage("帮我编译项目")]
→ base_chain 里 itemgetter("question") 取到 list
→ list 流到 retriever
→ tiktoken 期望 str，拿到 list，崩：
  TypeError: argument 'text': 'list' object cannot be converted to 'PyString'
```

为什么单元测试发现不了：单元测试 mock 了 `_get_qa_chain()` 返回假链，`astream` 也是假的，**retriever 根本没被调用**，tiktoken 不会执行，类型错误自然暴露不了。集成测试用真实 embedding，retriever 真正被调用，才崩。

修复：在 retriever 前插入 `_to_str = RunnableLambda(_to_question_str)` 归一化类型：
```python
"context": itemgetter("question") | _to_str | retriever | _format_docs
```

**💡 记忆要点**
- 框架改的是**传给 base_chain 的输入值**，不是 history 接口
- 单元测试发现不了 = retriever 被 mock 替代，没有执行路径到 tiktoken
- 修复关键词：`RunnableLambda` 类型归一化，插在 retriever 之前

---

### Q2 `from...import` 导致 mock 失效：本质原因是什么？

**❌ 我的答案**
> import 的内容和 patch 替换的内容不一致，导致没有真正生效。

**问题分析**
- 方向对，但"不一致"说得太模糊，面试官会追问"哪里不一致"
- 需要说清楚：`from X import Y` 在当前模块创建了**独立的本地变量**，patch 改的是 X 模块的属性，两者是两个不同的引用

**✅ 标准答案**

`from X import Y` 会在当前模块里创建一个**本地变量**，它是对原函数的独立引用。patch 之后：

```
X.Y              → 指向 mock 函数    ← patch 改了这里
main.py 里的 Y   → 还指向原函数      ← 没被动
```

两个变量在 patch 前指向同一函数，patch 后各自独立，本地变量不受影响。

类比：把公司官网的电话号码改了，但朋友早就把号码存手机里了，他打的还是旧号。

表现：mock 无效，调用了真实 LLM，单元测试产生 37 个 delta 事件而不是预期的 3 个。

修复：改用模块引用，每次调用通过模块对象查找属性：
```python
# ❌ 创建本地绑定，patch 无效
from src.chains.qa_chain import _get_qa_chain

# ✅ 持有模块引用，patch 有效
import src.chains.qa_chain as _qa_chain_module
chain = _qa_chain_module._get_qa_chain()
```

**💡 记忆要点**
- `from X import Y` = 创建本地变量，和 `X.Y` 是两个独立引用
- patch 的原则：**patch 你的代码实际用到的引用，不是函数定义的地方**
- 口诀：`from X import Y` → `patch("your_module.Y")`；`import X; X.Y()` → `patch("X.Y")`

---

## v0.2：SSE 流式架构

### Q3 为什么选 SSE 不选 WebSocket？

**✅ 我的答案（正确）**
> SSE 适合单向通信，WebSocket 适合双向通信。当前流式场景是服务器单向输出 token，不需要过度设计。

**💡 记忆要点**
- 一句话核心：LLM token streaming 是**单向推送**，SSE 够用，WebSocket 是过度设计
- SSE 基于 HTTP，实现简单；WebSocket 需要 Upgrade 握手、帧格式、心跳处理
- 面试补充：SSE 防火墙兼容性更好（走 HTTP 端口），WebSocket 有时需要特殊配置

---

### Q4 行缓冲里 `buffer = lines.pop()` 去掉会发生什么？

**✅ 我的答案（正确）**
> 去掉会导致数据格式混乱，甚至信息错误——chunk 在传输时被分割，接收时没有合并。

**💡 记忆要点**
- 网络传输以"包"为单位，包的边界不一定在行的边界
- `lines.pop()` 把最后一个**可能不完整的行**暂存，等下个 chunk 拼接后再处理
- 去掉后：不完整行直接进入 `for` 循环，`JSON.parse` 遇到残缺 JSON 抛异常，事件丢失
- 具体例子：
  ```
  包1: 'data: {"delta": "Hi'     ← 在 JSON 中间截断
  包2: 'Spark"}\n\n'

  没有 buffer：包1的残缺行直接 JSON.parse → 崩
  有 buffer：包1暂存，包2拼接后得到完整行 → 正常解析
  ```

---
