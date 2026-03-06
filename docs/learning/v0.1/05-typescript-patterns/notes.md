# 模块 05：TypeScript 工程模式（融合版）

> 基于 `hispark-ai-agent v0.1` 真实代码讲解
> 核心文件：`extension/src/executor/CommandExecutor.ts`、`extension/src/webview/chatHtml.ts`、`extension/src/client/ApiClient.ts`、`extension/src/webview/ChatPanel.ts`

---

## 这份笔记怎么读

模块 05 讲的不是语言基础，而是**工程决策**：同一个功能可以有多种写法，为什么这里选这种？
每一讲的核心问题都是：这个模式解决了什么问题，不用它会怎样。

---

## 第 1 讲：依赖注入（DI）—— 不是框架，是一种设计选择

### 【是什么】

依赖注入（Dependency Injection）：**把依赖从外部传进来，而不是在内部自己创建**。

这不需要任何框架（Angular/NestJS 的装饰器是 DI 框架），最朴素的形式就是构造函数参数。

### 【项目里在哪】

`extension/src/executor/CommandExecutor.ts`：

```typescript
type ExecuteFn = (command: string) => Promise<void>;
type ConfirmFn = (message: string) => Promise<boolean>;

export class CommandExecutor {
    constructor(
        private readonly executeFn: ExecuteFn,
        private readonly confirmFn: ConfirmFn
    ) {}
    // ...
}
```

### 【代码走读】

`CommandExecutor` 的核心业务是：根据 `ChatResponse` 决定是直接执行命令，还是先弹确认框再执行。

它依赖两个能力：

1. **执行命令**（`executeFn`）：生产环境里是 `vscode.commands.executeCommand`
2. **弹确认框**（`confirmFn`）：生产环境里是 `vscode.window.showWarningMessage`

这两个能力都通过构造函数注入，`CommandExecutor` 本身不 `import vscode`，完全不知道 VS Code 的存在。

生产代码里（`ChatPanel.ts`）是这样构造的：

```typescript
this._executor = new CommandExecutor(
    async (cmd: string) => { await vscode.commands.executeCommand(cmd); },
    async (msg: string) => {
        const result = await vscode.window.showWarningMessage(msg, '确认', '取消');
        return result === '确认';
    }
);
```

### 【如果不这样写】

如果 `CommandExecutor` 内部直接 `import * as vscode`，自己调 `vscode.commands.executeCommand`：

- 测试必须启动真实 VS Code 进程（或者 mock 整个 vscode 模块）
- `CommandExecutor` 与 VS Code 环境强耦合，换环境（如 Web Extension）成本高
- 业务逻辑（判断是否需要确认）和 VS Code 副作用混在一起，难以单独验证

### 【面试怎么说】

> "我的 `CommandExecutor` 通过构造函数接收 `executeFn` 和 `confirmFn` 两个函数，生产环境传 VS Code API，测试环境传 mock 函数。这样 `CommandExecutor` 本身不依赖 vscode 模块，可以在纯 Node.js 环境里跑单元测试，完全不需要 mock 框架。"

---

## 第 2 讲：函数类型作为依赖 vs 类/接口

### 【是什么】

DI 的依赖不一定要是"类"。TypeScript 支持把函数类型（`type ExecuteFn = ...`）作为依赖，更轻量。

### 【项目里在哪】

```typescript
type ExecuteFn = (command: string) => Promise<void>;
type ConfirmFn = (message: string) => Promise<boolean>;
```

### 【代码走读】

这是函数类型而不是接口（`interface`）或类（`class`）：

```typescript
// 函数类型（项目实际写法）
type ExecuteFn = (command: string) => Promise<void>;

// 接口写法（更重，通常在需要多方法时使用）
interface IExecutor {
    execute(command: string): Promise<void>;
}
```

为什么用函数类型？

- 依赖只有一个方法时，函数类型更简洁
- 传入时可以直接用 arrow function 或 async function，不需要实现接口
- 测试时直接传 `async (cmd) => { ... }` 即可，不需要 mock 类

### 【如果不这样写】

