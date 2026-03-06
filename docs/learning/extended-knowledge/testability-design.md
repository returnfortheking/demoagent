# 可测试性设计原则

> 跨模块通用知识——这些原则在项目所有模块里都有体现。
> 理解它们能帮你解释"为什么这样设计"，而不只是"这样设计能工作"。

---

## 核心洞察

**可测试性是设计质量，不是测试质量。**

一段代码难以测试，通常不是"测试写法不对"，而是代码本身的设计问题。
可测试的代码往往也是耦合更低、职责更清晰的代码。

这就是 TDD 的隐藏价值：它逼你在写实现之前先想"这东西怎么用"，自然就设计出更好的接口。

---

## 一、接缝理论（Seam Theory）

来源：Michael Feathers《修改代码的艺术》（*Working Effectively with Legacy Code*）

> **接缝（Seam）**：代码中可以改变行为而不修改该处代码的地方。

没有接缝，测试就必须在生产环境中运行，或者用重量级手段 mock 整个模块。

项目里的接缝都是有意设计的：

| 接缝位置 | 类型 | 项目例子 |
|---|---|---|
| 构造函数参数 | 对象接缝 | `CommandExecutor(executeFn, confirmFn)` |
| 构造函数默认值 | 对象接缝 | `ChatPanel(panel, client = defaultClient)` |
| 工厂函数 | 对象接缝 | `_get_chain()` / `_get_qa_chain()` |
| 模块导入路径 | 链接接缝 | `mocker.patch('src.chains.intent_classifier._get_chain')` |

**没有接缝的代码**是什么样的：

```typescript
// 坏：内部直接创建依赖，没有接缝
class CommandExecutor {
    async handle(response) {
        await vscode.commands.executeCommand(response.command); // 硬编码 VS Code 依赖
    }
}
```

测试这个就必须模拟整个 `vscode` 模块，成本极高。

---

## 二、依赖倒置原则（Dependency Inversion Principle）

SOLID 中的 D。

**传统方向（错）**：高层模块 → 直接依赖 → 低层具体实现

```
CommandExecutor → vscode.commands.executeCommand（具体实现）
```

**倒置后（对）**：高层模块 → 依赖抽象；低层实现 → 也依赖同一抽象

```
CommandExecutor → ExecuteFn（抽象）← vscode.commands.executeCommand（实现）
```

在项目里，`CommandExecutor` 不知道 `vscode` 的存在，它只知道"我有一个叫 `executeFn` 的函数"。高层业务逻辑不依赖底层具体实现，这就是倒置。

**Python 侧的对应**：

```python
# _get_chain() 是抽象接缝
def _get_chain() -> LLMChain:
    ...

# 测试只替换这一层，不关心 LLMChain 内部
mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)
```

---

## 三、谦逊对象模式（Humble Object Pattern）

来源：Gerard Meszaros《xUnit Test Patterns》

核心思想：**把难以测试的东西（副作用、外部依赖）和纯业务逻辑分离**，让业务逻辑变得"谦逊"（小而纯，容易测试）。

项目里最典型的例子：

```
ChatPanel（不谦逊——依赖 VS Code WebviewPanel，需要真实进程）
    ↓ 把纯逻辑提取出来
getHtmlContent()（谦逊——纯函数，返回字符串，无依赖）
CommandExecutor（谦逊——接收函数类型，不依赖 vscode）
```

Python 侧的对应：

```
classify_intent()（不谦逊——依赖 LLM 网络调用）
    ↓ 通过工厂函数隔离
_get_chain()（接缝——测试时整体替换）
JSON 解析逻辑（谦逊——纯字符串操作，可单独测试）
```

`ChatPanel` / `classify_intent` 是那个"不谦逊"的协调者（必须要外部依赖才能运行），
但通过提取，它内部的逻辑都被转移到了可以单独测试的单元。

---

## 四、测试替身分类（Test Doubles）

来源：Gerard Meszaros，"Test Double" 是所有替身的统称（不是 Mock）。

