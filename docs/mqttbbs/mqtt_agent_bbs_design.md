# MQTT Agent BBS — 智能体协作论坛设计

> 生成时间: 2026-05-16
> 对标: subagent 文件式协议 (input.txt / output.txt / [ROUND END])
> 定位: 用 MQTT Pub/Sub 模型实现智能体间的任务分发与结果收集

---

## 0. 核心理念

```

文件体系                    MQTT 主题
──────────────────────────────────────────────────
temp/{task}/input.txt      →  agent/board/task/{task_id}/input
temp/{task}/output.txt     →  agent/board/task/{task_id}/output
temp/{task}/               →  agent/board/task/{task_id}/
[ROUND END] 标记           →  agent/board/task/{task_id}/signal
轮询读取输出               →  Subscribe 输出主题，推送即达
PID 标识进程               →  node/{agent_id}/task/current
进程异常退出               →  LWT 自动发布 node/{agent_id}/status = offline
```

---

## 1. 主题树

```
agent/                              ← 根
│
├── board/                          ← 公告板（任务广场）
│   ├── task/{task_id}/
│   │   ├── input                  ← [Retain] 任务输入（≈input.txt）
│   │   ├── status                 ← [Retain] pending|running|done|failed
│   │   ├── claim                  ← [Retain] 认领人（谁在执行）
│   │   ├── stdout                 ← [非Retain] 标准输出（流式，seq编号）
│   │   ├── stderr                 ← [非Retain] 错误输出（流式，seq编号）
│   │   ├── signal                 ← [Retain] [START] [ROUND_END] [HEARTBEAT] [CANCEL]
│   │   ├── output                 ← [Retain] 最终产出（≈output.txt）
│   │   └── fs/                    ← 文件系统（任意中间文件存储）
│   │       └── {filename}
│   │
│   ├── open                        ← [Retain] 待认领任务索引
│   └── recent                      ← [Retain] 最近完成的任务（滑动窗口）
│
├── node/{agent_id}/
│   ├── status                     ← [Retain+LWT] online|busy|offline
│   ├── capability                 ← [Retain] 能力声明（JSON Schema）
│   ├── task/current               ← [Retain] 当前执行的任务ID
│   ├── task/history/              ← 历史任务列表
│   │   └── {task_id}              ← 该agent执行过的任务摘要
│   └── log/                       ← 该agent的日志流
│
├── sys/
│   ├── broadcast                  ← 全局广播（管理员/系统通知）
│   ├── heartbeat                  ← 所有节点心跳汇总
│   └── config/
│       ├── routing                ← 任务分发策略
│       └── acl                    ← 权限规则
│
└── registry/
    ├── alive                      ← [Retain] 当前在线节点列表
    └── capability_index           ← [Retain] 按能力索引的节点映射
```

---

## 2. 消息格式

### 2.1 发布任务（发 input）

```json
// PUBLISH → agent/board/task/task_001/input  [Retain=True, QoS=1]
{
  "task_id": "task_001",
  "type": "analyse_network",
  "priority": 3,
  "input": {
    "target": "192.168.1.0/24",
    "scan_type": "topology"
  },
  "resources": [
    {"url": "http://share/config.json", "role": "reference"}
  ],
  "timeout": 300,
  "created_at": "2026-05-16T10:00:00Z"
}
```

### 2.2 认领任务

```json
// PUBLISH → agent/board/task/task_001/claim  [Retain=True]
{
  "agent_id": "agent_alpha",
  "claimed_at": "2026-05-16T10:00:05Z"
}

// PUBLISH → agent/board/task/task_001/status  [Retain=True]
"running"

// PUBLISH → agent/node/agent_alpha/task/current  [Retain=True]
"task_001"

// PUBLISH → agent/node/agent_alpha/status  [Retain=True]
"busy"
```

### 2.3 流式输出（stdout / stderr）

```json
// PUBLISH → agent/board/task/task_001/stdout  [Retain=False, QoS=0]
{"seq": 1, "ts": "2026-05-16T10:00:10Z", "data": "扫描进行中: 发现5个存活主机"}
{"seq": 2, "ts": "2026-05-16T10:00:15Z", "data": "拓扑构建中..."}

// PUBLISH → agent/board/task/task_001/stderr  [Retain=False, QoS=0]
{"seq": 1, "ts": "2026-05-16T10:00:12Z", "data": "[WARN] 目标22端口超时，已跳过"}
```

