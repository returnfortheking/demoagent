# 模块 01：FastAPI + Pydantic v2 代码精讲

> 代码来源：`hispark-ai-agent/backend/src/api/`

---

## 第一讲：Pydantic 是什么，为什么要用它

### 【是什么】

Pydantic 是 Python 的**数据校验库**。你给它一个类定义，它帮你：
1. 验证传入的数据是否符合类型
2. 如果不符合，抛出清晰的错误
3. 把数据转换成你期望的类型

### 【项目里在哪】

`backend/src/api/models.py` 第 8-12 行：

```python
class ChatRequest(BaseModel):
    message: str
    thread_id: str
```

### 【代码走读】

这是最简单的 Pydantic 模型。你定义了两个字段，都是 `str` 类型，都没有默认值。

**没有默认值 = 必填字段。** 缺少任何一个，Pydantic 就会拒绝这个请求。

试想如果不用 Pydantic，你得这样写：
```python
# ❌ 不用 Pydantic 的写法（手动校验）
@app.post("/chat")
def chat(body: dict):
    if "message" not in body:
        return {"error": "message is required"}, 400
    if not isinstance(body["message"], str):
        return {"error": "message must be a string"}, 400
    if "thread_id" not in body:
        return {"error": "thread_id is required"}, 400
    # ... 还没开始写业务逻辑，已经写了 6 行校验
```

用 Pydantic：
```python
# ✅ 用 Pydantic 的写法
class ChatRequest(BaseModel):
    message: str
    thread_id: str

@app.post("/chat")
def chat(request: ChatRequest):
    # FastAPI + Pydantic 已经保证到这里 message 和 thread_id 一定存在且是 str
    # 直接写业务逻辑
```

### 【如果不这样写】

如果用普通 `dict` 接收请求体，你需要手动校验每个字段。漏掉一个就是 bug。
Pydantic 的价值是：**把校验规则写在类型定义里，强制执行，不可遗漏。**

### 【面试怎么说】

> "我用 Pydantic v2 定义了请求和响应的数据结构。它的核心价值是声明式校验——你在类定义上声明字段类型和约束，FastAPI 自动在每次请求进来时执行校验。如果字段缺失或类型不对，直接返回 422，业务逻辑层根本不会执行到。"

---

## 第二讲：422 是怎么来的

### 【是什么】

HTTP 422 Unprocessable Entity，表示请求格式正确（是合法的 JSON），但内容不符合业务规则。

区别：
- **400 Bad Request**：请求本身格式错误（不是合法 JSON，或者 Content-Type 不对）
- **422 Unprocessable Entity**：格式正确，但字段校验失败

### 【项目里在哪】

`backend/tests/unit/test_api.py` 第 101-113 行：

```python
def test_chat_missing_message():
    response = client.post("/chat", json={"thread_id": "t4"})
    assert response.status_code == 422

def test_chat_missing_thread_id():
    response = client.post("/chat", json={"message": "帮我编译"})
    assert response.status_code == 422
```

### 【代码走读】

这两个测试发送了**合法的 JSON**（Python dict 会被序列化成正确格式），但是缺少了必填字段。

FastAPI + Pydantic 的工作流程：
```
HTTP 请求到达
     ↓
FastAPI 尝试把请求体解析成 ChatRequest
     ↓
Pydantic 发现 message 字段缺失
     ↓
Pydantic 抛出 ValidationError（内部异常）
     ↓
FastAPI 捕获，自动返回 422 + 错误详情
     ↓
你的 chat() 函数根本没有被调用
```

**你作为开发者完全不需要写任何 try/except。** 这是 FastAPI + Pydantic 的核心价值：校验失败路径由框架处理。

实际返回的 422 响应体（FastAPI 自动生成）：
```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "message"],
            "msg": "Field required",
            "input": {"thread_id": "t4"}
        }
    ]
}
```

### 【面试怎么说】

> "缺字段返回 422 不是我写的逻辑，是 Pydantic 校验失败后 FastAPI 自动返回的。我在测试里专门验证了这个行为，确保 API 合约稳定——如果有人调用时漏了字段，不会进入业务逻辑，而是得到明确的错误响应。"

---

