# 学习计划：hispark-ai-agent v0.1 代码精讲

> **目标：** 对项目中每个重要代码细节能言之有物，能在面试中结合项目举例说明。
> **方式：** 代码讲解式——从项目真实代码出发，解释"是什么、为什么这样写、不这样写会怎样"。
> **节奏：** 每个模块独立完整，可按顺序也可跳跃学习。

---

## 模块 01：FastAPI + Pydantic v2

**为什么先学这个：** 这是最具体、最容易看懂的模块。API 的请求/响应模型是整个系统的"合约"，
理解它之后看其他模块会更顺。

**讲解内容：**
```
backend/src/api/models.py     ← Pydantic v2 模型定义
backend/src/api/main.py       ← FastAPI 路由、校验、异常处理
```

**覆盖概念：**
1. Pydantic v2 是什么，为什么用它而不是普通 dict
2. `BaseModel`、字段定义、默认值、可选字段
3. FastAPI 如何用 Pydantic 自动完成请求校验（422 的来源）
4. `response_model` 的作用：为什么要声明，不声明有什么后果
5. `Union[ActionResponse, AnswerResponse]`：联合类型的用途
6. `HTTPException`：为什么不直接 return 错误，而要 raise
7. `model_dump()`：Pydantic v2 的序列化方法（v1 叫 `.dict()`）

**面试高频问题预告：**
- "你的 API 如何做参数校验的？"
- "422 和 400 有什么区别？"
- "Pydantic v1 和 v2 有什么区别？"

---

## 模块 02：pytest 测试体系

**为什么这个模块单独讲：** 很多人会写测试但说不清楚测试策略。
这个项目的测试分层很清晰，是面试中很好的谈资。

**讲解内容：**
```
backend/tests/unit/test_api.py                  ← 单元测试：TestClient + Mock
backend/tests/unit/test_intent_classifier.py    ← 单元测试：Mock LLM
backend/tests/unit/test_qa_chain.py             ← 单元测试：Mock Chain
backend/tests/integration/test_llm_real.py      ← 集成测试：真实 API
tests/e2e/test_e2e_v01.py                       ← E2E：subprocess fixture
```

**覆盖概念：**
1. 测试金字塔：三层测试各自的职责边界
2. `pytest fixture`：什么是 fixture，`scope` 参数的含义
3. `pytest-mock` 的 `mocker.patch`：patch 的目标为什么要是"使用处"而非"定义处"
4. `@pytest.mark.integration`：如何隔离慢测试
5. `MagicMock` vs `mocker.patch` 的区别
6. Pydantic v2 可测性问题：为什么工厂函数是正确解法，Testing Seam 为什么不能进生产代码
7. E2E fixture 里的 subprocess 管理：scope="module" 的含义
8. 为什么 Mock 是"有意义的谎言"——集成测试是担保人

**面试高频问题预告：**
- "你怎么测试依赖外部 API 的代码？"
- "Mock 和 Stub 有什么区别？"
- "你的项目测试覆盖率怎么样？"（不是数字，是策略）

---

## 模块 03：LangChain 核心概念

**为什么这个比 RAG 先讲：** RAG 是建立在 LangChain 链式调用上的，
先理解 Chain 的概念，RAG 才能讲清楚。

**讲解内容：**
```
backend/src/config.py                           ← LLM 工厂函数
backend/src/chains/intent_classifier.py         ← LLMChain 完整实现
```

**覆盖概念：**
1. `ChatOpenAI`：LangChain 对 LLM 的抽象，为什么不直接调 requests
2. `PromptTemplate`：模板变量、`input_variables` 的作用
3. `LLMChain`：把 Prompt + LLM 组合成一个可调用单元
4. `LLMChain.run()` vs `.invoke()`：新旧 API 的区别
5. 为什么 v0.1 刻意用旧版 LLMChain（v0.2 对比用）
6. 结构化输出：为什么让 LLM 输出 JSON，怎么处理输出不稳定
7. DeprecationWarning 的含义：0.3.x 的 LLMChain 在 1.x 被移除
8. LCEL 预告：`prompt | llm | parser` 管道式设计的优势

**面试高频问题预告：**
- "你用 LangChain 做了什么？"
- "LangChain 解决了什么问题，不用它行不行？"
- "LLM 的输出不稳定怎么处理？"

---

## 模块 04：RAG 完整流程

**这是整个项目技术含量最高的模块。**
把 RAG 讲清楚是 LLM 应用开发岗位最重要的能力之一。

**讲解内容：**
```
backend/src/chains/qa_chain.py                  ← RAG 完整实现
backend/tests/fixtures/sample_docs.md           ← 知识库文档
backend/tests/integration/test_llm_real.py      ← RAG 质量测试
```

**覆盖概念：**

**第一层：向量化（Embedding）**
1. Embedding 是什么：把文本变成数字向量的过程
2. 为什么用向量：相似的语义，向量空间里距离近
3. `OpenAIEmbeddings`（智谱 embedding-3）：调用方式
4. 向量维度是什么意思

**第二层：向量数据库（Chroma）**
5. Chroma 是什么：专门存向量的数据库
6. `from_texts()`：文档如何被切分和存储
7. `as_retriever(search_kwargs={"k": 3})`：k=3 的含义
8. 内存模式 vs 持久化模式的区别

