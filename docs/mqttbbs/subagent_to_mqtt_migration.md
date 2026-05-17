# 多智能体改造路线 — subagent → MQTT BBS 迁移方案

> 时间: 2026-05-17
> 背景: mqtt_bbs 包已可用，本地 rmqtt Broker 已部署 (127.0.0.1:1883)

---

## 1. 当前架构 vs MQTT BBS 架构

```
当前 subagent 模式                    MQTT BBS 模式
────────────────────────────         ────────────────────────
agentmain.py --task {name}           AgentBoard.post_task()
  -> 创建 temp/{name}/                  -> PUBLISH board/task/{id}/input
  -> 写 input.txt                       -> Retain=True 持久化
  -> 子进程执行                          -> WorkerAgent 自动认领
  -> 轮询 output.txt                    -> 推送 output/signal
  -> 检测 [ROUND END]                  -> 收到 [ROUND_END] 信号
  +-- 本地文件系统                      +-- 网络 MQTT Broker
```

## 2. 对比维度

| 维度 | 文件模式 | MQTT BBS | 结论 |
|:----|:--------|:---------|:----|
| 通信方式 | 文件读写 | MQTT Pub/Sub | MQTT 更好 |
| 等待方式 | sleep 轮询 | subscribe 推送 | MQTT 更好 |
| 并行隔离 | 目录名隔离 | topic 隔离 | 等价 |
| 跨机器 | 需共享存储 (NFS) | 网络连接 | MQTT 胜 |
| 在线检测 | PID -> 可能僵尸 | CONNECT/LWT | MQTT 胜 |
| 历史保留 | 删 temp/ 丢失 | MariaDB 持久化 | MQTT 胜 |
| 依赖 | 零 | MQTT Broker + paho | 需部署 |

## 3. 替换点

### agentmain.py 改造

```python
# 当前: 文件模式
def main():
    task_name = parse_args().task
    text = read_input(task_name)
    result = execute(text)
    write_output(task_name, result)
    append_round_end(task_name)

# 改为: MQTT WorkerAgent 模式
def main():
    worker = WorkerAgent(f"agent_{os.urandom(4).hex()}")
    worker.on_task(lambda msg: execute(msg.input))
    worker.start(block=True)
```

### 上层调度（调 subagent 的地方）

```python
# 当前:
def call_subagent(name, text):
    Path(f"temp/{name}").mkdir()
    (f"temp/{name}/input.txt").write_text(text)
    run(["python", "agentmain.py", "--task", name])
    return poll_output(name)

# 改为:
def call_subagent_mqtt(task_type, task_input):
    board = AgentBoard("master")
    task_id = board.post_task(task_type, task_input)
    return board.wait_task(task_id)
```

## 4. 共存与升级路线

```
Phase 1 - 共存
  agentmain.py --task 仍然走文件（向后兼容）
  新增 agentmain.py --mqtt 走 MQTT BBS
  两边返回格式一致（TaskOutput）

Phase 2 - 默认切换
  默认改为 --mqtt
  --task 作为兼容遗留模式保留

Phase 3 - 利用 MQTT 新能力
  - 多个 WorkerAgent 自动负载均衡
  - 断线任务自动恢复
  - 在线/离线 Dashboard
  - 跨机器子任务分发
```

## 5. 与现有 subagent 的对应关系

| subagent 概念 | MQTT BBS 对应 | 文件 |
|:-------------|:--------------|:-----|
| temp/{name}/input.txt | board/task/{id}/input | bbs.py:post_task() |
| temp/{name}/output.txt | board/task/{id}/output | bbs.py:complete() |
| [ROUND END] | board/task/{id}/signal | bbs.py:complete() |
| PID 标识 | node/{agent}/task/current | bbs.py:claim_task() |
| 进程异常退出 | node/{agent}/status -> offline | client.py:LWT |
| 轮询 | subscribe 推送 | client.py:subscribe() |