如果改成 `interface IExecutor { execute(command: string): Promise<void>; }`：

- 测试时需要构造一个实现了该接口的对象
- 比直接传函数多一层样板代码
- 在只需要单个函数的场景，接口反而过度设计

### 【面试怎么说】

> "依赖不一定是类。当依赖只是一个函数时，我直接用函数类型声明，测试时传 arrow function，比定义接口和 mock 类更简洁。TypeScript 的结构化类型系统让这种做法很自然。"

---

## 第 3 讲：DI 如何消除 Mock 框架依赖

### 【是什么】

当依赖通过构造函数注入后，测试只需要传入普通函数——不需要 `sinon`、`jest.fn()` 这类 mock 框架。

### 【项目里在哪】

`extension/src/test/suite/commandExecutor.test.ts`：

```typescript
test('Normal command executes directly without confirmation', async () => {
    const executedCommands: string[] = [];
    const confirmMessages: string[] = [];

    const mockExecute = async (cmd: string) => { executedCommands.push(cmd); };
    const mockConfirm = async (msg: string) => { confirmMessages.push(msg); return true; };

    const executor = new CommandExecutor(mockExecute, mockConfirm);
    // ...

    assert.strictEqual(executedCommands.length, 1);
    assert.strictEqual(executedCommands[0], 'hispark-studio.build');
    assert.strictEqual(confirmMessages.length, 0);
});
```

### 【代码走读】

`mockExecute` 和 `mockConfirm` 都是普通的 `async` 函数：

- 用数组记录调用参数（相当于 spy）
- 通过返回值控制行为（`return true` / `return false`）
- 测试结束后直接 `assert` 数组内容

整个测试文件没有任何 `import sinon` 或 `import jest`——不需要 mock 框架，因为 DI 让"注入测试替身"变成了直接传参数。

测试覆盖了 4 个场景：

| 场景 | 期望行为 |
|---|---|
| 不需要确认的命令 | 直接执行，不调 confirmFn |
| 需要确认且用户同意 | 先调 confirmFn，再执行 |
| 需要确认但用户拒绝 | 调了 confirmFn，不执行 |
| answer 类型响应 | 直接返回，两个函数都不调 |

### 【如果不这样写】

如果 `CommandExecutor` 内部 `import vscode` 直接调 API：

- 必须 mock `vscode` 模块（`proxyquire` / `jest.mock`）
- 或者只能在真实 VS Code 进程里跑（Extension Host 测试，启动慢）
- 测试速度和可靠性都大幅下降

### 【面试怎么说】

> "因为 `CommandExecutor` 的依赖是通过构造函数注入的，测试里我只需要传两个 async 函数进去，用数组记录调用参数来验证行为。完全没用 mock 框架，测试代码也更易读——每个 test case 的意图一眼就能看出来。"

---

## 第 4 讲：纯函数提取——`getHtmlContent()` 为什么不在 `ChatPanel` 里

### 【是什么】

纯函数：相同输入永远返回相同输出，无副作用。
把纯逻辑从有副作用的类中提取成独立函数，可测试性和可复用性都更好。

### 【项目里在哪】

`extension/src/webview/chatHtml.ts`：

```typescript
export function getHtmlContent(): string {
    return `<!DOCTYPE html>
<html lang="zh-CN">
...
</html>`;
}
```

在 `ChatPanel.ts` 里使用：

```typescript
import { getHtmlContent } from './chatHtml';
// ...
panel.webview.html = getHtmlContent();
```

### 【代码走读】

`getHtmlContent()` 是一个纯函数：

- 输入：无（或隐式的模板字面量）
- 输出：固定的 HTML 字符串
- 副作用：无

如果把这段 HTML 字符串留在 `ChatPanel.ts` 里（比如直接写在 `createOrShow` 里），测试 HTML 结构就必须实例化 `ChatPanel`，而 `ChatPanel` 依赖 `vscode.WebviewPanel`，在没有 VS Code 进程的环境里无法创建。

提取成独立函数后，`chatPanel.test.ts` 直接测它：

