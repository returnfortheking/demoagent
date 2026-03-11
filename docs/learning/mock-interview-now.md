# 模拟面试 — 现在可以练的题（14题）

> 基于 v0.1/v0.2 项目经历，现在答效果最好
> 作答方式：直接在每题下方的"我的答案"里填写，然后找 Claude 对答案
> 对完答案的题目 → 记入 interview-qa.md

---

## P 类：深挖项目经历

### P2. RAG k=3 的局限

你的 RAG 链现在用 `k=3` 召回 3 个文档片段。如果用户问的问题需要跨多个文档的信息综合（比如"对比 Hi3861 和 Hi3516 的编译流程"），当前架构会有什么问题？你会怎么改？

**我的答案：**
> 当前仅寻找3个文档片段，如果面对多个芯片对比场景，比如对比多个芯片的编译流程差别。实际检索时，由于都是编译相关的信息，会导致只能选取3段信息。如果芯片型号大于3种，很容易出现检索信息不全的情况。底层原理上讲，这类相近的语义，当前缺少元数据做区分，很容易混淆或者缺失。固定k=3也比较死板，无法应对用户灵活的提问。

**问题分析**
- "语义相近难区分、缺少元数据"方向对
- 漏掉了最关键的问题：向量检索按**相似度排序取 Top-K**，3 个 slot 可能全被 Hi3861 的 chunk 占满（它们相似度更高），Hi3516 的信息一条都没召回——**相关不等于覆盖全面**
- 解决方案没有说出来

**✅ 标准答案**

核心问题：向量检索是 Top-K 相似度排序，不保证覆盖多个实体。查询"对比 Hi3861 和 Hi3516"时，k=3 的 3 个 slot 可能全给了 Hi3861，Hi3516 完全缺席。

改进方案（按实现难度排序）：

1. **加大 k + Reranker 精排**：k=20 先广撒网，再用 Reranker 从 20 个里选最终 5 个
2. **Query Decomposition（子问题拆解）**：把对比问题拆成两个子查询——"Hi3861 编译流程"和"Hi3516 编译流程"——分别检索，结果合并后送进 Prompt
3. **元数据过滤**：文档入库时打上 `chip_type` 标签，检索时强制每个芯片型号各取 k/n 个 chunk

**⚠️ 易混淆：MultiQueryRetriever ≠ Query Decomposition**

| | MultiQueryRetriever | Query Decomposition |
|--|--------------------|--------------------|
| **做什么** | 对同一个 query 生成 N 种不同表述，各自检索取并集 | 把一个复杂 query 拆成多个子问题，分别检索 |
| **解决的问题** | 单一表述召回率低（换个说法可能召回不同文档） | 跨实体覆盖不全（对比问题需要两边的信息） |
| **适用场景** | 模糊问题、单实体问题 | 对比/综合型多实体问题 ← **本题场景** |

对比 Hi3861 和 Hi3516 这类问题，应该用 **Query Decomposition**，不是 MultiQueryRetriever。

**💡 记忆要点**
- 核心问题：Top-K 相似度不等于覆盖全面
- 对比/多实体问题 → Query Decomposition（拆子问题）
- 单 query 召回率低 → MultiQueryRetriever（多角度改写）
- 两者容易混淆，区分关键：是"同一问题换说法"还是"拆成多个不同问题"

---

### P3. 同步函数阻塞事件循环

v0.2 的 `/chat/stream` 里，`classify_intent()` 是同步函数，在 async 上下文里直接调用。为什么同步函数会阻塞异步事件循环？`asyncio.to_thread` 是怎么解决这个问题的？

**我的答案：**
> 通过FastAPI配置了/chat/stream的API，接收到request才会触发classify_intent()，所以虽然classify_intent()是同步函数，但触发时机是阻塞的，需要等待request，后续的异步操作自然就会阻塞。asyncio.to_thread我还没修改，我不清楚怎么解决

**问题分析**
- 答案混淆了两个概念："等待 request 到来"是正常的网络 I/O 等待，和事件循环阻塞无关
- 真正的问题是：request **到达之后**，`classify_intent()` 执行期间（1-2s）整个事件循环被卡死
- `asyncio.to_thread` 部分直接放弃，面试中要说出思路

**✅ 标准答案**

**为什么会阻塞：**

asyncio 事件循环是**单线程**的，靠 `await` 关键字切换任务。协程遇到 `await` 就暂停、让出控制权，事件循环去处理其他请求。

`classify_intent()` 是同步函数，内部调用 LLM API 需要 1-2 秒，但**没有 `await`**，事件循环不知道要切换，只能原地等待。这 1-2 秒里，所有其他用户的请求都被挡在门外无法响应。

```
单线程事件循环：
  请求A → chat_stream() → classify_intent() [卡住1-2s] → 请求A继续
                                ↑
                     请求B、C、D 全在这里等，无法被处理
```

**`asyncio.to_thread` 的解法：**

