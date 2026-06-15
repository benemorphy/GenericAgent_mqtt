# Multiple Agents Brainstorm: MQTT-Based Infrastructure

> Generated: 2026-05-22
> Context: 基于现有 mqtt_bbs 代码库的架构分析与演进方案

---

## 一、现有架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                       MQTT Broker (RMQTT 1883)                      │
└──────┬─────────┬──────────┬──────────┬──────────┬──────────────────┘
       │         │          │          │          │
  ┌────▼──┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼────┐ ┌──▼──────────┐
  │BBS    │ │Board   │ │Worker  │ │Agent  │ │External     │
  │Client │ │Service │ │Agent(N)│ │Board  │ │Plugin(N)    │
  │(轻量) │ │(持久化)│ │(任务消)│ │(创建)│ │(飞书/Webhook)
  └───────┘ └────────┘ └────────┘ └───────┘ └─────────────┘
```

### 现有层叠结构

| 层 | 模块 | 职责 |
|----|------|------|
| L0 传输 | `client.py` (BBSClient) | 底层 MQTT 连接、心跳、QoS、MQTT 5.0 |
| L1 协议 | `board_client.py` (BoardClient) | 注册/发帖/查询/文件操作，请求-响应模式 |
| L2 业务 | `board_service.py` (BoardService) | 持久化服务、能力注册、心跳检测 |
| L3 任务 | `bbs.py` (AgentBoard + WorkerAgent) | 任务创建/认领/执行/完成，Map-Reduce |
| L3 状态 | `whiteboard.py` (WhiteboardKV) | 共享 KV 状态，CAS 乐观锁，分布式锁 |
| L3 编排 | `dag.py` (DAGWorkflow) | 有向无环图任务编排，自动并行+重试 |
| L2 扩展 | `plugin.py` / `plugin_manager.py` | 插件系统，事件驱动的热加载 |

### 现有 MQTT 主题协议

| 主题模式 | 用途 |
|----------|------|
| `bbs/{board}/register` + `/response/{corr_id}` | Agent 注册 |
| `bbs/{board}/post` + `/response/{corr_id}` | 发布帖子 |
| `bbs/{board}/new_post` | 新帖广播推送 |
| `bbs/{board}/query` + `/response/{corr_id}` | 查询帖子/计数 |
| `board/task/{id}/input` (retain) | 任务输入 |
| `board/task/{id}/output` (retain) | 任务输出 |
| `board/task/{id}/status` (retain) | 任务状态 |
| `board/open` (retain) | 待认领任务索引 |
| `board/capability/query` + `/response/{corr_id}` | 能力查询 |
| `node/{agent_id}/heartbeat` | 心跳 |
| `node/{agent_id}/status` | 状态变更 |
| `node/{agent_id}/task/current` | 当前任务 |
| `node/{agent_id}/task/input` | 定向任务推送 |
| `system/plugins/{load/unload/reload/list}` | 插件管理 |

### 现有 Boards

- `agent-bbs-test` — 默认公告板
- `agent-inspiration` — 灵感板
- `agent-whiteboard` — 白板 (WhiteboardKV 用)

### 现有 Agent 角色

| 角色 | 模块 | 行为 |
|------|------|------|
| AgentBoard | `bbs.py` | 创建任务、等待结果、Map-Reduce 聚合 |
| WorkerAgent | `bbs.py` | 认领任务、执行、流式输出、完成 |
| BoardClient | `board_client.py` | 通用公告板客户端，发帖/读帖 |
| WhiteboardKV | `whiteboard.py` | 读写共享状态，CAS 乐观锁 |
| MQTT Agent Runner | `mqtt_agent_runner.py` | 将 GeneraticAgent 包装为 MQTT Worker |

---

## 二、核心洞察与痛点

### 2.1 主题空间扁平化

当前主题 `bbs/`, `board/`, `node/`, `system/` 散落各处。未来扩展到 100+ Agent 时，通配符订阅可能产生严重消息渗透和过滤开销。

### 2.2 请求-响应模式的隐式耦合

当前使用 `corr_id` + `_wait_response()` 模式模拟 RPC。每个请求都要动态 subscribe -> wait -> unsubscribe:
- 产生毫秒级延迟累积
- 大量并发时 callback 注册表成为竞争热点 (`_pending_lock`)

### 2.3 任务系统的广义/狭义分裂

| 系统 | 定位 | 协议 |
|------|------|------|
| `AgentBoard+WorkerAgent` (bbs.py) | 子任务分发 | `board/task/{id}/*` |
| `BoardClient.post()` | 公告板消息 | `bbs/{board}/post` |

任务本质上也是消息。能力路由和定向分发仅在 `post_task_routed()` 中有，`BoardClient.post()` 没有。

### 2.4 白板的模式局限

WhiteboardKV 基于 BBS board 实现:
- 读写都是请求-响应模式，非真正的订阅-通知
- CAS 乐观锁通过 get -> compare -> post 实现，密集写场景有重试风暴风险
- 每个 `watch()` 靠新帖推送回调，无键级别过滤

### 2.5 心跳/健康检查的单点依赖

`BoardService._cleanup_loop()` 集中管理所有 Agent 心跳检测。BoardService 宕机则整个集群活性检测失效。

---

## 三、架构演进方案

### 方案 A: 主题分层治理 (Topic Governance)

```
v2/                   <- 顶层命名空间
  agent/{id}/         <- 每个 Agent 专属空间
    heartbeat         <- 心跳 (retain)
    status            <- online/offline/busy (retain)
    capability        <- 能力声明 (retain)
    task/input        <- 定向任务队列
    task/output       <- 定向任务结果
    log/{level}       <- 日志流 (QoS=0)

  board/{name}/       <- 公告板空间
    event/            <- 事件 (插件订阅层)
      post
      register
      file
    rpc/              <- RPC 调用层
      register.req/{corr_id}
      register.res/{corr_id}
      post.req/{corr_id}
      post.res/{corr_id}
    stream/           <- 流式层
      new_post        <- 新帖推送

  task/{id}/          <- 任务空间 (扁平化)
    input (retain)
    output (retain)
    status (retain)
    log (QoS=0)

  state/{namespace}/  <- 共享状态 (Whiteboard v2)
    {key} (retain)    <- 每个 key 独立主题

  system/             <- 系统空间
    plugin/load
    plugin/unload
    errors/{agent_id}
    metrics/{agent_id}
```

优势: 通配符订阅精确可控，`v2/agent/+/heartbeat` 替代模糊的 `node/+/heartbeat`。

### 方案 B: 响应槽机制 (Response Slot)

当前每次 RPC: `subscribe(specific_topic) -> publish -> wait -> unsubscribe`

优化: 每个 Agent 启动时预订阅自己的响应槽。

```
v2/agent/{id}/rpc/res/#    <- 预订阅

发送时:
  req_topic = v2/board/bbs-test/rpc/register.req/{corr_id}
  res_topic = v2/agent/{id}/rpc/res/{corr_id}

接收方看到 req 中的 `_reply_to` 字段:
  publish(v2/agent/{requester}/rpc/res/{corr_id}, response)
```

优势: 无动态 subscribe/unsubscribe，无 `_pending` 竞争表，纯内存匹配。

### 方案 C: 分布式 Agent Registry (去中心化心跳)

利用 MQTT Retain + LWT + Session Expiry 替代中心化心跳检测:

```
Agent 连接:
  - LWT: v2/agent/{id}/status <- "offline" (自动发布)
  - Session Expiry Interval: 60s
  - 发布: v2/agent/{id}/status <- "online" (retain)
  - 发布: v2/agent/{id}/capability <- [...] (retain)

其他 Agent 查询:
  subscribe("v2/agent/+/status")        <- 实时发现所有在线 Agent
  或: subscribe("v2/agent/+/capability") <- 能力发现
```

优势: 去中心化，Broker 分担活性检测，BoardService 崩溃不影响 Agent 间发现。

### 方案 D: 消息压缩与分片 (Large Payload)

MQTT 默认最大 payload ~256MB，大消息会阻塞 Broker 吞吐。

推荐: 元数据+内容分离，或显式分片协议:

```
v2/agent/{id}/file/{hash}/meta    <- 文件元信息
v2/agent/{id}/file/{hash}/chunk/{seq}  <- 分片内容
```

更简单: metadata 走 MQTT, blob 走文件系统/对象存储，MQTT 只传递路径引用。

### 方案 E: 插件系统升级 —— 过滤器链

当前插件订阅 `events/` 主题被动触发。升级为过滤器链模式:

```
BoardService._on_post()
  -> PluginManager.apply_filters("pre_post", payload)
    -> [rate_limiter, content_filter, audit_logger]
  -> 核心逻辑执行
  -> PluginManager.apply_filters("post_post", result)
    -> [feishu_push, webhook_notify, inspiration_auto]
```

优势: 插件可以拦截/修改/拒绝消息流，而非只做事后通知。支持 chain-of-responsibility 模式。

### 方案 F: 多 Broker 联邦 (Federation/Bridge)

当 Agent 数量 > 1000 或跨机房时:

```
RMQTT Node1 <-> RMQTT Node2
(agent-01~500)  (agent-501~1000)
```

利用 RMQTT 集群或 MQTT Bridge，实现跨 Broker 主题路由。

---

## 四、协议级改进建议

### 4.1 Payload Schema 规范化

当前 payload 格式不统一。建议统一:

```json
// 请求
{
  "v": 2,
  "type": "request",
  "corr_id": "uuid",
  "timestamp": 1234567890,
  "source": "agent_alpha",
  "reply_to": "v2/agent/alpha/rpc/res/",
  "payload": { ... }
}

// 响应
{
  "v": 2,
  "type": "response",
  "corr_id": "uuid",
  "status": "ok" / "error",
  "error": { "code": 400, "msg": "..." },
  "payload": { ... }
}

// 事件
{
  "v": 2,
  "type": "event",
  "event": "post_created",
  "source": "...",
  "payload": { ... }
}
```

### 4.2 优先级与 QoS 策略

| 消息类型 | QoS | Retain | 优先级 |
|---------|-----|--------|-------|
| 心跳 | 0 | Yes | 最高 |
| 任务输入 | 2 | Yes | 高 |
| 任务输出 | 2 | Yes | 高 |
| 状态变更 | 1 | Yes | 中 |
| RPC 请求 | 1 | No | 中 |
| 日志/流式 | 0 | No | 低 |
| 广播事件 | 1 | No | 中 |

### 4.3 速率控制与背压

Worker Agent 处理速率跟不上 Broker 推送时:

```
Agent 发布: v2/agent/{id}/flow/ready <- 0 (背压)
Agent 发布: v2/agent/{id}/flow/ready <- 1 (恢复)
```

分发前检查目标 Agent 的 flow/ready 状态。

---

## 五、重点演进路线图

### P0 (速赢 — 现有架构微调即可)

1. 响应槽预订阅 — 消除动态 subscribe/unsubscribe 开销
2. Retain 状态去中心化 — 利用 MQTT retain + LWT 替代 BoardService 心跳清理
3. Payload schema 统一 — 所有消息 `{v, type, corr_id, source, reply_to, payload}`

### P1 (核心能力增强)

4. 主题命名空间迁移 — 从 `board/task/{id}/input` 等迁移到 `v2/task/{id}/input`
5. 状态空间独立化 — WhiteboardKV 从 BBS board 迁移到 `v2/state/{namespace}/{key}`
6. 过滤器链插件 — 插件可拦截/修改消息流

### P2 (规模化)

7. 分片/大消息协议 — 文件传输走引用路径，大文本走分片
8. 多 Broker 联邦 — RMQTT 集群配置
9. WebSocket Bridge — 浏览器端 Agent 通过 WS 接入 MQTT 生态

### P3 (前沿)

10. 语义路由 — 用 Agent 能力描述做语义级任务路由，而非精确标签匹配
11. 自适应 QoS — 根据网络条件动态调整 QoS
12. 因果追溯 — 每条消息携带因果链 `{causes: [task_id, parent_msg_id]}`

---

## 六、与现有工具的集成关系

| 现有工具/SOP | 与脑暴关系 |
|-------------|-----------|
| `board_stress_sop.md` | 验证新主题命名空间和响应槽的性能基线 |
| `subagent.md` | 任务系统统一后，subagent 协议可作为 MQTT 任务的"文件协议镜像" |
| `emqtt_design_principles.md` | Erlang EMQTT 的 OTP 设计思想可指导 BoardService 重构 |
| `ljqCtrl_sop.md` | 键鼠操作可用作"物理世界 Agent"的能力声明 |
| `agent_dreaming_sop.md` | 联想发散能力可作为 Agent 的特殊能力注册 |
| `feishu_connect_sop.md` | 插件化后飞书 Bot 从硬编码变为 `plugins/feishu_push.py` |

---

## 七、开放问题

1. **Backward compatibility**: 主题迁移时旧主题是否保留 bridge？还是直接 breaking change？
2. **BoardService 角色**: 演进后 BoardService 应保留为可选持久化层，还是删减为纯插件运行时？
3. **Python vs Erlang vs Rust**: 重度场景下 Python paho-mqtt 的 GIL 是否成为瓶颈？RUST_ENV 已有 Rust 工具链。
4. **状态持久化**: WhiteboardKV 的 CAS 乐观锁在 MVCC 场景是否需要迁移到 etcd/Redis/MariaDB？
