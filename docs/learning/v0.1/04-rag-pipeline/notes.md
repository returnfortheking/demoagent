# 模块 04：RAG 完整流程

> 基于 `hispark-ai-agent v0.1` 真实代码讲解：`backend/src/chains/qa_chain.py`
>  
> 目标：把「RAG 从数据到答案」讲成一条完整、可复述、可面试的工程链路。

---

## 第 1 讲：RAG 是什么，为什么这个项目要用它

### 【是什么】

RAG（Retrieval-Augmented Generation，检索增强生成）是：

1. 先从私有知识库里检索相关内容
2. 再把检索结果交给 LLM 生成回答

一句话：**先找资料，再作答**，而不是让模型纯靠参数记忆“瞎猜”。

### 【项目里在哪】

- 检索与生成实现：`backend/src/chains/qa_chain.py`
- 入口调用点：`backend/src/api/main.py` 的 `answer_question(request.message)`
- 知识库文本：`backend/tests/fixtures/sample_docs.md`

### 【代码走读】

在 `/chat` 接口里，先做意图分类：

- 若 `type=action`，返回命令
- 否则走问答分支：`answer_question(...)`

这意味着 RAG 不是独立接口，而是 `/chat` 的一个分支能力，和 action 调用共享统一入口。

### 【如果不这样写】

如果不做 RAG，而直接 `llm.invoke(question)`：

- 回答可能“看起来合理但事实错误”
- 无法把答案绑定到你的业务文档
- 文档更新后，模型不会自动“知道新内容”

### 【面试怎么说】

> “我们在 `/chat` 的 answer 分支里接了 RAG。流程是：用户问题先经检索器命中文档片段，再把片段和问题一起喂给 LLM 生成回答。这样回答来源于项目私有知识，不是纯模型记忆，事实一致性更高。”

---

## 第 2 讲：Embedding —— 文本如何变成可检索向量

### 【是什么】

Embedding 是把文本映射到向量空间的过程。  
语义接近的文本，在向量空间里距离通常更近。

### 【项目里在哪】

`backend/src/chains/qa_chain.py`：

```python
_embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=os.getenv("ZHIPU_API_KEY"),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
)
```

### 【代码走读】

这里用的是 `langchain_openai.OpenAIEmbeddings`，但底层并不是 OpenAI 官方地址，而是智谱兼容 OpenAI 协议的网关：

- `model="embedding-3"`
- `openai_api_base="https://open.bigmodel.cn/api/paas/v4/"`

这是一个常见工程技巧：**用统一 SDK 抽象 + 兼容协议后端**，减少业务代码耦合。

### 【如果不这样写】

如果硬编码 requests 调 embedding API：

- 每次换模型供应商都要重写调用层
- 与 LangChain 组件的组合能力（Retriever、VectorStore）会下降
- 测试替身（mock）路径也更复杂

### 【补充：向量维度是什么】

Embedding 模型把一段文本映射成一个**固定长度的浮点数数组**，这个数组就是向量。长度叫**维度**。

```
“帮我编译项目” → [0.12, -0.34, 0.87, ..., 0.05]  # 1024 个数字
“build the project” → [0.11, -0.31, 0.85, ..., 0.04]  # 语义接近，数字也接近
```

- 智谱 `embedding-3` 的维度是 **2048**
- OpenAI `text-embedding-ada-002` 的维度是 **1536**
- 维度越高，表达能力越强，但存储和计算成本也越高

维度本身是模型训练时确定的，用户不能改，只能选不同维度的模型。

### 【补充：相似度检索怎么算”近”】

**Chroma 的默认距离函数是 L2（欧氏距离），不是余弦相似度。**

项目代码里没有显式指定：

```python
vectorstore = Chroma.from_texts(texts=chunks, embedding=_embeddings)
# 未传 collection_metadata，实际用 L2（默认）
```

如果要明确用余弦，需要显式配置：

```python
vectorstore = Chroma.from_texts(
    texts=chunks,
    embedding=_embeddings,
    collection_metadata={“hnsw:space”: “cosine”},
)
```