把同步函数交给**线程池**（独立 OS 线程）执行，同时在事件循环里 `await` 线程完成的信号。线程在跑的时候，事件循环可以继续处理其他请求。

```python
# ❌ v0.2 现状：同步调用，阻塞事件循环
intent = classify_intent(request.message)

# ✅ v0.3 改进：丢到线程池，不阻塞
intent = await asyncio.to_thread(classify_intent, request.message)
```

类比：单线程事件循环像一个收银员，同步调用相当于收银员亲自去仓库取货（期间收银台停摆）；`asyncio.to_thread` 相当于叫另一个员工去取货，收银员继续服务其他顾客。

**💡 记忆要点**
- 根因：asyncio 单线程，同步函数占用线程不释放，等于"独占"事件循环
- `asyncio.to_thread` = 把同步函数扔进线程池，用 `await` 等结果
- 适用场景：CPU 密集 / 同步 I/O 阻塞函数（如 requests、同步 LLM 调用）
- **核心思想：快资源不等慢操作**——同一模式贯穿 AI Infra 各层：
  - FastAPI：事件循环（快）不等同步 LLM 调用（慢）→ `asyncio.to_thread`
  - PyTorch 训练：GPU（快）不等数据加载（慢）→ `DataLoader num_workers`
  - vLLM 推理：GPU 生成 token（快）不等新请求调度（慢）→ Continuous Batching
  - Checkpoint：GPU 训练（快）不等磁盘写入（慢）→ 线程池异步保存

---

### P4. Prompt A/B 测试

你的项目里 Prompt 是放在 `intent_v1.py` 里的独立文件。如果现在要做 A/B 测试——给 50% 的用户用 `intent_v1`，另外 50% 用 `intent_v2`——你的代码需要改哪里？怎么做到不重启服务？

**我的答案：**
> 我的想法是借鉴依赖注入的方式，修改读取prompt的接口，把v1，v2都import到该文件。相关接口入参默认使用v1，但是也留出配置其他版本号的入参。在测试时一半用例使用默认参数，另一半使用v2入参。

**问题分析**
- 答的是**测试用例参数化**，题目问的是**生产环境 A/B 测试**，方向偏了
- 依赖注入思路是对的，但只答了这一点
- 三个核心问题全部遗漏：① 如何分流 ② 如何不重启切换 ③ 如何记录用了哪个版本

**✅ 标准答案**

A/B 测试需要解决三件事：

**① 分流：用 `thread_id` 哈希决定走哪个版本**
```python
import hashlib
def get_prompt_version(thread_id: str) -> str:
    h = int(hashlib.md5(thread_id.encode()).hexdigest(), 16)
    return "v2" if h % 2 == 0 else "v1"   # 50/50 分流
```
用 `thread_id` 哈希取模：同一个用户始终用同一个版本（体验一致），且无状态、不需要数据库。

**② 不重启切换：从外部配置读比例**
```python
import os
AB_RATIO = float(os.getenv("PROMPT_V2_RATIO", "0.5"))  # 默认 50%

def get_prompt_version(thread_id: str) -> str:
    h = int(hashlib.md5(thread_id.encode()).hexdigest(), 16)
    return "v2" if (h % 100) < int(AB_RATIO * 100) else "v1"
```
修改环境变量 `PROMPT_V2_RATIO=0.1` 后，新请求立刻生效，无需重启。比例可以从 10% 逐步放量到 100%。

**③ 记录版本（必须有，否则无法分析）**
```python
intent = classify_intent(request.message, prompt_version=version)
# 在响应里或日志里带上 prompt_version 字段，否则分析结果时不知道哪条用了哪个版本
```

**依赖注入的作用**：把 prompt template 作为参数传入链构建函数，而不是在函数内部硬编码 `import`——这样才能在运行时根据分流结果传入不同版本。

**💡 记忆要点**
- A/B 测试三件事：**分流（哈希取模）+ 动态配置（环境变量）+ 版本记录（日志）**
- `thread_id` 哈希分流：同用户始终同版本，无状态
- 不重启切换 = 把比例放到环境变量/配置中心，代码只读配置

---

### P5. 为什么从 RetrievalQA 迁移到 LCEL

你在 v0.1 里为什么没有直接用 `RetrievalQA.from_chain_type()`，而是在 v0.2 里改成手动组装 LCEL 链？除了"LCEL 更现代"，能说出具体的工程收益吗？

**我的答案：**
> 收益1：天然支持流式输出，不用自行封装。收益2,不用再写wrapped包装函数就能支持单元测试的patch。收益3代码简洁，可读性高

**问题分析**
- 收益1（流式）正确，是最重要的收益
- 收益2方向对，但描述不精确：问题不是"缺少包装函数"，而是 `RetrievalQA` 继承自 Pydantic BaseModel，Pydantic 把属性锁死，pytest-mock 无法 patch 它的方法
- 收益3（可读性）太软，不是工程收益
- 遗漏两个重要收益：原生 async 和 LangSmith 自动 trace

