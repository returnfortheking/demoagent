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
| v0.2 | F15–F22 | LCEL + SSE流式 + Prompt版本管理 + API契约门禁 | Q1 |
| v0.3 | F23–F31 | LangSmith + LLM-as-a-Judge + 性能基线 + Docker + 真实文档入库 | Q6 Q7 |
| v0.4 | F31–F41 | 进阶RAG + RAGAS + K8s编排 | Q8 Q9 Q10 |
| v0.5 | F42–F52 | LangGraph + Agentic RAG + 降级回滚 | Q4 Q11 Q12 |
| v0.6 | F53–F58 | Checkpoint + HITL | Q5 Q15 |
| v0.7 | F59–F64 | Multi-Agent Supervisor | Q13 |
| v0.8 | F65–F74 | MCP Client + MCP Server | Q16 |
| v1.0 | F75–F81 | 发布准备 | 全覆盖 |

---

## 校准说明（以当前仓库为准）

- `v0.1` 已在仓库落地，实施细节以 `docs/plans/2026-03-02-v0.1-plan.md` 与当前代码目录为准。
- `v0.2` 到 `v0.8` 属于规划路线，保持当前版本顺序不变。
- 面试收益优先级：主线必做 `v0.2`–`v0.6`；进阶加分 `v0.7`（Multi-Agent）和 `v0.8`（MCP）。

---

## v0.2+ 执行约束（新增）

- 后端测试路径统一使用：`backend/tests/unit/` 与 `backend/tests/integration/`。
- 扩展测试路径统一使用：`extension/src/test/suite/`（单测）与 `extension/src/test/e2e/`（端到端）。
- `/chat` 保持非流式契约；新增流式能力统一走 `/chat/stream`，并复用相同 `thread_id` 语义。
- 评估脚本需固定数据集版本并落盘结果文件，保证跨版本可复现对比。
- 涉及确认流程时，以后端图状态为唯一真源，前端只负责展示与回传确认事件。

---

## v0.1 — MVP (LLMChain + Extension骨架)

> 目标: Python backend 可回答问题+执行命令，VS Code Extension 可转发请求并执行 VS Code 命令
> 当前落地目录口径：`backend/tests/unit`、`backend/tests/integration`、`tests/e2e`、`extension/src/test/suite`

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
- Create: `backend/tests/integration/test_llm_real.py`
- Create: `backend/src/config.py`

**验收:**
```bash
cd backend && pytest tests/integration/test_llm_real.py -v -m integration
```
预期输出: `PASSED` (调用 GLM-4.7, 得到非空回复)

---

### F03 — 意图分类器 (LLMChain)

**commit:** `feat: add intent classifier using LLMChain`

**文件:**
- Create: `backend/src/chains/intent_classifier.py`
- Create: `backend/tests/unit/test_intent_classifier.py`

**验收:**
```bash
pytest tests/unit/test_intent_classifier.py -v
```
预期: 输入"帮我编译"→ `{"type": "action", "command": "hispark-studio.build"}`
预期: 输入"如何安装SDK"→ `{"type": "answer"}`

---

### F04 — RetrievalQA 链 (知识问答)

**commit:** `feat: add RetrievalQA chain with in-memory Chroma`

**文件:**
- Create: `backend/src/chains/qa_chain.py`
- Create: `backend/tests/fixtures/sample_docs.md` (5条示例文档)
- Create: `backend/tests/unit/test_qa_chain.py`

**验收:**
```bash
pytest tests/unit/test_qa_chain.py -v
```
预期: 查询 "BS21芯片支持什么" → 包含 sample_docs 中的内容

---

### F05 — /chat API 端点

**commit:** `feat: add FastAPI /chat endpoint`

**文件:**
- Create: `backend/src/api/main.py`
- Create: `backend/src/api/models.py`
- Create: `backend/tests/unit/test_api.py`

