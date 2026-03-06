# 模块 02：pytest 测试体系

> 基于 `hispark-ai-agent v0.1` 真实测试代码的讲解。
> 核心原则：每个概念都有对应的项目代码，不讲脱离代码的纯理论。

---

## 第 1 讲：测试金字塔 — 三层测试的职责边界

### 【是什么】

测试金字塔是一个分层策略：越底层越快、越多；越顶层越慢、越少。

```
        E2E（端到端）           ← 最少，最慢，最真实
       /             \
    集成测试（Integration）    ← 中等，真实 API
   /                     \
单元测试（Unit）              ← 最多，最快，全 Mock
```

### 【项目里在哪】

```
backend/tests/unit/
    test_api.py                  ← 单元：TestClient + Mock 函数
    test_intent_classifier.py    ← 单元：Mock _get_chain
    test_qa_chain.py             ← 单元+集成混合（Test 1 是集成）

backend/tests/integration/
    test_llm_real.py             ← 集成：真实调用 ZhipuAI API

tests/e2e/
    test_e2e_v01.py              ← E2E：subprocess 启动真实服务器
```

### 【各层的职责边界】

**单元测试（Unit）**
- 测一个函数/模块，隔离所有外部依赖（LLM、数据库、网络）
- 速度：毫秒级，CI 里每次提交都跑
- 例子：`test_classify_intent_build_action` — mock 掉 `_get_chain`，只测 JSON 解析逻辑

**集成测试（Integration）**
- 测真实调用链（真实 LLM API），验证单元测试 Mock 的假设是否成立
- 速度：秒级，只在 `-m integration` 时跑
- 例子：`test_classify_intent_build_real` — 真实发送"帮我编译项目"给 GLM，验证结果

**E2E 测试（End-to-End）**
- 测完整系统：启动真实服务器 + 发真实 HTTP 请求
- 速度：最慢（服务器启动 + LLM 调用），每天或发布前跑
- 例子：`test_build_intent` — 通过 httpx 发 POST /chat，验证整条链路

### 【如果不分层】

只写 E2E 测试：每次改一行代码都要等 30 秒，开发体验极差。
只写单元测试：Mock 了所有依赖，LLM 升级后返回格式变了，测试仍然通过，但生产挂了。

**单元测试是"效率保障"，集成测试是"Mock 担保人"。**

---

## 第 2 讲：pytest fixture — 什么是 fixture，scope 的含义

### 【是什么】

fixture 是 pytest 的"测试准备/清理"机制。一个 fixture 函数会在测试函数需要它时自动执行，并可以在测试后自动清理。

### 【项目里在哪】

`tests/e2e/test_e2e_v01.py` 第 14-39 行：

```python
@pytest.fixture(scope="module")
def api_server():
    """Start FastAPI server as subprocess, yield, then terminate."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            r = httpx.get(f"{BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        proc.terminate()
        pytest.fail("FastAPI server failed to start within 30 seconds")

    yield proc        # ← 这里是测试运行的位置

    proc.terminate()  # ← yield 之后的代码是清理逻辑
    proc.wait(timeout=10)
```

E2E 测试函数通过参数名 `api_server` 声明依赖：

```python
def test_health(api_server):          # 接收 fixture
    r = httpx.get(f"{BASE_URL}/health")
    ...
```

### 【scope 参数的含义】

| scope | 含义 | 本项目用例 |
|-------|------|----------|
| `"function"` | 默认，每个测试函数前后各执行一次 | `mocker`（pytest-mock 内置） |
| `"class"` | 每个测试类一次 | 本项目未用 |
| `"module"` | 每个测试文件一次 | `api_server`（E2E 的服务器） |
| `"session"` | 整个测试会话一次 | 本项目未用 |

**`scope="module"` 的设计意图：**

`api_server` fixture 启动一个真实的 uvicorn 进程，这个操作耗时 ~5秒。如果 scope 是默认的 `"function"`，5 个 E2E 测试就要启动/关闭 5 次服务器，浪费 25 秒。