**✅ 标准答案**

| 收益 | RetrievalQA（v0.1） | LCEL（v0.2） |
|------|-------------------|-------------|
| **流式输出** | 无原生支持，需额外封装 | `.astream()` 天然支持，v0.2 SSE 直接用 |
| **可测试性** | 继承 Pydantic BaseModel，方法被锁死，patch 极难 | 普通对象 + 工厂函数 `_get_qa_chain()`，patch 工厂函数即可替换整个链 |
| **原生 async** | 无 `.ainvoke()` / `.astream()`，异步需额外封装 | 所有 Runnable 天然支持同步/异步统一接口 |
| **LangSmith trace** | 只有一个整体 span，看不到内部步骤 | 每个 Runnable 节点自动上报，调试时可以看到 retriever / prompt / LLM 每步的输入输出 |
| **可组合性** | 黑盒，无法在中间插入自定义步骤 | 可以在任意位置插入 `RunnableLambda`（如 `_to_str` 类型归一化修复） |
| **生命周期** | **已在 LangChain 0.3.0 正式移除**（deprecated since v0.1.17） | 官方推荐路径，持续维护 |

面试口诀：**流式 + 可 mock + 原生 async + LangSmith trace + 可插入自定义步骤 + 官方已废弃旧 API**

**💡 记忆要点**
- 最重要的收益：**流式**（直接决定了 v0.2 SSE 能否实现）
- 可 mock 的根因：Pydantic BaseModel 锁属性，LCEL 是普通对象 + 工厂函数
- 遗漏项：原生 async / LangSmith 自动 trace / 可插入 RunnableLambda
- **补充加分项**：`RetrievalQA` 已在 LangChain 0.3.0 正式移除，迁移 LCEL 是官方强制要求，不只是"更现代"

---

## O 类：可观测性与生产质量

### O2. 测试分层的盲区

你的单元测试 mock 了 LLM 和 retriever，集成测试用真实 LLM。这样的测试分层策略有什么盲区？有没有某类 bug 是单元和集成都发现不了，只有 E2E 才能暴露的？（你项目里有没有这样的例子？）

**我的答案：**
> 测试分层策略对于我的项目基于这个前提：单元测试发现函数级问题，集成测试发现系统级问题(单侧)，e2e测试完成跨系统的全量测试。在跨系统真实场景下的测试问题只能e2e暴露。我发现过一个问题就是Extension端自己集成测试，没有发现问题，但是实际e2e测试发现rag接口无法跑通，原因就是Extension侧的集成测试把LLM和RAG接口调用mock了，两边各自都没问题，但是合在一起出现了版本兼容性问题。通过e2e发现并解决了。

**问题分析**
- 三层分工定义正确，"各自没问题，合在一起出现问题"核心洞察说到位了（B+）
- "版本兼容性问题"太模糊，项目里有两个更具体的 E2E-only bug 可以说
- 每层的盲区没有系统化讲完

**✅ 标准答案**

**各层盲区：**

| 测试层 | 能发现的 | 发现不了的 |
|--------|---------|-----------|
| 单元测试 | 函数逻辑、边界条件 | 真实 API 契约、真实 LLM 行为、组件间协议 |
| 集成测试 | 后端真实 LLM 调用、API 响应格式 | Extension↔Backend 协议对齐、postMessage IPC、Webview 渲染行为 |
| E2E | 跨进程 IPC、Webview 渲染时序、真实 VS Code 命令状态 | — |

**项目里两个真实的 E2E-only bug：**

**Bug 1：`.finally()` vs `.then()` 的 actionDone 问题**
- Extension 单测：`executor.handle()` 是 mock，永远成功，`.then()` 正常触发
- E2E 环境：`hispark-studio.build` 命令未注册 → `executor.handle()` reject → `.then()` 不执行 → `actionDone` 永远发不出去 → Playwright 等待超时
- 只有真实 VS Code 环境才有"命令未注册"这个状态，单测和集成测试都看不到

**Bug 2：Playwright 流式时序问题**
- 单测/集成测试：后端返回完整响应，没有流式渲染过程
- E2E：`.waitFor()` 等元素出现就读 `textContent()`，但此时流还没传完，只读到第一个 token
- 必须有真实 VS Code + Webview 渲染 + SSE 时序组合才能暴露

**💡 记忆要点**
- E2E-only 的 bug 特征：涉及**跨进程边界**（Extension Host ↔ Webview ↔ Backend）或**环境状态**（命令注册、真实渲染时序）
- 面试说项目例子时要具体到 bug 现象和根因，不要只说"版本兼容性问题"
- 口诀：单测看逻辑，集成看协议，E2E 看时序和环境

---

### O3. E2E 流式测试的脆弱性

你的流式 E2E 测试里，等 `#status-bar` 清空来判断流式完成。这个方法有什么脆弱性？如果 `streamDone` 消息丢失了（比如 Webview 重新加载），测试会怎样？更健壮的方案是什么？