**验收:**
```bash
pytest tests/unit/test_api.py -v
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
- Create: `extension/src/test/suite/chatPanel.test.ts`

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
- Create: `extension/src/test/suite/apiClient.test.ts`

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
- Create: `extension/src/test/suite/commandExecutor.test.ts`

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
- Modify: `extension/src/test/suite/commandExecutor.test.ts`（补充确认分支用例）

**验收:**
```bash
npm test
```
预期: `requires_confirmation: true` 的命令（flash/portionOfBurn）触发 `vscode.window.showWarningMessage` 测试 PASSED

---

### F12 — 跨栈集成测试

**commit:** `test: add backend E2E tests for v0.1 API contract`

**文件:**
- Create: `tests/e2e/test_e2e_v01.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v01.py -v
```
预期:
- GET `/health` 返回 200
- 发送 "编译项目"/"烧录固件" 返回正确 action JSON
- 缺失 `message` 字段返回 422

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

## v0.2 — LCEL 重构 + SSE 流式 + Prompt 版本管理 + API 契约门禁

> 目标: 将所有链改写为 LCEL pipe 风格，支持流式输出，提取 Prompt 到版本化文件，锁定 API 契约

### F15 — 意图分类器 LCEL 重构

**commit:** `refactor(F15): rewrite intent classifier as LCEL chain`

**文件:**
- Modify: `backend/src/chains/intent_classifier.py`
- Modify: `backend/tests/unit/test_intent_classifier.py`

**验收:**
```bash
pytest tests/unit/test_intent_classifier.py -v
```
预期: 所有测试 PASSED，链使用 `prompt | llm | JsonOutputParser()`

---

### F16 — RAG 链 LCEL 重构 + 会话记忆

**commit:** `refactor(F16): rewrite QA chain as LCEL pipeline with RunnableWithMessageHistory`

**文件:**
- Modify: `backend/src/chains/qa_chain.py`
- Modify: `backend/tests/unit/test_qa_chain.py`

**验收:**
```bash
pytest tests/unit/test_qa_chain.py -v
```
预期: 所有测试 PASSED，链使用 `RunnablePassthrough | prompt | llm | StrOutputParser()` 并由 `RunnableWithMessageHistory` 包装，`answer_question` 接受 `session_id` 参数

---

### F17 — Prompt 版本管理

**commit:** `feat(F17): extract prompts to versioned prompt files`

**文件:**
- Create: `backend/src/prompts/intent_v1.py`
- Create: `backend/src/prompts/qa_v1.py`
- Modify: `backend/src/chains/intent_classifier.py` (从 prompts/ 导入)
- Modify: `backend/src/chains/qa_chain.py` (从 prompts/ 导入)

**验收:**
```bash
python -c "from src.prompts.intent_v1 import INTENT_PROMPT; print('ok')"
```
预期: `ok`；`intent_classifier.py` 与 `qa_chain.py` 不含内联 prompt 字符串

---

### F18 — SSE 流式端点

**commit:** `feat(F18): add SSE streaming endpoint /chat/stream`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/unit/test_api_stream.py`

**验收:**
```bash
pytest tests/unit/test_api_stream.py -v
```
预期: `httpx` 异步客户端接收 SSE 事件流，逐块输出文本 PASSED；事件数据包含 `thread_id` 与增量文本字段

---

### F19 — Webview 流式显示

