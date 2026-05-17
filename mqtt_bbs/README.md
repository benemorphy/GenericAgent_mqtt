# MQTT Agent BBS

智能体协作消息总线 — 用 MQTT 实现的任务分发与结果收集系统。

对标当前 subagent 文件协议 (`input.txt` / `output.txt` / `[ROUND END]`)，
用 MQTT Pub/Sub 模型替代文件轮询。

## 快速开始

```bash
# 安装依赖
uv pip install paho-mqtt

# 终端1：启动工作智能体
python -m mqtt_bbs.examples.worker_agent

# 终端2：发布任务
python -m mqtt_bbs.examples.master_agent
```

## 架构

```
主智能体 (AgentBoard)                MQTT Broker               工作智能体 (WorkerAgent)
     │                            (broker.emqx.io)                  │
     ├── PUBLISH task/input ─────────→                              │
     │                              ⋱                              │
     │                              ├── SUB task/+/input ────────→  │
     │                              │                              ├── claim_task()
     │                              │                              ├── stream_out()  ← stdout
     │                              │                              ├── stream_err()  ← stderr
     │◂── NOTIFY task/stdout ───────│                              │
     │◂── NOTIFY task/stderr ──────│                              │
     │                              │                              ├── complete()
     │◂── NOTIFY task/signal ──────│── "[ROUND_END]"              │
     │◂── NOTIFY task/output ──────│── result                     │
```

## 核心 API

### AgentBoard（主智能体）

```python
from mqtt_bbs import AgentBoard

with AgentBoard("master") as board:
    task_id = board.post_task("analyse_log", {"path": "/var/log"})
    result = board.wait_task(task_id, timeout=60)
    print(result.status, result.result)
```

### WorkerAgent（工作智能体）

```python
from mqtt_bbs import WorkerAgent

agent = WorkerAgent("worker_01", capabilities=["analyse_log"])

@agent.on_task
def handle(task):
    agent.stream_out(f"开始执行: {task.type}")
    agent.stream_err("警告：磁盘空间不足")
    return {"result": "ok"}

agent.start()
```

## 文件映射

| 文件协议 | MQTT BBS | 说明 |
|:---------|:---------|:------|
| `input.txt` | `board/task/{id}/input` | Retain=True |
| `output.txt` | `board/task/{id}/output` | Retain=True |
| `[ROUND END]` | `board/task/{id}/signal` | QoS=2, Retain=True |
| stdout 流 | `board/task/{id}/stdout` | QoS=0 流式 |
| stderr 流 | `board/task/{id}/stderr` | QoS=0 流式 |
| PID 标识 | `node/{agent}/task/current` | Retain=True |
| 异常下线 | `node/{agent}/status` → offline | LWT 自动 |

## Broker

测试使用公共 EMQX: `broker.emqx.io:1883`（无需注册）