```typescript
import { getHtmlContent } from '../../webview/chatHtml';

test('HTML structure completeness', () => {
    const html = getHtmlContent();
    assert.ok(html.includes('<!DOCTYPE html>'));
});

test('No external scripts or resources', () => {
    const html = getHtmlContent();
    // 正则检查 src/href 属性，确保无外部 URL
    assert.ok(html.includes('Content-Security-Policy'));
});
```

这个测试**不需要 VS Code 进程**，在普通 Node.js 里就能跑。

### 【如果不这样写】

如果 HTML 内联在 `ChatPanel` 里：

- HTML 结构测试必须启动 Extension Host 进程
- CSP 合规性（无外部 URL）无法用快速单测验证
- HTML 逻辑和 WebviewPanel 生命周期逻辑混在一起，文件责任不清

### 【面试怎么说】

> "我把 HTML 生成提取成 `getHtmlContent()` 纯函数，放在独立文件。这样测试 HTML 结构和 CSP 合规性时，不需要启动 VS Code 进程，直接在 Node.js 里跑断言就行。单一职责 + 可测试性是这个提取的核心驱动。"

---

## 第 5 讲：TypeScript `interface` 设计——`ChatResponse`

### 【是什么】

TypeScript `interface` 声明数据契约：描述对象的"形状"，不包含实现。

### 【项目里在哪】

`extension/src/client/ApiClient.ts`：

```typescript
export interface ChatResponse {
    type: 'action' | 'answer';
    // action fields
    command?: string;
    args?: Record<string, unknown>;
    requires_confirmation?: boolean;
    description?: string;
    // answer fields
    answer?: string;
    sources?: string[];
}
```

### 【代码走读】

几个设计细节：

**1. 字面量联合类型（Discriminated Union）**

```typescript
type: 'action' | 'answer';
```

不用 `string`，而是用字面量联合。好处：

- TypeScript 能做穷举检查（exhaustiveness check）
- IDE 自动补全 `'action'` / `'answer'`，不会拼错
- 在 `CommandExecutor.handle()` 里 `if (response.type !== 'action') return;` 类型可以被 narrowing

**2. 可选字段（`?:`）**

`command`、`answer` 等字段是可选的，因为 action 类型不包含 `answer`，answer 类型不包含 `command`。

这和后端 Python 的 Pydantic 模型设计是镜像关系：

```python
class ActionResponse(BaseModel):
    type: str = "action"
    command: str
    requires_confirmation: bool = False
    description: Optional[str] = None
```

**3. `Record<string, unknown>`**

`args?: Record<string, unknown>` 表示"键是字符串，值是任意类型的对象"，比 `any` 更安全（`unknown` 需要类型收窄才能使用）。

### 【interface vs type alias】

```typescript
interface ChatResponse { ... }  // 可以被 extends，声明合并
type ChatResponse = { ... }     // 不支持声明合并，更适合联合/交叉类型
```

这里用 `interface` 是因为它是一个单纯的对象形状描述，没有联合/交叉的需求。

### 【面试怎么说】

> "前后端之间的数据契约我用 TypeScript `interface` 定义，`type` 字段用字面量联合而不是 `string`，这样在处理响应时 TypeScript 可以做类型 narrowing，分支逻辑的类型安全由编译器保证，不是运行时 if-else 猜出来的。"

---

## 第 6 讲：`ApiClient` 的方法拆分设计

### 【是什么】

把复合操作拆成最小可测单元（`buildUrl`、`parseResponse`、`sendMessage`），每个方法职责单一，可以分别测试。

### 【项目里在哪】

`extension/src/client/ApiClient.ts`：

```typescript
export class ApiClient {
    constructor(private readonly baseUrl: string) {}

    buildUrl(path: string): string {
        const cleanedBaseUrl = this.baseUrl.replace(/\/$/, '');
        const normalizedPath = path.startsWith('/') ? path : `/${path}`;
        return cleanedBaseUrl + normalizedPath;
    }

    parseResponse(raw: object): ChatResponse {
        return raw as ChatResponse;
    }

    async sendMessage(message: string, threadId: string): Promise<ChatResponse> {
        const url = this.buildUrl('/chat');
        const response = await fetch(url, { ... });
        const data = await response.json() as object;
        return this.parseResponse(data);
    }
}

export const defaultClient = new ApiClient('http://localhost:8000');
```

