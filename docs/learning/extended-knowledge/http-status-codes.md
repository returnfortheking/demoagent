# HTTP 状态码语义 — 扩展知识笔记

> 来源：Module 01 学习 HTTPException 时，讨论 LLM 解析失败应该返回 500 还是 422/502。
> 另一个 AI 建议用 422 或 502，分析后发现 422 语义错误，502 存在争议。
>
> 面试价值：体现你不只是"会用"状态码，而是理解其背后的 HTTP 协议语义。

---

## 状态码的分类逻辑

HTTP 状态码第一位数字代表大类：

| 大类 | 含义 | 谁的问题 |
|---|---|---|
| 2xx | 成功 | — |
| 3xx | 重定向 | — |
| 4xx | 客户端错误 | **调用方**的锅 |
| 5xx | 服务端错误 | **服务方**的锅 |

**这个区分是选择状态码的核心判断标准。**

---

## 最常用状态码详解

### 4xx — 客户端的锅

**400 Bad Request**
请求本身格式有问题（不是合法 JSON、Content-Type 不对、URL 格式错误）。
调用方传的东西服务端根本没法解析。

**422 Unprocessable Entity**
请求格式正确（合法 JSON），但字段校验失败（缺少必填字段、类型不对、值超出范围）。
FastAPI + Pydantic 校验失败时自动返回 422。

**401 Unauthorized**
未携带认证信息，或认证信息无效。

**403 Forbidden**
认证通过了，但没有权限做这件事。

**404 Not Found**
资源不存在。

### 5xx — 服务端的锅

**500 Internal Server Error**
服务端内部出了预料之外的错误。调用方请求完全正确，但服务端处理时失败了。
例：LLM 返回无法解析的格式、数据库连接断了、空指针异常。

**502 Bad Gateway**
服务端作为代理/网关，转发请求给上游时，上游返回了无效响应。
例：Nginx 后面的应用崩溃返回了非法 HTTP 响应，Nginx 就返回 502。

**503 Service Unavailable**
服务暂时不可用（过载、维护中）。通常带 `Retry-After` 头。
例：LLM API 服务宕机、速率限制被触发。

**504 Gateway Timeout**
作为代理时，上游超时没有响应。
例：转发给 LLM 的请求等了 30 秒没有回来。

---

## 项目里的实际案例

`backend/src/api/main.py`：
```python
try:
    intent = classify_intent(request.message)
except ValueError as e:
    raise HTTPException(status_code=500, detail=str(e))
```

`classify_intent` 抛出 `ValueError` 是因为 LLM 返回了无法解析成 JSON 的内容。

**为什么是 500，不是 422 或 502：**

| 选项 | 分析 |
|---|---|
| **422** | ❌ 语义错误。422 表示"你的请求有问题"，但这里请求完全合法，是 LLM 输出不规范，是服务端的问题。用 422 会误导调用方以为是自己传错了参数。 |
| **502** | ⚠️ 有争议。502 通常指"作为代理，上游返回了无效 HTTP 响应"。GLM 其实返回了合法 HTTP 200，只是 JSON 内容不符合我们的预期，不完全符合 502 的语义。 |
| **500** | ✅ 准确。服务端内部逻辑失败，调用方的请求没有问题。 |

**更细腻的方案（v0.1 没实现，面试可以提）：**

```python
# 更精确的错误语义
except LLMUnavailableError:
    raise HTTPException(status_code=503, detail="LLM service unavailable")  # 上游宕机
except LLMTimeoutError:
    raise HTTPException(status_code=504, detail="LLM response timeout")     # 上游超时
except ValueError as e:
    raise HTTPException(status_code=500, detail=str(e))                     # 解析失败
```

---

## 面试怎么用这部分知识

### 被问到"LLM 调用失败你返回什么状态码"时

> "目前返回 500。选择依据是：调用方的请求格式完全正确，是服务端的 LLM 输出无法解析，所以是 5xx 而不是 4xx。
>
> 我考虑过 422，但 422 语义是'客户端请求字段校验失败'，不适合表示服务端依赖出错的场景。
>
> 如果要更精细，可以区分 503（LLM 服务不可用）和 504（LLM 响应超时），但 v0.1 先用 500 统一处理，后续版本会细化。"

### 被问到"422 和 400 的区别"时

> "400 是请求本身不合法，服务端连解析都做不到。422 是请求格式合法、可以解析，但字段校验不通过。
> FastAPI 默认用 422 表示 Pydantic 校验失败，因为此时 JSON 是合法的，只是字段值不符合模型定义。"

### 被问到"如何设计 API 错误码"时

> "选状态码的核心判断是：这个错误是谁的锅？调用方传错了 → 4xx。服务端处理失败 → 5xx。
> 4xx 里再区分：格式问题（400）、字段校验（422）、权限问题（401/403）、资源不存在（404）。
> 5xx 里再区分：内部逻辑失败（500）、上游不可用（502/503）、上游超时（504）。"