**余弦相似度的原理（作为知识点理解）：**

```
相似度 = 向量A · 向量B / (|A| × |B|)
```

值域是 [-1, 1]，1 表示方向完全相同（语义最近），0 表示无关。
注意：-1 在几何上是”方向相反”，不等于语义上的”反义词”，实际工程里更看相对排序，不看绝对值语义。

为什么余弦适合文本？它只看方向，不看向量长度：同一个意思用长句和短句表达，向量长度不同，但方向接近。

**L2 和余弦的关系：**
当 embedding 模型对向量做了归一化（很多模型会这样），两者排序等价：
`||A-B||² = 2(1 - cosθ)`，单位向量下 L2 距离与余弦距离单调对应。

用户查询时（以 Chroma 默认 L2 为例）：
```
query “帮我编译” → embedding → query 向量
                              ↓
              Chroma: 和所有 chunk 向量算 L2 距离
                              ↓
              返回距离最小的 k=3 个 chunk
```

### 【补充：`_embeddings` 为什么不用懒加载】

代码里有个不对称：

```python
# 模块级创建（非懒加载）
_embeddings = OpenAIEmbeddings(model=”embedding-3”, ...)

# 懒加载
_qa_chain: RetrievalQA | None = None
```

原因：`OpenAIEmbeddings(...)` 只是**配置对象**，不发网络请求；真正的 embedding API 调用发生在 `build_retriever` 里的 `Chroma.from_texts()` 阶段。所以 import 不会触发网络副作用，不需要懒加载。`_qa_chain` 则相反——`RetrievalQA.from_chain_type()` 内部会调 `build_retriever`，继而触发真实 embedding 调用，所以必须懒加载。

### 【面试怎么说】

> “Embedding 层我用的是 OpenAI-compatible 接口，SDK 层保持 LangChain 标准抽象，底层通过 `openai_api_base` 指向智谱，上层不感知厂商。向量是把文本映射成固定维度的浮点数组，语义接近的文本向量方向相近。Chroma 默认用 L2 距离做检索；如果要用余弦相似度，需显式传 `collection_metadata={'hnsw:space': 'cosine'}`，v0.1 里没有配置，用的是 L2 默认值。”

---

## 第 3 讲：文本切分（Chunking）—— 为什么不是整篇文档直接入库

### 【是什么】

Chunking 是把长文档拆成可检索的小片段。  
否则向量检索粒度太粗，命中效果差。

### 【项目里在哪】

`build_retriever()`：

```python
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks: list[str] = []
for doc in docs:
    chunks.extend(splitter.split_text(doc))
```

### 【代码走读】

- `chunk_size=500`：每个块大约 500 字符
- `chunk_overlap=50`：相邻块有 50 字符重叠，降低语义断裂
- `RecursiveCharacterTextSplitter`：优先按更自然的分隔符切，再退化到字符级

这是一组“保守但实用”的默认参数，适合 v0.1 小规模知识库。

### 【如果不这样写】

常见反例：

1. **不切分**：一整篇文档入库，检索命中大段噪音，上下文利用率低  
2. **切太碎**：每块信息不足，LLM 拿到片段后难以回答完整问题  
3. **无 overlap**：关键信息刚好落在块边界，语义被切断

### 【补充：`RecursiveCharacterTextSplitter` 里的 “Recursive” 是什么意思】

不是”递归调用自身”的意思，而是**按优先级顺序逐级尝试分隔符**，直到能把文本切到目标大小为止。

默认分隔符列表（从高优先到低优先）：

```
[“\n\n”, “\n”, “ “, “”]
```

工作逻辑：

```
1. 先试用 “\n\n”（段落边界）切：结果块 <= chunk_size？保留
2. 如果某块还太大，再试 “\n”（行边界）切
3. 还太大？再试 “ “（词边界）切
4. 仍然太大？直接按字符数强切（””）
```

**为什么这比”按固定字符数切”更好：**

- 固定字符数切（`CharacterTextSplitter`）：直接在第 500 个字符截断，可能切在词中间或句子中间
- 递归切分：尽量在最自然的语义边界断开，切到”段落 > 行 > 词”，内容完整性更好