### 【代码走读】

**`buildUrl()`**：处理 URL 拼接的两个边界问题：

1. `baseUrl` 末尾可能有 `/`：`'http://localhost:8000/'.replace(/\/$/, '')` → 去掉
2. `path` 可能没有前缀 `/`：统一加上

这两个逻辑提取出来之后，可以用纯函数测试覆盖：

```typescript
test('buildUrl avoids double slash when baseUrl has trailing slash', () => {
    const client = new ApiClient('http://localhost:8000/');
    assert.strictEqual(client.buildUrl('/chat'), 'http://localhost:8000/chat');
});
```

**`parseResponse()`**：目前是 `raw as ChatResponse`（简单类型断言）。单独提取的意义在于：

- 将来做 Zod 校验或字段转换时，改这一个方法即可
- 测试可以单独验证解析逻辑，不需要 mock `fetch`

**`sendMessage()`**：真实网络调用，集成测试覆盖，不在单元测试里 mock。

**`defaultClient`**：模块级导出的默认实例，生产环境直接使用，测试环境可以传入自定义实例替换。

### 【如果不这样写】

如果把 URL 拼接和 `fetch` 都写在 `sendMessage` 里：

- `buildUrl` 的边界条件（双斜杠）无法单独测试
- 所有测试都要 mock `fetch`，测试成本更高

### 【面试怎么说】

> "我把 `ApiClient` 拆成 `buildUrl`、`parseResponse`、`sendMessage` 三个方法。URL 拼接和响应解析是纯逻辑，可以单独测试，不需要 mock 网络；`sendMessage` 有 `fetch` 副作用，留给集成测试。这样单测快而准，集成测试覆盖真实链路。"

---

## 第 7 讲：`Thenable<T>` vs `Promise<T>`——VS Code 的历史遗留

### 【是什么】

`Thenable<T>` 是 VS Code API 返回的类型，它只有 `.then()` 方法，是 `Promise` 的超集接口。
`Promise<T>` 是标准 JavaScript Promise。

### 【项目里在哪】

`ChatPanel.ts`：

```typescript
async (cmd: string) => { await vscode.commands.executeCommand(cmd); }
```

`vscode.commands.executeCommand` 返回 `Thenable<T>`，但 `await` 可以用于任何 `Thenable`，所以这里直接 `await` 没有问题。

### 【为什么 VS Code 用 Thenable 而不是 Promise】

历史原因：VS Code 最早开发时（2015 年），JavaScript 的 `Promise` 还没有标准化。VS Code 用的是自己的 promise 实现（类似 `TPromise`），对外暴露成 `Thenable` 接口，只承诺"这个东西有 `.then()`"，不承诺是标准 `Promise`。

现代代码里：

- `await Thenable` → 完全没问题，`await` 对 Thenable 友好
- `Promise.all([Thenable, ...])` → **有问题**，`Promise.all` 期望的是 `PromiseLike`，但 VS Code 的 `Thenable` 类型定义满足这个要求

实际工程里：直接 `await vscode.xxx()` 是最安全的用法，不要试图把 VS Code 返回值存成 `Promise<T>` 变量。

### 【面试怎么说】

> "VS Code API 返回 `Thenable<T>` 不是 `Promise<T>`，这是历史遗留。实际用法是直接 `await`，因为 `await` 对任何 Thenable 都有效。如果要组合多个 VS Code 调用，先用 `await` 逐个解包，而不是直接传给 `Promise.all`。"

---

## 第 8 讲：`ChatPanel` 里 DI 的全貌——两条 DI 链

### 【是什么】

`ChatPanel` 是整个 Extension 的核心协调者，它组合了两条 DI 链。

### 【项目里在哪】

`extension/src/webview/ChatPanel.ts`：

