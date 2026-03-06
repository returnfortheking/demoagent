# 模块 03：LangChain 核心概念（融合版）

> 基于 `hispark-ai-agent v0.1` 真实代码讲解  
> 核心文件：`backend/src/config.py`、`backend/src/chains/intent_classifier.py`

---

## 这份融合版怎么读

这份笔记把两种风格合在一起：

- **结构化复述**：沿用“是什么 / 在哪 / 走读 / 反例 / 面试表达”
- **机制细节**：补足 API 行为、参数语义、迁移信号和测试边界

目标：既能讲“工程决策”，也能讲“底层细节”。

---

## 第 1 讲：LangChain 在本项目里的角色

### 【是什么】

在 v0.1 里，LangChain 主要提供三层抽象：

1. `ChatOpenAI`：统一模型调用接口  
2. `PromptTemplate`：模板变量管理和渲染  
3. `LLMChain`：把 Prompt + LLM 组合成可调用单元

### 【项目里在哪】

- `backend/src/config.py`：`get_llm()`
- `backend/src/chains/intent_classifier.py`：`_prompt`、`_get_chain()`、`classify_intent()`
- `backend/src/api/main.py`：`/chat` 路由调用 `classify_intent()`

### 【代码走读】

`/chat` 的第一步就是意图分类：

```text
用户输入
  -> classify_intent
      -> action: 返回命令
      -> answer: 走 RAG
```

这让意图分类模块成为“流量路由器”。

### 【如果不这样写】

如果不用 LangChain，业务层要自己处理：

- Prompt 拼装
- HTTP 请求
- 输出解析
- 错误处理

功能能做，但可维护性和复用性更差。

### 【面试怎么说】

> “我在 v0.1 用 LangChain 把意图分类标准化：`ChatOpenAI` 做模型调用，`PromptTemplate` 做协议化 prompt，`LLMChain` 做调用编排。这样后续迁移 LCEL 时改动边界清晰。”

---

## 第 2 讲：`ChatOpenAI`——名字叫 OpenAI，但不只连 OpenAI

### 【是什么】

`ChatOpenAI` 是 LangChain 的“聊天模型客户端抽象”。  
底层只要是 OpenAI-compatible 接口，都能接。

### 【项目里在哪】

`backend/src/config.py`：

```python
def get_llm(model: str = "glm-4-flash") -> ChatOpenAI:
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise ValueError("ZHIPU_API_KEY environment variable is not set")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
        temperature=0.1,
    )
```

### 【代码走读】

关键点：

- `openai_api_base` 指向智谱兼容网关
- `temperature=0.1` 保持结构化输出稳定
- 缺 key 直接 fail fast（`ValueError`）

### 【如果不这样写】

如果每个模块都直接 `requests.post(...)`：

- 重复代码多
- 模型切换成本高
- 难与 LangChain 组件组合

### 【补充：为什么是工厂函数】

`get_llm()` 是一层集中配置：

- 统一管理 model/base_url/temperature
- 测试可 mock 这个函数
- 避免调用方散落配置

### 【面试怎么说】

> “我通过 `get_llm()` 做统一模型配置，业务层只依赖抽象，不关心具体厂商。底层换模型供应商时，优先改配置而不是改业务代码。”

---

## 第 3 讲：`PromptTemplate` vs f-string（重点）

### 【是什么】

两者不是互斥关系，而是层级不同：

- `f-string`：字符串语法工具
- `PromptTemplate`：可编排的模板对象

### 【项目里在哪】

`intent_classifier.py`：

```python
_prompt = PromptTemplate(
    input_variables=["message"],
    template=_PROMPT_TEMPLATE
)
```

### 【f-string 能不能“显式声明输入变量”？】

能，但方式不同：

```python
def build_prompt(message: str) -> str:
    return f"用户输入：{message}"
```

这确实有显式输入（函数参数）。  
但它缺少模板对象层的“可编排元数据”。

### 【为什么 PromptTemplate 在工程里更好】