**我的答案：**
> 如果用户重启webview，会导致测试用例挂死，永远等待不到状态栏清空。更健壮的方案是在消息完全发送后，保存到本地一个信号文件，另一侧轮询监听这个信号文件，发现即代表操作完成，另外设置最大超时时间，避免意外场景导致挂死。这样既不会多余等待，又能兼容异常场景。

**问题分析**
- 超时机制方向正确
- 信号文件方案**张冠李戴**：`E2E_SIGNAL_FILE` 是项目 keepalive 机制，解决的是"VS Code 进程存活"问题，不是"流式完成检测"问题。Webview 是沙箱进程，也无法直接写文件系统
- 漏掉了更隐蔽的脆弱性：`#status-bar` 在第一个 `streamChunk` 时就清空了，不是等 `streamDone`

**✅ 标准答案**

**两层脆弱性：**

**① Webview 重载（你答到了）**
Webview 重载 → DOM 全清空 → `#status-bar` 变空 → 测试误判"完成" → 读到空内容或错误内容

**② streamChunk 提前清空 status-bar（更隐蔽）**
```
streamChunk(token1) → status-bar 清空   ← 测试轮询到空，以为流结束
streamChunk(token2) → ...（流还在继续）
streamDone          → 消息气泡才定型
```
status-bar 清空 ≠ 流结束，它在第一个 token 到来时就清空了。

**更健壮的方案：专用 DOM 信号节点**

```typescript
// chatHtml.ts：streamDone 时写入信号，而不是依赖 status-bar 的隐式状态
case 'streamDone':
    document.getElementById('stream-status')!.dataset.state = 'done';
```

```typescript
// Playwright：等专用信号节点出现，语义明确
await activeFrame.locator('#stream-status[data-state="done"]').waitFor({ timeout: 20000 });
const text = await activeFrame.locator('#messages div').last().textContent();
```

优点：`streamDone` 丢失 → 节点永远不出现 → 超时报错，不会误判通过。语义比"等 status-bar 空"清晰得多。

**💡 记忆要点**
- 信号文件 = keepalive（进程存活），不是流式完成检测——两个不同问题
- `#status-bar` 空 ≠ 流结束，第一个 `streamChunk` 就会清空它
- 健壮的流式测试：在 DOM 里放**专用完成信号节点**，由 `streamDone` 处理器写入

**📌 易错对比：E2E_SIGNAL_FILE vs 流式完成检测**

| | E2E_SIGNAL_FILE | 流式完成检测 |
|--|----------------|------------|
| **解决的问题** | VS Code 进程何时关闭 | 流式内容何时传完 |
| **通信双方** | 测试进程 ↔ Extension Host | Extension Host → Webview DOM |
| **机制** | 测试写文件 → Extension 轮询文件存在 | `streamDone` → DOM 节点写入 → Playwright 等节点 |
| **发生时机** | 测试全程持续（keepalive） | 单次响应结束时（一次性） |

一句话区分：信号文件是"告诉 VS Code 别关门"，DOM 信号节点是"告诉测试内容写完了"。

---

## R 类：RAG 进阶

### R2. 召回噪声的影响

召回的 3 个文档片段，你是直接全塞进 Prompt 的。如果这 3 个片段里有 1 个完全不相关（噪声），会对 LLM 的回答质量有什么影响？有什么工程手段可以在进 Prompt 之前过滤掉噪声片段？

**我的答案：**
> 会导致幻觉或准确率下降。可以扩大K值，先粗召回更多比如20，然后针对这20个回答进行精排序(问题和答案片段一起放到类似Transformer模型中计算相似度)，取最高的几个答案，比如3~5个，过滤噪声

**问题分析**
- 核心方案正确：扩大 K 粗召回 + 精排取 Top-N（B+）
- "类似 Transformer 模型" 描述准确但缺术语，应说 **Reranker / Cross-Encoder**
- 影响描述不够具体，噪声有两种危害需要区分
- 遗漏阈值过滤

**✅ 标准答案**

**噪声的两种危害：**
- LLM **主动采纳**了噪声内容 → 答案里出现错误信息（幻觉，Faithfulness↓）
- 噪声**稀释上下文**，相关 chunk 信号被淹没 → LLM 忽略正确内容，答案不完整（Answer Relevancy↓）

**标准解法：两阶段召回**
```
第一阶段（粗召回）：向量检索 Top-20，扩大覆盖面
        ↓
第二阶段（Reranker 精排）：
  - 原理：把 (query, chunk) 拼在一起送入 Cross-Encoder，计算精确相关性分数
  - 输出：每个 chunk 一个分数
        ↓
阈值过滤 + Top-N：
  - 低于阈值的全丢（哪怕凑不够 3 个也不补噪声）
  - 剩余按分数取 Top-3~5 送入 Prompt
```

