# Brainstorm: 基础设施层分离 — 本地Agent + 云端MQTT基础设施

> 生成: 2026-05-22 | 前置: 好奇心系列完成后的架构演进
> 核心追问: 将RMQTT/BoardService/Persistence搬到云端VPS后，GA的架构如何变化？

---

## 1. 现状诊断: 基础设施的耦合程度

### 当前架构（单机全耦合）

```
┌─────────────────────────────────────────────────┐
│ Local Machine (Windows)                          │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  GA Agent │  │ LLM本地  │  │ TMWebDriver    │  │
│  │  (agent)  │  │ (llama)  │  │ (浏览器)       │  │
│  └─────┬─────┘  └──────────┘  └───────────────┘  │
│        │ MQTT                                     │
│  ┌─────┴────────────────────────────────────────┐ │
│  │  基础设施层 (全部本地)                          │ │
│  │  RMQTT Broker :1883 → BoardService             │ │
│  │  MariaDB :3306 → Whiteboard / Scheduler        │ │
│  │  Plugin Manager → CuriosityBoard/auto_log      │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 好消息: config.py 已预留环境变量

| 变量 | 默认值 | 用途 |
|:-----|:-------|:------|
| `MQTT_HOST` | 127.0.0.1 | Broker地址 |
| `MQTT_PORT` | 1883 | Broker端口 |
| `MQTT_HMAC_SECRET` | mqtt_bbs_* | 消息签名密钥 |
| agent.env JWT | 本地签发 | 客户端认证 |

> **改一个环境变量就能连远程Broker**——但BoardService本身也跑在本地，它也需要连Broker。
> 真正的工程是：**把BoardService + MariaDB + PluginSystem 也搬到云端**，本地只剩Agent + 本地独占资源。

---

## 2. 目标架构: 基础设施与Agent分离

### 最终形态（三层分离）

```
┌──────────────────────────────────────────────────────┐
│ Cloud VPS (Infrastructure Layer)                      │
│                                                        │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ RMQTT    │  │BoardService│  │ Plugin Manager    │  │
│  │ Broker   │◄─┤ + Whiteboad│  │ (CuriosityBoard)  │  │
│  │ :1883    │  │ + Scheduler│  │                   │  │
│  └────┬─────┘  └─────┬──────┘  └──────────────────┘  │
│       │              │                                 │
│  ┌────┴──────────────┴─────────────────────────────┐  │
│  │ Persistence Layer (MariaDB / S3 / Redis)         │  │
│  │ 帖子/任务/白板持久化                               │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  + TLS/Cert Manager / Auth Gateway                     │
│  + Docker Compose / health checks / logging            │
└────────────────────────┬───────────────────────────────┘
                         │ MQTT over TLS (port 8883)
                         │
┌────────────────────────┴───────────────────────────────┐
│ Local Machine A (Agent Layer)                           │
│  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │ GA Agent       │  │ 本地独占资源                    │  │
│  │ (BoardClient)  │  │ - LLM推理 (llama-server)       │  │
│  │                │  │ - TMWebDriver (浏览器)          │  │
│  │ MQTT→云端      │  │ - 文件系统 (本机目录)            │  │
│  │ auth: JWT+env  │  │ - OCR/VLM 本地服务              │  │
│  └────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Local Machine B (另一台Agent)                           │
│ 同A，独立身份认证，共享同一套Board/Persistence           │
└────────────────────────────────────────────────────────┘
```

---

## 3. 关键设计决策

### 3.1 什么必须上云，什么不能上云

| 组件 | 上云？ | 理由 |
|:-----|:------:|:------|
| RMQTT Broker | ✅ 必须 | 消息中枢，Agent间桥梁 |
| BoardService | ✅ 必须 | 业务逻辑，需要全局状态 |
| MariaDB | ✅ 必须 | 全局持久化 |
| Whiteboard | ✅ 必须 | 共享状态，跨Agent |
| Plugin Manager | ✅ 推荐 | 云端运行，一致性高 |
| CuriosityBoard | ✅ 推荐 | 多Agent讨论的天然位置 |

| 组件 | 必须本地 | 理由 |
|:-----|:---------|:------|
| LLM推理 | ✅ 必须 | 模型文件/显存独占，不能远程 |
| TMWebDriver | ✅ 必须 | 操作本机浏览器 |
| 文件系统IO | ✅ 必须 | 读写本机文件 |
| OCR/VLM 服务 | ✅ 必须 | 摄像头/GPU本地 |
| 密钥文件 | ✅ 必须 | 安全边界，不出本地 |

### 3.2 核心挑战: BoardService 何时连接Broker

目前BoardService启动时序:
```
1. 启动RMQTT Broker (本地进程)
2. 启动BoardService (连接本地127.0.0.1:1883)
3. 启动Agent (连接本地127.0.0.1:1883)
```

迁移后:
```
VPS:  1. RMQTT Broker 启动 (远程)
      2. MariaDB 启动 (远程)
      3. BoardService 启动 (远程，连接远程Broker)
      4. Plugin Manager 启动 (远程)

