# HiSpark AI Agent — Feature Roadmap (Git 提交路线图)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 定义整个项目从 v0.1 到 v1.0 的所有 git 提交节点，每个节点有明确的验收标准，用于指导 AI 阶段性开发与验收。

**原则:**
- 每个 Feature (F) = 一次 git commit，对应一个可独立验证的最小功能单元
- 每版本开发时，先写对应版本的详细 TDD 计划（`docs/plans/YYYY-MM-DD-vX.X-plan.md`），再执行
- F 编号不跨版本复用，方便引用
- 验收标准 = 可运行的命令 + 预期输出

---

## 版本总览

| 版本 | Feature 范围 | 核心技术 | 面经覆盖 |
|------|------------|---------|---------|
| v0.1 | F01–F14 | LLMChain + RetrievalQA + Gradio + Extension骨架 | Q2 Q3 Q14 ★MVP |
| v0.2 | F15–F20 | LCEL + SSE流式 | Q1 |
| v0.3 | F21–F26 | LangSmith + LLM-as-a-Judge | Q6 Q7 |
| v0.4 | F27–F36 | 进阶RAG + RAGAS | Q8 Q9 Q10 |
| v0.5 | F37–F46 | LangGraph + Agentic RAG + web_searcher | Q4 Q11 Q12 |
| v0.6 | F47–F52 | Checkpoint + HITL | Q5 Q15 |
| v0.7 | F53–F58 | Multi-Agent Supervisor | Q13 |
| v0.8 | F59–F68 | MCP Client + MCP Server | Q16 |
| v1.0 | F69–F72 | 发布准备 | 全覆盖 🚀 |

---

## v0.1 — MVP (LLMChain + Extension骨架)

> 目标: Python backend 可回答问题+执行命令，VS Code Extension 可转发请求并执行 VS Code 命令

### F01 — Python 项目初始化

**commit:** `chore: init Python backend project structure`

**文件:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/src/__init__.py`
- Create: `backend/tests/__init__.py`

**验收:**
```bash
cd backend && pip install -e ".[dev]"
python -c "import langchain; print('ok')"
```
预期输出: `ok`

---

### F02 — Zhipu LLM 连通测试

**commit:** `test: verify Zhipu GLM API connection`

**文件:**
- Create: `backend/tests/test_llm_connection.py`
- Create: `backend/src/config.py`

**验收:**
```bash
cd backend && pytest tests/test_llm_connection.py -v
```
预期输出: `PASSED` (调用 GLM-4.7, 得到非空回复)

---

### F03 — 意图分类器 (LLMChain)

**commit:** `feat: add intent classifier using LLMChain`

**文件:**
- Create: `backend/src/chains/intent_classifier.py`
- Create: `backend/tests/test_intent_classifier.py`

**验收:**
```bash
pytest tests/test_intent_classifier.py -v
```
预期: 输入"帮我编译"→ `{"type": "action", "command": "hispark-studio.build"}`
预期: 输入"如何安装SDK"→ `{"type": "answer"}`

---

### F04 — RetrievalQA 链 (知识问答)

**commit:** `feat: add RetrievalQA chain with in-memory Chroma`

**文件:**
- Create: `backend/src/chains/qa_chain.py`
- Create: `backend/tests/fixtures/sample_docs.md` (5条示例文档)
- Create: `backend/tests/test_qa_chain.py`

**验收:**
```bash
pytest tests/test_qa_chain.py -v
```
预期: 查询 "BS21芯片支持什么" → 包含 sample_docs 中的内容

---

### F05 — /chat API 端点

**commit:** `feat: add FastAPI /chat endpoint`

**文件:**
- Create: `backend/src/api/main.py`
- Create: `backend/src/api/models.py`
- Create: `backend/tests/test_api.py`

**验收:**
```bash
pytest tests/test_api.py -v
```
预期:
- POST `/chat` `{"message": "编译", "thread_id": "t1"}` → `{"type": "action", "command": "hispark-studio.build"}`
- POST `/chat` `{"message": "如何烧录", "thread_id": "t1"}` → `{"type": "answer", "answer": "..."}`

---

### F06 — Gradio UI

**commit:** `feat: add Gradio chat UI`

**文件:**
- Create: `backend/src/ui/gradio_app.py`

**验收:**
```bash
python src/ui/gradio_app.py
```
预期: 浏览器打开 http://localhost:7860，可以发送消息并收到回复（手动验收）

> **Note:** Gradio 是 Python 侧的独立调试工具，不依赖 VS Code。最终产品 UI 在 TypeScript Webview。

---

### F07 — VS Code Extension 初始化

**commit:** `chore: init VS Code extension project structure`

**文件:**
- Create: `extension/package.json`
- Create: `extension/tsconfig.json`
- Create: `extension/src/extension.ts`
- Create: `extension/.vscodeignore`

**验收:**
```bash
cd extension && npm install && npm run compile
```
预期: 无编译错误，生成 `out/extension.js`

---

### F08 — Webview 面板 (骨架)

**commit:** `feat: add Webview chat panel with postMessage echo`

**文件:**
- Create: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/webview/chat.html`
- Create: `extension/src/test/webview.test.ts`