**Reranker vs 向量检索的区别：**
- 向量检索：query 和 chunk 各自独立编码，再算余弦相似度（Bi-Encoder，快但精度低）
- Reranker：query + chunk 拼在一起编码，捕捉精细交互信息（Cross-Encoder，慢但精度高）

**2026 年 Reranker 选型（已更新）：**

| 场景 | 推荐模型 | 理由 |
|------|---------|------|
| 本地部署 + 有 GPU（国内首选） | `BGE-reranker-v2-m3` | 北京智源出品，开源免费，多语言，数据不出内网，50-100ms GPU 延迟 |
| API 调用 + 延迟敏感 <300ms | `Voyage Rerank 2.5` | 延迟约 200-250ms，精度接近 Cohere，价格约 Cohere 1/3，适合实时问答 |
| API 调用 + 生产可靠性优先 | `Cohere Rerank 3.5` | 有 SLA 保证，延迟约 600ms，跨国团队或有境外合规通道时选 |
| API 调用 + 预算极度有限 | `ZeroEntropy zerank-2` | 比 Cohere 便宜 40x，支持 100+ 语言 |
| 英文原型验证 | `ms-marco-MiniLM-L-6-v2` | 轻量快速，适合快速验证，不上生产 |

> **国内大厂注意**：百度/阿里/字节/华为以 BGE 为主——数据合规，不走境外 API。Cohere/Voyage 主要用于国际化团队。面试点 BGE 是最稳的选择。

**💡 记忆要点**
- 两阶段口诀：**向量检索扩 Recall，Reranker 提 Precision**
- 别忘阈值：低分 chunk 宁缺勿滥，不强行补噪声
- 选型口诀：有 GPU/国内 → BGE；延迟敏感 API → Voyage；稳定 SLA → Cohere；省钱 API → ZeroEntropy；原型 → MiniLM

---

### R3. 上下文依赖型问题

用户问"上次你说的那个编译命令是什么"——这个问题本身没有任何技术关键词，向量检索会召回什么？结果有意义吗？这类"上下文依赖型"问题在 RAG 里怎么处理？

**我的答案：**
> 按当前的实现，会检索编译命令相关文档，可能会返回多个不同芯片型号的编译命令。
  结果能起到部分参考效果，但无法解决实际问题。
  上下文依赖型问题两种思路，一种简单实现，不知道就说我不知道，通过prompt约束LLM的回答。
  另一种需要LLM端支持保存长短期记忆，当前场景应该是短期记忆。把记忆的文本也放到RAG检索内容里或者直接作为system prompt。

**问题分析**
- "把历史放进 system prompt"方向对，但只解决了生成阶段，检索阶段还是用原始模糊 query
- 最关键的解法遗漏：**检索之前改写 query**（Query Contextualization）
- 问题根源："上次你说的那个编译命令"这句话没有技术关键词，直接检索召回的是错误内容

**✅ 标准答案（2026 年主流做法）**

**问题的本质：**
原始 query 依赖上下文，无法独立检索。必须在检索**之前**用对话历史改写成自包含的 query。

```
原始 query："上次你说的那个编译命令是什么"   ← 没有技术关键词，检索结果乱
    ↓  Query Contextualization（LLM 结合历史改写）
改写后："Hi3861 芯片的 SCons 编译命令"        ← 自包含，可以独立检索
    ↓
向量检索 → 正确 chunk → 生成正确答案
```

**LangChain 内置解法：`create_history_aware_retriever`**

```python
from langchain.chains import create_history_aware_retriever

# 用 LLM 把上下文依赖的 query 改写成独立 query
history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)
```
内部做了两步：① 把对话历史 + 当前 query 送给 LLM → 输出自包含的改写 query；② 用改写后的 query 去检索。

**三层解法（按复杂度排序）：**

| 层次 | 方案 | 场景 |
|------|------|------|
| 兜底 | Prompt 约束：找不到就说不知道 | 简单实现，成本低 |
| 标准 | `create_history_aware_retriever` 改写 query | 生产推荐，解决检索阶段问题 |
| 进阶 | 短期记忆（滑动窗口最近 N 轮）+ query 改写 | 复杂对话，避免历史过长超 token |

**💡 记忆要点**
- 上下文依赖问题的根源在**检索阶段**，不是生成阶段
- 核心解法：**Query Contextualization**——检索前用历史改写 query，让它自包含
- LangChain 关键词：`create_history_aware_retriever`
- 把历史只放进 system prompt 是不够的，检索还是用了错误的 query

---

### R5. 区分两种幻觉

RAGAS 的 Faithfulness 指标低，说明 LLM 在"幻觉"。但你怎么区分"LLM 用了 context 但理解错了"和"LLM 完全忽略 context 自己编的"这两种情况？从 Prompt 设计角度怎么缓解？

**我的答案：**
> 用了context理解错了 代表LLM模型能力本身出了问题，忽略LLM代表模型稳定性不佳。
  前者prompt侧重让LLM深度思考，后者让LLM在输出答案前进行复查。
  同时，可以检测context和答案的相关性，用于测试修改prompt后的效果。

