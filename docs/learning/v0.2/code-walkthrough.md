# v0.2 代码走读

> 对真实代码的逐行解释，补充 notes.md 里的概念说明。
> 涉及文件：`backend/src/chains/qa_chain.py`、`backend/src/api/main.py`、
> `extension/src/webview/ChatPanel.ts`、`extension/src/webview/streamingState.ts`

---

## 一、`qa_chain.py` 走读

### 文件整体结构

```
L49-53   embeddings 初始化（模块级常量，不发网络请求）
L59-73   session history store
L81-99   build_retriever（公开工具函数）
L106-163 懒加载链：_qa_chain + _get_qa_chain()
L172-185 公开接口：answer_question()
```

---

### `_embeddings`（L49）

```python
_embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=os.getenv("ZHIPU_API_KEY"),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
)
```

只是创建客户端对象，不发网络请求。实际调用 embedding API 只在 `build_retriever` 里才发生。
放顶层没有副作用，模块 import 时不会触发网络调用。

---

### session store（L59-73）

```python
_session_store: dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]
```

`_session_store` 是模块级全局字典，进程生命周期内存活。每个 `session_id` 对应一个
`ChatMessageHistory`（本质是一个消息列表，存 HumanMessage / AIMessage）。

v0.2 用内存存，够验证多轮对话。v0.3+ 换 Redis 只需要改这一个函数，`RunnableWithMessageHistory`
的调用侧不变。

---

### `_to_question_str` + `_to_str`（L126-141）

```python
def _to_question_str(x) -> str:
    if isinstance(x, list) and x:          # 收到 [HumanMessage(...)]  ← 最常见
        last = x[-1]
        return last.content if isinstance(last, BaseMessage) else str(last)
    if isinstance(x, BaseMessage):         # 收到单个 BaseMessage
        return x.content
    return str(x)                          # 收到普通字符串（单元测试 / 直接调用 base_chain）

_to_str = RunnableLambda(_to_question_str)
```

三种分支对应三种可能收到的类型：
- `RunnableWithMessageHistory` 包装后传来 `[HumanMessage]`（正常运行路径）
- 极端情况传来单个 `BaseMessage`
- 普通字符串（单元测试 mock 或直接调用 `base_chain.invoke()`）

`_to_str` 在模块加载时就创建好，是模块级常量，`_get_qa_chain()` 直接复用它。

---

### `_get_qa_chain()` 管道组装（L144-164）

```python
_qa_chain: RunnableWithMessageHistory | None = None

def _get_qa_chain() -> RunnableWithMessageHistory:
    global _qa_chain
    if _qa_chain is None:          # 只有第一次调用才真正构建
        retriever = build_retriever(_load_sample_docs())   # 此处才调 embedding API
        prompt = ChatPromptTemplate.from_template(QA_PROMPT_TEMPLATE)
        base_chain = (
            {
                "context": itemgetter("question") | _to_str | retriever | _format_docs,
                "question": itemgetter("question") | _to_str,
            }
            | prompt
            | get_llm()
            | StrOutputParser()
        )
        _qa_chain = RunnableWithMessageHistory(
            base_chain,
            get_session_history,
            input_messages_key="question",
        )
    return _qa_chain
```

**管道数据流（以 `{"question": "HiSpark 支持哪些芯片？"}` 为例）：**

```
输入 dict
  ↓
{ "context": ..., "question": ... }   ← RunnableParallel，两条支路同时跑
  │
  ├── context 支路：
  │     itemgetter("question")  → [HumanMessage("HiSpark 支持哪些芯片？")]  ← 框架包装后
  │     | _to_str               → "HiSpark 支持哪些芯片？"                  ← 归一化回 str
  │     | retriever             → [Document(...), Document(...), Document(...)]
  │     | _format_docs          → "chunk1\n\nchunk2\n\nchunk3"
  │
  └── question 支路：
        itemgetter("question")  → [HumanMessage("HiSpark 支持哪些芯片？")]
        | _to_str               → "HiSpark 支持哪些芯片？"
  ↓
{"context": "chunk1\n\n...", "question": "HiSpark 支持哪些芯片？"}
  ↓
prompt（ChatPromptTemplate）  → 填充成完整 Prompt 文本
  ↓
get_llm()                     → AIMessage("HiSpark Studio 支持以下芯片...")
  ↓
StrOutputParser()             → "HiSpark Studio 支持以下芯片..."   ← 最终字符串
```

