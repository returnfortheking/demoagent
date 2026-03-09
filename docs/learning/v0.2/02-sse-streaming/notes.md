# 模块 02：SSE 流式架构（端到端）

> 基于 `hispark-ai-agent v0.2` 真实代码讲解
> 核心文件：`backend/src/api/main.py`、`extension/src/webview/ChatPanel.ts`、`extension/src/webview/streamingState.ts`

---

## 第 1 讲：SSE 协议基础

### 【是什么】

SSE（Server-Sent Events）是基于 HTTP 的**单向推送**协议。服务器保持 HTTP 连接不断开，持续向客户端推送文本事件。

**事件格式：**
```
data: {"delta": "Hello"}\n\n
data: {"delta": " world"}\n\n
data: [DONE]\n\n
```
- 每条事件以 `data: ` 开头
- 事件体结束后用两个换行（`\n\n`）分隔
- `[DONE]` 是 OpenAI 规范的终止约定，不是协议的硬性要求，但已成行业标准

### 【SSE vs WebSocket】

| 维度 | SSE | WebSocket |
|------|-----|-----------|
| 方向 | 单向（服务器→客户端） | 双向 |
| 协议 | 基于 HTTP/1.1 | 需要 `Upgrade` 握手 |
| 实现复杂度 | 低（就是 HTTP 长连接） | 高（帧格式、心跳、重连） |
| 适用场景 | LLM token 流式输出、通知推送 | 聊天室、协同编辑、游戏 |
| 防火墙兼容性 | 好（HTTP 端口） | 有时需要特殊配置 |

**本项目选 SSE 的原因：** LLM token streaming 是单向推送，SSE 足够用，WebSocket 是过度设计。

### 【面试怎么说】

> "流式输出我选了 SSE，因为 LLM token streaming 本质上是服务器单向推送，SSE 基于 HTTP 就能实现，FastAPI 用 `StreamingResponse` 几行代码就搞定。WebSocket 是双向协议，用在这里杀鸡用牛刀，还要处理握手和帧格式，复杂度不值得。"

---

## 第 2 讲：FastAPI 后端实现

### 【项目里在哪】

```
backend/src/api/main.py
  @app.post("/chat/stream")        # L49
  async def chat_stream(...)
```

### 【核心代码走读】

```python
from fastapi.responses import StreamingResponse

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():                     # ① 异步生成器
        intent = classify_intent(request.message)   # ② 同步分类（阻塞）

        if intent.get("type") == "action":
            event_data = {
                "thread_id": request.thread_id,
                "type": "action",
                "command": intent["command"],
                ...
            }
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"  # ③ 单条 action 事件
        else:
            chain = _qa_chain_module._get_qa_chain()   # ④ 通过模块引用访问
            async for token in chain.astream(          # ⑤ LCEL 异步流式调用
                {"question": request.message},
                config={"configurable": {"session_id": request.thread_id}},
            ):
                event_data = {"thread_id": request.thread_id, "delta": token}
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"  # ⑥ 每个 token 一条事件

        yield "data: [DONE]\n\n"   # ⑦ 终止标志

    return StreamingResponse(generate(), media_type="text/event-stream")  # ⑧ SSE 响应
```

**逐点解析：**

① `async def generate()` 是 Python 异步生成器。有 `yield` 的 `async def` 函数就是异步生成器。

② `classify_intent` 是同步函数，在 async 上下文里调用会阻塞事件循环。v0.2 接受这个阻塞（意图分类耗时 1-2s，对用户来说可以接受）。v0.3+ 可以改为 `await asyncio.to_thread(classify_intent, ...)` 避免阻塞。

③ action 意图：单条事件，不用流式。

④ `_qa_chain_module._get_qa_chain()` 通过模块引用访问，支持 mock（`from ... import` 创建本地绑定，无法被 patch）。

⑤ `chain.astream(input, config)` 是 LCEL 的异步流式调用。返回异步迭代器，每次 `yield` 一个 token 字符串。

⑥ `ensure_ascii=False`：保证中文字符不被转义成 `\uXXXX`。

⑦ 无论 action 还是 answer，最后都 yield `[DONE]`。

⑧ `StreamingResponse` 持续写入 generate() 产生的数据，直到生成器结束。

### 【面试怎么说】

> "FastAPI 的 SSE 实现：`StreamingResponse` 接收一个异步生成器，生成器里用 `async for token in chain.astream(...)` 遍历 LCEL 链的流式输出，每个 token 格式化成 `data: {...}\n\n` 推送出去。`astream` 是 LCEL Runnable 协议的一部分，所有链天然支持，不需要额外配置。"

---

## 第 3 讲：httpx 异步流式单元测试

### 【项目里在哪】

```
backend/tests/unit/test_api_stream.py
```

### 【核心工具：ASGITransport】

```python
from httpx import AsyncClient, ASGITransport

async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    async with client.stream("POST", "/chat/stream", json={...}) as response:
        async for line in response.aiter_lines():
            if line:
                raw_lines.append(line)
```