**问题分析**

❌ **混淆点 1：把两种幻觉的根因归为"模型固有缺陷"**
- 你的说法：误读 = 模型能力问题，幻造 = 模型稳定性问题
- 实际：两种幻觉的根因都是 **Prompt 设计问题**，不是模型能力问题。同一个模型，换个带锚定指令或 CoT 的 Prompt，幻觉率会显著下降。把锅甩给"模型能力/稳定性"，面试官会追问"那你怎么解决"——你就答不上了。

❌ **混淆点 2：跳过了"区分方法"这个核心考点**
- 题目问的第一句是"怎么区分"，你直接跳到了 Prompt 缓解方案
- 区分和缓解是两个独立问题：先说我能**检测出是哪种**，再说我能**用 Prompt 减轻它**

- "让 LLM 深度思考"：太模糊，应答 Chain-of-Thought + 引用原文

**✅ 标准答案**

**区分两种幻觉：**

| 类型 | 表现 | 判断方法 |
|------|------|---------|
| **Type 1 — 误读**：用了 context 但理解错 | 答案有 context 的元素，但结论被扭曲或过度推断 | LLM-as-Judge："答案中每个关键结论，能从 context 严格推出吗？" |
| **Type 2 — 幻造**：完全忽略 context 自编 | 答案里出现了 context 根本没有的事实/数字 | 对答案每个 claim 做语义比对：这个信息在 context 里有没有？ |

> **RAGAS Faithfulness 和两种幻觉的关系（重要订正）：**
> - Faithfulness 检测的是"answer 里有没有 context 不支持的 claim"，**两种幻觉都会触发**，不是只检测 Type 2
> - 区别在于检出可靠性：Type 2（信息压根不在 context）→ 几乎必然被捕捉；Type 1（细微误读/过度推断）→ Judge 宽松时可能漏过
> - 因此：Faithfulness 低 → 优先排查 Type 2；Faithfulness 正常但答案感觉不对 → 用"逻辑核查式" LLM Judge 专门追查 Type 1

**Prompt 缓解方案：**

```
针对 Type 2（幻造）——加锚定指令：
  "仅根据下方文档回答，文档中没有的信息请回复'文档未提及'"

针对 Type 1（误读）——加引用推理（Chain-of-Thought）：
  "先引用文档中支持你答案的原句，再基于原句给出结论"

两种都有效——加自检指令：
  "回答完成后，检查你的每个结论是否有文档原文支撑，若没有请删除"
```

**💡 记忆要点**
- 区分口诀：**Type 2 看 claim 来源（context 里有没有），Type 1 看推理链（结论逻辑对不对）**
- Prompt 三板斧：**锚定指令**（只用 context）→ **引用推理**（先引文再结论）→ **自检**（回答后验证每个 claim）
- Faithfulness 两种都能捕捉，但 **Type 2 检出率高，Type 1 细微误读可能漏**；Faithfulness 正常但答案有问题 → 专门用逻辑核查式 Judge 追 Type 1

---

## T 类：刁钻追问

### T1. dict 是怎么变成 RunnableParallel 的

LCEL 的 `|` 运算符背后是 `__or__` 方法的重载。那 `{"context": chain_a, "question": chain_b}` 这个 dict 是怎么变成 `RunnableParallel` 的？LangChain 在哪里做了这个转换？

**我的答案：**
> 这个dict被传给了 prompt，prompt里有context和question的占位符，相当于把dict的value填入了prompt。然后prompt本身是LangChain提供的，天生支持runnable

**问题分析**

❌ **混淆点：把"dict 填占位符"和"dict 转 RunnableParallel"当成同一件事**
- 你答的是 PromptTemplate 用 dict 填 `{context}` `{question}` 占位符——这是 Prompt **执行阶段**的行为
- 题目问的是 dict **在 `|` 运算符内**如何被转换成 Runnable——这发生在 Prompt 介入之前
- dict 里的 value 是 Runnable（retriever/chain），不是静态字符串，必须先并行执行才能得到结果

**✅ 标准答案**

转换发生在 `|` 运算符执行时，由 `Runnable.__ror__` 触发：

```python
# dict | prompt → Python 调用 prompt.__ror__(dict)
# __ror__ 内部调用 coerce_to_runnable(dict)
# coerce_to_runnable：isinstance(thing, dict) → RunnableParallel(thing)
# 最终构建 RunnableSequence(RunnableParallel(...), prompt, ...)
```

**为什么是"并行"：** RunnableParallel 把同一个 input 同时分发给所有 value 并发执行。这里有两个动机——①结构上：两个分支都需要原始 input，串行管道中第一步输出后原始 input 就丢了；②性能上：多个耗时分支可以并发节省时间。两者都是设计动机。

