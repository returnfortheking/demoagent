# Redux Saga — 扩展知识笔记

> 来源：学习 Module 02 pytest fixture 的 `yield` 语法时，联想到之前 React 项目里的 yield 用法。
>
> 面试价值：体现技术广度 + 跨语言概念迁移能力。

---

## 为什么需要 Saga

Redux reducer 是纯函数，不能有副作用。但真实应用需要异步操作（网络请求、定时器）。

```
Redux Thunk（简单方案）：action creator 返回函数，内部 async/await
  ↓ 问题：逻辑分散、难测试、复杂流程难管理

Redux Saga（复杂方案）：把所有副作用集中到独立层管理
```

---

## 核心设计思想

> 不直接执行副作用，而是 yield 一个"描述对象"（Effect），让 Saga 中间件去执行。

```typescript
// ❌ 直接执行（耦合真实 API，难测试）
const user = await fetch('/api/user/1')

// ✅ Saga 方式：yield 一个纯 JS 对象
const user = yield call(fetch, '/api/user/1')
// call(...) 返回 { type: 'CALL', fn: fetch, args: ['/api/user/1'] }
// 中间件拿到这个对象后才真正执行 fetch
```

**测试优势**：因为 yield 出来的是普通对象，测试时不需要 Mock 任何东西：

```typescript
expect(gen.next().value).toEqual(call(fetch, '/api/user/1'))
// 直接比较对象，无副作用
```

---

## 四个核心 Effect

| Effect | 作用 | 等价写法 |
|---|---|---|
| `call(fn, ...args)` | 调用异步函数并等待 | `await fn(...args)` |
| `put(action)` | 向 store dispatch action | `dispatch(action)` |
| `take(actionType)` | 等待某个 action | 事件监听 |
| `select(selector)` | 读取 store 状态 | `store.getState()` |
| `takeEvery(type, saga)` | 监听每次 action | `addEventListener` |
| `takeLatest(type, saga)` | 只保留最新，取消旧的 | 防抖语义 |

---

## Worker / Watcher 分层模式

```
rootSaga
  └── watcherSaga（监听层）：只负责"监听哪些 action"
        └── workerSaga（执行层）：负责"具体做什么"
```

```typescript
// Worker：具体业务逻辑
function* loginSaga(action) {
    try {
        const user = yield call(loginApi, action.payload)
        yield put({ type: 'LOGIN_SUCCESS', payload: user })
    } catch (error) {
        yield put({ type: 'LOGIN_FAILURE', payload: error.message })
    }
}

// Watcher：监听策略
function* watchLogin() {
    yield takeEvery('LOGIN_REQUEST', loginSaga)
}
```

**分层价值**：只需改 watcher 就能切换并发策略，worker 代码不动。

---

## takeEvery vs takeLatest

| | takeEvery | takeLatest |
|---|---|---|
| 行为 | 每个 action 都处理，可并发 | 新 action 到来取消上一个 |
| 适用场景 | 点赞、独立请求 | 搜索框、防抖场景 |

---

## 与 Python yield 的对比

| | Python pytest fixture | TypeScript Redux Saga |
|---|---|---|
| 语法标记 | 含 yield 自动成为生成器 | 必须写 `function*` |
| yield 的值 | 资源对象（交给测试函数） | Effect 对象（交给中间件） |
| 暂停/恢复 | pytest 框架控制 | Saga 中间件控制 |
| 核心目的 | setup/teardown 分界线 | 把副作用描述和执行分离 |
| 共同本质 | 生成器：暂停函数，把控制权交出去 ||

---

## 面试怎么用这部分知识

### 直接问到 Saga 时

> "我在之前的 React 项目里用过 Redux Saga，主要处理登录、数据加载这类异步流程。
> Saga 最吸引我的是它的可测试性——因为 `call`/`put` 返回的是普通对象，
> 不需要 Mock 任何真实 API，测试写起来非常干净。
> 相比 Thunk，Saga 在复杂流程（比如多步骤表单、需要取消的轮询）上更容易维护。"

### 被问到"你的技术广度"时

> "我主要做 Python 后端，但也接触过 React 前端。
> 有意思的是，当我深入学习 Python pytest fixture 里的 `yield` 语法时，
> 我意识到和 Redux Saga 的生成器用法其实是同一个底层概念——
> 都是用生成器的'暂停/恢复'机制，把控制权交给框架，
> 只是一个用于测试的 setup/teardown，一个用于异步副作用管理。
> 这种跨语言、跨场景的概念迁移让我觉得很有意思。"

### 被问到"Saga 和 Thunk 区别"时

> "Thunk 简单场景够用，action creator 返回函数，内部直接 async/await，门槛低。
> Saga 的核心差异是把'描述做什么'和'真正执行'分开——
> yield call(...) 只是产出一个普通对象，中间件才去真正调用。
> 这带来两个优势：测试不需要 Mock，以及可以用 takeLatest 这类操作符精细控制并发。
> 缺点是学习曲线陡，生成器语法不直观，小项目用 Thunk 就够了。"
