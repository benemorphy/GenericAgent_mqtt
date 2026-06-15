# 内存泄漏排查五步法 SOP

> 从 LLM Cache RS 排障（06-10/06-11）提炼的通用排查框架

## 五步排查链

| 步 | 检查点 | 典型症状 | 检查方法 |
|----|--------|----------|----------|
| 1 | **Vec/集合无条件增长** | 进程内存只增不减 | grep store()/insert()/push() 是否检查 exists/去重 |
| 2 | **锁序逆序+重入** | 死锁报警/并发性能下降 | 检查持有锁A时是否调用了内部获取锁B的函数，是否有逆序(A→B→A) |
| 3 | **句柄/资源泄漏** | 句柄数缓慢爬升后稳定 | Windows: `GetProcessHandleCount` / task manager; Named Pipe/Socket/TCP 连接数 |
| 4 | **参数/常量冲突** | 配置不生效、容量检查形同虚设 | 检查同类常量是否在多个文件中重复定义，实际使用与预期值是否一致 |
| 5 | **删除操作留悬空引用** | 删除后索引/缓存仍有指向已删数据的指针 | 检查 delete()/remove() 是否同步清理了所有索引结构 |

## 排查工具

```python
# 监控进程内存和句柄数
import psutil
p = psutil.Process(PID)
p.memory_info().rss       # 物理内存
p.num_handles()           # 句柄数 (Windows)
p.num_fds()               # 文件描述符 (Linux)
```

## 典型泄漏模式速查

| 模式 | 根因 | 修复 |
|------|------|------|
| hkey_index 膨胀 | store() 未检查 key 重复 | push 前 contains() |
| freq_list 重复 | 相同 key 二次 store | 先 delete 旧索引 |
| 锁序逆序重入 | 持写锁时调内部读锁 | 接收 Arc 直接复用 |
| 管道实例无限 | loop {create→spawn} 无上限 | Semaphore 限流 |
| estimated_size 低估 | 用 len() 非 capacity() | 改用 capacity() + 栈开销 |
