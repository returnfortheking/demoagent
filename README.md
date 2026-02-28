# HiSpark AI Agent

> 用自然语言控制嵌入式开发全流程的 AI Agent，同时是 LangChain 技术栈演进式学习项目。

## 快速开始

```bash
cd backend
cp .env.example .env   # 填入 ZHIPU_API_KEY
pip install uv
uv sync
uv run pytest          # 跑测试
uv run python -m src.api.main  # 启动后端
```

## 演进版本

| Tag | 核心技术 | 面经覆盖 |
|-----|---------|---------|
| v0.1 | 旧版 LangChain (LLMChain + RetrievalQA) | Q2 Q3 Q8 Q14 |
| v0.2 | LCEL 重构 | Q1 |
| v0.3 | LangSmith Tracing + 评估 | Q6 Q7 |
| v0.4 | 进阶 RAG (混合检索 + Reranker + RAGAS) | Q8 Q9 Q10 |
| v0.5 | LangGraph Agentic RAG (ReAct) | Q4 Q11 Q12 |
| v0.6 | Checkpoint + HITL | Q5 Q15 |
| v0.7 | Multi-Agent Supervisor | Q13 |
| v0.8 | VS Code Extension | Q16思路 |

详见 [设计文档](docs/plans/2026-02-28-design.md)
