# 模块 06：Extension E2E 测试 — 学习笔记

> 完整开发复盘见 `dev-retrospective.md`。
> 本文聚焦"是什么 / 为什么 / 面试怎么说"。

---

## 一、整体架构：为什么要两阶段两进程

### 是什么

```
npm run test:e2e
      │
      ▼
Node.js 进程（runTests.ts）← 你是指挥官，不在 VS Code 里
      │
      ├─ spawn uvicorn（Python 后端，port 8001）
      │
      ├─ Phase 1：启动 VS Code-A → Mocha 在 Extension Host 内跑
      │           index.ts → extensionHost.test.ts
      │           VS Code-A 退出
      │
      └─ Phase 2：启动 VS Code-B（CDP port 9222，keepAlive 45s）
                  indexKeepAlive.ts → 打开 webview
                  webview.playwright.ts → Playwright 从外部连入操作
```

### 为什么两个 VS Code 进程

Phase 1 用 Mocha 测"逻辑层"（HTTP、命令激活、DI），VS Code 跑完直接退出。
Phase 2 需要 VS Code 保持运行，让 Playwright 有时间操作 webview，所以另起一个带 keepAlive 的 VS Code。

### 为什么 Playwright 在外部 Node.js 进程，而不在 Extension Host 里

从 Electron Extension Host 内部向自己的 `--remote-debugging-port` 发 CDP 连接，在 Windows 上会**死锁**（自引用 CDP 连接）。解法：把 Playwright 移到 `runTests.ts` 所在的外部 Node.js 进程，从外部连进 VS Code。

### 面试怎么说

> "Extension 的 E2E 测试分两阶段。Phase 1 用 `@vscode/test-electron` 在 VS Code 的 extension host 里跑 Mocha，测 HTTP 调用、命令激活、DI 构造函数。Phase 2 另起一个带 CDP 端口的 VS Code，用 Playwright 从外部进程连进去，操作 webview DOM，验证完整的用户交互链路。两阶段分开是因为 Playwright 不能在 Extension Host 里自连 CDP，Windows 上会死锁。"

---

## 二、@vscode/test-electron

### 是什么

VS Code 官方测试库。帮你做：
1. 下载对应版本 VS Code（缓存到 `.vscode-test/`）
2. 用 CLI 启动 VS Code，加载你的扩展
3. VS Code 内部自动调用 `extensionTestsPath` 文件的 `run()` 导出函数
4. 测试跑完，VS Code 退出，返回 Promise

### 关键参数

```typescript
await runTests({
    extensionDevelopmentPath,   // 扩展根目录，VS Code 加载这个扩展
    extensionTestsPath,         // 指向 Mocha runner 的 JS 文件
    extensionTestsEnv: {        // 注入环境变量到 Extension Host
        HISPARK_TEST_BACKEND_PORT: '8001',
    },
    launchArgs: [               // 传给 VS Code CLI 的额外参数
        '--remote-debugging-port=9222'
    ],
});
```

- `extensionDevelopmentPath`：告诉 VS Code "把这个目录作为扩展加载"
- `extensionTestsPath`：VS Code 启动后自动 `require` 这个文件并调用 `run()`
- `extensionTestsEnv`：环境变量注入，测试代码通过 `process.env` 读取
- `launchArgs`：Phase 2 用来开启 CDP 端口

### 面试怎么说

> "`@vscode/test-electron` 帮我管理 VS Code 的生命周期——下载、启动、注入扩展、运行测试、退出。我只需要提供 Mocha runner 文件的路径，它会在 VS Code 内部调用 `run()` 函数。测试端口通过 `extensionTestsEnv` 注入，在 Extension Host 里用 `process.env` 读取，不需要硬编码。"

---

## 三、后端进程管理

### child_process.spawn

```typescript
const backend = cp.spawn(
    'python',
    ['-m', 'uvicorn', 'src.api.main:app', '--host', '127.0.0.1', '--port', '8001'],
    { cwd: backendDir, stdio: 'inherit' }
);
```

`spawn` 只是"启动了进程"，不代表端口已开放监听。

### waitForHealth 轮询