**验收:**
```bash
cd extension && npm test
```
预期: Webview 面板创建测试 PASSED

---

### F09 — HTTP Client (调用 FastAPI)

**commit:** `feat: add HTTP client calling FastAPI /chat`

**文件:**
- Modify: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/client/ApiClient.ts`
- Create: `extension/src/test/apiClient.test.ts`

**验收:**
```bash
npm test
```
预期: ApiClient 测试 PASSED (mock server)

---

### F10 — 命令执行器

**commit:** `feat: add Command Executor for VS Code commands`

**文件:**
- Create: `extension/src/executor/CommandExecutor.ts`
- Create: `extension/src/test/commandExecutor.test.ts`

**验收:**
```bash
npm test
```
预期: 收到 `{"type":"action","command":"hispark-studio.build"}` → 调用 `vscode.commands.executeCommand` 测试 PASSED

---

### F11 — 危险命令确认对话框

**commit:** `feat: add confirmation prompt for destructive commands`

**文件:**
- Modify: `extension/src/executor/CommandExecutor.ts`
- Create: `extension/src/test/confirmationPrompt.test.ts`

**验收:**
```bash
npm test
```
预期: `requires_confirmation: true` 的命令（flash/portionOfBurn）触发 `vscode.window.showWarningMessage` 测试 PASSED

---

### F12 — 跨栈集成测试

**commit:** `test: cross-stack integration (FastAPI → Extension → executeCommand)`

**文件:**
- Create: `tests/integration/test_e2e_v01.py`

**验收:**
```bash
cd backend && uvicorn src.api.main:app &
cd tests/integration && pytest test_e2e_v01.py -v
```
预期:
- 发送 "编译项目" → 收到 action JSON，Extension mock 调用命令 PASSED
- 发送 "如何查看栈分析" → 收到 answer JSON PASSED

---

### F13 — v0.1 基线评估

**commit:** `eval: v0.1 baseline evaluation on 20 operation QA pairs`

**文件:**
- Create: `backend/scripts/eval_v01_baseline.py`
- Create: `docs/evaluation/results/v0.1-baseline.json`

**验收:**
```bash
python scripts/eval_v01_baseline.py
```
预期: 输出 20 条结果，记录 `command_match_rate`（不预设分数，记录事实）

---

### F14 — git tag v0.1

**commit:** `chore: tag v0.1 MVP release`

**验收:**
```bash
git tag v0.1 && git log --oneline -15
```
预期: 看到 F01–F14 的提交历史，tag v0.1 存在

---

## v0.2 — LCEL 重构 + SSE 流式

> 目标: 将所有链改写为 LCEL pipe 风格，支持流式输出

### F15 — 意图分类器 LCEL 重构

**commit:** `refactor: rewrite intent classifier as LCEL chain`

**文件:**
- Modify: `backend/src/chains/intent_classifier.py`
- Modify: `backend/tests/test_intent_classifier.py`

**验收:**
```bash
pytest tests/test_intent_classifier.py -v
```
预期: 所有测试 PASSED，链使用 `prompt | llm | JsonOutputParser()`

---

### F16 — RAG 链 LCEL 重构

**commit:** `refactor: rewrite QA chain as LCEL pipeline`

**文件:**
- Modify: `backend/src/chains/qa_chain.py`
- Modify: `backend/tests/test_qa_chain.py`

**验收:**
```bash
pytest tests/test_qa_chain.py -v
```
预期: 所有测试 PASSED，链使用 `RunnablePassthrough | prompt | llm | StrOutputParser()`

---

### F17 — SSE 流式端点

**commit:** `feat: add SSE streaming endpoint /chat/stream`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/test_api_stream.py`