**为什么 dict 写法能在管道里用？**

LCEL 里，dict 中的值如果是 Runnable，整个 dict 被自动包装成 `RunnableParallel`，
两条支路的输入都是同一个上游输出，并行执行，结果合并成新 dict。

---

## 二、`main.py` 走读：`generate()` 异步生成器

```python
async def chat_stream(request: ChatRequest):
    async def generate() -> AsyncGenerator[str, None]:   # ← 闭包，可访问外层 request
        intent = classify_intent(request.message)        # ① 同步调用，阻塞当前协程约 1-2s

        if intent.get("type") == "action":
            event_data = { "thread_id": ..., "type": "action", ... }
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"  # ② 一条 action 事件
        else:
            chain = _qa_chain_module._get_qa_chain()     # ③ 模块引用，支持 mock
            async for token in chain.astream(            # ④ 异步迭代，每个 token 一次循环
                {"question": request.message},
                config={"configurable": {"session_id": request.thread_id}},
            ):
                event_data = {"thread_id": request.thread_id, "delta": token}
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"    # ⑤ 无论哪种分支，最后都 DONE

    return StreamingResponse(generate(), media_type="text/event-stream")
```

关键细节：
- `generate` 定义在 `chat_stream` 内部，是**闭包**，直接访问 `request` 对象
- `StreamingResponse(generate(), ...)` 接收**生成器对象**，不是函数本身
- `ensure_ascii=False`：保证中文不被转义成 `\uXXXX`
- ① 处同步函数在 async 上下文阻塞事件循环，v0.2 接受（1-2s 可接受），
  v0.3 可改为 `await asyncio.to_thread(classify_intent, ...)`

---

## 三、`ChatPanel.ts` 走读：`sendMessageStream()`

函数分三段：

### 第一段：立刻给用户反馈（L47）

```typescript
void this._webviewPanel.webview.postMessage({ type: 'statusUpdate', text: '正在识别意图...' });
```

在发 HTTP 请求**之前**就先给 Webview 发状态更新，用户马上看到"正在识别意图..."，
体验不会觉得卡顿。

`void`：TypeScript 里 `postMessage` 返回 `Promise`，`void` 明确表示"故意不等它"，
消除编译器"未处理 Promise"警告。

---

### 第二段：构造 http.request 选项（L49-60）

```typescript
const options: http.RequestOptions = {
    hostname: url.hostname,
    port: parseInt(url.port || '80'),
    path: url.pathname,
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),   // ← 必须提前计算
    },
};
```

`Content-Length` 必须提前算好——`http.request` 是流式写入，服务器需要知道 body 有多长。

---

### 第三段：行缓冲 + 事件分发（L62-98）

```typescript
let buffer = '';
res.on('data', (chunk: string) => {
    buffer += chunk;                      // 拼接新收到的数据
    const lines = buffer.split('\n');     // 按换行切分
    buffer = lines.pop() ?? '';           // 最后一段可能不完整，存起来等下次
    for (const line of lines) {
        if (!line.startsWith('data: ')) { continue; }  // 过滤空行等非 SSE 行
        const payload = line.slice(6);    // 去掉 "data: " 前缀
        if (payload === '[DONE]') {
            void this._webviewPanel.webview.postMessage({ type: 'streamDone' });
            return;
        }
        const event = JSON.parse(payload);
        if (event['type'] === 'action') {
            // action：先发 statusUpdate，命令执行完后 finally 发 actionDone
            this._executor.handle(event).finally(() => {
                void this._webviewPanel.webview.postMessage({ type: 'actionDone', description });
            });
        } else if (event['delta'] !== undefined) {
            // 普通 token：发 streamChunk
            void this._webviewPanel.webview.postMessage({ type: 'streamChunk', delta: event['delta'] });
        }
    }
});

req.write(body);   // 写入 request body
req.end();         // 发送请求
```

**行缓冲的必要性：**