| 类型 | 特征 | 项目里的例子 |
|---|---|---|
| **Dummy** | 只是占位，不被实际用到 | `void extensionUri`（ChatPanel 里的占位参数） |
| **Stub** | 返回固定值，不验证调用 | `mockConfirm` 固定 `return true` |
| **Spy** | 记录调用参数，供事后断言 | `executedCommands.push(cmd)` |
| **Mock** | 预设期望，调用后自动验证 | sinon / jest.fn()（项目里没用到） |
| **Fake** | 有简化实现的真实替代 | 内存 Chroma（vs 持久化 Chroma） |

`commandExecutor.test.ts` 用的是 **Spy 模式**——用数组记录调用，测试后手动 assert。这是最轻量的做法，不需要 mock 框架：

```typescript
const executedCommands: string[] = [];
const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };

// 测试后
assert.strictEqual(executedCommands.length, 1);
assert.strictEqual(executedCommands[0], 'hispark-studio.build');
```

**什么时候需要 Mock 框架？**

当 Spy 模式太繁琐时——比如要验证"调用顺序"、"某方法被调用了 N 次但传入不同参数"。
项目目前的场景用 Spy 就够了。

---

## 五、"不要 Mock 你不拥有的东西"

来源：Steve Freeman & Nat Pryce《Growing Object-Oriented Software, Guided by Tests》

规则：**对第三方库（vscode、fetch、langchain）不要直接 mock，而是用自己的包装层隔离它。**

原因：
- 第三方 API 会变，你的 mock 不会跟着变，导致"测试通过但实际挂了"
- 直接 mock 第三方意味着你在测试自己对它的假设，不是它真实的行为

项目里的体现：

```python
# 不直接 mock OpenAI SDK 或 LLMChain 内部
# 而是 mock 自己的工厂函数（这是你拥有的边界）
mocker.patch("src.chains.intent_classifier._get_chain", return_value=mock_chain)
```

```typescript
// 不直接 mock vscode.commands.executeCommand
// 而是把它包进 lambda 注入，测试层传自己的 lambda
const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
const executor = new CommandExecutor(mockExecute, mockConfirm);
```

---

## 六、patch 目标：使用处而非定义处

Python 的 `mocker.patch` 有一个经典陷阱：

```python
# 错：patch 定义处（不生效）
mocker.patch("langchain.chains.LLMChain")

# 对：patch 使用处（生效）
mocker.patch("src.chains.intent_classifier._get_chain")
```

原因：Python 的 `import` 是把名字绑定到当前模块的命名空间。
patch 定义处只影响源模块，不影响已经 import 进来的引用。
**在哪里用到的，就在哪里替换。**

这个规则不只是 Python 的问题，它是所有语言里"测试替身注入点"的通用原则：
替换的是调用者持有的引用，不是被调用者的定义。

---

## 七、测试金字塔的逻辑

```
        /  E2E  \          ← 少量，慢，验证全链路
       / 集成测试 \         ← 适量，验证真实依赖协作
      /  单元测试  \        ← 大量，快，验证纯逻辑
```

| | 单元测试 | 集成测试 | E2E |
|---|---|---|---|
| 速度 | 毫秒级 | 秒级 | 分钟级 |
| 隔离性 | 完全隔离 | 部分隔离 | 无隔离 |
| 失败定位 | 精确 | 模糊 | 很模糊 |
| 维护成本 | 低 | 中 | 高 |

**关键结论**：单元测试只有在"有接缝可以注入替身"的前提下才能大量存在。
没有 DI 设计，测试全部堆到集成层和 E2E 层，速度慢、维护贵、失败难定位。

项目里三层测试的分工：

```
单元测试  → CommandExecutor、getHtmlContent、buildUrl、classify_intent（mock chain）
集成测试  → answer_question（真实 LLM）、/chat 接口（真实 FastAPI + mock chain）
E2E       → 真实 VS Code + 真实后端，验证消息从 webview 到后端再回来的完整链路
```

---

## 八、Testing Seam vs 标准 DI

这是一个重要的边界，项目里有明确记录（`docs/incidents/2026-03-04-chain-wrapper-in-production.md`）。