`ASGITransport(app=app)` 把 `app` 作为传输层——请求不经过真实的 HTTP 服务器，直接调用 ASGI 接口。这让流式测试可以在内存里运行，速度快，不需要启动服务器。

### 【关键测试设计：mock astream】

```python
async def _astream(input_, config=None):
    for token in ["Hello", " world", "!"]:
        yield token

mock_chain = mocker.MagicMock()
mock_chain.astream = _astream  # 直接把函数赋给 MagicMock 的属性
mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)
```

注意：`mock_chain.astream = _astream` 而不是 `mock_chain.astream.return_value = ...`。因为 `astream` 是异步生成器函数，它本身需要是可调用的 `async def`，不能用 `return_value`。

### 【断言 SSE 格式的方式】

```python
data_lines = [l for l in raw_lines if l.startswith("data: ")]
assert data_lines[-1] == "data: [DONE]"   # 最后一条是终止标志

delta_events = [json.loads(l[6:]) for l in data_lines[:-1]]  # l[6:] 去掉 "data: " 前缀
assert len(delta_events) == 3
full_text = "".join(e["delta"] for e in delta_events)
assert full_text == "Hello world!"
for e in delta_events:
    assert e["thread_id"] == "t1"
```

---

## 第 4 讲：Node.js Extension 侧 SSE 消费

### 【项目里在哪】

```
extension/src/webview/ChatPanel.ts
  sendMessageStream(message, threadId)
```

### 【为什么用 `http.request` 而不是 `fetch`】

`fetch` 的流式 API（`response.body.getReader()`）在 Node.js 里可以用，但行为细节和浏览器略有差异。Node.js 原生 `http.request` 更稳定，且基于 Stream API，行缓冲逻辑完全可控。

### 【行缓冲（Line Buffering）】

```typescript
let buffer = '';
res.on('data', (chunk: string) => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';  // 最后一个可能是不完整行，保留到下次
    for (const line of lines) {
        if (!line.startsWith('data: ')) { continue; }
        // 处理完整的 SSE 行
    }
});
```

**为什么需要 buffer？**

网络传输以"包"为单位，包的边界不一定在行的边界。可能发生：
- 一个 chunk 包含多个完整 SSE 行
- 一个 chunk 在某行的中间截断
- 下一个 chunk 继续这个未完成的行

`lines.pop()` 把最后一个（可能不完整的）行暂存在 buffer，等下个 chunk 到来时拼接。

**这是处理流式文本的标准技巧，面试时可以直接展示这段代码。**

### 【postMessage 架构：Extension Host → Webview 消息总线】

```
Backend (SSE)  →  ChatPanel.sendMessageStream  →  postMessage  →  chat.html handler
                  (Extension Host 进程)              (IPC)          (Webview 沙箱)
```

四种消息类型：

| 消息类型 | 触发时机 | Webview 的响应 |
|---------|---------|--------------|
| `statusUpdate` | 发送请求立刻 + 收到 action 事件时 | 更新 `#status-bar` 文字 |
| `streamChunk` | 收到每个 delta 事件 | 清空 status-bar，追加文字到流式气泡 |
| `streamDone` | 收到 `[DONE]` | 流式气泡定型（去掉临时 id） |
| `actionDone` | executor.handle() 完成（finally） | 清空 status-bar，追加 "已执行：xxx" 气泡 |

### 【`executor.handle().finally()` 而不是 `.then()`】

```typescript
// ✅ finally：无论命令成功/失败，都发出 actionDone
this._executor.handle(event).finally(() => {
    void this._webviewPanel.webview.postMessage({ type: 'actionDone', description });
});

// ❌ then：命令失败时（如 E2E 环境里命令未注册），actionDone 不发出
this._executor.handle(event).then(() => {
    void this._webviewPanel.webview.postMessage({ type: 'actionDone', description });
});
```

**设计权衡记录（见 v0.2-retrospective.md 问题5）：**
在真实 HiSpark Studio 环境里命令不会失败，`.finally()` 的语义等价于 `.then()`。在 E2E 测试环境里命令未注册，`.finally()` 让 UI 流程可以完整验证。这是一个"当前阶段可接受的简化"，v0.3 可以加 error handling 改进。

---

## 第 5 讲：`streamingState.ts` 纯函数状态机

### 【是什么】

```typescript
// streamingState.ts — 零依赖，可在 Node.js 测试
export interface StreamingState {
    statusText: string;
    messages: StreamMessage[];
    _pendingText: string;
}

export function applyStreamEvent(
    state: StreamingState,
    event: { type: string; [key: string]: unknown }
): StreamingState {
    switch (event['type']) {
        case 'statusUpdate':  return { ...state, statusText: event['text'] as string };
        case 'streamChunk':   return { ...state, statusText: '', _pendingText: state._pendingText + event['delta'] };
        case 'streamDone':    return { statusText: '', messages: [...state.messages, { text: state._pendingText, finalized: true }], _pendingText: '' };
        case 'actionDone':    return { statusText: '', messages: [...state.messages, { text: `已执行：${event['description']}` }], _pendingText: '' };
        default:              return state;
    }
}
```