**验收:**
```bash
pytest tests/test_api_stream.py -v
```
预期: `httpx` 异步客户端接收 SSE 事件流，逐块输出文本 PASSED

---

### F18 — Webview 流式显示

**commit:** `feat: add streaming display in Webview (EventSource)`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Modify: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/test/streaming.test.ts`

**验收:**
```bash
npm test
```
预期: EventSource mock 测试 PASSED，文字逐步追加到 DOM

---

### F19 — 流式集成测试

**commit:** `test: integration test for streaming (FastAPI SSE + httpx)`

**文件:**
- Create: `tests/integration/test_e2e_v02_stream.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v02_stream.py -v
```
预期: 完整流式响应接收测试 PASSED

---

### F20 — git tag v0.2

**commit:** `chore: tag v0.2 LCEL + streaming`

---

## v0.3 — LangSmith + LLM-as-a-Judge

> 目标: 全链路可观测，评估框架自动化

### F21 — LangSmith 链路追踪

**commit:** `feat: add LangSmith tracing with @traceable decorator`

**文件:**
- Modify: `backend/src/chains/intent_classifier.py`
- Modify: `backend/src/chains/qa_chain.py`
- Modify: `backend/.env.example` (添加 4 个 LANGSMITH_ 变量)
- Create: `backend/tests/test_langsmith_trace.py`

**验收:**
```bash
pytest tests/test_langsmith_trace.py -v
```
预期: 调用链后可在 LangSmith 控制台看到 trace（smoke test，实际验收手动查看）

---

### F22 — LLM-as-a-Judge 评估器

**commit:** `feat: add LLM-as-a-Judge evaluator (Faithfulness + Answer Relevancy)`

**文件:**
- Create: `backend/src/evaluation/llm_judge.py`
- Create: `backend/tests/test_llm_judge.py`

**验收:**
```bash
pytest tests/test_llm_judge.py -v
```
预期: 给定 question/answer/context → 返回 0-1 分数 PASSED

---

### F23 — 自动评估脚本

**commit:** `feat: add evaluation runner script with JSON report`

**文件:**
- Create: `backend/scripts/eval_runner.py`
- Create: `docs/evaluation/results/v0.3-llm-judge.json`

**验收:**
```bash
python scripts/eval_runner.py --dataset docs/evaluation/dataset.json
```
预期: 输出包含每条 QA 的 faithfulness/answer_relevancy 分数，保存 JSON 报告

---

### F24 — Webview 对话历史 + 来源展示

**commit:** `feat: show conversation history and source citations in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Modify: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/test/sourceDisplay.test.ts`

**验收:**
```bash
npm test
```
预期: sources 数组正确渲染为引用列表 PASSED

---

### F25 — RAGAS TestsetGenerator 脚本

**commit:** `feat: add RAGAS testset generator script from HiSpark docs`

**文件:**
- Create: `backend/scripts/generate_docqa.py`
- Create: `docs/evaluation/README.md` (说明如何运行生成)

**验收:**
```bash
python scripts/generate_docqa.py --input docs/hispark-readme.md --output docs/evaluation/docqa_generated.json --count 20
```
预期: 生成 20 条 QA 对，JSON 格式

---

### F26 — git tag v0.3

**commit:** `chore: tag v0.3 LangSmith + evaluation`

---

## v0.4 — 进阶 RAG + RAGAS

> 目标: 生产级检索管道，量化评估质量

### F27 — BGE 向量 + FAISS 存储

**commit:** `feat: add BGE embeddings with FAISS vector store`

**文件:**
- Create: `backend/src/retrieval/vector_store.py`
- Create: `backend/tests/test_vector_store.py`

**验收:**
```bash
pytest tests/test_vector_store.py -v
```
预期: 文档索引+检索测试 PASSED，Top-K 结果相关

---

### F28 — BM25 稀疏检索

**commit:** `feat: add BM25 sparse retriever`

**文件:**
- Create: `backend/src/retrieval/bm25_retriever.py`
- Create: `backend/tests/test_bm25.py`

**验收:**
```bash
pytest tests/test_bm25.py -v
```
预期: BM25 检索关键词精确匹配测试 PASSED

---

### F29 — RRF 融合检索

**commit:** `feat: add RRF fusion retriever (BM25 + vector)`

**文件:**
- Create: `backend/src/retrieval/hybrid_retriever.py`
- Create: `backend/tests/test_hybrid_retriever.py`

**验收:**
```bash
pytest tests/test_hybrid_retriever.py -v
```
预期: 融合排序结果优于单一检索 PASSED

---

### F30 — BGE-Reranker 精排

**commit:** `feat: add BGE-Reranker cross-encoder for result reranking`

**文件:**
- Create: `backend/src/retrieval/reranker.py`
- Create: `backend/tests/test_reranker.py`

**验收:**
```bash
pytest tests/test_reranker.py -v
```
预期: Reranker 对候选结果重排，相关性分数更高 PASSED

---

### F31 — 语义分块

**commit:** `feat: add semantic chunking strategy`

**文件:**
- Create: `backend/src/ingestion/chunker.py`
- Create: `backend/tests/test_chunker.py`

**验收:**
```bash
pytest tests/test_chunker.py -v
```
预期: 固定/滑动/语义三种分块策略各自单测 PASSED

---

### F32 — RAGAS 评估管道

**commit:** `feat: add RAGAS evaluation pipeline (4 metrics)`

**文件:**
- Create: `backend/src/evaluation/ragas_eval.py`
- Create: `backend/tests/test_ragas_eval.py`
- Create: `docs/evaluation/results/v0.4-ragas.json`

**验收:**
```bash
pytest tests/test_ragas_eval.py -v
python scripts/eval_runner.py --mode ragas
```
预期: Context Recall/Precision/Faithfulness/Answer Relevancy 四项指标有值

---

### F33 — 知识库上传 API

**commit:** `feat: add knowledge base upload endpoint (POST /kb/upload)`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/test_kb_api.py`