改为 `scope="module"` 后：整个 `test_e2e_v01.py` 文件只启动一次服务器，5 个测试共用，测试完毕后关闭一次。

### 【yield 是分界线】

```python
@pytest.fixture
def some_resource():
    resource = setup()    # "前置准备" — 在 yield 之前
    yield resource        # 把资源交给测试函数
    cleanup(resource)     # "后置清理" — 在 yield 之后（即使测试失败也会执行）
```

yield 之前 = `setup`，yield 之后 = `teardown`。这是 pytest fixture 的核心模式。

---

## 第 3 讲：mocker.patch — 为什么要 patch"使用处"而非"定义处"

### 【是什么】

`mocker.patch` 是 pytest-mock 提供的工具，用于临时替换一个对象（函数/方法/属性）为 Mock 对象，测试结束后自动恢复。

### 【项目里在哪】

`test_api.py` 第 24-26 行：

```python
mock_classify = mocker.patch(
    "src.api.main.classify_intent",    # ← patch 的路径
    return_value={...},
)
```

`test_intent_classifier.py` 第 28 行：

```python
mocker.patch("src.chains.intent_classifier._chain.run", return_value=llm_response)
```

### 【关键原则：patch 使用处，不是定义处】

**示例：**

```python
# src/chains/intent_classifier.py（定义处）
def classify_intent(message: str) -> dict:
    ...

# src/api/main.py（使用处）
from src.chains.intent_classifier import classify_intent

@app.post("/chat")
def chat(request: ChatRequest):
    intent = classify_intent(request.message)  # 这里用到
```

**错误写法：**

```python
mocker.patch("src.chains.intent_classifier.classify_intent", ...)
```

**正确写法：**

```python
mocker.patch("src.api.main.classify_intent", ...)
```

**为什么？**

因为 `from src.chains.intent_classifier import classify_intent` 执行后，
`src.api.main` 模块里有了一个**本地名字** `classify_intent`，指向原始函数对象。

patch 定义处时，修改的是 `src.chains.intent_classifier` 模块里的名字，
但 `src.api.main` 里的本地引用**不受影响**，仍然指向原始函数。

patch 使用处时，直接替换 `src.api.main` 里的本地名字，调用时自然走到 Mock。

**记忆口诀：谁用谁负责。patch 测试对象实际用到的那个名字。**

---

## 第 4 讲：@pytest.mark.integration — 隔离慢测试

### 【是什么】

`@pytest.mark.integration` 是一个自定义标记，用来标识"需要真实外部服务"的测试，
让开发者可以选择性地运行或跳过这些测试。

### 【项目里在哪】

**注册标记**（`pyproject.toml`）：

```toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (real API calls)",
]
```

**使用标记**（`test_llm_real.py` 第 16 行起）：

```python
@pytest.mark.integration
def test_llm_normal_invoke():
    llm = get_llm()
    response = llm.invoke("用一句话介绍你自己")
    assert isinstance(response.content, str)
```

**标记在单元测试文件里的混合**（`test_qa_chain.py` 第 30 行）：

```python
@pytest.mark.integration
def test_build_retriever_returns_non_none():
    """这个测试在 test_qa_chain.py 里，但需要真实 embedding API。"""
    ...
```

### 【如何使用】

```bash
# 只跑单元测试（跳过 integration 标记的测试）
pytest -m "not integration"

# 只跑集成测试
pytest -m integration

# 跑所有测试
pytest
```

### 【设计价值】

这个设计让"快速反馈循环"成为可能：

- 开发时：`pytest -m "not integration"` — 几秒钟，随时跑
- 提交前：`pytest` — 完整验证，包含真实 API

**如果不标记**：每次改一行代码，所有 LLM API 调用都会触发，等待时间变长，开发者会放弃频繁跑测试。

---

## 第 5 讲：MagicMock vs mocker.patch — 两种 Mock 的区别

### 【项目里在哪】

`test_qa_chain.py` 第 60-62 行：

```python
mock_chain = mocker.MagicMock()                   # 创建 MagicMock 对象
mock_chain.run.return_value = "BS21 芯片支持Wi-Fi和蓝牙"  # 设置返回值
mocker.patch("src.chains.qa_chain._get_qa_chain", return_value=mock_chain)  # 注入
```

### 【MagicMock 是什么】

`MagicMock` 是 Python 标准库 `unittest.mock` 的一个类，用来创建一个"万能替代品"：

```python
from unittest.mock import MagicMock

m = MagicMock()
m.run("任何参数")        # 不报错，返回另一个 MagicMock
m.run.return_value = "hello"  # 设置返回值
m.run("参数")            # → "hello"
m.run.assert_called_once()    # 验证是否被调用了一次
```

**"Magic"的含义：** 它连 `__len__`、`__iter__`、`__str__` 等魔术方法都预设好了，不会因为调用特殊方法而报错。

### 【mocker.patch 与 MagicMock 的关系】

`mocker.patch` 内部会自动创建一个 MagicMock 来替换目标：

```python
# 这两段代码等价：
mock_classify = mocker.patch("src.api.main.classify_intent", return_value={...})

# 等价于：
mock = MagicMock(return_value={...})
original = src.api.main.classify_intent
src.api.main.classify_intent = mock
# 测试结束后自动恢复：
src.api.main.classify_intent = original
```

### 【区别对比】

| | mocker.patch | MagicMock |
|---|---|---|
| 用途 | 替换模块里的已有名字 | 创建一个假对象 |
| 自动清理 | 是（测试结束后自动恢复） | 否（你创建的，你管理） |
| 典型用法 | `mocker.patch("模块路径")` | `mock = mocker.MagicMock()` |
| 使用场景 | 函数调用路径上的替换 | 需要注入的对象（如 return_value） |

**test_qa_chain.py 的组合用法解读：**

```python
mock_chain = mocker.MagicMock()          # 创建一个假的 chain 对象
mock_chain.run.return_value = "回答内容" # 让它的 run() 返回固定值
mocker.patch(                             # 让 _get_qa_chain() 返回这个假对象
    "src.chains.qa_chain._get_qa_chain",
    return_value=mock_chain
)
```

这里需要两步是因为：我们不只是替换一个函数，还需要控制那个函数**返回的对象**的行为。

---

## 第 6 讲：Pydantic v2 可测性问题 — 工厂函数是正确解法

### 【问题背景】

这是本项目经历过的一次真实事故，面试时非常有谈资。

`LLMChain` 继承自 `Pydantic v2 BaseModel`，Pydantic v2 重写了 `__setattr__` 和 `__delattr__`，
不允许在运行时对实例属性自由赋值/删除。

`mocker.patch` 替换和恢复属性的完整过程：
```python
setattr(obj, 'run', mock_value)   # 替换
delattr(obj, 'run')               # 恢复（测试结束后）
```

当 `obj` 是 Pydantic v2 实例时，`delattr` 报错：
```
pydantic.errors.PydanticUserError: Cannot modify attribute
```

### 【错误的解法：Testing Seam 混入生产代码】

v0.1 开发时，为了让 `mocker.patch("...._chain.run", ...)` 能工作，
在生产代码 `src/chains/intent_classifier.py` 里加了一个包装类：

```python
# ❌ 错误做法 —— 已在 2026-03-04 移除
class _ChainWrapper:
    """Thin wrapper around LLMChain to allow attribute-level mocking."""
    def __init__(self, llm_chain: LLMChain) -> None:
        self._llm_chain = llm_chain
    def run(self, **kwargs) -> str:
        return self._llm_chain.run(**kwargs)

_chain = _ChainWrapper(LLMChain(llm=get_llm(), prompt=_prompt))
```