```typescript
// 每秒检查 /health，最多 30 次
await waitForHealth(`http://127.0.0.1:8001/health`);
```

为什么不 `sleep(3000)`？固定 sleep 在快机器上浪费时间，在慢机器上可能不够。轮询在服务就绪的第一时间继续，更稳健。

**对比 Python E2E**：pytest 里用 `subprocess.Popen` + `yield`，原理完全一样，只是语言不同。

### finally 保证清理

```typescript
try {
    // 所有测试逻辑
} finally {
    backend.kill();  // 无论成功或失败，都杀掉后端进程
}
```

不加 `finally`：测试失败时后端进程残留，下次跑测试时 8001 端口被占用。

**对比 pytest**：`yield` fixture 里 `yield` 之后的代码等同于 `finally`。

### 面试怎么说

> "后端用 `child_process.spawn` 启动，启动后不能直接用，要轮询 `/health` 确认就绪。结束时用 `finally` 保证无论测试成败都 `kill()` 掉进程，避免端口残留。这和 Python 里的 pytest yield fixture 是同一个模式。"

---

## 四、Mocha TDD 接口

### 两种接口对比

| 接口 | 关键字 | 默认 |
|------|--------|------|
| BDD | `describe / it / before / after` | ✅ Mocha 默认 |
| TDD | `suite / test / setup / teardown` | 需显式声明 |

```typescript
// 必须声明，否则 suite is not defined
const mocha = new Mocha({ ui: 'tdd', timeout: 30000 });
```

VS Code 官方示例都用 TDD 接口，历史惯例。

### Mocha runner 是胶水层

```typescript
// index.ts —— @vscode/test-electron 要求这个文件导出 run()
export async function run(): Promise<void> {
    const mocha = new Mocha({ ui: 'tdd' });
    // 扫描同目录下所有 *.test.js
    fs.readdirSync(__dirname)
        .filter(f => f.endsWith('.test.js'))
        .forEach(f => mocha.addFile(path.resolve(__dirname, f)));

    return new Promise((resolve, reject) => {
        mocha.run(failures => failures > 0 ? reject(...) : resolve());
    });
}
```

框架约定：`extensionTestsPath` 指向的文件必须导出 `run(): Promise<void>`。这个文件负责把 Mocha 的回调风格包装成 Promise，让 `runTests.ts` 的 `await` 能等到结果。

---

## 五、依赖注入如何让 E2E 成为可能

### 问题

`ChatPanel` 原来硬编码 `defaultClient`（port 8000），E2E 测试后端在 8001。

### 错误解法：Testing Seam

```typescript
// ❌ 不能这样做
static createForTest(panel, client) { ... }
```

方法名含 `test` 字样 = Testing Seam = 生产代码为测试妥协。这与 `_ChainWrapper` 事故同款错误。

### 正确解法：构造函数可选参数

```typescript
// ✅ 标准 DI，不含测试语义
constructor(panel: vscode.WebviewPanel, client: ApiClient = defaultClient) {
    this._client = client;
}
```

- 生产代码：`new ChatPanel(panel)` → 走默认 8000，无感知
- 测试代码：`new ChatPanel(panel, new ApiClient('http://127.0.0.1:8001'))` → 注入 8001

**DI 的价值在问题 5 得到证明**：`indexKeepAlive.ts` 需要打 8001，直接用构造函数注入就解决了，不需要改任何生产逻辑。

### 面试怎么说

> "我把 `ChatPanel` 的构造函数改成 `constructor(panel, client = defaultClient)`，这是标准依赖注入。生产代码调用方式不变，测试时直接传入指向 8001 的 client，零侵入。这个设计在 E2E 测试的 keepAlive 场景里直接体现了价值——不需要任何 if/switch 判断环境，就能切换后端地址。"

---

## 六、CDP 连接时机与 OOPIF（核心难点）

### OOPIF 是什么

VS Code webview 是 **Out-Of-Process IFrame**：不同源的 iframe（`vscode-webview://`）运行在独立的 Chromium 渲染进程中。

```
VS Code Electron 进程
  ├─ 渲染进程 A：主窗口 HTML（vscode-file://）
  │    └─ <iframe class="webview">  ← 壳，外层
  └─ 渲染进程 B：webview 内容（vscode-webview://）← 独立进程！
       └─ <iframe name="active-frame">  ← 你的 HTML
            └─ #chat-input、#send-btn、#messages
```

### CDP 会话时机是决定性变量

通过 5 组控制变量实验验证的结论：

| 组 | 连接方式 | frame 访问 | 结果 |
|----|---------|-----------|------|
| ① | 5s sleep | frameLocator | FAIL |
| ② | 直连（无等待） | frameLocator | FAIL（ECONNREFUSED）|
| ③ | 重试连接 | page.frames() | PASS |
| ④ | 重试连接 | frameLocator | PASS |
| ⑤ | 5s sleep | page.frames() | FAIL |

**结论：决定成败的是连接时机，不是 frame 访问方式。**

- **早连接（重试）**：`Target.setAutoAttach` 在 Webview OOPIF 创建之前下达 → 捕获 `attachedToTarget` 事件 → frame 可见
- **晚连接（5s sleep）**：`Target.setAutoAttach` 在 OOPIF 已独立运行后下达 → 对已运行 OOPIF 的发现能力不可靠 → frame 不可见