| | 标准 DI | Testing Seam |
|---|---|---|
| 定义 | 通过接口/参数将依赖从外部注入 | 专门为测试在生产代码里加的"后门" |
| 能否进生产代码 | 可以，这是正常设计 | **不能**，污染生产代码 |
| 识别特征 | 构造函数参数、工厂函数、默认值 | `createForTest()`、`_testOnly_xxx`、`if (process.env.TEST)` |
| 项目例子（对） | `constructor(panel, client = defaultClient)` | — |
| 项目例子（错） | — | `static createForTest(panel, client)` |

规则：**如果一个方法或字段的名字里有 `test`、`mock`、`fake`，它就不应该出现在 `src/` 里。**

---

## 九、DI 形态选型与 wiring 成本

你在实践里经常会遇到一个误区：把"是否使用 DI"和"是否使用容器"混为一谈。

- 手动构造注入（函数/接口入参）是 DI
- 容器注册解析（IoC）也是 DI

两者主要区别不是能力边界，而是**装配责任放在哪**。

### 什么是 wiring 成本

`wiring` 指的是：为了把依赖送到真正使用它的对象，需要经过多少层"手动接线"（构造参数透传、工厂参数透传、初始化顺序维护）。

当系统变大时，常见现象是：

- 上层类明明不用某依赖，却要接收并继续往下传
- 生产/测试实现切换时，改动点分散在多个调用处
- 生命周期（创建/销毁）策略无法集中管理

这就是 wiring 成本上升。

### 手动注入 vs 容器化 DI（选型对照）

| 维度 | 手动构造注入 | 容器化 DI |
|---|---|---|
| 初始心智负担 | 低 | 中（要理解注册/解析） |
| 小规模开发效率 | 高 | 中 |
| 大规模扩展（多模块） | 容易出现透传参数 | 装配集中，扩展更稳 |
| 多环境切换（prod/test） | 需在调用点分别切换 | 可在组合根集中切换 |
| 生命周期管理 | 依赖手工约定 | 可统一策略（singleton/scoped/transient） |
| 调试可见性 | 调用链直观 | 需理解容器解析路径 |

### 升级到容器的信号

出现以下 2-3 条，就可以考虑容器化 DI：

1. 同一个依赖被跨 3 层以上透传（中间层不使用）
2. 测试替换实现需要改多个入口文件
3. 资源对象（连接池/客户端）创建和回收点分散
4. 不同运行模式（本地/CI/线上）装配逻辑越来越多

### 什么时候保持手动注入更好

- 依赖数量少，组合点单一
- 架构层次浅，没有跨模块传递压力
- 对象生命周期简单（进程结束统一回收）

一句话：**容器化 DI 优化的是装配复杂度，不是业务复杂度。**

---

## 核心原则速记

```
1. 可测试性 = 设计质量，测试困难 = 设计信号
2. 依赖从外部注入，不要内部创建（DI）
3. 纯逻辑 / 副作用分离（Humble Object）
4. 第三方依赖用自己的包装层隔离，不要直接 mock
5. 测试替身能用 Spy 就不用 Mock 框架
6. patch 使用处，不是定义处
7. 单元测试大量 + 快速，E2E 少量 + 覆盖关键路径
8. Testing Seam 不进生产代码
9. DI 形态按规模选：容器优化装配复杂度，不替代业务设计
```

---

## 项目里的对应关系总览

| 原则 | Python 侧 | TypeScript 侧 |
|---|---|---|
| 接缝理论 | `_get_chain()` 工厂函数 | `CommandExecutor` 构造函数参数 |
| 依赖倒置 | `get_llm()` 工厂，业务层不关心厂商 | `ExecuteFn` 类型，业务层不关心 vscode |
| 谦逊对象 | JSON 解析逻辑提取，与 LLM 调用分离 | `getHtmlContent()` 从 `ChatPanel` 提取 |
| 不 mock 第三方 | patch `_get_chain`，不 patch LangChain | 注入 lambda，不 mock vscode 模块 |
| patch 使用处 | `mocker.patch("src.chains...._get_chain")` | 直接传 mockExecute 进构造函数 |
| Testing Seam 禁入 | 禁止 `_ChainWrapper`（事故记录） | 禁止 `createForTest()` |
| DI 形态选型 | 先手动注入，规模上来再容器化 | `CommandExecutor` 先函数注入，按需升级容器 |