**commit:** `feat(F19): add streaming display in Webview (EventSource)`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Modify: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/test/suite/streaming.test.ts`

**验收:**
```bash
npm test
```
预期: EventSource mock 测试 PASSED，文字逐步追加到 DOM

---

### F20 — 流式集成测试

**commit:** `test(F20): integration test for streaming (FastAPI SSE + httpx)`

**文件:**
- Create: `tests/e2e/test_e2e_v02_stream.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v02_stream.py -v
```
预期: 完整流式响应接收测试 PASSED

---

### F21 — API 契约门禁

**commit:** `test(F21): add API contract tests for /chat and /chat/stream`

**文件:**
- Create: `backend/tests/integration/test_api_contract.py`

**验收:**
```bash
cd backend && pytest tests/integration/test_api_contract.py -v
```
预期: `/chat` 与 `/chat/stream` 的字段名、类型、状态码、错误码校验全部 PASSED

---

### F22 — git tag v0.2

**commit:** `chore(F22): tag v0.2 LCEL + streaming`

---

## v0.3 — LangSmith + LLM-as-a-Judge + 性能基线 + Docker

> 目标: 全链路可观测，评估框架自动化，服务容器化

> **已知遗留 bug（v0.3 开发时修复）：** `stream-bubble` id 未清理导致多次流式请求内容污染，详见 `docs/changelogs/v0.2-retrospective.md` 第九节。

### F23 — LangSmith 链路追踪

**commit:** `feat(F23): add LangSmith tracing with @traceable decorator`

**文件:**
- Modify: `backend/src/chains/intent_classifier.py`
- Modify: `backend/src/chains/qa_chain.py`
- Modify: `backend/.env.example` (添加 4 个 LANGSMITH_ 变量)
- Create: `backend/tests/unit/test_langsmith_trace.py`

**验收:**
```bash
pytest tests/unit/test_langsmith_trace.py -v
```
预期: 调用链后可在 LangSmith 控制台看到 trace（smoke test，实际验收手动查看）

---

### F24 — LLM-as-a-Judge 评估器

**commit:** `feat(F24): add LLM-as-a-Judge evaluator (Faithfulness + Answer Relevancy)`

**文件:**
- Create: `backend/src/evaluation/llm_judge.py`
- Create: `backend/tests/unit/test_llm_judge.py`

**验收:**
```bash
pytest tests/unit/test_llm_judge.py -v
```
预期: 给定 question/answer/context → 返回 0-1 分数 PASSED

---

### F25 — 自动评估脚本

**commit:** `feat(F25): add evaluation runner script with JSON report`

**文件:**
- Create: `backend/scripts/eval_runner.py`
- Create: `docs/evaluation/results/v0.3-llm-judge.json`

**验收:**
```bash
python scripts/eval_runner.py --dataset docs/evaluation/dataset.json
```
预期: 输出包含每条 QA 的 faithfulness/answer_relevancy 分数，保存 JSON 报告

---

### F26 — 性能与成本基线

**commit:** `perf(F26): add latency and token cost baseline script`

**文件:**
- Create: `backend/scripts/eval_perf_cost.py`
- Create: `docs/evaluation/results/v0.3-perf-cost.json`

**验收:**
```bash
cd backend && python scripts/eval_perf_cost.py
```
预期: 输出并落盘 10 条查询的 p95 延迟与 token 消耗统计

---

### F27 — Docker 部署流水线

**commit:** `feat(F27): add Dockerfile and docker-compose for backend`

**文件:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Modify: `backend/.env.example` (补充容器运行所需变量)

**验收:**
```bash
docker compose up --build -d
curl http://localhost:8000/health
```
预期: `{"status": "ok"}`

> **CI 接入时机**：F27 完成后在同一版本（v0.3）接入 GitHub Actions，
> `xvfb-run` 解决 Extension E2E 显示器问题，ZHIPU_API_KEY 配置为 Repository Secret。
> Extension E2E 不进 Docker 容器，始终在 runner 宿主机执行。

---

### F28 — Webview 对话历史 + 来源展示

**commit:** `feat(F28): show conversation history and source citations in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Modify: `extension/src/webview/ChatPanel.ts`
- Create: `extension/src/test/suite/sourceDisplay.test.ts`

**验收:**
```bash
npm test
```
预期: sources 数组正确渲染为引用列表 PASSED

---

### F29 — RAGAS TestsetGenerator 脚本

**commit:** `feat(F29): add RAGAS testset generator script from HiSpark docs`

**文件:**
- Create: `backend/scripts/generate_docqa.py`
- Create: `docs/evaluation/README.md` (说明如何运行生成)

**验收:**
```bash
python scripts/generate_docqa.py --input docs/hispark-readme.md --output docs/evaluation/docqa_generated.json --count 20
```
预期: 生成 20 条 QA 对，JSON 格式

---

### F30 — 真实 HiSpark 文档入库

**commit:** `feat(F30): ingest real HiSpark documentation into Chroma knowledge base`

**文件:**
- Create: `backend/scripts/ingest_docs.py` (读取 docs/hispark/ 目录，分块，写入 Chroma)
- Create: `docs/hispark/` (存放真实 HiSpark 官方文档，MD/PDF 格式)
- Modify: `backend/src/chains/qa_chain.py` (build_retriever 指向真实 Chroma 持久化路径)
- Create: `docs/evaluation/results/v0.3-real-docs-baseline.json` (用真实文档重跑 F25 评估脚本的结果)

**验收:**
```bash
cd backend && python scripts/ingest_docs.py --input ../docs/hispark/ --persist ./chroma_db
pytest tests/unit/test_qa_chain.py -v
python scripts/eval_runner.py --dataset docs/evaluation/docqa_generated.json
```
预期: 文档入库成功；QA chain 单测 PASSED；评估脚本产出含真实指标的 JSON（与 sample_docs 基线可对比）

