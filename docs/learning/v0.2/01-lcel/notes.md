# 模块 01：LCEL 与 Runnable 体系（融合版）

> 基于 `hispark-ai-agent v0.2` 真实代码讲解
> 核心文件：`backend/src/chains/intent_classifier.py`、`backend/src/chains/qa_chain.py`

---

## 第 1 讲：什么是 LCEL，为什么要迁移

### 【是什么】

LCEL（LangChain Expression Language）是 LangChain 0.1+ 引入的管道式链式调用 API。

```python
# v0.1 写法（LLMChain，已废弃）
chain = LLMChain(llm=get_llm(), prompt=prompt)
result = chain.run(message="帮我编译项目")

# v0.2 写法（LCEL）
chain = prompt | get_llm() | JsonOutputParser()
result = chain.invoke({"message": "帮我编译项目"})
```

`|` 不是按位或，它是 `Runnable.__or__` 运算符的重载，把两个 Runnable 串联成管道。

### 【项目里在哪】

```
backend/src/chains/intent_classifier.py
  _chain = prompt | get_llm() | JsonOutputParser()   # L32
```

### 【核心设计：Runnable 协议】

任何实现了以下方法的对象都是 Runnable：
- `.invoke(input)` → 同步调用，返回单个结果
- `.stream(input)` → 同步流式调用，返回迭代器
- `.astream(input)` → 异步流式调用，返回异步迭代器

LangChain 里的 `ChatOpenAI`、`ChatPromptTemplate`、`JsonOutputParser`、`StrOutputParser`、`RunnableLambda` 都实现了这个协议，所以都可以用 `|` 串联。

### 【如果不这样写——LLMChain 的问题】

```python
# v0.1 的问题：
chain = LLMChain(llm=get_llm(), prompt=prompt)
# 1. 继承自 Pydantic BaseModel，pytest-mock 无法直接 patch .run()
# 2. 只能 .run()，不支持 .astream()（流式输出需要单独处理）
# 3. 在 LangChain 1.0 中被彻底移除
```

LCEL 的收益：
1. **可测性**：不依赖 Pydantic，`_get_chain()` 工厂函数返回普通 Runnable，可自由 Mock
2. **流式**：所有 Runnable 自动支持 `.astream()`，不需要任何额外代码
3. **可组合**：用 `|` 串联，逻辑一目了然；复杂管道可以拆分成命名变量

### 【面试怎么说】

> "v0.2 我把所有链从 `LLMChain` / `RetrievalQA` 迁移到了 LCEL。LCEL 用 `|` 运算符把 Prompt、LLM、Parser 串成管道，每个节点都是 Runnable，天然支持 `.astream()` 做流式输出——这正是 v0.2 实现 SSE streaming 的基础。迁移后测试也更简单了，不再需要 v0.1 里那个绕过 Pydantic 约束的包装类。"

---

## 第 2 讲：`RunnableLambda`——把普通函数插入管道

### 【是什么】

```python
from langchain_core.runnables import RunnableLambda

def _to_question_str(x) -> str:
    ...

_to_str = RunnableLambda(_to_question_str)

# 现在 _to_str 是 Runnable，可以用 | 串联
base_chain = itemgetter("question") | _to_str | retriever | _format_docs
```

### 【为什么需要它】

`itemgetter("question")` 是普通 Python 对象，不是 Runnable。在 LCEL 管道里直接用 `itemgetter("question") | retriever` 是可以的（`itemgetter` 被自动包装），但自定义函数需要显式用 `RunnableLambda` 包装。

### 【项目里为什么要有 `_to_question_str`】

这是 v0.2 最重要的 bug 的修复点：

```python
# ❌ 没有 _to_str 的版本：
base_chain = {
    "context": itemgetter("question") | retriever | _format_docs,  # retriever 收到 [HumanMessage]
    "question": itemgetter("question"),                              # prompt 收到 [HumanMessage]
}

# ✅ 有 _to_str 的版本：
base_chain = {
    "context": itemgetter("question") | _to_str | retriever | _format_docs,  # retriever 收到 str
    "question": itemgetter("question") | _to_str,                            # prompt 收到 str
}
```

`_to_str` 在这里做的是类型归一化（type normalization）。

---

## 第 3 讲：`RunnableWithMessageHistory`——会话记忆的实现方式

### 【是什么】

```python
_qa_chain = RunnableWithMessageHistory(
    base_chain,               # 被包装的无状态 LCEL 链
    get_session_history,      # 工厂函数：session_id -> ChatMessageHistory
    input_messages_key="question",  # 指定哪个 key 是用户输入
)
```

调用时：
```python
_qa_chain.invoke(
    {"question": "帮我编译项目"},
    config={"configurable": {"session_id": "thread-123"}},
)
```

### 【它做了什么】

1. 从 `get_session_history("thread-123")` 拿到（或创建）该会话的历史记录
2. **把 `input["question"]` 的值包装成 `[HumanMessage(content=input["question"])]`**（⚠️ 关键行为）
3. 把历史消息 + 当前用户消息一起注入到 `base_chain` 的上下文里
4. base_chain 执行完后，把用户消息和 AI 回复都记录进 `ChatMessageHistory`

### 【`input_messages_key` 的副作用——项目里遇到的 bug】

`input_messages_key="question"` 告诉框架："question 这个字段是用户的消息输入，我要把它当消息历史处理。"

框架的处理方式是把字符串包装成 `[HumanMessage]`，让它与历史消息列表格式统一。

