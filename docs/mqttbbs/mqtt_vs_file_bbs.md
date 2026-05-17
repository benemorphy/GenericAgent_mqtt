# MQTT BBS vs 文件 BBS：MQTT 解锁的能力

> 本文档对比 MQTT BBS 模式与遗留的文件 BBS 模式，阐述 MQTT 模式带来的架构级能力跃迁。

## 核心差异维度

| 维度 | 文件BBS | MQTT BBS |
|------|---------|----------|
| 通信模型 | 轮询(读文件→解析→写文件) | 事件驱动(发布/订阅) |
| 空间范围 | 单机 | 跨网络 |
| 任务分发 | 手动指定agent目录 | 能力声明+自动匹配 |
| 实时性 | 秒级(轮询间隔) | 毫秒级(push) |
| 并行性 | 串行(每agent单任务) | N:M 任意并发 |
| 存活检测 | 无(进程死=静默) | Will Message 自动通知 |
| 消息可靠性 | 无(文件写一半crash就丢) | QoS 0/1/2 三级保证 |
| 第三方集成 | 需直接读写文件系统 | 任何MQTT客户端皆可接入 |

---

## 8 个文件BBS做不到的事

### 1. 跨机器协作

文件 BBS 被物理机牢牢锁死。MQTT 让 agent 跨越机器边界：

```
Desktop AgentBoard ──── Internet ──── Laptop WorkerAgent
                                        └── Phone Dashboard
```

**实战**：在台式机提交长任务，WorkerAgent 在笔记本上跑（笔记本有 GPU），手机上的 MQTT App 随时看进度。

**文件BBS做不到**：文件系统是单机概念，NFS/CIFS 映射太脆弱，权限和延迟不可控。

### 2. 能力声明与智能匹配

WorkerAgent 上线时自动**广播能力清单**：

```json
// node/agent_wang/status → online 时携带
{
  "capabilities": ["python", "data_analysis", "pandas", "git_ops"],
  "load": 0.3,
  "max_concurrency": 2
}
```

AgentBoard 分发任务时自动匹配最适合的 agent，不需要人工指定路由。

**文件BBS做不到**：文件里存能力声明可以，但需要手动遍历所有目录检查每个 agent 在不在线、忙不忙。

### 3. 实时流式输出

WorkerAgent 在处理过程中逐行推送结果：

```
node/agent_alpha/stdout → "正在分析第1/100页..."
node/agent_alpha/stdout → "发现模式A, 置信度85%"
node/agent_alpha/stdout → "正在分析第2/100页..."
```

Dashboard 实时显示这些日志，就像 `tail -f`。

**文件BBS做不到**：必须等 agent 完成（或定时轮询 output.txt），中间状态不可见。一个跑10分钟的任务，文件模式要么干等、要么轮询产生大量读 IO。

### 4. Map-Reduce 并行分发

```python
# 通配符订阅收集结果
board.subscribe("agent/board/task/+/output")
board.post_task("分析文件A")  # → WorkerAgent-1
board.post_task("分析文件B")  # → WorkerAgent-2
board.post_task("分析文件C")  # → WorkerAgent-3
wait_all()  # 汇总
```

**文件BBS做不到真正的并行**：需为每个子任务创建独立目录 + 独立 agent 实例，手动管理 N 个进程的 input/output 文件，自行写合并逻辑。

MQTT 的**通配符订阅** `board/task/+/output` 让收集结果变成一行代码。

### 5. 广播/组播 — 全局指令

```python
# 一条消息通知所有 agent
board.publish("agent/board/global/signal", "[SUSPEND]")
# 所有订阅了 agent/board/global/+ 的 agent 同步暂停
```

**文件BBS做不到**：需要编辑每个 agent 目录的 input.txt，或 kill 进程全部重来。

### 6. 运行时干预 — 手术刀式控制

对正在运行的 agent 动态注入指令：

```python
# 在 Dashboard 上点"停止"
board.publish(f"agent/board/task/{task_id}/signal", "[CANCEL]")
# 注入新指令
board.publish(f"agent/board/task/{task_id}/intervene", "跳过第3步，直接分析附件")
```

**文件BBS做不到**：agent 运行中无法干预（不会去读文件直到当前回合结束）。想停止只能 kill 进程。

### 7. 第三方系统集成

任何 MQTT 客户端都能参与生态，不依赖 Python、不依赖本代码库：

```
Node.js 服务 ──→ 监听 agent/board/task/+/status ←── Dashboard
Grafana    ──→ 接收 agent/node/+/metrics
IFTTT      ──→ 收到 done 信号 → 发 Slack 通知
```

**文件BBS做不到**：第三方必须直接访问文件系统，跨语言解析 input.txt/output.txt 格式，耦合度高。

### 8. 持久化队列与离线缓冲

MQTT Broker 自带消息持久化：

- Agent 离线 → 消息在 broker 排队
- Agent 上线 → 自动接收积压消息
- QoS 2 确保每条消息恰好一次

**文件BBS做不到**：agent 崩溃时写到一半的 output.txt 是损坏的，没有回滚、没有重试、没有 at-least-once 语义。

---

## 一句话总结

> **文件 BBS 是点对点、轮询、单机、串行；MQTT BBS 是发布/订阅、事件驱动、跨网络、并行** —— 前者是单机模拟多进程，后者是真·分布式多智能体。

类比：

| 文件BBS | MQTT BBS |
|---------|----------|
| 写信给你→你看→你回信→我收信 | 群里说话→谁有能力谁接→实时刷屏→@人 |
| 离线=失联 | 在线状态实时可见 |
| 一人一队 | 弹性工作池 |
| 不可打断 | 随时插话/撤回/补充 |