### 重试连接实现

```typescript
async function connectToVsCode(cdpPort: number): Promise<Browser> {
    for (let i = 0; i < 20; i++) {        // 最多试 20 次
        try {
            return await chromium.connectOverCDP(
                `http://localhost:${cdpPort}`,
                { timeout: 3000 }
            );
        } catch {
            await sleep(500);              // 连不上等 500ms 再试
        }
    }
    throw new Error('Could not connect');
}
```

CDP 端口一开放就立刻连上，比固定 sleep 更早建立会话。

### 固定 sleep 的两个问题

1. **太短**：CDP 端口还没开，ECONNREFUSED
2. **太长**：OOPIF 已独立运行，`Target.setAutoAttach` 无法可靠发现已有 OOPIF target，frame 不可见

### frameLocator vs page.frames()

两者在相同连接条件下结果完全一致。本项目保留两条路是为了健壮性：

```typescript
// 主路径：CDP frame 树查找（已经过实验验证稳定）
const activeFrame = await findActiveFrameViaCdp(page);
if (activeFrame) {
    await activeFrame.locator('#chat-input').fill(MESSAGE);
    return;
}

// 兜底：frameLocator（DOM 路径）
const webviewFrame = page
    .frameLocator('iframe.webview')
    .frameLocator('#active-frame');
await webviewFrame.locator('#chat-input').fill(MESSAGE);
```

### 面试怎么说

> "VS Code 的 webview 是 OOPIF——运行在独立 Chromium 进程里。测试时发现 Playwright 有时能访问到 webview，有时访问不到。我设计了 5 组控制变量实验，固定其他变量分别测试'连接时机'和'frame 访问方式'对结果的影响。实验证明决定成败的是 CDP 会话建立的时机：早连接（重试）时 CDP 会话跟随 OOPIF 初始化，frame 可见；晚连接（固定 sleep）时 OOPIF 已完全隔离，frame 不可见。这个发现也纠正了外部工具对根因的错误解释。"

---

## 七、Playwright 核心概念速查

### 对象层级

```
Browser（VS Code 进程）
  └── BrowserContext（独立 cookie/存储空间）
        └── Page（一个窗口/标签页）
              └── Frame（iframe）
                    └── Locator（定位元素）
```

### 连接方式

```typescript
// 连接已运行的 Electron/Chrome（本项目用法）
const browser = await chromium.connectOverCDP('http://localhost:9222');

// 启动新浏览器（普通网页测试用）
const browser = await chromium.launch();
```

### Locator 常用操作

```typescript
locator('#chat-input').fill('文字')     // 填文本（自动等可交互）
locator('#send-btn').click()            // 点击（自动等可见）
locator('#messages div').first()        // 取第一个匹配
locator('iframe.webview').count()       // 数量（不会因不存在而报错）
locator('iframe.webview').waitFor()     // 显式等待出现
locator('iframe.webview').getAttribute('class')  // 读属性
locator('#messages div').textContent()  // 读文本内容
```

### 等待机制

Playwright 所有操作都内置自动等待：先等元素出现、可见、可交互，再执行操作。`timeout` 是等待的上限，不是操作的延迟。

### deadline 轮询模式

```typescript
const deadline = Date.now() + 20000;    // 截止时刻
while (Date.now() < deadline) {
    // 检查条件
    await sleep(300);                   // 每 300ms 检查一次
}
```

适合"等待某个状态"而非"等待某个元素"。

---

## 八、keepAlive 机制

### v0.1 原始实现（固定 sleep）

```typescript
// indexKeepAlive.ts —— 早期版本
export async function run(): Promise<void> {
    const client = new ApiClient(`http://127.0.0.1:${backendPort}`);
    const panel = vscode.window.createWebviewPanel(...);
    panel.webview.html = getHtmlContent();
    new ChatPanel(panel, client);       // DI 注入 8001

    await new Promise(r => setTimeout(r, 45000));  // 保活 45 秒
}
```

为什么不用 `vscode.commands.executeCommand('hispark-ai-agent.openChat')`？
因为命令底层走 `createOrShow()` → `defaultClient`（port 8000），会打到错误的后端。直接用 DI 构造函数才能注入测试端口。

45 秒 = VS Code 启动（5s）+ webview 渲染（5s）+ Playwright 连接操作（10s）+ LLM 响应（5s）+ 余量（20s）。

**问题**：用例 10 秒跑完，VS Code 还要傻等剩下 35 秒才关闭，每次 E2E 耗时约 1 分钟。

---

### v0.1.3 改进：信号文件机制

**核心思路**：用例跑完后立刻发信号，VS Code 收到信号后立即关闭，而不是等固定时间。

```
runTests.ts                          indexKeepAlive.ts
─────────────────────────────────    ─────────────────────────────────
创建信号文件路径 signalFile            轮询检查 signalFile 是否出现
注入 E2E_SIGNAL_FILE 环境变量  ──→   每 500ms 检查一次（最多等 90s）
                                                │