```typescript
export class ChatPanel {
    private readonly _client: ApiClient;
    private readonly _executor: CommandExecutor;

    constructor(panel: vscode.WebviewPanel, client: ApiClient = defaultClient) {
        this._client = client;
        this._executor = new CommandExecutor(
            async (cmd) => { await vscode.commands.executeCommand(cmd); },
            async (msg) => {
                const result = await vscode.window.showWarningMessage(msg, '确认', '取消');
                return result === '确认';
            }
        );
    }
}
```

### 【代码走读】

**DI 链 1：`ApiClient` 注入**

- 构造函数参数：`client: ApiClient = defaultClient`
- 生产代码：`new ChatPanel(panel)` → 使用默认值 `defaultClient`（指向 8000 端口）
- E2E 测试：`new ChatPanel(panel, new ApiClient('http://localhost:8001'))` → 注入测试后端

**DI 链 2：`CommandExecutor` 内部构造**

- `CommandExecutor` 接收函数类型依赖
- `ChatPanel` 在构造时把 VS Code API 包装成 lambda 传进去
- `CommandExecutor` 本身不知道 VS Code 的存在

**为什么 `_executor` 不也作为参数注入？**

因为 `CommandExecutor` 的两个 lambda 直接依赖 `vscode`，已经处于 Extension Host 进程里，没有"需要换掉这两个实现"的测试场景。`CommandExecutor` 本身是通过函数类型 DI 实现可测的，不需要再在 `ChatPanel` 层面对它做 DI。

**没有 `createForTest()` 方法：**

有些框架会加 `static createForTest(panel, client)` 来专门给测试用。这里没有——因为标准构造函数已经支持参数注入，不需要专属测试入口（专属测试入口是 Testing Seam，会污染生产代码）。

### 【面试怎么说】

> "`ChatPanel` 组合了两条 DI 链：`ApiClient` 通过构造函数参数注入（默认值是生产用的 `defaultClient`），`CommandExecutor` 在内部构造时接收 lambda。这样 E2E 测试只需要传不同 `baseUrl` 的 `ApiClient` 就能切换后端地址，不需要任何测试专用入口方法。"

---

## 第 9 讲：手动注入 vs 容器化 DI（VS Code 风格）

### 【是什么】

这两种写法都属于 DI（依赖注入），区别不在"是不是 DI"，而在"谁来负责装配依赖"：

- 手动构造注入（你当前项目）：调用方显式 `new` 并传入依赖
- 容器化 DI（VS Code IDE 本体风格）：先注册服务，再由容器按声明解析依赖

面试时建议用这两个术语：

- `Manual Constructor Injection / Functional DI`
- `Container-based DI / Service Registration + Resolution`

### 【项目里在哪】

你当前项目属于手动注入：

```typescript
const executor = new CommandExecutor(
    async (cmd: string) => { await vscode.commands.executeCommand(cmd); },
    async (msg: string) => {
        const result = await vscode.window.showWarningMessage(msg, '确认', '取消');
        return result === '确认';
    }
);
```

VS Code IDE 本体属于容器化 DI（示意）：

```typescript
// 注册（组合根）
registerSingleton(ICommandRuntime, CommandRuntime);

// 使用处只声明依赖
class ActionController {
    constructor(@ICommandRuntime private readonly runtime: ICommandRuntime) {}
}
```

### 【代码走读】

你一直追问的 `wiring`，本质是"装配链路"成本：依赖要经过多少层手动传递。

手动注入的装配路径：

```text
A new B(execFn, confirmFn)
  -> B 再 new C(...)
  -> C 再 new D(...)
```

依赖图一旦变深，很多层会出现"只转发不使用"的参数，这就是 wiring 成本上涨。

容器化 DI 的装配路径：

```text
App 启动时统一 register
业务类只声明“我要什么服务”
InstantiationService 负责解析和复用
```

为什么你当前体感差异不明显？你的判断是对的：

- 依赖数量少
- 组合点集中（基本就在 `ChatPanel`）
- 跨层传播浅
- 生命周期管理简单（进程级统一回收）
- 生产/测试切换点不多

在这个规模下，手动注入是高性价比方案。

### 【如果不这样写】

两边都可能写过头，关键是规模匹配：