本地: 5. GA Agent 启动 (连接远程Broker)
      6. LLM/浏览器/文件系统 正常运行
```

**问题**: 如果BoardService启动失败或VPS维护，Agent也需要优雅降级。

### 3.3 安全性

| 层 | 措施 | 状态 |
|:----|:------|:------|
| 传输 | MQTT over TLS (端口8883) | 需要配置 |
| 认证 | JWT Token (已有agent.env) | **现有可用** |
| 授权 | 角色隔离 (board/worker/observer) | **现有可用** |
| 消息签名 | HMAC (已有config.py) | **现有可用** |
| 网络 | VPS防火墙 + 仅开放MQTT端口 | 需要配置 |

### 3.4 离线模式 (Crucial)

Agent必须能在VPS不可用时继续工作——但降级到"单机模式"。

```
Agent启动 → 尝试连接远程Broker
  ├─ 成功 → 全功能模式 (Board/Persistence/多Agent)
  └─ 失败 → 降级模式:
       ├─ 创建本地临时Board (lite in-memory board)
       ├─ 任务日志写本地文件
       └─ 每N分钟重试连接 → 恢复后同步
```

---

## 4. 实施路线（建议3阶段）

### 阶段1: 配置化 + 远程Broker测试 (1周)

**目标**: 不搬任何服务，先验证远程连接可行性

```
1. 买VPS → 部署RMQTT Broker (最简单的组件)
2. 配置TLS证书 (Let's Encrypt + MQTT over TLS)
3. 创建远程JWT (在VPS上签发)
4. 本地Agent改 MQTT_HOST 为VPS IP → 验证连接
5. BoardService仍在本地的同时连远程Broker
```

**验收**: Agent通过MQTT over TLS连接到云端Broker，Post/Board正常。

### 阶段2: BoardService上云 (2-3周)

```
1. 把BoardService + config.py + agent.env 打包Docker
2. Docker Compose: RMQTT + MariaDB + BoardService
3. 迁移已有数据 (mysqldump → 远程导入)
4. 本地Agent连远程Broker + 远程BoardService
5. 验证多Agent: 本地A + 本地B 通过云端协作
```

**验收**: 两台不同机器上的Agent通过云BoardService协作完成任务。

### 阶段3: 离线降级 + 运营 (1周)

```
1. 实现Agent启动时的Broker健康探测
2. 实现降级模式: 连不上 → 单机lite board
3. 实现恢复同步: 上线后拉取云端未读消息
4. 添加监控: BoardService健康检查 + 告警
5. 文档: 部署运维手册
```

---

## 5. 需要预先解决的代码问题

### 5.1 环境变量集中化

当前 `127.0.0.1` 散落在约20+个文件中。虽然不是每个都需要改（很多LLM/浏览器相关），但需要清理。

### 5.2 BoardService启动时序

当前BoardService假定Broker已在本地运行。搬上云后，Docker Compose可以用 `depends_on` 保证顺序。

### 5.3 本地独占资源的显式声明

当前没有"本地独占"的概念。需要明确标记:
```python
LOCAL_RESOURCES = {
    "llm": {"type": "local", "host": "127.0.0.1:8080"},
    "browser": {"type": "local", "host": "127.0.0.1:18765"},
    "filesystem": {"type": "local", "cwd": "..."},
}
```

### 5.4 Agent身份注入

当前Agent身份通过 `agent.env` 静态配置。远程多Agent需要:
```yaml
# 每个Agent一个独立身份文件
agent_a.env:  MASTER_JWT=xxx
agent_b.env:  WORKER_JWT=yyy
```

---

## 6. 开放问题

1. **BoardService的Plugin Manager上云后**：插件（如CuriosityBoard）也运行在云端？那如何访问本地资源？
   → 插件分两类：**系统插件**(云端运行，纯MQTT逻辑) vs **本地钩子**(Agent进程内运行，访问本地资源)

2. **本地LLM的调度**：如果A机器LLM更强，B机器LLM更弱，云端BoardService能否智能路由任务？
   → 需WorkerAgent注册时声明能力 (已有 capability matching)

3. **成本**：VPS + MariaDB + 带宽。MQTT消息量有多大？
   → 估算: 每个Agent每分钟约10条消息，每条<1KB，10个Agent < 100KB/min → 极低

4. **延迟**：本地→云端MQTT延迟约20-50ms，对Agent的"感知-思考-行动"循环影响多大？
   → MQTT是异步pub/sub，BoardClient的等待模式有超时机制，延迟影响可控

5. **运维**：如果VPS挂了，所有Agent都降级。如何通知用户？
   → 本地Agent检测到连接失败后，可在本地UI显示黄色警告

---

> 下一篇：如果需要推进，建议从 **阶段1: 远程Broker测试** 开始。
> 先买VPS部署RMQTT，改一个环境变量看看能不能连上——这是最快的"验证原型"。