### 【为什么提取为纯函数——testability 原则】

这是 v0.1 `chatHtml.ts` 提取的同一模式。

Webview 的消息处理逻辑原本是嵌在 `chat.html` 的 `<script>` 里的：
```html
<script>
window.addEventListener('message', event => {
    // 业务逻辑直接写在这里
});
</script>
```

这段代码无法 import，无法在 Node.js 环境里测试。

**提取原则：** 把"做什么"（状态转换逻辑）从"怎么显示"（DOM 操作）里分离出来。

```
chat.html <script>
  收到 message → applyStreamEvent(state, event) → 根据新 state 更新 DOM
                    ↑
           这个函数可以独立测试
```

测试结果：4 个单元测试，6ms 完成。

### 【不可变更新（Immutable Update）】

```typescript
// ✅ 不修改原 state，返回新 state
return { ...state, statusText: event['text'] as string };

// ❌ 修改原 state（有副作用，测试难以追踪）
state.statusText = event['text'] as string;
return state;
```

不可变更新让状态转换可预测、可测试：给定相同输入，永远返回相同输出。这是 React Redux 的 reducer 模式，这里用同样的思路。

---

## 第 6 讲：流式 E2E 测试的时序陷阱

### 【背景】

Playwright 流式答案测试，第一版失败：
```
Expected chip-related keyword in stream answer, got: "HiSpark Studio for"
```

"HiSpark Studio for" 只是第一两个 token，流式传输还没完成。

### 【根因】

```typescript
// ❌ 第一版：元素出现就立刻读
await activeFrame.locator('#messages div').nth(divsBefore1).waitFor({ timeout: 20000 });
const streamText = await activeFrame.locator('#messages div').nth(divsBefore1).textContent() ?? '';
assert.ok(chipKeywords.some(kw => streamText.includes(kw)));
```

`.waitFor()` 只等 DOM 元素存在，不等内容填充完毕。第一个 `streamChunk` 消息就会创建流式气泡，此时气泡只有第一个 token。

### 【修复：等流式结束后再读】

```typescript
// ✅ 等 status-bar 清空（= 流式结束标志），再读内容
const deadline2 = Date.now() + 20000;
while (Date.now() < deadline2) {
    const sb = await activeFrame.locator('#status-bar').textContent() ?? '';
    if (!sb.trim()) { break; }   // status-bar 空了 = [DONE] 已收到
    await sleep(200);
}
const streamText = await activeFrame.locator('#messages div').nth(divsBefore1).textContent() ?? '';
```

**这个模式的普遍性：**

流式测试（不只是 LLM，也包括文件上传进度、视频加载等）的断言策略：
1. 找一个"流式结束的可观测信号"（status-bar 消失、进度条达到 100%、loading 图标消失）
2. 等这个信号出现后，再断言最终状态

不要断言流式过程中的内容（除非你要测"第 N 个 token 是否符合预期"这种极端情况）。

---

## 总结：v0.2 流式架构的完整数据流

```
用户点击"流式发送"
  ↓
chat.html 发 postMessage({type:'stream', message}) 给 Extension Host
  ↓
ChatPanel.sendMessageStream(message, threadId)
  → 立刻 postMessage({type:'statusUpdate', text:'正在识别意图...'})
  ↓
http.request POST /chat/stream
  ↓
FastAPI chat_stream()
  → classify_intent() [同步，~1-2s]
  ↓
  ┌─ action 意图 ─────────────────────────────────────────────────────────┐
  │  yield "data: {type:'action', ...}\n\n"                               │
  │  yield "data: [DONE]\n\n"                                             │
  │  ↓                                                                    │
  │  ChatPanel 处理：                                                      │
  │    postMessage({type:'statusUpdate', text:'执行中：编译项目'})          │
  │    executor.handle(event).finally(() => postMessage({type:'actionDone'}))│
  │    chat.html: #messages 追加 "已执行：编译项目"                         │
  └───────────────────────────────────────────────────────────────────────┘
  ┌─ answer 意图 ─────────────────────────────────────────────────────────┐
  │  async for token in chain.astream(...)                                │
  │    yield "data: {thread_id, delta:token}\n\n"  ← 每个 token 一条      │
  │  yield "data: [DONE]\n\n"                                             │
  │  ↓                                                                    │
  │  ChatPanel 处理：                                                      │
  │    每个 delta → postMessage({type:'streamChunk', delta})               │
  │    [DONE] → postMessage({type:'streamDone'})                          │
  │    chat.html: 流式气泡逐渐增长，[DONE] 后气泡定型                      │
  └───────────────────────────────────────────────────────────────────────┘
```