**第三层：检索增强生成（RAG）**
9. RetrievalQA.from_chain_type：把检索器和 LLM 组合起来
10. `chain_type="stuff"`：把检索到的文档"塞"进 Prompt
11. 完整数据流：用户问题 → 向量化 → 检索 → 拼 Prompt → LLM 生成
12. 懒加载模式：为什么用 `_get_qa_chain()` 而不是模块级初始化

**第四层：RAG 质量评估**
13. 为什么关键词断言比精确匹配更适合 RAG 测试
14. `sources: []`：v0.1 为空，v0.4 要真正返回来源

**面试高频问题预告：**
- "RAG 是什么，解决了什么问题？"
- "你的 RAG 效果好不好，怎么评估的？"
- "向量数据库和普通数据库有什么区别？"
- "chunk size 和 k 值怎么调？"（v0.1 还没调，但要知道概念）

---

## 模块 05：TypeScript 工程模式

**前提：** 你已经熟悉 VS Code Extension 架构，这个模块只补充项目里用到的工程模式。

**讲解内容：**
```
extension/src/executor/CommandExecutor.ts       ← 依赖注入模式
extension/src/webview/chatHtml.ts               ← 纯函数提取
extension/src/client/ApiClient.ts               ← 接口设计
extension/src/test/suite/commandExecutor.test.ts ← 依赖注入如何使测试变简单
```

**覆盖概念：**
1. 依赖注入（DI）：不是框架，而是一种设计选择
2. 为什么 `CommandExecutor` 通过构造函数接收函数而不是直接调 vscode API
3. 纯函数：`getHtmlContent()` 为什么要从 `ChatPanel` 里提取出来
4. `Thenable<T>` vs `Promise<T>`：VS Code API 的历史遗留问题
5. TypeScript 接口（interface）：`ChatResponse` 的设计

**面试高频问题预告：**
- "你怎么测试 VS Code Extension 的代码？"
- "什么是依赖注入，你在项目里怎么用的？"

---

## 模块 06：Python 后端 + VS Code Extension 联合 E2E 测试

**为什么单独成模块：** 这是 v0.1 里技术深度最高的测试工程决策。
两个进程、两种语言、一次 `npm run test:e2e` 跑通全链路——能讲清楚这个，面试中"工程质量"一栏直接拉满。

**讲解内容：**
```
extension/src/test/e2e/runTests.ts          ← 外部启动器：后端进程 + VS Code 启动
extension/src/test/e2e/index.ts             ← Mocha runner（extension host 内）
extension/src/test/e2e/extensionHost.test.ts ← 实际测试用例（extension host 内）
extension/src/webview/ChatPanel.ts          ← DI 修改：constructor(panel, client = defaultClient)
```

**覆盖概念：**

**第一层：两进程架构**
1. 为什么需要两个进程：runTests.ts（Node.js）vs extensionHost.test.ts（VS Code Electron）
2. `@vscode/test-electron`：它做了什么——下载 VS Code、注入 extension、连接测试 runner
3. `extensionDevelopmentPath` vs `extensionTestsPath`：两个路径各自的含义
4. `extensionTestsEnv`：如何把端口号从外部进程传进 extension host

**第二层：后端进程管理**
5. `child_process.spawn` vs Python E2E 里的 `subprocess.Popen`：同一个模式，不同语言
6. `waitForHealth()` 轮询：为什么不能 sleep 固定时间
7. `finally { backend.kill() }`：资源清理的保证——与 pytest `yield` fixture 对比
8. `stdio: 'inherit'`：为什么测试时要看到后端日志

**第三层：Mocha TDD interface**
9. Mocha 两种接口：BDD（`describe/it`）vs TDD（`suite/test`）——必须显式指定 `ui: 'tdd'`
10. 为什么 VS Code extension 测试用 TDD interface（历史惯例，VS Code 官方示例均如此）

**第四层：依赖注入如何让 E2E 成为可能**
11. 为什么要改 `ChatPanel.ts` 构造函数：`defaultClient` 硬编码 8000，E2E 需要 8001
12. `constructor(panel, client = defaultClient)`：标准 DI 不是测试代码——和 Testing Seam 的区别
13. 为什么没有 `createForTest()` 方法：命名带 test 字样 = Testing Seam = 2026-03-04 事故同款错误

**第五层：端口隔离策略**
14. 为什么用 8001 不用 8000：避免与开发时运行的后端实例冲突
15. `HISPARK_TEST_BACKEND_PORT` 环境变量：测试用端口的传递链路

**面试高频问题预告：**
- "你的 Extension 怎么测试的？有没有自动化测试？"
- "你怎么做前后端的联合测试？"
- "什么是依赖注入，你在项目里哪里用了？"（可以结合 ChatPanel + CommandExecutor 两个例子回答）
- "测试里的进程管理是怎么做的？"

---

## 学习顺序建议

**标准顺序（推荐）：** 01 → 02 → 03 → 04 → 05 → 06

**如果有面试压力：**
- 明天有面试 → 先看 03（LangChain）+ 04（RAG）
- 面试强调工程质量 → 先看 02（测试体系）+ 06（联合 E2E）

---

## 每次学习的格式

每讲一个概念，我都会给你：

```
【是什么】  一句话解释
【项目里在哪】  具体文件 + 行号
【代码走读】  逐段讲解，为什么这样写
【如果不这样写】  反例或替代方案的后果
【面试怎么说】  30秒版本的表达模板
```

---

## 开始

告诉我从哪个模块开始，我们就进入第一讲。