**验收:**
```bash
pytest tests/test_kb_api.py -v
```
预期: 上传 PDF/MD 文件后可检索到内容 PASSED

---

### F34 — Webview 知识库上传 UI

**commit:** `feat: add knowledge base upload UI in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/kbUpload.test.ts`

**验收:**
```bash
npm test
```
预期: 文件选择器调用 POST /kb/upload 测试 PASSED

---

### F35 — RAG 集成测试

**commit:** `test: integration test for full RAG pipeline (upload → query → evaluate)`

**文件:**
- Create: `tests/integration/test_e2e_v04_rag.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v04_rag.py -v
```
预期: 上传文档 → 提问 → RAGAS 评分全流程 PASSED

---

### F36 — git tag v0.4

**commit:** `chore: tag v0.4 advanced RAG + RAGAS`

---

## v0.5 — LangGraph + Agentic RAG

> 目标: 引入状态图，实现 retrieve→grade→generate/websearch 自适应流程

### F37 — AgentState 定义

**commit:** `feat: define AgentState for LangGraph`

**文件:**
- Create: `backend/src/agent/state.py`
- Create: `backend/tests/test_agent_state.py`

**验收:**
```bash
pytest tests/test_agent_state.py -v
```
预期: AgentState TypedDict 序列化/反序列化 PASSED

---

### F38 — retrieve 节点

**commit:** `feat: add retrieve node to LangGraph`

**文件:**
- Create: `backend/src/agent/nodes/retrieve.py`
- Create: `backend/tests/test_node_retrieve.py`

**验收:**
```bash
pytest tests/test_node_retrieve.py -v
```
预期: 给定 query → 返回 docs 列表 PASSED

---

### F39 — grade 节点 + 条件边