Playwright 用例执行完毕                          │
  → 成功：writeFileSync(signalFile, 'pass')     │
  → 失败：writeFileSync(signalFile, 'fail')  ←──┘ signalFile 出现
  → finally: await keepAliveVsCode               VS Code 读取结果后退出
                                              runTests.ts 的 await 返回
```

**两种模式**（通过 `E2E_MODE` 环境变量控制）：

| 模式 | 用途 | 失败时行为 |
|------|------|-----------|
| `gate` | CI / commit-msg hook | 立刻退出（不等待） |
| `manual` | 本地手动调试 | 等 5 秒再退出（方便截图排查） |

**效果**：E2E 总耗时从 ~60s 降至 ~25s（用例执行完立刻关闭，节省 35s 固定等待）。

### 面试怎么说

> "最初 keepAlive 用固定 45 秒 sleep，用例 10 秒跑完后还要傻等 35 秒。我改成信号文件机制：runTests.ts 把信号文件路径通过环境变量注入给 indexKeepAlive.ts，Playwright 用例执行完后写入 pass/fail，keepAlive 侧轮询到文件出现后立即退出，VS Code 也随之关闭。同时用 E2E_MODE 区分 gate 模式（失败立刻退出）和 manual 模式（失败等 5 秒方便排查），E2E 总耗时从 60 秒降到 25 秒。"

---

## 九、面试高频问答

### "你的 Extension 怎么做自动化测试的？"

> "分两层。第一层在 VS Code extension host 里用 Mocha 跑，可以直接调 VS Code API，测 HTTP 请求、命令激活、DI 构造函数，这层是逻辑层验证。第二层用 Playwright 从外部 Node.js 进程通过 CDP 连进 VS Code，找到 webview 里的 iframe，模拟用户填写消息、点击发送，断言响应渲染到 DOM——这层是完整链路的 UI 验证。一条命令 `npm run test:e2e` 跑通全流程，包括自动启动 Python 后端。"

### "前后端联合测试怎么做的？"

> "runTests.ts 负责编排：先用 child_process.spawn 启动 Python uvicorn 后端，轮询 /health 确认就绪，再跑两个阶段的 VS Code 测试。结束时 finally 块保证 kill 掉后端进程。测试的端口通过环境变量注入，避免和开发环境的后端冲突。"

### "依赖注入在这里起了什么作用？"

> "E2E 测试后端跑在 8001，但 ChatPanel 默认打 8000。如果没有 DI，只能改生产代码或加 `createForTest` 这种污染生产代码的方法。因为构造函数设计成 `constructor(panel, client = defaultClient)`，测试时直接 `new ChatPanel(panel, new ApiClient(':8001'))` 就解决了，生产代码零修改。这个设计在开发时是为了可测试性，结果在 E2E 场景里直接派上用场。"

### "Playwright 测 webview 遇到了什么难点？"

> "VS Code webview 是 OOPIF，运行在独立进程里。Playwright 用 Target.setAutoAttach 追踪 OOPIF frame，这个命令对尚未创建的 target 是可靠的，但对已经独立运行的 OOPIF 发现能力不可靠。我做了控制变量实验，发现决定成败的不是 frameLocator 还是 page.frames()，而是连接时机——必须在 Webview 创建之前发出 setAutoAttach，才能通过事件捕获 frame 引用。解法是重试连接替代固定 sleep，CDP 端口一开放立刻连上。这个实验同时纠正了外部工具对根因的错误解释。"

### "测试里的进程管理怎么做的？"

> "用 child_process.spawn 启动后端，不直接 await（spawn 只是启动），而是轮询 /health 等就绪信号。用 try/finally 保证无论测试成败都 kill 掉进程，原理和 pytest 的 yield fixture 一样——yield 之前是 setup，finally 是 teardown。"

---

## 十、关键数字备查

| 指标 | 数值 |
|------|------|
| 总测试数 | 4（Phase 1: 3 + Phase 2: 1）|
| CDP 端口 | 9222 |
| 后端测试端口 | 8001（区别于生产 8000）|
| keepAlive 时长 | 45s |
| CDP 连接重试 | 20 次，每次间隔 500ms |
| 控制变量实验组数 | 5 组 |
| AI 调试失败迭代次数 | 10+ 次 |
