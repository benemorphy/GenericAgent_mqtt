# 技能学习报告: error_handling_patterns

| 属性 | 值 |
|------|-----|
| 版本 | rev6 |
| 评分 | 84/100 PASS |
| 案例数 | 5 条 |
| 模式总数 | 10 个 |
| 继承自 rev5 | 10 个 |
| 新增 | 0 个 |

## 知识模式

### 领域专有 (10个)
- [95%] Exception handling syntax (try-catch-finally patterns)
- [90%] Error return codes and result types (e.g., Result<T, E> pattern)
- [85%] Graceful degradation and fallback strategies
- [85%] 在缺乏异常处理机制的语言中，使用返回码和errno模式来指示错误，而非依赖语言内置异常结构。
- [85%] 在统计假设检验中，区分第一类错误（假阳性，错误拒绝真零假设）和第二类错误（假阴性），以准确评估测试结果。
- [85%] 在发布-订阅模式中，通过解耦发布者和订阅者，避免同步模式如RPC和点对点消息的紧耦合，实现最高级别的松耦合。
- [80%] Error propagation and logging best practices
- [80%] 使用访问者模式时，通过编译器错误强制处理所有新定义的对象类型，确保类型安全。
- [80%] 异常处理语法应提供关键字和结构，将错误处理代码与正常逻辑分离，提高代码可读性和维护性。
- [75%] Recovery and retry patterns (e.g., circuit breaker)

## 参考案例 (5条)

- [Exception handling](https://en.wikipedia.org/wiki/Exception_handling)
- [Visitor pattern](https://en.wikipedia.org/wiki/Visitor_pattern)
- [Type I and type II errors](https://en.wikipedia.org/wiki/Type_I_and_type_II_errors)
- [Exception handling syntax](https://en.wikipedia.org/wiki/Exception_handling_syntax)
- [Publish–subscribe pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern)