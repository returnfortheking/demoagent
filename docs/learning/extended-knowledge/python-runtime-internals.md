# Python 运行时原理 — 扩展知识笔记

> 来源：Module 02 学习 mocker.patch 时，产生了两个真实疑问：
> 1. `from src.chains... import` 为什么从 `src` 开始，路径规则是什么？
> 2. mocker.patch 的"替换和恢复"是什么层面的，代码文件被改了吗？
>
> 面试价值：体现你理解 Python 的模块系统和运行时机制，不只是会用 API。

---

## 疑问 1：import 路径为什么从 `src` 开始

### 问题来源

`main.py` 里有这一行：

```python
from src.chains.intent_classifier import classify_intent
```

为什么是从 `src` 这层开始，而不是从项目根目录，也不是从 `main.py` 所在的目录？

### 根本原因：`sys.path`

Python 执行 import 时，会在 `sys.path`（一个目录列表）里逐个查找。关键问题是：**哪个目录被加进了 `sys.path`？**

pytest 的配置（`pyproject.toml`）把 `backend/` 目录作为测试根目录，pytest 启动时把它加入 `sys.path`：

```
sys.path 包含：
  D:/AI/2026/LangGraph/hispark-ai-agent/backend/   ← 从这一层开始数
```

从 `backend/` 往下看：

```
backend/               ← sys.path 里的这一层（import 的起点）
  src/                 ← src
    api/               ← api
      main.py          ← main
    chains/            ← chains
      intent_classifier.py  ← intent_classifier
```

所以 `from src.chains.intent_classifier import classify_intent` 的含义是：
> 从 `sys.path` 里找到 `backend/`，进入 `src/chains/`，找到 `intent_classifier.py`，取出 `classify_intent`。

### 规则总结

**import 路径从 `sys.path` 里包含的那个目录开始数，不是从项目根，也不是从当前文件所在目录。**

| 如果 sys.path 加的是… | import 写法 |
|---|---|
| `backend/` | `from src.chains.xxx import ...` |
| `backend/src/` | `from chains.xxx import ...` |
| `backend/src/chains/` | `from xxx import ...` |

不同项目 import 写法不一样，根本原因就是 `sys.path` 设置不同。

---

## 疑问 2：mocker.patch 的替换和恢复是什么层面的

### 问题来源

`mocker.patch("src.api.main.classify_intent", ...)` 说是"替换"函数，测试结束后"恢复"。
**源代码文件有没有被修改？** 还是什么所谓的"运行时"？

### 答案：内存层面，源文件完全不动

Python 每个模块被 import 后，在内存里有一个**模块对象**，可以理解成一个字典，记录这个模块里所有的名字和对应的值：

```python
# main.py 被 import 后，内存里大概是：
sys.modules["src.api.main"] = {
    "app":              <FastAPI 实例>,
    "classify_intent":  <真实函数对象>,   ← from ... import 进来的本地名字
    "answer_question":  <真实函数对象>,
    "chat":             <路由函数>,
    ...
}
```

`mocker.patch("src.api.main.classify_intent", ...)` 的完整过程：

```python
# 1. 找到内存里的模块对象
module = sys.modules["src.api.main"]

# 2. 保存原来的值（用于恢复）
original = module.classify_intent

# 3. 把那个名字换成 MagicMock
module.classify_intent = MagicMock(return_value={...})

# --- 测试运行，调用 classify_intent 时走到 MagicMock ---

# 4. 测试结束，恢复原值
module.classify_intent = original
```

**源代码文件 `main.py` 一个字节都没有动。**

下次 Python 重新 import 这个模块，还是完整的原始代码。

### 运行时（Runtime）的含义

"运行时"指程序跑起来之后的状态，相对于"编译时"或"源码"。

| 层面 | 含义 | patch 发生在这里吗 |
|---|---|---|
| 源码层面 | `.py` 文件内容 | ❌ |
| 编译层面 | `.pyc` 字节码 | ❌ |
| 运行时层面 | 内存里的对象和变量 | ✅ |

Python 是动态语言，模块对象的属性可以在运行时随意修改，这是 `mocker.patch` 能工作的根本原因。如果是 C++ 这类静态编译语言，就做不到这种运行时替换。

---

## 两个疑问的联系

理解了 `sys.path`（疑问 1），就能理解为什么 patch 路径要写 `"src.api.main.classify_intent"`：

- `src.api.main` 是 Python 找到 `main.py` 的路径（从 `sys.path` 里的 `backend/` 开始数）
- `classify_intent` 是那个模块对象字典里的键名

`mocker.patch` 的字符串参数本质上是在说：
> "在 `sys.modules` 里找到 `src.api.main` 这个模块对象，把它的 `classify_intent` 属性临时换掉。"
