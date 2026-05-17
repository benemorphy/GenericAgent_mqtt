# 技能学习报告: python_async_optimization

| 属性 | 值 |
|------|-----|
| 版本 | rev6 |
| 评分 | 96/100 PASS |
| 案例数 | 15 条 |
| 模式总数 | 24 个 |
| 继承自 rev5 | 24 个 |
| 新增 | 0 个 |

## 知识模式

### 领域专有 (9个)
- [95%] 异步事件循环与协程调度优化
- [95%] 在优化异步Python代码前，必须使用cProfile和内存分析器进行性能剖析，以识别真正的瓶颈而非凭直觉优化。
- [90%] 异步I/O操作与并发控制（如asyncio.Semaphore）
- [90%] 对于I/O密集型应用，应使用asyncio和async/await模式替代同步阻塞调用，以实现非阻塞并发并提升吞吐量。
- [88%] 异步任务管理与超时处理（如asyncio.wait与asyncio.gather）
- [85%] 异步代码性能分析与瓶颈定位（如asyncio调试与profiling）
- [85%] 优化Python代码时，应结合CPU优化（如算法改进）、内存优化（如减少对象创建）、缓存（如functools.lru_cache）和并行化（如concurrent.futures）等多层次策略。
- [82%] 异步库与框架选择及最佳实践（如aiohttp、asyncpg）
- [80%] 在构建高性能异步API或并发系统时，优先使用FastAPI等原生支持异步的框架，并充分利用async/await语法编写非阻塞端点。

### 高级模式 (15个)
- [93%] 使用 async/await 而非回调模式
- [92%] 避免在异步中使用阻塞 IO 操作
- [91%] 使用 asyncio 正确管理事件循环
- [89%] 合理使用 asyncio.gather 并发执行
- [88%] 掌握异步编程核心模式
- [87%] 使用 asyncio.TaskGroup 管理任务生命周期
- [86%] 使用 asyncio.timeout 设置超时控制
- [85%] 使用 asyncio.Semaphore 控制并发数
- [85%] 在异步代码中，使用TaskGroup管理并发任务，并配合信号量（Semaphore）控制并发数，避免资源耗尽。
- [84%] 使用 asyncio.Queue 实现生产者消费者模式
- [83%] 使用异步上下文管理器处理资源释放
- [82%] 使用 asyncio.create_task 启动后台任务
- [80%] 使用 asyncio.as_completed 处理最先完成的任务
- [80%] 为异步操作设置超时（timeout）并使用队列（Queue）进行任务调度，防止单个任务阻塞整个事件循环。
- [75%] 数据库访问在异步应用中应使用异步驱动（如asyncpg、aiomysql）并优化查询，避免同步数据库调用阻塞事件循环。

## 参考案例 (15条)

- agentskill_skills/wshobson/python-performance-optimization
- agentskill_skills/dicklesworthstone/python-performance-optimization
- agentskill_skills/neversight/python-performance-optimization
- agentskill_skills/aiskillstore/python-performance-optimization
- agentskill_skills/fabioeducacross/python-performance-optimization
- agentskill_skills/microck/async-python-patterns
- agentskill_skills/ljchg12-hue/python-performance-optimization
- wshobson/agents/python-performance-optimization
- agentskill_skills/josiahsiegel/python-asyncio
- agentskill_skills/gaku52/python-development