**这是错误的**，原因：
- `_ChainWrapper` 没有任何业务价值，存在的唯一目的是让 pytest-mock 能工作
- 这叫 **Testing Seam（测试缝隙）**：为测试需求而修改生产代码
- 违反"生产代码（`src/`）不得包含测试专用代码"的原则

### 【正确解法：工厂函数（Factory Function）】

遇到 Pydantic v2 patch 限制时，正确做法是**不 patch 实例属性，改为 patch 工厂函数**。

当前代码 `intent_classifier.py`：

```python
# ✅ 正确做法
_chain: LLMChain | None = None

def _get_chain() -> LLMChain:
    """懒加载工厂函数，首次调用时创建 LLMChain 实例。"""
    global _chain
    if _chain is None:
        _chain = LLMChain(llm=get_llm(), prompt=_prompt)
    return _chain

def classify_intent(message: str) -> dict:
    raw: str = _get_chain().run(message=message)  # 通过工厂获取实例
    ...
```

测试里 patch 工厂函数，完全不碰 LLMChain 实例：

```python
# test_intent_classifier.py
mock_chain = mocker.MagicMock()
mock_chain.run.return_value = llm_response
mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)
```

`_get_chain` 是模块里的普通函数名（不是 Pydantic 实例属性），patch 完全合法。

### 【两种解法对比】

| | ❌ _ChainWrapper（已移除） | ✅ 工厂函数（当前） |
|---|---|---|
| 生产代码污染 | 有（包装类混入 src/） | 无 |
| patch 目标 | `_chain.run`（实例属性） | `_get_chain`（模块函数） |
| 初始化时机 | import 时立即创建（eager） | 首次调用时创建（lazy） |
| 测试代码 | `mocker.patch("..._chain.run", ...)` | `mocker.patch("..._get_chain", ...)` |

**额外收益**：工厂函数模式同时实现了懒加载（lazy init），
import 时不触发 LLM 连接，启动更快。

### 【事故记录】

- 发现时间：2026-03-04（代码学习复盘时）
- 修复 commit：`8d4a998`
- 预防措施：`scripts/check_src_purity.py`（自动扫描 src/ 是否含测试专用类）
- 完整复盘：`docs/incidents/2026-03-04-chain-wrapper-in-production.md`

---

## 第 7 讲：monkeypatch — 临时修改环境变量

### 【是什么】

`monkeypatch` 是 pytest 内置的 fixture，提供对环境变量、模块属性、文件系统的临时修改，
测试结束后自动恢复。

### 【项目里在哪】

`test_llm_real.py` 第 26-35 行：

```python
@pytest.mark.integration
def test_llm_invalid_key_raises(monkeypatch):
    """Test that an invalid API key causes an exception to be raised."""
    monkeypatch.setenv("ZHIPU_API_KEY", "invalid_key_xxx")  # 临时覆盖环境变量
    llm = get_llm()
    with pytest.raises(Exception):
        llm.invoke("test")
    # 测试结束后，ZHIPU_API_KEY 自动恢复为原值
```

### 【与 os.environ 的区别】

**错误写法：**

```python
os.environ["ZHIPU_API_KEY"] = "invalid_key_xxx"
# 测试结束后需要手动恢复，容易忘记，污染其他测试
```

**正确写法：**

```python
monkeypatch.setenv("ZHIPU_API_KEY", "invalid_key_xxx")
# pytest 自动恢复，测试隔离
```

### 【monkeypatch 常用方法】

| 方法 | 用途 |
|------|------|
| `monkeypatch.setenv("KEY", "value")` | 设置环境变量 |
| `monkeypatch.delenv("KEY")` | 删除环境变量 |
| `monkeypatch.setattr(obj, "attr", value)` | 替换对象属性 |
| `monkeypatch.chdir("/tmp")` | 切换工作目录 |

**`monkeypatch` vs `mocker.patch` 的选择：**

- 修改环境变量 → `monkeypatch.setenv`
- 替换模块里的函数/类 → `mocker.patch`
- 两者都有 scope="function" 的自动清理