**💡 记忆要点**
- `dict | Runnable` → `__ror__` → `coerce_to_runnable` → `RunnableParallel`
- 转换在 `|` 运算符内完成，Prompt 收到的是各分支执行后的结果 dict
- 并行的两个原因：**结构**（保留原始 input）+ **性能**（并发执行）

---

### T2. StrOutputParser 遇到 tool_call

你说 `StrOutputParser` 把 `AIMessage` 展开成字符串。如果 LLM 返回的是带 tool_call 的 `AIMessage`（比如 Function Call 的响应），`StrOutputParser` 还能用吗？应该用什么？

**我的答案（⚠️ 标注：作答时知识不足）：**
> 如果换成带tool_call的，就不能用了，需要替换成 pydantictoolparser()或with_structured_output()

**问题分析**
- 结论正确，但缺少"为什么不能用"的根因——面试必然追问
- 漏掉最重要的危险点：不是报错，而是**静默返回空字符串**

**✅ 标准答案**

`StrOutputParser` 只读 `AIMessage.content`。tool_call 场景下 LLM 的响应是：
```python
AIMessage(content="",  # ← 空字符串
          tool_calls=[{"name": "search", "args": {...}}])
```
所以 `StrOutputParser` **不会报错，而是静默返回 `""`**，工具调用信息完全丢失。这比抛异常更危险。

替代方案：

| 方案 | 适用场景 |
|------|---------|
| `JsonOutputToolsParser` | 需要灵活处理多个工具调用，输出 `list[dict]` |
| `PydanticToolsParser` | 需要类型安全和结构校验，输出 Pydantic 对象 |
| `with_structured_output()` | 单一结构化输出，最简洁，内部自动处理 |

**💡 记忆要点**
- StrOutputParser 遇到 tool_call：**不报错，静默返回空字符串**，是隐性 bug
- 根因：tool_call 在 `.tool_calls` 字段，不在 `.content`
- 现在项目没有 `bind_tools()`，所以用 StrOutputParser 完全正确；引入 Agent 后需替换

---

## S 类：系统设计（概念题，不需要实操）

### S4. 向量库选型

你现在用 Chroma 做本地向量库。如果要把这个系统从"单机开发版"迁移到"生产版"，向量库选型你会怎么考虑？Chroma / Milvus / Qdrant / Pinecone 各适合什么规模和场景？

**我的答案：**
>

---

## 独立学习后可答（补知识即可，和版本无关）

### R1. 切块策略的局限

你的 RAG 现在是 chunk_size=500，overlap=50。如果用户的问题是"帮我总结这份文档的核心要点"，而文档有 5 万字，当前的切块策略会有什么问题？你会怎么改进？

**我的答案：**
> 当前的切块策略会导致总共有100多个切块，但实际上没有一个切块是和问题密切相关的。我的思路是提供分层索引，把全局信息归纳总结成新的chunk，在检索时根据问题的颗粒度选取相近的chunk返回。

**问题分析**
- 核心问题识别正确：全局性问题 vs 局部 chunk，向量匹配天然失效
- 分层索引方向正确，但缺具体分层结构和检索策略

**✅ 标准答案**

**问题根因**：向量检索依赖语义相似度，"总结全文"这类全局问题和任何单个 500 字 chunk 的相似度都不高，Top-K 检索拿到的是噪声。

**改进：两层索引（Hierarchical Index）**

```
第一层：文档级摘要 chunk（用 LLM 对全文生成摘要，作为独立向量存入库）
第二层：原始 500 字 chunk（保留细节）

检索策略：
- 全局问题（总结/概览）→ 匹配第一层摘要 → 直接用摘要作 context
- 局部问题（某功能怎么配置）→ 匹配第二层 chunk → 精确召回
```

LangChain 有现成实现：`ParentDocumentRetriever`（子 chunk 检索，返回父 chunk 完整内容）。

**💡 记忆要点**
- 全局问题 + 局部 chunk = 向量检索失效，是 RAG 经典盲区
- 解法口诀：**分层存，按粒度取**——摘要层接全局问题，chunk 层接局部问题

---

### R4. 跨语言检索

你的项目里 embedding 模型用的是智谱的 `embedding-3`。如果用户问题是英文，但知识库是中文文档，跨语言语义检索效果会怎样？有什么解法？

**我的答案：**
> 跨语言语义检索效果会下降。解法实际不复杂，先让LLM把query翻译成中文就ok了

**问题分析**
- "效果会下降"方向对，但忽略了一个重要前提：`embedding-3` 本身是多语言模型
- 翻译是有效方案，但不是唯一解，且有翻译延迟和错误风险

**✅ 标准答案**

**先判断模型能力**：智谱 `embedding-3` 是多语言模型，中英文跨语言检索有一定支持，效果下降幅度比单语言模型小得多。对于简单场景，直接用可能就够了。

**效果不够时的解法（按实现成本排序）：**