**面试类比：**

> “就像切蛋糕先用大刀，大刀切不齐再换小刀，最后才用手掰。每次都从最自然的缝隙切入。”

### 【面试怎么说】

> “我在 RAG 里用了 `chunk_size=500 / overlap=50`。核心考虑是平衡三件事：检索精度、上下文完整性、以及 token 成本。overlap 是为了降低边界断裂，避免答案依赖的信息被切到两个块里。`RecursiveCharacterTextSplitter` 的 'Recursive' 是指按优先级逐级尝试分隔符（段 > 行 > 词 > 字符），尽量在语义边界断开，而不是无脑按字符数截断。”

---

## 第 4 讲：Chroma 检索器 —— 向量库层到底做了什么

### 【是什么】

向量数据库负责：

1. 存储向量化后的文本块
2. 对用户 query 做相似度检索
3. 返回 top-k 最相关片段

### 【项目里在哪】

`build_retriever()`：

```python
vectorstore = Chroma.from_texts(
    texts=chunks,
    embedding=_embeddings,
)
return vectorstore.as_retriever(search_kwargs={"k": 3})
```

### 【代码走读】

- `from_texts(...)`：把 chunk 列表嵌入并写入 Chroma
- `as_retriever(k=3)`：每次返回最相似的 3 段上下文

当前是**内存模式**（未配置 `persist_directory`），进程重启后重建索引。  
这在学习版项目里很合理：实现简单、启动成本可接受。

### 【如果不这样写】

如果 `k` 太小（如 1）：

- 可能漏掉答案所需补充信息

如果 `k` 太大（如 10+）：

- 噪音段变多，Prompt 被稀释，token 成本变高

### 【面试怎么说】

> “向量库存储和检索我用 Chroma，`k=3` 是保守默认值。v0.1 先追求链路稳定，后续版本再系统调参（chunk size、k、rerank）。当前是内存库，方便开发和测试。”

---

## 第 5 讲：RetrievalQA 组装 —— 检索器和 LLM 如何拼起来

### 【是什么】

`RetrievalQA` 是 LangChain 的组合器，把：

- Retriever（检索）
- LLM（生成）

装成一个可调用 chain。

### 【项目里在哪】

`_get_qa_chain()`：

```python
_qa_chain = RetrievalQA.from_chain_type(
    llm=get_llm(),
    chain_type="stuff",
    retriever=retriever,
)
```

### 【代码走读】

`chain_type="stuff"` 的语义是：  
把检索到的多个片段直接拼接（stuff）到同一个 prompt 里再回答。

它的优点是实现简单、路径短，缺点是上下文变大后可能引入噪音。  
对于 v0.1 的小知识库场景，这个取舍是合理的。

### 【补充：chain_type 有哪些，什么时候用】

LangChain 提供 4 种 chain_type，面试常被追问：

| chain_type | 工作方式 | 适用场景 | 代价 |
|---|---|---|---|
| `stuff` | 把所有 chunk 拼成一个 prompt | 小知识库（< 4k token） | 超出上下文窗口时直接失败 |
| `map_reduce` | 每个 chunk 单独问 LLM，再汇总答案 | 文档多、chunk 总量超出上下文 | 多次 LLM 调用，成本高、耗时长 |
| `refine` | 先对第一个 chunk 给出初步答案，再逐块”精炼”更新 | 需要答案随新信息递进式改善 | 串行调用，延迟高；早期错误会传播 |
| `map_rerank` | 每个 chunk 单独生成答案 + 置信度，取最高置信度的那个 | 答案来自单一最关键片段 | 多次 LLM 调用；不擅长跨多 chunk 综合 |

**v0.1 为什么选 `stuff`：**

- 知识库是单个 fixture 文档，切块后 token 总量远低于上下文限制
- `stuff` 实现最简单、路径最短、最容易调试
- 其他链型适用于文档量增长后的优化，不是起步必须项

**面试补充说法：**

