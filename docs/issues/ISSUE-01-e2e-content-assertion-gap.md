# ISSUE-01: E2E 流式回答内容断言缺口

| 字段 | 内容 |
|------|------|
| **状态** | 已知缺口，待 v0.3 修复 |
| **发现版本** | v0.2 |
| **计划修复** | v0.3 F23/F24（LangSmith + LLM-as-a-Judge） |
| **文件** | `extension/src/test/e2e/webview.playwright.ts` |
| **发现日期** | 2026-03-11 |

---

## 问题描述

E2E 流式测试（Phase 2 Playwright）中，对 `/chat/stream` 返回的知识问答内容，原断言通过关键词列表（芯片型号）来验证 RAG 是否召回了正确文档：

```typescript
// 原断言（已废弃）
const chipKeywords = ['BS20', 'BS21', 'WS63', '芯片', '型号', '支持'];
const hasChipKeyword = chipKeywords.some(kw => streamText.includes(kw));
assert.ok(hasChipKeyword, ...);
```

该断言在 3 次重复执行中出现 1 次失败（成功率约 2/3），属于 flaky test。

---

## 根因分析

LLM 偶发性地返回极短泛化回答（如 `"HiSpark Studio for VS Code 插件"`），未包含任何芯片型号关键词。根因是 RAG 检索结果不稳定，偶尔未能将芯片型号文档片段送入 LLM 上下文，导致 LLM 仅凭通用知识给出一句话回答。

关键词断言本身也存在设计问题：原列表包含 `Hi3861`、`Hi3516` 等在 `sample_docs.md` 中并不存在的型号，以及过于宽泛的 `支持` 一词（问题本身即含该词）。

---

## 临时处理（v0.2 现状）

将内容断言降级为纯长度检查，仅验证流式机制本身正常工作：

```typescript
// 当前断言（临时）
assert.ok(streamText.length > 20,
    `Stream answer too short (streaming mechanism broken?), got: ${streamText.slice(0, 200)}`);
```

**质量缺口**：RAG 召回准确性、LLM 回答相关性不再被 E2E gate 覆盖。

---

## 修复计划

在 v0.3 F23/F24 中接入 LangSmith + LLM-as-a-Judge 后，用评估器替代关键词断言：

- F23 LangSmith 追踪：每次 E2E 调用自动生成 trace
- F24 LLM-as-a-Judge：对 trace 中的 `answer` 字段自动评估 Answer Relevancy / Faithfulness
- 届时删除 `webview.playwright.ts` 中的临时长度断言，或保留作为基础烟雾测试

---

## 关联

- Roadmap: `docs/plans/2026-03-02-feature-roadmap.md` v0.3 节
- 流式 E2E 测试: `extension/src/test/e2e/webview.playwright.ts` ~L138