**commit:** `feat: add grade node and conditional edge (relevant/not_relevant)`

**文件:**
- Create: `backend/src/agent/nodes/grade.py`
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/test_node_grade.py`

**验收:**
```bash
pytest tests/test_node_grade.py -v
```
预期: 相关文档 → 路由到 generate；不相关 → 路由到 web_search PASSED

---

### F40 — web_searcher Tool

**commit:** `feat: add web_searcher tool (Tavily)`

**文件:**
- Create: `backend/src/agent/tools/web_searcher.py`
- Create: `backend/tests/test_web_searcher.py`

**验收:**
```bash
pytest tests/test_web_searcher.py -v
```
预期: 搜索 "HiSpark BS21 chip" → 返回结果列表 PASSED (mock Tavily)

---

### F41 — generate 节点

**commit:** `feat: add generate node with source attribution`

**文件:**
- Create: `backend/src/agent/nodes/generate.py`
- Create: `backend/tests/test_node_generate.py`

**验收:**
```bash
pytest tests/test_node_generate.py -v
```
预期: 给定 docs + query → 生成含来源的回答 PASSED

---

### F42 — StateGraph 组装

**commit:** `feat: assemble LangGraph StateGraph (retrieve→grade→generate/websearch)`

**文件:**
- Create: `backend/src/agent/graph.py`
- Create: `backend/tests/test_graph.py`

**验收:**
```bash
pytest tests/test_graph.py -v
```
预期: 完整 graph 编译成功，两条路径（有文档/无文档）各自测试 PASSED

---

### F43 — 工具调用可视化

**commit:** `feat: stream node events to Webview for tool call visualization`

**文件:**
- Modify: `backend/src/api/main.py`
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/toolVisualization.test.ts`

**验收:**
```bash
npm test
```
预期: SSE 事件包含 `{type: "node_start", node: "retrieve"}` 等，Webview 正确显示 PASSED

---

### F44 — LangGraph 集成测试

**commit:** `test: integration test for LangGraph agent (two paths)`

**文件:**
- Create: `tests/integration/test_e2e_v05_graph.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v05_graph.py -v
```
预期: doc 路径 + web 路径各自端到端测试 PASSED

---

### F45 — RAGAS 评估更新 (LangGraph)

**commit:** `eval: update RAGAS evaluation on LangGraph agent`

**文件:**
- Create: `docs/evaluation/results/v0.5-ragas.json`

**验收:**
```bash
python scripts/eval_runner.py --mode ragas --version v0.5
```
预期: 对比 v0.4 评估报告，记录指标变化（不预设结论）

---

### F46 — git tag v0.5

**commit:** `chore: tag v0.5 LangGraph + Agentic RAG`

---

## v0.6 — Checkpoint + HITL

> 目标: 记忆跨轮对话，危险操作须人工确认后恢复

### F47 — MemorySaver Checkpoint

**commit:** `feat: add MemorySaver checkpoint with thread_id session isolation`

**文件:**
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/test_checkpoint.py`

**验收:**
```bash
pytest tests/test_checkpoint.py -v
```
预期: 同一 thread_id 两次对话共享上下文，不同 thread_id 隔离 PASSED

---

### F48 — interrupt_before HITL 节点

**commit:** `feat: add interrupt_before for flash/portionOfBurn nodes`

**文件:**
- Create: `backend/src/agent/nodes/flash.py`
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/test_hitl_interrupt.py`

**验收:**
```bash
pytest tests/test_hitl_interrupt.py -v
```
预期: 烧录意图 → graph 暂停，state 为 INTERRUPTED PASSED

---

### F49 — /chat/confirm 恢复端点