> “如果知识库规模上去了，我会先考虑 `map_reduce`；如果答案明显来自某一段而不是综合多段，可以试 `map_rerank`。当前 v0.1 是 `stuff`，因为语料小、链路短、调试成本最低。”

### 【如果不这样写】

如果一上来就用更复杂链型（如 map-reduce/refine）：

- 代码复杂度和调试成本上升
- 在小规模语料上不一定有明显收益

### 【面试怎么说】

> “v0.1 的 RAG 采用 `RetrievalQA + chain_type=stuff`，目的是先用最短路径跑通可验证链路。`stuff` 把所有 chunk 直接拼入 prompt，适合小语料库。如果文档量增长超出上下文窗口，再升级到 `map_reduce`。复杂链型是后续优化选项，不是起步阶段必须项。”

---

## 第 6 讲：懒加载（Lazy Init）—— 为什么 `_get_qa_chain()` 是关键设计

### 【是什么】

懒加载：模块导入时不初始化重资源，首次调用时再创建并缓存。

### 【项目里在哪】

`qa_chain.py`：

```python
_qa_chain: RetrievalQA | None = None

def _get_qa_chain() -> RetrievalQA:
    global _qa_chain
    if _qa_chain is None:
        retriever = build_retriever(_load_sample_docs())
        _qa_chain = RetrievalQA.from_chain_type(...)
    return _qa_chain
```

`answer_question()`：

```python
def answer_question(question: str) -> str:
    return _get_qa_chain().run(question)
```

### 【代码走读】

这个模式解决了两个工程问题：

1. **启动成本**：导入模块时不触发真实 embedding / chain 构建  
2. **可测试性**：单测可直接 patch `_get_qa_chain`，绕开网络调用

注意：`_embeddings` 对象是在模块加载时创建的，但实际网络调用发生在 `build_retriever` 执行阶段，而不是 import 阶段。

### 【如果不这样写】

若模块级 eager 初始化（import 就构建 QA chain）：

- 任何 import 都可能触发慢调用或外部依赖错误
- 单元测试会更难隔离
- 启动与调试体验明显变差

### 【面试怎么说】

> “我把 QA chain 做成 lazy singleton：首次调用时构建，后续复用。好处是 import 无副作用、启动更快、且测试可通过 patch 工厂函数隔离外部依赖。”

---

## 第 7 讲：知识库装载路径 —— 为什么要用 `pathlib` 相对定位

### 【是什么】

代码需要稳定找到 `sample_docs.md`，不能依赖“当前工作目录刚好正确”。

### 【项目里在哪】

`_load_sample_docs()`：

```python
fixture_path = (
    pathlib.Path(__file__).parent.parent.parent
    / "tests"
    / "fixtures"
    / "sample_docs.md"
)
text = fixture_path.read_text(encoding="utf-8")
return [text]
```

### 【代码走读】

`__file__` 基于模块自身路径定位，再拼接到 `tests/fixtures/sample_docs.md`。  
因此不管你从项目根目录还是其他目录启动，路径都稳定。

### 【如果不这样写】

如果用相对路径字符串（如 `open("tests/fixtures/sample_docs.md")`）：

- 当 CWD 变化时直接报 `FileNotFoundError`
- CI、IDE、脚本启动路径不同会导致“本地可跑，线上失败”

### 【面试怎么说】

> “知识库 fixture 的路径我用 `pathlib + __file__` 做相对定位，避免 CWD 依赖。这是后端项目里常见的稳定性细节，能减少环境差异导致的路径问题。”

---

## 第 8 讲：RAG 在 API 层的返回契约

### 【项目里在哪】

`backend/src/api/main.py`：

```python
answer = answer_question(request.message)
return AnswerResponse(answer=answer).model_dump()
```

`backend/src/api/models.py`：

```python
class AnswerResponse(BaseModel):
    type: str = "answer"
    answer: str
    sources: list[Any] = []
```

### 【代码走读】

当用户问题被判定为问答意图时：

1. 调 `answer_question`（RAG）
2. 包装成 `AnswerResponse`
3. `sources` 当前固定空列表（v0.1 未返回来源）

这是一种“先固定契约、后扩展字段语义”的做法，前后端接口更稳定。