---

## 第 8 讲：E2E fixture 中的 subprocess 管理 — 细节解读

### 【代码走读】

`tests/e2e/test_e2e_v01.py` 第 14-39 行，逐段解析：

**第一部分：启动服务器**

```python
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=BACKEND_DIR,           # 切换到 backend 目录，确保 Python 能找到 src 包
    stdout=subprocess.DEVNULL, # 抑制服务器输出，不污染测试日志
    stderr=subprocess.DEVNULL,
)
```

`sys.executable` 而不是 `"python"`：确保用的是当前虚拟环境的 Python，不是系统 Python。

**第二部分：健康检查轮询**

```python
for _ in range(30):              # 最多等 30 秒
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2)
        if r.status_code == 200:
            break                # 服务器就绪，退出循环
    except Exception:
        pass                     # 服务器还没起来，静默忽略连接错误
    time.sleep(1)
else:                            # for 循环正常结束（没有 break）时执行
    proc.terminate()
    pytest.fail("FastAPI server failed to start within 30 seconds")
```

**`for...else` 的 Python 语义：** `else` 块在循环"耗尽"（没有 `break`）时执行。这里等于说"如果 30 次都没成功，就报错"。

**第三部分：yield 与清理**

```python
yield proc        # 把 proc 交给测试函数（虽然大多数测试忽略它）

proc.terminate()  # 发送 SIGTERM，让 uvicorn 优雅关闭
proc.wait(timeout=10)  # 等待进程真正退出，防止僵尸进程
```

### 【scope="module" 的实际效果】

```
test_e2e_v01.py 开始
  ↓
api_server fixture 启动（uvicorn 子进程）
  ↓
test_health(api_server) 运行
test_build_intent(api_server) 运行
test_flash_intent(api_server) 运行
test_knowledge_qa(api_server) 运行
test_missing_message_field(api_server) 运行
  ↓
api_server fixture 清理（terminate + wait）
test_e2e_v01.py 结束
```

服务器只启动一次，5 个测试共用同一个进程。

---

## 第 9 讲：Mock 是"有意义的谎言"— 集成测试是担保人

### 【核心思想】

单元测试里 Mock 了 LLM，意味着我们在"撒谎"：假设 LLM 总是返回格式正确的 JSON。
这个"谎言"让测试速度极快，但它依赖一个**假设**：真实 LLM 也会返回这种格式。

**集成测试就是验证这个假设的担保人。**

### 【项目里的体现】

单元测试的"谎言"：

```python
# test_intent_classifier.py
mocker.patch("src.chains.intent_classifier._chain.run",
             return_value='{"type": "action", "command": "hispark-studio.build", ...}')
```

这个 Mock 假设：LLM 会返回纯 JSON，不会有前缀。

集成测试的"担保"：

```python
# test_llm_real.py
@pytest.mark.integration
def test_classify_intent_build_real():
    result = classify_intent("帮我编译项目")
    assert result["type"] == "action"
    assert result["command"] == "hispark-studio.build"
```

真实调用 GLM，验证 prompt 设计是否真的能让 LLM 返回正确格式。

**如果集成测试失败而单元测试通过**：说明 Mock 的假设有问题，需要修改 prompt 或加强格式处理。

### 【RAG 测试为什么用关键词断言】

`test_llm_real.py` 第 78-83 行：

```python
def test_rag_sdk_download_url():
    answer = answer_question("WS63的SDK从哪里下载？")
    assert "gitee" in answer          # 关键词断言
    assert "fbb_ws63" in answer       # 关键词断言
```

**为什么不用 `assert answer == "xxx"` 精确匹配？**

LLM 的输出是概率性的，每次措辞不同，但**事实内容**应该包含关键词。
关键词断言既灵活（允许 LLM 用不同措辞），又严格（核心信息必须出现）。

如果用精确匹配，今天跑过，明天 LLM 换个说法，测试莫名失败。

---

## 面试题问答