| 维度 | f-string | PromptTemplate |
|---|---|---|
| 输入声明 | 通过函数参数 | `input_variables` 元数据 |
| 模板对象可复用 | 弱（通常是函数或字符串） | 强（模板对象可传递） |
| 与 LangChain 组合 | 需额外包装 | 原生可接 `LLMChain` / LCEL |
| 可观测/可追踪 | 需自建 | 更容易纳入链式追踪 |
| 部分变量绑定 | 自己写逻辑 | 支持 `partial(...)` |

### 【代码细节】

模板中 `{{` / `}}` 是字面花括号转义：

- `{message}`：变量占位符
- `{{` `}}`：输出 JSON 的实际花括号

### 【如果不这样写】

f-string 在小脚本没问题，但到链式系统会出现：

- 组合成本变高
- 模板契约分散
- 测试与替换困难

### 【面试怎么说】

> “f-string 能拼字符串，但 `PromptTemplate` 是可编排对象。它显式暴露输入变量、可复用、可组合，更适合接入链路和后续 LCEL 迁移。”

---

## 第 4 讲：`LLMChain` 组装与调用语义

### 【是什么】

`LLMChain` 把 Prompt 和 LLM 绑定成一个执行单元。

### 【项目里在哪】

`intent_classifier.py`：

```python
def _get_chain() -> LLMChain:
    global _chain
    if _chain is None:
        _chain = LLMChain(llm=get_llm(), prompt=_prompt)
    return _chain
```

### 【代码走读】

调用时：

```python
raw: str = _get_chain().run(message=message)
```

内部发生的是：

1. `PromptTemplate.format(message=...)`
2. LLM 调用
3. 返回字符串

### 【`.run()` vs `.invoke()`】

| 维度 | `.run()` | `.invoke()` |
|---|---|---|
| 状态 | 旧 API（deprecated） | 推荐 API |
| 输入 | 关键字参数 | 字典 |
| 输出 | 多为字符串 | 更统一（Runnable 体系） |

项目里故意保留 `.run()`，用于 v0.2 与 LCEL 对比。

### 【面试怎么说】

> “v0.1 保留 `LLMChain.run()` 是教学性决策，目的是在 v0.2 迁移到 LCEL 后形成新旧对照，能清楚解释迁移收益和风险。”

---

## 第 5 讲：懒加载与可测试性（`_get_chain` 模式）

### 【是什么】

`_get_chain()` 是“懒加载 + 模块级缓存”：

- 首次调用才创建 chain
- 后续复用已创建实例

### 【项目里在哪】

`intent_classifier.py`：

```python
_chain: LLMChain | None = None
```

### 【代码走读】

收益有两个：

1. import 过程不触发真实模型调用
2. 测试可 patch `_get_chain`，彻底绕开网络依赖

单测就是这样做的：

```python
mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)
```

### 【如果不这样写】

如果 patch 实例属性（如 `_chain.run`）：

- 在某些框架组合下稳定性差
- teardown 容易出现问题

这点你项目的事故文档也有记录：

- `docs/incidents/2026-03-04-chain-wrapper-in-production.md`

### 【面试怎么说】

> “我把真实链构建放在 `_get_chain()`，单测 patch 工厂函数而不是 patch 实例属性，能稳定隔离外部依赖，也更符合可测试性设计。”

---

## 第 6 讲：`classify_intent` 的防御式解析

### 【是什么】

LLM 输出不稳定，必须把它当“不可信输入”处理。

### 【项目里在哪】

`intent_classifier.py`（核心逻辑）：

```python
raw: str = _get_chain().run(message=message)
stripped = raw.strip()

if stripped.startswith("```"):
    ...

if not stripped.startswith("{"):
    raise ValueError(...)

result = json.loads(stripped)
```

### 【代码走读】

这段逻辑是三道防线：

1. Prompt 约束：要求纯 JSON
2. 代码净化：剥离 Markdown 代码块
3. 严格校验：不是裸 JSON 就抛错

API 层统一捕获：

```python
except ValueError as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### 【为什么不是“容错兜底返回 answer”】

