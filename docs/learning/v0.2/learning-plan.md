# 学习计划：hispark-ai-agent v0.2 代码精讲

> **目标：** 对 v0.2 新增的技术点能言之有物。v0.2 的核心是 **LCEL 重构** 和 **SSE 流式架构**，这两个主题在 LangChain 相关面试中出现频率极高。
> **方式：** 与 v0.1 相同，从项目真实代码出发讲解。
> **前提：** 已完成 v0.1 学习模块（尤其是 03-langchain-core 和 04-rag-pipeline）。

---

## 模块 01：LCEL 与 Runnable 体系

**为什么先学这个：** v0.2 的所有重构都建立在 LCEL 上。理解 LCEL 的设计哲学，才能说清楚为什么从 LLMChain 迁移过来，收益是什么。

**讲解内容：**
```
backend/src/chains/intent_classifier.py    ← LCEL 意图分类链
backend/src/chains/qa_chain.py             ← LCEL RAG 链 + RunnableWithMessageHistory
backend/src/prompts/intent_v1.py           ← 版本化 Prompt
backend/src/prompts/qa_v1.py
```

**覆盖概念：**

**第一层：LCEL 基础**
1. `|` 运算符的含义：把两个 Runnable 串联成管道
2. `Runnable` 协议：任何有 `.invoke()` / `.stream()` / `.astream()` 的对象
3. `ChatPromptTemplate.from_template()`：替代 `PromptTemplate`，处理 Chat 格式
4. `JsonOutputParser`：如何处理 markdown 代码块包裹的 JSON（vs v0.1 手写 strip）
5. `StrOutputParser`：把 `AIMessage` 对象展开为字符串
6. `RunnableLambda`：把普通 Python 函数包装为 Runnable，插入 LCEL 管道

**第二层：LCEL 与旧 API 对比**
7. `LLMChain.run(question)` → `(prompt | llm | parser).invoke({"message": question})`
8. `RetrievalQA.from_chain_type(...)` → 手动组装：`itemgetter | retriever | _format_docs`
9. 为什么 LCEL 的可测性更好（不依赖 Pydantic BaseModel）
10. 懒加载工厂函数模式在 LCEL 里同样适用

**第三层：RunnableWithMessageHistory**
11. 它解决什么问题：让无状态的 LCEL 链具备多轮对话记忆
12. `get_session_history(session_id)` 的设计：用 dict 存 `ChatMessageHistory`
13. `input_messages_key` 的副作用：输入值会被包装成 `[HumanMessage]`（v0.2 的核心 bug）
14. `_to_question_str` + `RunnableLambda`：如何在管道里归一化输入类型
15. 调用时 `config={"configurable": {"session_id": sid}}` 的含义

**面试高频问题预告：**
- "你用 LangChain 做了哪些？从 v0.1 到 v0.2 有什么改进？"
- "什么是 LCEL？和以前的 Chain 有什么区别？"
- "RunnableWithMessageHistory 是怎么实现多轮对话的？"
- "你遇到过 LangChain 框架的坑吗？"（`input_messages_key` 包装问题）

---

## 模块 02：SSE 流式架构（端到端）

**为什么单独成模块：** SSE 是现代 LLM 应用的标配。从 FastAPI 后端到 Extension 前端，整个链路涉及多个技术点，每个节点都有面试价值。

**讲解内容：**
```
backend/src/api/main.py                     ← FastAPI StreamingResponse
backend/tests/unit/test_api_stream.py       ← 异步流式单元测试
extension/src/webview/ChatPanel.ts          ← Node.js http.request SSE 消费
extension/src/webview/chatHtml.ts           ← Webview 流式渲染
extension/src/webview/streamingState.ts     ← 纯函数状态机
extension/src/test/suite/streaming.test.ts  ← 纯函数单元测试
tests/e2e/test_e2e_v02_stream.py           ← 集成测试（真实 LLM 流式）
```

**覆盖概念：**

**第一层：SSE 协议**
1. SSE 是什么：基于 HTTP 长连接的单向推送协议
2. 事件格式：`data: <payload>\n\n`（每个事件后两个换行）
3. `[DONE]` 约定：OpenAI 规范的流式终止标志
4. SSE vs WebSocket：为什么 LLM streaming 场景选 SSE

**第二层：FastAPI 后端**
5. `StreamingResponse(generator, media_type="text/event-stream")`：如何实现 SSE
6. `async def generate()` + `yield`：Python 异步生成器
7. `chain.astream(input, config)` vs `chain.invoke()`：异步流式 vs 同步
8. action 意图的处理：SSE 返回单条 action 事件，不用 astream

**第三层：httpx 异步流式测试**
9. `AsyncClient(transport=ASGITransport(app=app))`：不启动真实 HTTP 服务器测试 FastAPI
10. `async with client.stream(...) as response`：httpx 流式客户端
11. `response.aiter_lines()`：逐行异步迭代 SSE 响应
12. 为什么要过滤空行（`if line`）
13. 为什么 mock `src.chains.qa_chain._get_qa_chain` 而不是 `src.api.main._get_qa_chain`：模块引用 vs `from ... import` 绑定

**第四层：Node.js Extension 侧**
14. `http.request()` 读取 SSE：Node.js stream 的 `data` 事件
15. 行缓冲（line buffering）：为什么要 `buffer += chunk; lines = buffer.split('\n'); buffer = lines.pop()`
16. `postMessage` 架构：Extension Host → Webview 的消息总线
17. `statusUpdate` / `streamChunk` / `streamDone` / `actionDone`：四种消息类型的语义

**第五层：Webview 纯函数状态机**
18. `streamingState.ts`：为什么提取为纯函数（testability，同 v0.1 `chatHtml.ts`）
19. `applyStreamEvent(state, event) -> newState`：不可变状态更新
20. Playwright 流式 E2E 测试的时序问题：为什么要等 status-bar 清空后再断言内容

**面试高频问题预告：**
- "LLM 的流式输出是怎么实现的？后端和前端分别做了什么？"
- "SSE 和 WebSocket 的区别是什么？你为什么选 SSE？"
- "你怎么测试流式接口？"
- "Node.js 怎么消费 SSE 流？"

---

## 学习顺序建议

**标准顺序：** 01 → 02

**如果面试侧重 LangChain 技术栈：** 先深读 01，重点是 LCEL 对比 LLMChain，以及 `RunnableWithMessageHistory` 的机制和坑。

**如果面试侧重系统设计：** 先读 02 的第一层（SSE 协议）和 架构决策部分，然后展开各层细节。

---

## 关联文档

- 复盘文档（问题与决策记录）：`docs/changelogs/v0.2-retrospective.md`
- v0.1 学习文档（前置知识）：`docs/learning/v0.1/`
- v0.2 开发计划：`docs/plans/2026-03-07-v0.2-plan.md`