> **里程碑意义**: 此 Feature 之后，所有评估指标均基于真实内容，调优过程具备可比性。

---

### F31 — git tag v0.3

**commit:** `chore(F31): tag v0.3 LangSmith + evaluation + Docker + real docs`

---

## v0.4 — 进阶 RAG + RAGAS + K8s 编排

> 目标: 生产级检索管道，量化评估质量，服务可编排部署

### F32 — BGE 向量 + FAISS 存储

**commit:** `feat(F32): add BGE embeddings with FAISS vector store`

**文件:**
- Create: `backend/src/retrieval/vector_store.py`
- Create: `backend/tests/unit/test_vector_store.py`

**验收:**
```bash
pytest tests/unit/test_vector_store.py -v
```
预期: 文档索引+检索测试 PASSED，Top-K 结果相关

---

### F33 — BM25 稀疏检索

**commit:** `feat(F33): add BM25 sparse retriever`

**文件:**
- Create: `backend/src/retrieval/bm25_retriever.py`
- Create: `backend/tests/unit/test_bm25.py`

**验收:**
```bash
pytest tests/unit/test_bm25.py -v
```
预期: BM25 检索关键词精确匹配测试 PASSED

---

### F34 — RRF 融合检索

**commit:** `feat(F34): add RRF fusion retriever (BM25 + vector)`

**文件:**
- Create: `backend/src/retrieval/hybrid_retriever.py`
- Create: `backend/tests/unit/test_hybrid_retriever.py`

**验收:**
```bash
pytest tests/unit/test_hybrid_retriever.py -v
```
预期: 融合排序结果优于单一检索 PASSED

---

### F35 — BGE-Reranker 精排

**commit:** `feat(F35): add BGE-Reranker cross-encoder for result reranking`

**文件:**
- Create: `backend/src/retrieval/reranker.py`
- Create: `backend/tests/unit/test_reranker.py`

**验收:**
```bash
pytest tests/unit/test_reranker.py -v
```
预期: Reranker 对候选结果重排，相关性分数更高 PASSED

---

### F36 — 语义分块

**commit:** `feat(F36): add semantic chunking strategy`

**文件:**
- Create: `backend/src/ingestion/chunker.py`
- Create: `backend/tests/unit/test_chunker.py`

**验收:**
```bash
pytest tests/unit/test_chunker.py -v
```
预期: 固定/滑动/语义三种分块策略各自单测 PASSED

---

### F37 — RAGAS 评估管道

**commit:** `feat(F37): add RAGAS evaluation pipeline (4 metrics)`

**文件:**
- Create: `backend/src/evaluation/ragas_eval.py`
- Create: `backend/tests/unit/test_ragas_eval.py`
- Create: `docs/evaluation/results/v0.4-ragas.json`

**验收:**
```bash
pytest tests/unit/test_ragas_eval.py -v
python scripts/eval_runner.py --mode ragas
```
预期: Context Recall/Precision/Faithfulness/Answer Relevancy 四项指标有值；结果落盘后加入 gate-feature.sh 门禁

---

### F38 — K8s 编排

**commit:** `feat(F38): add Kubernetes manifests for backend deployment`

**文件:**
- Create: `k8s/deployment.yaml`
- Create: `k8s/service.yaml`
- Create: `k8s/configmap.yaml`
- Create: `k8s/hpa.yaml`

**验收:**
```bash
kubectl apply -f k8s/
kubectl get pods
curl http://$(kubectl get svc hispark-backend -o jsonpath='{.spec.clusterIP}'):8000/health
```
预期: Pod Running，/health 返回 200

---

### F39 — 知识库上传 API