## 第三讲：响应模型的设计——为什么要有多个 Response 类

### 【是什么】

同一个 `/chat` 接口，根据意图类型返回不同结构的响应。

### 【项目里在哪】

`backend/src/api/models.py` 第 15-30 行：

```python
class ActionResponse(BaseModel):
    type: str = "action"      # 有默认值，不需要调用时传入
    command: str
    args: dict[str, Any] = {} # 默认空字典
    requires_confirmation: bool
    description: str

class AnswerResponse(BaseModel):
    type: str = "answer"
    answer: str
    sources: list[Any] = []   # 默认空列表，v0.1 暂未实现
```

### 【代码走读】

**第一个细节：`type: str = "action"`**

`type` 字段有默认值 `"action"`，这意味着创建 `ActionResponse` 时不需要传 `type`：
```python
ActionResponse(command="build", requires_confirmation=False, description="编译")
# type 自动是 "action"
```

为什么要显式定义 `type` 字段而不是让调用方推断？因为这个字段会出现在 JSON 响应里，TypeScript 的 Extension 端需要靠它来决定怎么处理响应：
```typescript
if (response.type === 'action') { /* 执行命令 */ }
else { /* 显示文字 */ }
```

**第二个细节：`args: dict[str, Any] = {}`**

`Any` 来自 `typing` 模块，表示"任意类型"。这里用它是因为 `args` 的值是扩展字段，v0.1 里是空字典，未来可能放任意键值对。

注意：这里写的是 `dict[str, Any]` 而不是 `dict`——前者更精确，表示 key 一定是 str，value 可以是任意类型。

**第三个细节：`sources: list[Any] = []`**

空列表作为默认值，说明 v0.1 不返回来源文档。这是有意的设计，不是遗漏——在模型定义里写明白，比在代码注释里解释要强。

### 【如果不这样写——用单个大 Response 类的后果】

```python
# ❌ 反例：一个类包含所有字段
class ChatResponse(BaseModel):
    type: str
    command: Optional[str] = None
    args: Optional[dict] = None
    requires_confirmation: Optional[bool] = None
    description: Optional[str] = None
    answer: Optional[str] = None
    sources: Optional[list] = None
```

问题：所有字段都是 Optional，TypeScript 端处理时每个字段都要判空。
而且，这个类无法在文档里清楚表达"action 类型必须有 command，answer 类型必须有 answer"。

**两个独立的类，约束更清晰，生成的 OpenAPI 文档也更准确。**

---

## 第四讲：`response_model` 的作用

### 【是什么】

FastAPI 路由装饰器上的 `response_model` 参数，声明这个接口返回什么类型。

### 【项目里在哪】

`backend/src/api/main.py` 第 21 行：

```python
@app.post("/chat", response_model=Union[ActionResponse, AnswerResponse])
```

### 【代码走读】

`Union[ActionResponse, AnswerResponse]` 表示这个接口可能返回两种类型之一。

`response_model` 做了三件事：

**1. 生成 OpenAPI 文档**
FastAPI 自动生成 `/docs` 接口文档，里面会准确描述 `/chat` 的两种返回格式。没有 `response_model`，文档里的响应部分是空的。

**2. 过滤多余字段**
如果你的返回对象里有额外字段（比如调试信息），`response_model` 会过滤掉，只返回模型里声明的字段。这防止了敏感数据泄漏。

**3. 响应校验**
FastAPI 会在返回前验证响应数据是否符合模型定义。如果代码里返回了错误类型的数据，会抛出 500 而不是静默地返回脏数据。

**注意这个代码细节：**
```python
return ActionResponse(...).model_dump()
```

`model_dump()` 把 Pydantic 对象转成 Python dict，然后 FastAPI 再序列化成 JSON。
这里有点冗余（声明了 `response_model` 但又手动 `model_dump()`），更 idiomatic 的写法是直接返回对象：
```python
return ActionResponse(...)  # FastAPI 会通过 response_model 自动序列化
```
但两种写法的最终结果是一样的，这是代码质量审查时发现的一个 minor 问题，保留下来了。

### 【面试怎么说】