### 2.4 任务完成

```json
// PUBLISH → agent/board/task/task_001/signal  [Retain=True, QoS=2]
"[ROUND_END]"

// PUBLISH → agent/board/task/task_001/status  [Retain=True]
"done"

// PUBLISH → agent/board/task/task_001/output  [Retain=True]
{
  "task_id": "task_001",
  "agent_id": "agent_alpha",
  "status": "completed",
  "result": {
    "hosts_found": 5,
    "topology": {
      "nodes": [...],
      "edges": [...]
    }
  },
  "metrics": {
    "duration_sec": 42,
    "errors": 1,
    "warnings": 3
  }
}

// PUBLISH → agent/node/agent_alpha/task/history/task_001  [Retain=True]
{ "status": "completed", "duration_sec": 42, "score": 85 }

// PUBLISH → agent/node/agent_alpha/status  [Retain=True]
"online"
```

### 2.5 任务失败

```json
// PUBLISH → agent/board/task/task_001/status  [Retain=True]
"failed"

// PUBLISH → agent/board/task/task_001/output  [Retain=True]
{
  "task_id": "task_001",
  "agent_id": "agent_alpha",
  "status": "failed",
  "error": {
    "type": "timeout",
    "msg": "执行超过300秒限制",
    "partial_result": {...}
  },
  "partial_output": "agent/board/task/task_001/stdout 的最后N条"
}

// PUBLISH → agent/board/task/task_001/signal  [Retain=True]
"[ROUND_END]"
```

### 2.6 取消任务

```json
// PUBLISH → agent/board/task/task_001/signal  [Retain=True, QoS=2]
"[CANCEL]"

// 执行中的 agent 收到后自行清理并回复
// PUBLISH → agent/board/task/task_001/status  [Retain=True]
"cancelled"
```

---

## 3. 协作生命周期

```
主智能体                              MQTT Broker                      子智能体(们)
  │                                      │                                   │
  │── ① PUBLISH task/input ──────────→ │                                   │
  │── ② PUBLISH task/status "pending"─→│                                   │
  │                                      │                                   │
  │                                      │── ③ 按capability匹配投递 ────→ │
  │                                      │                                   │── ④ 能力匹配？认领
  │                                      │                                   │── PUBLISH task/claim ──→
  │                                      │                                   │── PUBLISH task/status "running"
  │                                      │                                   │── PUBLISH node/self/status "busy"
  │                                      │                                   │
  │◂── ⑤ NOTIFY task/status "running" ─│── 流转                              │
  │◂── NOTIFY task/stdout (流式) ──────│── 流转                              │── ⑥ PUBLISH stdout seq 1~N
  │◂── NOTIFY task/stderr (流式) ──────│── 流转                              │── PUBLISH stderr seq 1~N
  │                                      │                                   │
  │                                      │                                   │── ⑦ 执行完毕
  │                                      │                                   │── PUBLISH task/output ──→
  │                                      │                                   │── PUBLISH task/signal
  │                                      │                                   │   "[ROUND_END]" ──→
  │                                      │                                   │── PUBLISH task/status "done"
  │                                      │                                   │── PUBLISH node/self/status "online"
  │                                      │                                   │
  │◂── ⑧ NOTIFY task/signal ──────────│── 流转                               │
  │  "[ROUND_END]"                      │                                   │
  │── ⑨ 读取 output ──→               │                                   │
  │── 验证结果                           │                                   │
  │── 完成                               │                                   │
```

---

## 4. 智能体注册与发现

### 能力声明

```json
// PUBLISH → agent/node/agent_alpha/capability  [Retain=True, QoS=1]
{
  "agent_id": "agent_alpha",
  "version": "1.2.0",
  "capabilities": [
    {"type": "scan_network", "params": {"max_hosts": 100}},
    {"type": "analyse_log", "params": {"formats": ["json", "csv"]}},
    {"type": "generate_report", "params": {"formats": ["pdf", "md"]}}
  ],
  "max_concurrency": 3,
  "max_payload_bytes": 1048576,
  "tags": ["security", "analysis"]
}
```

### 注册中心汇总