但 base_chain 里 `itemgetter("question") | retriever`，retriever 收到的是 `[HumanMessage("帮我编译项目")]`，而不是字符串 `"帮我编译项目"`。

tiktoken（词元计数库）对 list 调用了期望 str 的接口，崩了：
```
TypeError: argument 'text': 'list' object cannot be converted to 'PyString'
```

**修复：在 retriever 之前插入 `_to_str` 归一化：**
```python
"context": itemgetter("question") | _to_str | retriever | _format_docs
```

### 【`get_session_history` 的设计】

```python
_session_store: dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]
```

v0.2 用 in-process dict 存会话。`ChatMessageHistory` 本身是 list，`add_user_message()` / `add_ai_message()` 追加消息。

这是最简单的实现，足以验证多轮对话概念。v0.3+ 可以换成 Redis 或数据库持久化，只需要替换 `get_session_history` 函数，`RunnableWithMessageHistory` 的接口不变。

### 【面试怎么说】

> "RAG 链的多轮对话我用了 `RunnableWithMessageHistory`，它把无状态的 LCEL 链包装成有状态的，每个 session_id 对应一个 `ChatMessageHistory`，存在内存 dict 里。
>
> 这里踩了一个坑：设置 `input_messages_key="question"` 后，框架会把 question 字符串包装成 `[HumanMessage]` 再传给 base chain，导致后面的 retriever 收到 list 而不是 string，tiktoken 崩了。解决方案是在 retriever 前插入一个 `RunnableLambda` 做类型归一化。这个坑是单元测试里发现不了的，集成测试跑真实 embedding 才暴露出来。"

---

## 第 4 讲：Prompt 版本管理（F17）

### 【是什么】

```
backend/src/prompts/
    __init__.py
    intent_v1.py    ← INTENT_PROMPT_TEMPLATE
    qa_v1.py        ← QA_PROMPT_TEMPLATE
```

### 【为什么单独提取】

v0.1 的 Prompt 直接硬编码在 Chain 实现文件里。这样做有几个问题：

1. 改 Prompt 需要修改业务逻辑文件，影响范围不明确
2. 无法在不改代码的情况下做 A/B 测试（`intent_v1.py` vs `intent_v2.py`）
3. diff 不直观：git blame 显示的是 Chain 文件的修改，而不是 Prompt 的修改

**提取后的好处：**
- Prompt 变更有独立的 git 提交记录
- `intent_v2.py` 可以直接在测试里导入对比效果
- 业务代码只 import Prompt 常量，不关心 Prompt 内容

### 【面试怎么说】

> "v0.2 我把 Prompt 从业务逻辑文件里提取出来，放到 `src/prompts/intent_v1.py` 等独立文件。好处是 Prompt 变更有独立的 git 历史，后面做 A/B 测试时可以直接 `from src.prompts.intent_v2 import INTENT_PROMPT_TEMPLATE` 替换，不需要改 Chain 的代码。"

---

## 第 5 讲：patch 目标——`from ... import` vs 模块引用

### 【这是整个测试章节最重要的细节之一】

v0.2 `main.py` 的 `/chat/stream` 端点需要调用 `_get_qa_chain()`。

**错误写法（第一版实现）：**
```python
# main.py
from src.chains.qa_chain import _get_qa_chain  # ❌ 创建了本地绑定

async def generate():
    chain = _get_qa_chain()  # 调用的是本地绑定，不受 patch 影响
```

**测试里 patch：**
```python
mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)
# ❌ patch 修改了模块里的 _get_qa_chain，但 main.py 里的本地绑定没有变
```

结果：mock 无效，`_get_qa_chain()` 调用了真实函数，初始化了真实链，调用了真实 LLM。

**正确写法：**
```python
# main.py
import src.chains.qa_chain as _qa_chain_module  # ✅ 持有模块引用

async def generate():
    chain = _qa_chain_module._get_qa_chain()  # 每次通过模块对象查找属性
```

**测试里 patch：**
```python
mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)
# ✅ patch 修改了模块的 _get_qa_chain 属性，_qa_chain_module._get_qa_chain 查找时得到 mock
```

### 【原则总结】

```
Patch 你测试的代码实际用到的引用，而不是函数定义所在的地方。

代码的导入方式         正确的 patch 路径
─────────────────────────────────────────────────────
from X import Y       →  patch("your_module.Y")
import X; X.Y(...)    →  patch("X.Y")
import X as alias; alias.Y(...)  →  patch("X.Y")（alias只是模块引用，patch模块属性即可）
```

---

## 思维导图

```
LCEL 体系
│
├── 管道语法：prompt | llm | parser
│   ├── | 是 __or__ 运算符重载
│   ├── 每个节点都是 Runnable（invoke/stream/astream）
│   └── RunnableLambda：把普通函数变成 Runnable
│
├── 会话记忆：RunnableWithMessageHistory
│   ├── 包装无状态链 → 有状态
│   ├── input_messages_key 的副作用（⚠️ 包装成 [HumanMessage]）
│   └── 修复：_to_str 归一化
│
├── 可测性
│   ├── 不依赖 Pydantic BaseModel → 无需 _ChainWrapper
│   ├── _get_chain() 工厂函数 → patch 入口
│   └── from...import 陷阱 → 改用模块引用
│
└── Prompt 版本管理
    ├── 提取到 src/prompts/
    └── v1/v2... 独立文件，支持 A/B 对比
```