| 方案 | 做法 | 优缺点 |
|------|------|-------|
| Query 翻译 | 检索前用 LLM 把英文 query 译成中文 | 简单直接，有翻译延迟和误译风险 |
| 换多语言 Embedding | 改用 `text-embedding-3-large`（OpenAI）或 `BGE-M3` | 效果最好，成本较高 |
| 双语入库 | 文档入库时同时存中英文版本 | 覆盖全但存储翻倍 |

**实际选型**：先测 `embedding-3` 原生效果；不够再加 Query 翻译；生产要求高换 BGE-M3（开源多语言 Embedding）。

**💡 记忆要点**
- 先问"我用的 Embedding 支不支持多语言"，再决定要不要加翻译
- Query 翻译是最轻量的补丁，但不是银弹
- BGE-M3 = 多语言 Embedding 的开源首选（和 BGE-Reranker 同系列）

---

### A4. MCP vs Function Call 选型

你知道 Function Call 和 MCP 协议的区别。如果你的 HiSpark 工具集要开放给其他 AI 助手（比如 Claude Desktop、Cursor）直接调用，你会选择封装成 Function Call 还是 MCP Server？权衡是什么？

**我的答案：**
> 我会封装成MCP Server。MCP与具体模型无关，已经解耦了，这样一次性能支持主流的所有AI助手，不用纠结每个AI助手的FC协议细节和FC调用语法等信息。

**问题分析**
- 结论正确，核心权衡讲清楚了
- 可以补充 Function Call 仍然适用的反例，答案更完整

**✅ 标准答案**

选 **MCP Server**，理由：

- **协议解耦**：MCP 是 Anthropic 主导的开放协议，Claude Desktop、Cursor、Windsurf 等主流 AI 客户端已原生支持，工具实现一次即可
- **不绑定模型**：Function Call 是各家模型自己的调用格式（OpenAI、GLM、Gemini 各不同），跨模型需要重复适配
- **开放生态**：HiSpark 工具暴露为 MCP Server 后，任何支持 MCP 的客户端都能发现并调用

**Function Call 仍然适合的场景**：工具只给单一模型内部用、需要极低延迟（MCP 走 stdio/HTTP 有额外开销）、或者模型厂商的 FC 有特殊能力（如 parallel tool calling）。

**💡 记忆要点**
- MCP = 工具的"USB 接口"，标准化后设备通用；FC = 每家厂商私有接口，需要适配器
- 对外开放工具 → MCP；模型内部紧耦合 → FC

---

## 整体复盘（2026-03-11）

### 得分概览

| 题目 | 领域 | 表现 | 核心问题 |
|------|------|------|---------|
| P2 | RAG 多实体 | B | 知道元数据方向，没说出 Top-K 不保证覆盖的根因 |
| P3 | 事件循环阻塞 | C | 混淆"等请求到来"和"阻塞事件循环"两个概念 |
| P4 | A/B 测试 | C | 答成测试用例参数化，分流/不重启/版本记录三要素全漏 |
| P5 | LCEL 迁移 | B+ | 流式答到了，mock 根因描述不精确，漏掉 async/trace |
| O2 | 测试分层 | B+ | 洞察对，举例太模糊，项目真实 bug 没发挥出来 |
| O3 | 流式 E2E | B- | 超时方向对，信号文件张冠李戴（keepalive ≠ 完成检测）|
| R2 | 召回噪声 | B | 核心方案对，Reranker 术语不够精准 |
| R3 | 上下文依赖查询 | B+ | 接近标准答案 |
| R5 | 两种幻觉 | C+ | 漏掉"如何区分"核心考点，直接跳到缓解方案 |
| T1 | dict→RunnableParallel | D | 答了 Prompt 填占位符，完全偏离方向 |
| T2 | StrOutputParser 边界 | B- | 结论对，漏掉"静默返回空字符串"的危险点 |
| R1 | 切块局限 | B | 分层索引方向对，缺具体层次结构和检索策略 |
| R4 | 跨语言检索 | B- | 漏掉"先判断 embedding 是否支持多语言"前置步骤 |
| A4 | MCP vs FC | A- | 最完整的一题，只差 FC 适用反例 |
| S4 | 向量库选型 | — | 未作答，待补充知识后练习 |

### 三个知识盲区

**① 概念混淆**（P3、O3、T1）：用相关但不精确的概念替代了正确答案，方向感觉对但答到了旁边。

**② 只答"是什么"，漏掉"为什么"**（P4、R5、T2）：P4 漏了不重启切换和版本记录；R5 跳过了区分方法；T2 没说静默失败根因。面试官必然追问。

**③ 项目举例不够具体**（O2、O3）：真实 bug 是最有说服力的素材，但停在"版本兼容性"等模糊描述，没发挥出来。

### 重点复背（最薄弱三题）

- **P3**：asyncio 单线程 → 同步函数占用 → `asyncio.to_thread` 扔线程池
- **P4**：A/B 三要素 = 哈希分流 + 环境变量动态配置 + 版本记录日志
- **T1**：`dict | Runnable` → `__ror__` → `coerce_to_runnable` → `RunnableParallel`