```json
// agent 定期 PUBLISH → agent/registry/alive  [Retain=True]
["agent_alpha", "agent_beta", "agent_gamma"]

// agent/registry/capability_index  [Retain=True]
{
  "scan_network": ["agent_alpha", "agent_gamma"],
  "analyse_log": ["agent_alpha", "agent_beta"],
  "generate_report": ["agent_beta", "agent_gamma"]
}
```

### 在线检测（LWT）

```
CONNECT 时设置:
  Will Topic:   agent/node/agent_alpha/status
  Will Payload: "offline"
  Will QoS:     1
  Will Retain:  true

正常下线 → PUBLISH agent/node/agent_alpha/status → "offline"
异常断线 → Broker 自动帮发 LWT → 状态变 "offline"
```

---

## 5. QoS 策略

| 场景 | QoS | 说明 |
|:----|:---:|:-----|
| 任务 input | **1** | At least once，不能丢 |
| 任务 output | **1** | At least once，不能丢 |
| signal [ROUND_END] | **2** | Exactly once，防重复 |
| signal [CANCEL] | **2** | Exactly once，防误判 |
| stdout/stderr 流 | **0** | 丢了可重发，不阻塞 |
| 节点 status | **1** | 状态必须准确 |
| 能力声明 | **1** | 初始必须到达 |
| 心跳 | **0** | 高频低优 |

---

## 6. 并行与隔离

```
┌─ 文件体系 ──────────────────┐
│ temp/task_A/                │
│ temp/task_B/       ← 目录隔离│
│ temp/task_C/                │
└─────────────────────────────┘

┌─ MQTT BBS ──────────────────┐
│ board/task/A/*               │
│ board/task/B/*     ← 主题隔离 │
│ board/task/C/*               │
└─────────────────────────────┘
```

多个智能体可以同时订阅不同任务，互不干扰：

```
agent_alpha → 认领 task_A → Subscribe task/A/stdout, task/A/signal
agent_beta  → 认领 task_B → Subscribe task/B/stdout, task/B/signal
agent_gamma → 认领 task_C
同时运行，独立反馈
```

---

## 7. 与当前文件体系对比总结

| 维度 | 文件体系 | MQTT BBS |
|:----|:--------|:---------|
| **等待方式** | 轮询 30次×5秒 | 订阅即推送，实时到达 |
| **并发隔离** | 目录名隔离 | 主题名隔离 |
| **信号传递** | output中含[ROUND END] | 独立signal主题 |
| **异常检测** | 超时判定（Poll无响应） | LWT + 心跳，Broker主动通知 |
| **历史追溯** | `ls temp/` 看有哪些任务 | 订阅 `task/+/status` 通配符 |
| **跨机器** | 需共享存储 (NFS/Samba) | TCP连接即可，天然跨网络 |
| **部署开销** | 0（仅文件系统） | 需MQTT Broker（如EMQX） |
| **流式输出** | 无，只能等最终output | stdout/stderr独立流式主题 |
| **能力发现** | 无，需手动分配 | capability声明+注册中心 |
| **在线状态** | 无，只能超时判断 | CONNECT/LWT 精确在线检测 |

---

## 8. 推荐 Broker

| Broker | 适合场景 | 说明 |
|:-------|:--------|:-----|
| **EMQX** | 生产级 | 集群、ACL、规则引擎、WebHook，开源 |
| **Mosquitto** | 轻量/开发 | 单机、配置简单、资源占用低 |
| **NanoMQ** | 嵌入式/边缘 | 极轻量，C语言实现 |
| **VerneMQ** | 高可用 | Erlang实现，与EMQX同生态 |

**推荐选型路线**：开发用 Mosquitto → 生产用 EMQX

---

## 9. 落地路径

```
Phase 1: 协议匹配
  └── 文件版 subagent → MQTT 版 adapter 封装
  └── input 写入 → PUBLISH task/input
  └── output 读取 → Subscribe task/output
  └── 结果判断 → Subscribe task/signal "[ROUND_END]"

Phase 2: 增强能力
  └── 流式 stdout/stderr（实时代理反馈）
  └── 节点注册 & 能力发现（自动匹配任务）
  └── LWT 在线检测（异常感知）

Phase 3: 去中心化
  └── 多 Broker 桥接（跨机房协作）
  └── 离线队列（Persistent Session）
  └── 任务重试 & 超时自愈
```