**commit:** `feat: add /chat/confirm endpoint to resume interrupted graph`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/test_hitl_resume.py`

**验收:**
```bash
pytest tests/test_hitl_resume.py -v
```
预期: 确认后调用 `graph.invoke(None, config)` 恢复执行 PASSED

---

### F50 — VS Code 确认对话框

**commit:** `feat: add VS Code modal confirmation dialog for HITL`

**文件:**
- Modify: `extension/src/executor/CommandExecutor.ts`
- Create: `extension/src/test/hitlModal.test.ts`

**验收:**
```bash
npm test
```
预期: 收到 `requires_confirmation: true` → showWarningMessage → POST /chat/confirm PASSED

---

### F51 — HITL 集成测试

**commit:** `test: integration test for full HITL flow (interrupt → confirm → resume)`

**文件:**
- Create: `tests/integration/test_e2e_v06_hitl.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v06_hitl.py -v
```
预期: 烧录流程完整中断-恢复-执行 PASSED

---

### F52 — git tag v0.6

**commit:** `chore: tag v0.6 Checkpoint + HITL`

---

## v0.7 — Multi-Agent Supervisor

> 目标: 按意图路由到专职 Agent

### F53 — Supervisor 路由器

**commit:** `feat: add Supervisor agent for intent routing (DevOps vs Knowledge)`

**文件:**
- Create: `backend/src/agent/supervisor.py`
- Create: `backend/tests/test_supervisor.py`

**验收:**
```bash
pytest tests/test_supervisor.py -v
```
预期: "编译"→ DevOps；"如何安装SDK"→ Knowledge PASSED

---

### F54 — DevOps Agent 子图

**commit:** `feat: add DevOps Agent subgraph (build/flash/analysis commands)`

**文件:**
- Create: `backend/src/agent/agents/devops_agent.py`
- Create: `backend/tests/test_devops_agent.py`

**验收:**
```bash
pytest tests/test_devops_agent.py -v
```
预期: 处理编译/烧录/分析意图，返回正确 action JSON PASSED

---

### F55 — Knowledge Agent 子图

**commit:** `feat: add Knowledge Agent subgraph (RAG + web search)`

**文件:**
- Create: `backend/src/agent/agents/knowledge_agent.py`
- Create: `backend/tests/test_knowledge_agent.py`

**验收:**
```bash
pytest tests/test_knowledge_agent.py -v
```
预期: 处理知识问答意图，RAG 检索+生成 PASSED

---

### F56 — Webview 多 Agent 状态显示

**commit:** `feat: show active agent indicator in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/agentIndicator.test.ts`

**验收:**
```bash
npm test
```
预期: SSE 事件 `{type: "agent_switch", agent: "devops"}` 在 Webview 中正确显示 PASSED

---

### F57 — Multi-Agent 集成测试

**commit:** `test: integration test for multi-agent routing`

**文件:**
- Create: `tests/integration/test_e2e_v07_multiagent.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v07_multiagent.py -v
```
预期: 混合意图对话 → 正确路由到两个 Agent PASSED

---

### F58 — git tag v0.7

**commit:** `chore: tag v0.7 Multi-Agent Supervisor`

---

## v0.8 — MCP Client + MCP Server

> 目标: Python Agent 作为 MCP Client 调用外部工具；HiSpark Extension 作为 MCP Server

### F59 — Python MCP Client (filesystem)

**commit:** `feat: add MCP client connecting to filesystem MCP server`

**文件:**
- Create: `backend/src/mcp/client.py`
- Create: `backend/tests/test_mcp_client.py`

**验收:**
```bash
pytest tests/test_mcp_client.py -v
```
预期: 通过 MCP 协议读取本地文件列表 PASSED (mock server)

---

### F60 — Python MCP Client (web-search)

**commit:** `feat: add MCP client connecting to web-search MCP server`

**文件:**
- Modify: `backend/src/mcp/client.py`
- Create: `backend/tests/test_mcp_websearch.py`

**验收:**
```bash
pytest tests/test_mcp_websearch.py -v
```
预期: 通过 MCP 协议执行 web 搜索 PASSED (mock server)

---

### F61 — HiSpark MCP Server 初始化

**commit:** `feat: add HiSpark MCP Server to Extension`

**文件:**
- Create: `extension/src/mcp/HiSparkMcpServer.ts`
- Create: `extension/src/test/mcpServer.test.ts`

**验收:**
```bash
npm test
```
预期: MCP Server 启动，响应 tools/list 请求 PASSED

---

### F62 — MCP Tool: hispark_build/rebuild/clean

**commit:** `feat: expose hispark_build/rebuild/clean as MCP Tools`

**文件:**
- Modify: `extension/src/mcp/HiSparkMcpServer.ts`
- Create: `extension/src/test/mcpTools.test.ts`

**验收:**
```bash
npm test
```
预期: MCP Client 调用 `hispark_build` Tool → `vscode.commands.executeCommand('hispark-studio.build')` PASSED

---

### F63 — MCP Tool: hispark_flash/stackAnalysis/imageAnalysis

**commit:** `feat: expose flash/stackAnalysis/imageAnalysis as MCP Tools`

**文件:**
- Modify: `extension/src/mcp/HiSparkMcpServer.ts`

**验收:**
```bash
npm test
```
预期: flash Tool 包含 `requires_confirmation: true` 元数据 PASSED

---

### F64 — Agent 运行时发现 HiSpark MCP Tools

**commit:** `feat: Agent discovers HiSpark commands via MCP at runtime`

**文件:**
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/test_mcp_tool_discovery.py`

