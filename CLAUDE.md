# HiSpark AI Agent — Claude Code 项目说明

## 项目简介

为 HiSpark Studio for VS Code 插件开发的 AI Agent，通过自然语言控制嵌入式开发全流程，同时作为 LangChain/LangGraph/RAG/LangSmith 技术栈的演进式学习项目。

## 技术栈

- **Backend**: Python 3.11+, LangChain 0.3.x, LangGraph 0.2.x, FastAPI, Chroma
- **LLM**: 智谱 GLM-4.7 / GLM-5（OpenAI-compatible API）
- **Extension**: TypeScript, VS Code Extension API（v0.8+）
- **测试**: pytest, RAGAS, LangSmith

## 开发原则

1. **TDD 严格执行**: 先写测试（看到 FAILED），再写实现
2. **演进式开发**: 每个版本有 git tag，有 changelog，有痛点记录
3. **YAGNI**: 不为未来版本提前实现功能
4. **每个版本 = 一个面经学习单元**: 见 `docs/plans/2026-02-28-design.md`

## 当前版本

见 `git tag` 列表，当前开发版本见最新 tag。

## LLM 配置

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="glm-4-flash",
    openai_api_key=os.getenv("ZHIPU_API_KEY"),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
)
```

## 关键文档

- 设计文档: `docs/plans/2026-02-28-design.md`
- 面经覆盖地图: 设计文档第 8 节
- 每版本说明: `docs/changelogs/vX.Y.md`