**commit:** `feat(F39): add knowledge base upload endpoint (POST /kb/upload)`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/unit/test_kb_api.py`

**验收:**
```bash
pytest tests/unit/test_kb_api.py -v
```
预期: 上传 PDF/MD 文件后可检索到内容 PASSED

---

### F40 — Webview 知识库上传 UI

**commit:** `feat(F40): add knowledge base upload UI in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/suite/kbUpload.test.ts`

**验收:**
```bash
npm test
```
预期: 文件选择器调用 POST /kb/upload 测试 PASSED

---

### F41 — RAG 集成测试

**commit:** `test(F41): integration test for full RAG pipeline (upload → query → evaluate)`

**文件:**
- Create: `tests/e2e/test_e2e_v04_rag.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v04_rag.py -v
```
预期: 上传文档 → 提问 → RAGAS 评分全流程 PASSED

---

### F42 — git tag v0.4

**commit:** `chore(F42): tag v0.4 advanced RAG + RAGAS + K8s`

---

## v0.5 — LangGraph + Agentic RAG + 降级回滚

> 目标: 引入状态图，实现 retrieve→grade→generate/websearch 自适应流程，添加节点级降级策略

### F43 — AgentState 定义

**commit:** `feat(F43): define AgentState for LangGraph`

**文件:**
- Create: `backend/src/agent/state.py`
- Create: `backend/tests/unit/test_agent_state.py`

**验收:**
```bash
pytest tests/unit/test_agent_state.py -v
```
预期: AgentState TypedDict 序列化/反序列化 PASSED

---

### F44 — retrieve 节点

**commit:** `feat(F44): add retrieve node to LangGraph`

**文件:**
- Create: `backend/src/agent/nodes/retrieve.py`
- Create: `backend/tests/unit/test_node_retrieve.py`

**验收:**
```bash
pytest tests/unit/test_node_retrieve.py -v
```
预期: 给定 query → 返回 docs 列表 PASSED

---

### F45 — grade 节点 + 条件边

**commit:** `feat(F45): add grade node and conditional edge (relevant/not_relevant)`

**文件:**
- Create: `backend/src/agent/nodes/grade.py`
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/unit/test_node_grade.py`

**验收:**
```bash
pytest tests/unit/test_node_grade.py -v
```
预期: 相关文档 → 路由到 generate；不相关 → 路由到 web_search PASSED

---

### F46 — web_searcher Tool

**commit:** `feat(F46): add web_searcher tool (Tavily)`

**文件:**
- Create: `backend/src/agent/tools/web_searcher.py`
- Create: `backend/tests/unit/test_web_searcher.py`

**验收:**
```bash
pytest tests/unit/test_web_searcher.py -v
```
预期: 搜索 "HiSpark BS21 chip" → 返回结果列表 PASSED (mock Tavily)

---

### F47 — generate 节点

**commit:** `feat(F47): add generate node with source attribution`

**文件:**
- Create: `backend/src/agent/nodes/generate.py`
- Create: `backend/tests/unit/test_node_generate.py`

**验收:**
```bash
pytest tests/unit/test_node_generate.py -v
```
预期: 给定 docs + query → 生成含来源的回答 PASSED

---

### F48 — StateGraph 组装

**commit:** `feat(F48): assemble LangGraph StateGraph (retrieve→grade→generate/websearch)`

**文件:**
- Create: `backend/src/agent/graph.py`
- Create: `backend/tests/unit/test_graph.py`

**验收:**
```bash
pytest tests/unit/test_graph.py -v
```
预期: 完整 graph 编译成功，两条路径（有文档/无文档）各自测试 PASSED

---

### F49 — 工具调用可视化

**commit:** `feat(F49): stream node events to Webview for tool call visualization`

**文件:**
- Modify: `backend/src/api/main.py`
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/suite/toolVisualization.test.ts`

**验收:**
```bash
npm test
```
预期: SSE 事件包含 `{type: "node_start", node: "retrieve"}` 等，Webview 正确显示 PASSED

---

### F50 — LangGraph 集成测试

**commit:** `test(F50): integration test for LangGraph agent (two paths)`

**文件:**
- Create: `tests/e2e/test_e2e_v05_graph.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v05_graph.py -v
```
预期: doc 路径 + web 路径各自端到端测试 PASSED

---

### F51 — 降级与回滚策略

**commit:** `feat(F51): add per-node fallback strategy in LangGraph`

**文件:**
- Modify: `backend/src/agent/nodes/grade.py`
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/integration/test_fallbacks.py`

**验收:**
```bash
cd backend && pytest tests/integration/test_fallbacks.py -v
```
预期: web_search 节点超时时自动降级到 RAG 路径；LLM 异常时返回结构化错误，PASSED

---

### F52 — RAGAS 评估更新 (LangGraph)