因为那会把协议错误静默吞掉，线上难排查。  
这里选择“显式失败”，可观测性更好。

### 【测试对应】

`backend/tests/unit/test_intent_classifier.py` 明确覆盖：

- 纯文本输出 -> 抛 `ValueError`
- 带前缀 JSON -> 抛 `ValueError`

### 【面试怎么说】

> “我把 LLM 输出当外部脏输入来处理，先净化再校验，非法格式明确抛错并在 API 层统一映射为 500。这样故障可见、可测、可追踪。”

---

## 第 7 讲：为什么 v0.1 明知 deprecated 仍使用旧链

### 【是什么】

这不是忽视 warning，而是“阶段性取舍”。

### 【项目里依据】

- `README.md` 演进表：v0.1 旧版链，v0.2 LCEL
- 集成测试日志里可看到 deprecation warning（可作为迁移信号）

### 【代码走读】

策略是：

1. v0.1 先跑通功能与测试
2. v0.2 再迁移范式
3. 用同一业务场景对比前后实现

### 【如果一开始就上全部新方案】

- 学习和排障变量过多
- 难判断是业务问题还是框架迁移问题

### 【面试怎么说】

> “我保留旧版 API 作为基线，不是技术懒惰，而是工程控制变量：先验证业务正确，再做框架升级，迁移收益才能被量化。”

---

## 第 8 讲：LCEL 迁移预告（v0.2 方向）

### 【v0.1 现状】

- `PromptTemplate + LLMChain`
- `run()` 输出文本
- 手动 JSON 解析

### 【v0.2 目标（示意）】

```python
chain = prompt | llm | parser
result = chain.invoke({"message": message})
```

### 【收益】

1. 编排更清晰（管道式）
2. 与 streaming/并行能力更一致
3. 与新生态（Runnable）对齐

### 【风险】

1. 解析语义变化需要回归测试
2. Prompt 和 parser 可能要联动调整

---

## 第 9 讲：把“内容理解”和“工程理解”合在一起

### 内容层你要会讲

- `ChatOpenAI` 是统一模型调用抽象
- `PromptTemplate` 把输入和协议结构化
- `LLMChain` 完成调用编排

### 工程层你要会讲

- 为什么有 `get_llm()` 工厂
- 为什么有 `_get_chain()` 懒加载
- 为什么解析失败要抛异常
- 为什么 v0.1 不急着一步到位 LCEL

---

## 总结：模块 03 的知识地图

```text
get_llm() 统一模型配置
  ↓
PromptTemplate 声明变量与输出协议
  ↓
LLMChain 组装调用链（v0.1 旧范式）
  ↓
classify_intent 防御式解析 JSON
  ↓
API 层按 type 分流 action / answer
  ↓
单测 + 集成测试验证稳定性与真实性
```

---

## 面试题速答（融合版）

**Q1：LangChain 在你项目里做了什么？**  
> 用 `ChatOpenAI + PromptTemplate + LLMChain` 构建意图分类链，统一模型调用与 prompt 管理，减少样板代码并支持后续迁移。

**Q2：PromptTemplate 比 f-string 强在哪？**  
> f-string 是字符串语法；PromptTemplate 是可编排对象。它显式暴露输入变量、可复用、可组合，天然适配链式系统和后续 LCEL。

**Q3：LLM 输出不稳定怎么处理？**  
> 三层防线：prompt 约束、代码块剥离、裸 JSON 校验。解析失败抛 `ValueError`，API 层统一转 500，保证可观测。

**Q4：为什么还用 `run()` 而不是 `invoke()`？**  
> v0.1 作为旧链基线，v0.2 做 LCEL 迁移对比。阶段性保留旧 API 是为了控制变量，不是忽视升级。

**Q5：为什么 patch `_get_chain` 而不是 patch `_chain.run`？**  
> `_get_chain` 是稳定的测试边界，能完全绕过真实网络调用，也能避免实例属性 patch 带来的不稳定问题。