> "我在路由上声明了 `response_model`，有三个好处：FastAPI 自动生成准确的 API 文档、对响应数据做二次校验、防止多余字段泄漏。对于 `/chat` 接口，我用了 `Union[ActionResponse, AnswerResponse]` 表示两种可能的响应结构，TypeScript 端根据 `type` 字段来判断是哪种。"

---

## 第五讲：HTTPException 与错误处理

### 【是什么】

FastAPI 中返回错误响应的标准方式，通过 `raise` 而不是 `return`。

### 【项目里在哪】

`backend/src/api/main.py` 第 30-33 行：

```python
try:
    intent = classify_intent(request.message)
except ValueError as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### 【代码走读】

**为什么用 `raise` 而不是 `return`？**

如果用 `return`：
```python
# ❌ 不要这样做
if error:
    return {"error": "something went wrong"}, 500
# 后面的代码还会继续执行...
answer = answer_question(...)
```

用 `raise` 后，函数立即中断，不需要 `else` 或提前 `return`：
```python
# ✅ raise 立即终止函数
try:
    intent = classify_intent(request.message)
except ValueError as e:
    raise HTTPException(status_code=500, detail=str(e))

# 能走到这里，说明 intent 一定是合法的
if intent.get("type") == "action":
    ...
```

**为什么是 500 而不是 400？**

`classify_intent` 抛出 `ValueError` 是因为 LLM 返回了无法解析的内容。这不是调用方的问题（请求格式是对的），而是服务端的 LLM 出了问题。所以是 500（服务端错误），不是 400/422（客户端错误）。

**`detail=str(e)` 的含义**

把 `ValueError` 的错误消息放进响应体的 `detail` 字段。FastAPI 的标准错误格式：
```json
{
    "detail": "LLM returned non-JSON content: '```json...'"
}
```

### 【面试怎么说】

> "我在 `classify_intent` 的调用处加了 try/except，因为 LLM 输出不稳定，有时会返回无法解析成 JSON 的内容。这种情况下是服务端问题，所以返回 500 而不是 400。用 `raise HTTPException` 而不是 return，是因为 raise 会立即中断执行流，代码结构更清晰。"

---

## 第六讲：FastAPI 的路由函数怎么工作

### 【项目里在哪】

`backend/src/api/main.py` 完整看一遍：

```python
app = FastAPI(title="HiSpark AI Agent", version="0.1.0")

@app.post("/chat", response_model=Union[ActionResponse, AnswerResponse])
def chat(request: ChatRequest):
    ...

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse().model_dump()
```

### 【代码走读】

**`app = FastAPI(...)` 是入口**

`FastAPI()` 实例就是整个应用。`title` 和 `version` 出现在自动生成的 `/docs` 页面上。

**`@app.post("/chat")` 装饰器做了什么**

它把 `chat` 函数注册为处理 `POST /chat` 请求的处理器。当一个 POST 请求到达 `/chat` 路径时，FastAPI：
1. 读取请求体 JSON
2. 尝试创建 `ChatRequest(...)` 实例（触发 Pydantic 校验）
3. 校验通过 → 调用 `chat(request)` 函数
4. 校验失败 → 直接返回 422，不调用函数

**`def chat(request: ChatRequest)` 的类型注解是关键**

FastAPI 通过**类型注解**知道要把请求体解析成 `ChatRequest`。这不是普通的 Python 类型提示——FastAPI 运行时会真正用它来解析和校验数据。

如果参数名不叫 `request` 叫 `body` 也没关系，关键是类型注解 `: ChatRequest`。

**`GET /health` 为什么不需要参数**

```python
def health():
    return HealthResponse().model_dump()