### Q1：你怎么测试依赖外部 API 的代码？

> 我们用两层策略：
> 单元层用 `mocker.patch` Mock 掉 LLM 调用，测试 JSON 解析、路由逻辑等纯 Python 逻辑，速度毫秒级，随时跑；
> 集成层用 `@pytest.mark.integration` 标记，只在需要时运行真实 API，验证 Mock 的假设是否成立。
> 这样既保证开发效率，又不会因为 Mock 掩盖真实问题。

### Q2：Mock 和 Stub 有什么区别？

> Stub 只提供返回值（让代码能运行），Mock 还能验证调用行为（是否被调用、调用参数）。
> 项目里 `mocker.patch(..., return_value=...)` 偏 Stub，而用 `mock.assert_called_once()` 验证调用时就变成了 Mock。

### Q3：你的项目测试覆盖率怎么样？

> 我们关注的是测试策略而不是数字。单元测试覆盖所有业务逻辑分支（5 种意图场景），
> 集成测试验证真实 LLM 行为，E2E 测试覆盖 5 个关键用户场景。
> 真正有价值的是：单元测试 Mock 的假设，都有对应的集成测试来担保。

### Q4：pytest fixture 的 scope 参数怎么选？

> 看资源的创建成本和隔离需求：
> 轻量资源（dict、临时对象）用默认 function scope；
> 重量资源（数据库连接、HTTP 服务器进程）用 module 或 session scope，避免重复创建；
> 需要测试间完全隔离的（如环境变量修改）用 function scope 保证每次都是干净状态。
> 项目里 E2E 的服务器用 module scope，因为启动一次需要 5 秒，5 个测试共用节省时间。

### Q5：patch 路径写错了会怎样？

> 测试会通过，但是假的。比如把 `src.api.main.classify_intent` 写成 `src.chains.intent_classifier.classify_intent`，
> `mocker.patch` 替换的是定义处的名字，但 `main.py` 里已经 `from ... import classify_intent`，
> 拿到的是一个本地引用，不受影响，实际还是调用了真实函数（可能打到真实 LLM）。
> 正确原则：patch 使用处的路径，不是定义处。

---

## 学习过程中的真实疑问

### Q：`mocker` 参数没有 import，pytest 怎么知道要注入什么？

pytest 在运行测试之前，会扫描所有已注册的 fixture，构建一张名字→函数的映射表：

```
"mocker"     → pytest-mock 库里定义的 fixture 函数
"tmp_path"   → pytest 内置 fixture
"api_server" → test_e2e_v01.py 里自己定义的 fixture
```

当 pytest 准备运行 `test_chat_build_intent(mocker)` 时，它读取参数名 `mocker`，去表里查，找到对应函数，执行后把结果传进来。这个机制叫**依赖注入（Dependency Injection）**，匹配依据是**参数名**，不是类型。

`pytest-mock` 库安装后通过 pytest 插件机制自动注册 `mocker`，所以不需要任何 import，只需要在函数参数里写名字。

```python
def test_a(mocker):       # 参数名 "mocker" → 自动注入
def test_b(api_server):   # 参数名 "api_server" → 自动注入
def test_c():             # 无参数 → 不查表
```

---

## 知识点速查

| 概念 | 一句话总结 |
|------|----------|
| 测试金字塔 | 单元多而快，集成中，E2E 少而真实 |
| fixture | 测试的"准备+清理"机制，yield 是分界线 |
| scope="module" | 整个文件共用一个 fixture 实例 |
| mocker.patch | 替换使用处的名字（不是定义处）|
| @pytest.mark.integration | 标记慢测试，按需运行 |
| MagicMock | 万能假对象，可设置返回值和验证调用 |
| _ChainWrapper | Pydantic v2 不可 patch 属性，用普通类包装 |
| monkeypatch | 临时修改环境变量，测试后自动恢复 |
| 关键词断言 | LLM 输出不稳定，用 `in` 而非 `==` |