### 【如果不这样写】

如果现在就返回不稳定结构（有时有 `sources`，有时没有）：

- 前端类型判断复杂化
- 接口演进容易破坏兼容性

### 【面试怎么说】

> “v0.1 的 RAG 回答只返回 `answer`，`sources` 先占位为空，目的是保持接口契约稳定。后续版本再把检索来源透出，不会破坏前端解析逻辑。”

---

## 第 9 讲：RAG 测试策略 —— 为什么要“关键词断言”

### 【项目里在哪】

- 单元测试：`backend/tests/unit/test_qa_chain.py`
- 集成测试：`backend/tests/integration/test_llm_real.py`

### 【代码走读】

单元测试（快）：

- patch `_get_qa_chain` 返回 `MagicMock`
- 验证 `answer_question` 的调用与返回类型逻辑

集成测试（真）：

- 真实调用 `answer_question(...)`
- 用关键词断言事实是否出现（如 `gitee`、`fbb_ws63`、`HISPARK_TOOL_PATH`）

为什么不是精确匹配整句？

- LLM 措辞是概率性的，逐字匹配会造成大量误报
- 关键词断言抓“事实正确性”，更符合 RAG 质量验证目标

### 【如果不这样写】

只做单测：

- 可能掩盖真实 embedding/LLM 失败

只做精确字符串断言：

- 内容正确但措辞不同也会失败，测试脆弱

### 【面试怎么说】

> “RAG 我用了双层测试：单测验证代码路径，集成测试验证真实语义结果。集成层采用关键词断言而不是整句匹配，因为 LLM 语言表达有随机性，但关键事实必须稳定。”

---

## 第 10 讲：v0.1 的已知边界与可升级方向

### 【当前边界】

1. 知识库来自单个 fixture 文档，不是生产级数据管道  
2. Chroma 内存模式，无持久化索引  
3. `sources` 未回传具体来源片段  
4. 使用 `RetrievalQA.run()`（LangChain 旧接口，存在 deprecation 提示）

### 【升级方向（按优先级）】

1. **可观测性**：把检索命中文本和得分输出到日志  
2. **可解释性**：返回 `sources`（文档名、片段、相似度）  
3. **持久化**：Chroma 增加持久化目录，减少重复构建  
4. **API 升级**：迁移到 LCEL / `invoke` 体系，减少旧 API 技术债

---

## 总结：RAG 在本项目里的完整数据流

```text
用户提问
  ↓
/chat 路由
  ↓
intent_classifier 判断为 answer
  ↓
answer_question(question)
  ↓
_get_qa_chain()（首次调用时构建）
  ├─ _load_sample_docs() 读知识库文本
  ├─ build_retriever()
  │   ├─ TextSplitter 切块
  │   ├─ Embedding 向量化
  │   └─ Chroma 建索引 + top-k retriever
  └─ RetrievalQA.from_chain_type(stuff)
  ↓
chain.run(question) 生成答案
  ↓
AnswerResponse(answer=..., sources=[])
  ↓
返回给 Extension 展示
```

---

## 面试题速答

**Q1：RAG 解决了什么问题？**  
> 解决“模型只靠参数记忆导致事实漂移”的问题。先检索私有知识再生成，答案和业务文档绑定，稳定性更高。

**Q2：你们的 RAG 在代码里怎么落地？**  
> `qa_chain.py` 里用 `TextSplitter + OpenAIEmbeddings + Chroma + RetrievalQA(stuff)` 组链，`answer_question` 暴露给 `/chat` 的 answer 分支调用。

**Q3：为什么要做懒加载？**  
> 避免 import 时副作用，提升启动速度，并让单测可以 patch `_get_qa_chain` 完全绕开网络依赖。

**Q4：RAG 怎么测试质量？**  
> 单测 mock 链路验证代码行为；集成测真实调用并做关键词断言，验证核心事实而不是逐字文案。

**Q5：v0.1 最大局限是什么？**  
> `sources` 还没回传，知识库规模小且内存索引，属于学习版实现。升级方向是可解释性、持久化和 LCEL 迁移。