```
网络包1: "data: {\"delta\": \"Hi"    ← 在行中间截断
网络包2: "Spark\"}\n\ndata: {\"delta\": \" Studio\"}\n\n"

没有 buffer：
  split('\n') → ["data: {\"delta\": \"Hi", ...]  ← 第一行不完整，JSON.parse 崩

有 buffer：
  包1处理后 buffer = "data: {\"delta\": \"Hi"  ← 不完整行暂存
  包2到来后 buffer + 包2 = 完整两行，正常处理
```

**为什么用 `.finally()` 而不是 `.then()`：**

E2E 测试环境里 `hispark-studio.build` 命令未注册，`executor.handle()` 会 reject。
`.then()` 在 reject 时不执行，`actionDone` 永远不发出，Playwright 等 UI 反馈会超时。
`.finally()` 无论成功失败都执行，UI 流程可以完整走完。

---

## 四、`streamingState.ts` 走读

```typescript
export interface StreamingState {
    statusText: string;        // status-bar 显示的文字
    messages: StreamMessage[]; // 已完成的消息气泡列表
    _pendingText: string;      // 流式进行中的文字（还没变成消息气泡）
}
```

三个字段对应 UI 的三个区域：状态栏 / 消息列表 / 当前正在流入的临时内容。

**`_pendingText` 的生命周期：**

```
流式开始                                         流式结束
    ↓                                               ↓
_pendingText = ""  →  "H"  →  "Hi"  →  "Hi!"  →  messages 里新增 {text: "Hi!", finalized: true}
                                                    _pendingText = ""
```

每个 `streamChunk` 追加 token 到 `_pendingText`，`streamDone` 时"转正"进 `messages`，然后清空。
UI 层逻辑：有 `_pendingText` 就渲染临时气泡，有 `messages` 就渲染定型气泡。

**各 case 的状态变化：**

```typescript
'statusUpdate'  → 只改 statusText，其他不动
'streamChunk'   → 清空 statusText（第一个 token 到了），追加 _pendingText
'streamDone'    → _pendingText 转正进 messages，清空 statusText 和 _pendingText
'actionDone'    → 追加 "已执行：xxx" 进 messages，清空 statusText 和 _pendingText
```

**不可变更新：**

```typescript
// ✅ 返回新对象，不修改原 state
return { ...state, statusText: event['text'] as string };

// ❌ 修改原 state，有副作用，测试难以追踪
state.statusText = event['text'] as string;
return state;
```

给定相同输入永远返回相同输出，这是 Redux reducer 的同一模式，也是这个函数可以用
纯 Node.js 单元测试覆盖的原因。

---

## 完整数据流总览

```
用户在 Webview 点击"流式发送"
  ↓
chat.html postMessage({type:'stream', message}) → Extension Host
  ↓
ChatPanel.sendMessageStream(message, threadId)
  → 立刻 postMessage({type:'statusUpdate', text:'正在识别意图...'}) → Webview 状态栏更新
  ↓
http.request POST /chat/stream
  ↓
FastAPI generate()
  → classify_intent() [同步，~1-2s]
  ↓
  ┌─ action 意图 ──────────────────────────────────────────────────┐
  │  yield "data: {type:'action', command, ...}\n\n"               │
  │  yield "data: [DONE]\n\n"                                      │
  │  ↓ ChatPanel：                                                 │
  │    postMessage(statusUpdate: "执行中：编译项目")                │
  │    executor.handle().finally → postMessage(actionDone)         │
  │  ↓ Webview：                                                   │
  │    状态栏短暂显示"执行中"，actionDone 后消息区追加"已执行：..."  │
  └────────────────────────────────────────────────────────────────┘
  ┌─ answer 意图 ──────────────────────────────────────────────────┐
  │  async for token in chain.astream(...)                         │
  │    yield "data: {thread_id, delta:token}\n\n"  × N            │
  │  yield "data: [DONE]\n\n"                                      │
  │  ↓ ChatPanel：                                                 │
  │    每个 delta → postMessage(streamChunk)                       │
  │    [DONE]     → postMessage(streamDone)                        │
  │  ↓ Webview：                                                   │
  │    流式气泡逐渐增长，streamDone 后气泡定型                      │
  └────────────────────────────────────────────────────────────────┘
```