- 小项目过早上容器：注册样板、心智负担、调试跳转成本都会上升
- 大项目一直手动传：会出现参数透传、装配分散、环境切换改动面大

一句话：容器主要优化的是"装配复杂度"，不是"业务复杂度"。

### 【面试怎么说】

> "我现在用的是手动构造注入（函数注入），因为依赖少、组合点集中，容器化收益暂时不显著。容器化 DI 更适合依赖图深、跨模块复用多、需要统一生命周期和环境切换策略的场景。本质上，两者都属于 DI，只是装配责任的位置不同。"

---

## 总结：模块 05 的知识地图

```text
CommandExecutor
  ← 构造函数注入 ExecuteFn + ConfirmFn（函数类型 DI）
  ← 测试时传 plain async function，无需 mock 框架

getHtmlContent()
  ← 纯函数提取，脱离 ChatPanel 可独立测试
  ← 测试 HTML 结构 + CSP 合规性，不依赖 VS Code 进程

ApiClient
  ← buildUrl / parseResponse 拆成最小可测单元
  ← defaultClient 模块级默认实例，测试时传入替换
  ← ChatResponse interface：字面量联合类型 + 可选字段

ChatPanel
  ← client 通过构造函数注入（默认值 = defaultClient）
  ← executor 在内部构造，lambda 包装 VS Code API
  ← 无 createForTest()：标准 DI 不需要测试专用入口

DI 选型
  ← 当前阶段：手动构造注入（低心智、低样板）
  ← 规模增长后：容器化 DI（统一装配与生命周期）
```

---

## 面试题速答

**Q1：什么是依赖注入，你在项目里怎么用的？**
> "依赖注入就是把依赖从外部传进来而不是内部自己创建。我在 `CommandExecutor` 里注入了 `executeFn` 和 `confirmFn` 两个函数类型，生产传 VS Code API，测试传 plain async function，完全不需要 mock 框架。在 `ChatPanel` 里注入了 `ApiClient`，生产用默认 8000 端口，E2E 测试用 8001 端口，两处 DI 覆盖了不同层的测试需求。"

**Q2：你怎么测试 VS Code Extension 的代码？**
> "分三层：纯逻辑（`CommandExecutor`、`getHtmlContent`）用普通 Node.js 单测，不依赖 VS Code 进程；`ApiClient` 的 URL 拼接和响应解析也是单测；整个前后端链路用 E2E 测（`@vscode/test-electron` 启动真实 VS Code + subprocess 启动后端）。DI 是让单测能在 Extension 里工作的关键，没有 DI 就没有轻量单测。"

**Q3：TypeScript interface 和 type 有什么区别？**
> "最实际的区别：`interface` 支持声明合并（declaration merging）和 `extends`，`type` 支持联合类型（`|`）和交叉类型（`&`）。对象形状描述优先用 `interface`，需要表达'这个类型是 A 或 B'时用 `type` 的联合。项目里 `ChatResponse` 用 `interface`，`type` 字段内部用字面量联合 `'action' | 'answer'`。"

**Q4：`Thenable` 和 `Promise` 有什么区别？**
> "VS Code API 返回 `Thenable<T>`，只承诺有 `.then()` 方法，是历史遗留。直接 `await` 没问题，`await` 对任何 Thenable 有效。实际编码规则：VS Code 返回值直接 `await`，不要试图赋给 `Promise<T>` 变量或传给 `Promise.all`。"

**Q5：`CommandExecutor` 的测试里为什么没有 import sinon 或 jest？**
> "因为 DI 把'如何替换依赖'变成了'如何传参数'。两个依赖都是普通函数类型，测试直接传 async lambda 进去，用数组记录调用参数。这比 mock 框架更轻——没有框架配置，没有 restore/reset 步骤，assert 直接检查数组，测试意图一目了然。"

**Q6：你为什么没直接上容器化 DI？**
> "当前项目依赖数量少、组合点集中，手动构造注入已经能覆盖生产与测试切换，且可读性更高。容器化 DI 的主要收益在于大规模系统里的统一装配和生命周期管理；在当前阶段边际收益不高，所以我选择先保持手动注入，等依赖图变深再升级。"