**验收:**
```bash
pytest tests/test_mcp_tool_discovery.py -v
```
预期: Agent 启动时调用 `tools/list` 获取可用 HiSpark 工具，无需硬编码 PASSED

---

### F65 — MCP 对比文档

**commit:** `docs: add MCP vs Function Calling comparison note`

**文件:**
- Create: `docs/notes/mcp-vs-function-calling.md`

**内容要点:** 运行时发现 vs 编译时耦合、松耦合体现点、面经叙述角度

---

### F66 — MCP 集成测试

**commit:** `test: integration test for MCP (Agent ↔ HiSpark MCP Server)`

**文件:**
- Create: `tests/integration/test_e2e_v08_mcp.py`

**验收:**
```bash
pytest tests/integration/test_e2e_v08_mcp.py -v
```
预期: Python Agent 通过 MCP 调用 HiSpark Tool，Extension 执行 VS Code 命令 PASSED

---

### F67 — RAGAS 最终评估

**commit:** `eval: final RAGAS evaluation on full agent (v0.8)`

**文件:**
- Create: `docs/evaluation/results/v0.8-ragas-final.json`

**验收:**
```bash
python scripts/eval_runner.py --mode ragas --version v0.8
```
预期: 对比 v0.4/v0.5 历史报告，记录完整演进曲线

---

### F68 — git tag v0.8

**commit:** `chore: tag v0.8 MCP integration`

---

## v1.0 — 发布准备

### F69 — OpenAPI Spec 完善

**commit:** `docs: finalize OpenAPI spec for /chat and /kb endpoints`

**文件:**
- Create: `docs/api-spec.yaml`

**验收:**
```bash
python -c "import yaml; yaml.safe_load(open('docs/api-spec.yaml'))"
```
预期: YAML 合法，所有端点文档完整

---

### F70 — .vsix 打包

**commit:** `chore: package VS Code extension as .vsix`

**文件:**
- Modify: `extension/package.json` (publisher, version, icon)

**验收:**
```bash
cd extension && npx vsce package
ls *.vsix
```
预期: 生成 `hispark-ai-agent-1.0.0.vsix`

---

### F71 — README 更新

**commit:** `docs: update README with architecture diagram and version history`

**文件:**
- Modify: `README.md`

---

### F72 — git tag v1.0

**commit:** `chore: tag v1.0 production release 🚀`

---

## 快速索引

| Feature | 版本 | 关键词 |
|---------|------|-------|
| F01-F06 | v0.1 | Python backend 初始化 |
| F07-F11 | v0.1 | Extension 骨架 + 命令执行器 |
| F12-F14 | v0.1 | 集成测试 + 基线评估 |
| F15-F20 | v0.2 | LCEL 重构 + SSE 流式 |
| F21-F26 | v0.3 | LangSmith + LLM-as-a-Judge |
| F27-F36 | v0.4 | 进阶 RAG + RAGAS |
| F37-F46 | v0.5 | LangGraph + Agentic RAG |
| F47-F52 | v0.6 | Checkpoint + HITL |
| F53-F58 | v0.7 | Multi-Agent Supervisor |
| F59-F68 | v0.8 | MCP Client + Server |
| F69-F72 | v1.0 | 发布准备 |

**总计: 72 个 git 提交节点**