**commit:** `eval(F52): update RAGAS evaluation on LangGraph agent`

**文件:**
- Create: `docs/evaluation/results/v0.5-ragas.json`

**验收:**
```bash
python scripts/eval_runner.py --mode ragas --version v0.5
```
预期: 对比 v0.4 评估报告，记录指标变化（不预设结论）

---

### F53 — git tag v0.5

**commit:** `chore(F53): tag v0.5 LangGraph + Agentic RAG`

---

## v0.6 — Checkpoint + HITL

> 目标: 记忆跨轮对话，危险操作须人工确认后恢复

### F54 — Checkpoint 基线（MemorySaver）

**commit:** `feat(F54): add MemorySaver checkpoint with thread_id session isolation`

**文件:**
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/unit/test_checkpoint.py`

**验收:**
```bash
pytest tests/unit/test_checkpoint.py -v
```
预期: 同一进程内同一 thread_id 两次对话共享上下文，不同 thread_id 隔离 PASSED（跨进程持久化在 F80 加强）

---

### F55 — interrupt_before HITL 节点

**commit:** `feat(F55): add interrupt_before for flash/portionOfBurn nodes`

**文件:**
- Create: `backend/src/agent/nodes/flash.py`
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/unit/test_hitl_interrupt.py`

**验收:**
```bash
pytest tests/unit/test_hitl_interrupt.py -v
```
预期: 烧录意图 → graph 暂停，state 为 INTERRUPTED PASSED

---

### F56 — /chat/confirm 恢复端点

**commit:** `feat(F56): add /chat/confirm endpoint to resume interrupted graph`