```

健康检查不需要请求体，所以函数没有参数。返回 `HealthResponse()` 时用了默认值 `status="ok"`，不需要传任何参数。

---

## 第七讲：TestClient——在测试里如何调用 API

### 【是什么】

FastAPI 内置的测试工具，让你不需要真正启动 HTTP 服务器就能测试 API。

### 【项目里在哪】

`backend/tests/unit/test_api.py` 第 14-16 行：

```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
```

### 【代码走读】

`TestClient(app)` 把 FastAPI 应用包装成一个可以直接调用的对象。

```python
# 这行代码完整地模拟了一次 HTTP POST 请求：
response = client.post("/chat", json={"message": "帮我编译项目", "thread_id": "t1"})
```

- `"/chat"` — 路径
- `json=...` — 请求体，TestClient 自动序列化成 JSON，设置 `Content-Type: application/json`
- 返回值是一个响应对象，有 `.status_code`、`.json()` 等属性

**为什么不用真实的 `requests.post("http://localhost:8000/chat", ...)`？**

因为那需要先启动服务器。`TestClient` 直接调用 FastAPI 的 Python 函数，速度快（毫秒级），不需要网络，不需要端口，不依赖运行环境。

**`client = TestClient(app)` 放在文件顶层（不在测试函数里）**

这意味着所有测试函数共用同一个 client 实例。这没问题，因为 TestClient 是无状态的——每次 `.post()` 都是独立的请求。

### 【面试怎么说】

> "FastAPI 的 `TestClient` 让我不需要启动服务器就能测试 API 行为。它直接调用 FastAPI 应用的内部逻辑，速度很快。我用它测试了 6 个场景：两种 action 响应、知识问答响应、两种 422 错误、健康检查。这些测试是纯单元测试，通过 Mock 隔离了 LLM 调用，每次运行不到 2 秒。"

---

## 第八讲：`model_dump()` —— Pydantic v2 的序列化

### 【是什么】

把 Pydantic 模型对象转换成 Python 原生 dict 的方法。

### 【Pydantic v1 vs v2 的区别】

| | Pydantic v1 | Pydantic v2 |
|--|-------------|-------------|
| 序列化 | `.dict()` | `.model_dump()` |
| 配置类 | `class Config:` | `model_config = ConfigDict(...)` |
| 速度 | 纯 Python | Rust 核心，快 5-50 倍 |
| 类型验证 | 运行时 | 运行时 + 更严格 |

**为什么项目里要用 v2？**

LangChain 0.3.x 已经迁移到 Pydantic v2。如果你用 v1，会有大量版本冲突警告，甚至运行时错误。

### 【面试怎么说】

> "我用的是 Pydantic v2，主要区别是 `.dict()` 换成了 `.model_dump()`，配置用 `model_config = ConfigDict(...)` 而不是内嵌的 `class Config`。LangChain 0.3.x 依赖 Pydantic v2，所以统一用 v2 避免版本冲突。"

---

## 总结：这个模块的知识地图

```
用户发请求
    ↓
FastAPI 路由匹配 (@app.post("/chat"))
    ↓
Pydantic 解析请求体 (ChatRequest)
    ↓ 失败 → 422（框架自动）
    ↓ 成功
业务逻辑 (chat 函数)
    ↓ 出错 → raise HTTPException(500)
    ↓ 成功
构建响应对象 (ActionResponse / AnswerResponse)
    ↓
response_model 校验 + 序列化
    ↓
返回 JSON
```

---

## 面试题汇总

**Q: FastAPI 如何做参数校验？**
> 通过 Pydantic v2 的 BaseModel。在路由函数参数上用类型注解声明请求体的模型类，FastAPI 自动校验。字段缺失或类型错误直接返回 422。

**Q: 422 和 400 的区别？**
> 400 Bad Request 是请求格式本身有问题（比如不是合法 JSON）。422 Unprocessable Entity 是请求格式正确但字段校验失败（缺少必填字段、类型不对）。FastAPI 默认用 422 表示 Pydantic 校验失败。

**Q: Pydantic v1 和 v2 的区别？**
> v2 用 Rust 实现核心，性能提升 5-50 倍；API 上 `.dict()` 改为 `.model_dump()`，`class Config` 改为 `model_config = ConfigDict(...)`；验证更严格，对 Optional 字段的处理也有变化。

**Q: 为什么用 raise HTTPException 而不是 return？**
> raise 会立即中断函数执行，不需要在后面加 else 或 return。语义上也更准确——这不是正常返回值，而是一个异常情况。FastAPI 捕获 HTTPException 并将其转换成对应状态码的 HTTP 响应。

**Q: response_model 有什么作用？**
> 三个作用：①生成准确的 OpenAPI 文档；②在响应返回前校验数据，防止返回错误格式；③过滤掉模型定义之外的多余字段，防止敏感数据泄漏。