**文件:**
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/unit/test_hitl_resume.py`

**验收:**
```bash
pytest tests/unit/test_hitl_resume.py -v
```
预期: 确认后调用 `graph.invoke(None, config)` 恢复执行 PASSED

---

### F57 — VS Code 确认对话框

**commit:** `feat(F57): add VS Code modal confirmation dialog for HITL`

**文件:**
- Modify: `extension/src/executor/CommandExecutor.ts`
- Create: `extension/src/test/suite/hitlModal.test.ts`

**验收:**
```bash
npm test
```
预期: 收到 `requires_confirmation: true` → showWarningMessage → POST /chat/confirm PASSED
补充约束: 前端确认框只消费后端中断事件，后端 graph 状态是唯一确认真源

---

### F58 — HITL 集成测试

**commit:** `test(F58): integration test for full HITL flow (interrupt → confirm → resume)`

**文件:**
- Create: `tests/e2e/test_e2e_v06_hitl.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v06_hitl.py -v
```
预期: 烧录流程完整中断-恢复-执行 PASSED

---

### F59 — git tag v0.6

**commit:** `chore(F59): tag v0.6 Checkpoint + HITL`

---

## v0.7 — Multi-Agent Supervisor

> 目标: 按意图路由到专职 Agent

### F60 — Supervisor 路由器

**commit:** `feat(F60): add Supervisor agent for intent routing (DevOps vs Knowledge)`

**文件:**
- Create: `backend/src/agent/supervisor.py`
- Create: `backend/tests/unit/test_supervisor.py`

**验收:**
```bash
pytest tests/unit/test_supervisor.py -v
```
预期: "编译"→ DevOps；"如何安装SDK"→ Knowledge PASSED

---

### F61 — DevOps Agent 子图

**commit:** `feat(F61): add DevOps Agent subgraph (build/flash/analysis commands)`

**文件:**
- Create: `backend/src/agent/agents/devops_agent.py`
- Create: `backend/tests/unit/test_devops_agent.py`

**验收:**
```bash
pytest tests/unit/test_devops_agent.py -v
```
预期: 处理编译/烧录/分析意图，返回正确 action JSON PASSED

---

### F62 — Knowledge Agent 子图

**commit:** `feat(F62): add Knowledge Agent subgraph (RAG + web search)`

**文件:**
- Create: `backend/src/agent/agents/knowledge_agent.py`
- Create: `backend/tests/unit/test_knowledge_agent.py`

**验收:**
```bash
pytest tests/unit/test_knowledge_agent.py -v
```
预期: 处理知识问答意图，RAG 检索+生成 PASSED

---

### F63 — Webview 多 Agent 状态显示

**commit:** `feat(F63): show active agent indicator in Webview`

**文件:**
- Modify: `extension/src/webview/chat.html`
- Create: `extension/src/test/suite/agentIndicator.test.ts`

**验收:**
```bash
npm test
```
预期: SSE 事件 `{type: "agent_switch", agent: "devops"}` 在 Webview 中正确显示 PASSED

---

### F64 — Multi-Agent 集成测试

**commit:** `test(F64): integration test for multi-agent routing`

**文件:**
- Create: `tests/e2e/test_e2e_v07_multiagent.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v07_multiagent.py -v
```
预期: 混合意图对话 → 正确路由到两个 Agent PASSED

---

### F65 — git tag v0.7

**commit:** `chore(F65): tag v0.7 Multi-Agent Supervisor`

---

## v0.8 — MCP Client + MCP Server

> 目标: Python Agent 作为 MCP Client 调用外部工具；HiSpark Extension 作为 MCP Server

### F66 — Python MCP Client (filesystem)

**commit:** `feat(F66): add MCP client connecting to filesystem MCP server`

**文件:**
- Create: `backend/src/mcp/client.py`
- Create: `backend/tests/unit/test_mcp_client.py`

**验收:**
```bash
pytest tests/unit/test_mcp_client.py -v
```
预期: 通过 MCP 协议读取本地文件列表 PASSED (mock server)

---

### F67 — Python MCP Client (web-search)

**commit:** `feat(F67): add MCP client connecting to web-search MCP server`

**文件:**
- Modify: `backend/src/mcp/client.py`
- Create: `backend/tests/unit/test_mcp_websearch.py`

**验收:**
```bash
pytest tests/unit/test_mcp_websearch.py -v
```
预期: 通过 MCP 协议执行 web 搜索 PASSED (mock server)

---

### F68 — HiSpark MCP Server 初始化

**commit:** `feat(F68): add HiSpark MCP Server to Extension`

**文件:**
- Create: `extension/src/mcp/HiSparkMcpServer.ts`
- Create: `extension/src/test/suite/mcpServer.test.ts`

**验收:**
```bash
npm test
```
预期: MCP Server 启动，响应 tools/list 请求 PASSED

---

### F69 — MCP Tool: hispark_build/rebuild/clean

**commit:** `feat(F69): expose hispark_build/rebuild/clean as MCP Tools`

**文件:**
- Modify: `extension/src/mcp/HiSparkMcpServer.ts`
- Create: `extension/src/test/suite/mcpTools.test.ts`

**验收:**
```bash
npm test
```
预期: MCP Client 调用 `hispark_build` Tool → `vscode.commands.executeCommand('hispark-studio.build')` PASSED

---

### F70 — MCP Tool: hispark_flash/stackAnalysis/imageAnalysis

**commit:** `feat(F70): expose flash/stackAnalysis/imageAnalysis as MCP Tools`

**文件:**
- Modify: `extension/src/mcp/HiSparkMcpServer.ts`

**验收:**
```bash
npm test
```
预期: flash Tool 包含 `requires_confirmation: true` 元数据 PASSED

---

### F71 — Agent 运行时发现 HiSpark MCP Tools

**commit:** `feat(F71): Agent discovers HiSpark commands via MCP at runtime`

**文件:**
- Modify: `backend/src/agent/graph.py`
- Create: `backend/tests/unit/test_mcp_tool_discovery.py`

**验收:**
```bash
pytest tests/unit/test_mcp_tool_discovery.py -v
```
预期: Agent 启动时调用 `tools/list` 获取可用 HiSpark 工具，无需硬编码 PASSED

---

### F72 — MCP 对比文档

**commit:** `docs(F72): add MCP vs Function Calling comparison note`

**文件:**
- Create: `docs/notes/mcp-vs-function-calling.md`

**内容要点:** 运行时发现 vs 编译时耦合、松耦合体现点、面经叙述角度

---

### F73 — MCP 集成测试

**commit:** `test(F73): integration test for MCP (Agent ↔ HiSpark MCP Server)`

**文件:**
- Create: `tests/e2e/test_e2e_v08_mcp.py`

**验收:**
```bash
pytest tests/e2e/test_e2e_v08_mcp.py -v
```
预期: 先通过协议层 contract test（tools/list, tools/call）再跑端到端链路，最终 Python Agent 通过 MCP 调用 HiSpark Tool 并成功执行 VS Code 命令

---

### F74 — RAGAS 最终评估

**commit:** `eval(F74): final RAGAS evaluation on full agent (v0.8)`

**文件:**
- Create: `docs/evaluation/results/v0.8-ragas-final.json`

**验收:**
```bash
python scripts/eval_runner.py --mode ragas --version v0.8
```
预期: 对比 v0.4/v0.5 历史报告，记录完整演进曲线

---

### F75 — git tag v0.8

**commit:** `chore(F75): tag v0.8 MCP integration`

---

## v1.0 — 发布准备

### F76 — OpenAPI Spec 完善

**commit:** `docs(F76): finalize OpenAPI spec for /chat and /kb endpoints`

**文件:**
- Create: `docs/api-spec.yaml`

**验收:**
```bash
python -c "import yaml; yaml.safe_load(open('docs/api-spec.yaml'))"
```
预期: YAML 合法，所有端点文档完整

---

### F77 — .vsix 打包

**commit:** `chore(F77): package VS Code extension as .vsix`

**文件:**
- Modify: `extension/package.json` (publisher, version, icon)

**验收:**
```bash
cd extension && npx vsce package
ls *.vsix
```
预期: 生成 `hispark-ai-agent-1.0.0.vsix`

---

### F78 — README 更新

**commit:** `docs(F78): update README with architecture diagram and version history`

**文件:**
- Modify: `README.md`

---

### F79 — 发布说明与变更日志冻结

**commit:** `docs(F79): finalize changelog and release checklist for v1.0`

**文件:**
- Create: `docs/changelogs/v1.0-release-notes.md`
- Create: `docs/changelogs/v1.0-checklist.md`

**验收:**
```bash
python -c "from pathlib import Path; print(Path('docs/changelogs/v1.0-release-notes.md').exists() and Path('docs/changelogs/v1.0-checklist.md').exists())"
```
预期: 输出 `True`

---

### F80 — Checkpoint 持久化升级（Sqlite/Postgres）

**commit:** `feat(F80): add durable checkpoint saver for cross-process resume`

**文件:**
- Modify: `backend/src/agent/graph.py`
- Create: `backend/src/agent/checkpoint_store.py`
- Create: `backend/tests/integration/test_checkpoint_persistence.py`

**验收:**
```bash
cd backend && pytest tests/integration/test_checkpoint_persistence.py -v
```
预期: 重启进程后，同一 `thread_id` 可恢复中断状态并继续执行

---

### F81 — 安全基线门禁（Tool + KB）

**commit:** `feat(F81): add security baseline for tool whitelist and kb upload limits`

**文件:**
- Modify: `backend/src/api/main.py`
- Modify: `backend/src/agent/tools/`
- Create: `backend/tests/unit/test_security_baseline.py`

**验收:**
```bash
cd backend && pytest tests/unit/test_security_baseline.py -v
```
预期: 非白名单工具拒绝执行；KB 上传类型/大小/超时限制生效

---

### F82 — git tag v1.0

**commit:** `chore(F82): tag v1.0 production release`

---

## 快速索引

| Feature | 版本 | 关键词 |
|---------|------|-------|
| F01–F06 | v0.1 | Python backend 初始化 |
| F07–F11 | v0.1 | Extension 骨架 + 命令执行器 |
| F12–F14 | v0.1 | 集成测试 + 基线评估 |
| F15–F17 | v0.2 | LCEL 重构 + Prompt 版本管理 |
| F18–F22 | v0.2 | SSE 流式 + API 契约门禁 |
| F23–F27 | v0.3 | LangSmith + 评估 + 性能基线 + Docker |
| F28–F31 | v0.3 | Webview 来源展示 + RAGAS 数据集 + 真实文档入库 |
| F32–F38 | v0.4 | 进阶 RAG + RAGAS + K8s |
| F39–F42 | v0.4 | KB 上传 + RAG 集成测试 |
| F43–F53 | v0.5 | LangGraph + Agentic RAG + 降级回滚 |
| F54–F59 | v0.6 | Checkpoint + HITL |
| F60–F65 | v0.7 | Multi-Agent Supervisor |
| F66–F75 | v0.8 | MCP Client + Server |
| F76–F82 | v1.0 | 发布准备 |

**总计: 82 个 git 提交节点**
