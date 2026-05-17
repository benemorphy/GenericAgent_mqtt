# MariaDB 持久化方案 — Retain + Session 消息

> **背景**: 使用公共 EMQX Broker (broker.emqx.io)，无法控制 Broker 侧的持久化行为。
> **方案**: 在应用层（Python BBSClient）用本地 MariaDB 实现 Retain 持久化 + Session 离线队列。
> **目标**: 替代 EMQX 的 Retain As Published + Persistent Session，不依赖 Broker 配置。
> **数据库**: MariaDB 12.1.2 (127.0.0.1:3306, user=root, password=mariadb)

---

## 1. 架构定位

```
                     ┌──────────────────────┐
  PUB/SUB            │   公共 EMQX Broker    │  ← 实时消息通道，无持久化保证
                     │   broker.emqx.io:1883 │
                     └──────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
    ┌────▼────┐          ┌─────▼─────┐          ┌─────▼─────┐
    │ Agent A │          │ Agent B   │          │  Persist  │
    │ (Worker)│          │ (Master)  │          │   Layer   │
    └─────────┘          └───────────┘          └─────┬─────┘
                                                      │
                                               ┌──────▼──────┐
                                               │  MariaDB    │
                                               │  12.1.2     │
                                               │  mqtt_bbs   │
                                               │    DB       │
                                               └─────────────┘
```

**核心思路**: Persistence Layer 是一个**透明的中间层**，Agent 调用 publish()/subscribe() 时自动拦截：
- **写入路径**: PUBLISH → 写 MariaDB → 发 MQTT（双写）
- **读取路径**: SUBSCRIBE → 订阅 MQTT + 从 MariaDB 恢复 Retain + 重放离线消息

---

## 2. 数据库设计

### 2.1 数据库与表

```sql
-- 创建专用数据库
CREATE DATABASE IF NOT EXISTS mqtt_bbs 
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mqtt_bbs;

-- ── 表1: retained_messages ──
-- 对标: EMQX Retain 特性。每条 topic 保留最新一条消息。
-- 作用: Agent 重启/新订阅时恢复最后状态

CREATE TABLE IF NOT EXISTS retained_messages (
    topic           VARCHAR(512)    NOT NULL PRIMARY KEY,
    payload         LONGTEXT        NOT NULL,
    content_type    VARCHAR(64)     DEFAULT 'application/json',
    qos             TINYINT         DEFAULT 1,
    source_agent    VARCHAR(128)    DEFAULT NULL,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) 
                                      ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 表2: session_queue ──
-- 对标: EMQX Persistent Session。
-- Agent 离线时暂存消息，上线后按顺序重放。
-- 每条消息独立，一个 topic 可有多条未读。

CREATE TABLE IF NOT EXISTS session_queue (
    id              BIGINT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    target_agent    VARCHAR(128)    NOT NULL COMMENT '收件人 agent_id',
    topic           VARCHAR(512)    NOT NULL,
    payload         LONGTEXT        NOT NULL,
    qos             TINYINT         DEFAULT 1,
    seq             INT             NOT NULL DEFAULT 0 COMMENT '消息序号',
    is_retained     BOOLEAN         DEFAULT FALSE,
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    delivered       BOOLEAN         DEFAULT FALSE,
    delivered_at    DATETIME(3)     DEFAULT NULL,
    
    INDEX idx_agent_undelivered (target_agent, delivered, seq),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── 表3: agent_sessions ──
-- 跟踪每个 Agent 的会话状态：最后一次上线/下线时间

CREATE TABLE IF NOT EXISTS agent_sessions (
    agent_id        VARCHAR(128)    NOT NULL PRIMARY KEY,
    last_online     DATETIME(3)     DEFAULT NULL,
    last_offline    DATETIME(3)     DEFAULT NULL,
    last_seq        INT             NOT NULL DEFAULT 0 COMMENT '最后发送的seq',
    status          ENUM('online','offline','busy') DEFAULT 'offline',
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                                      ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 查询示例

```sql
-- 恢复某 Agent 所有未读离线消息（按顺序）
SELECT * FROM session_queue 
WHERE target_agent = 'worker_01' AND delivered = FALSE 
ORDER BY seq ASC;

-- 恢复 Retain 状态（Agent 订阅后读取全部 retained topics）
SELECT * FROM retained_messages 
WHERE topic LIKE 'agent/board/task/%';

-- 获取某 task 的最新 input/output
SELECT * FROM retained_messages 
WHERE topic IN (
  'agent/board/task/task_001/input',
  'agent/board/task/task_001/output',
  'agent/board/task/task_001/signal'
);

-- 清理过期 session 消息（7天以上）
DELETE FROM session_queue 
WHERE created_at < NOW() - INTERVAL 7 DAY;
```

---

## 3. 持久化层设计

### 3.1 类结构

```
BBSClient (现有)
    │   publish() → MQTT Broker
    │   subscribe() → MQTT Broker  
    │   _on_message() → callback
    │
    ▼
    ┌─────────────────────────────────────┐
    │  BBSClientWithPersistence          │  ← 新增，继承/装饰 BBSClient
    │                                     │
    │  publish(topic, payload, retain)   │  ├─ retain=True → 写 MariaDB
    │                                     │  │                 → 发 MQTT
    │  subscribe(topic, callback)        │  ├─ SUB MQTT → callback
    │                                     │  ├─ 读 retained_messages → callback
    │  _on_connect()                      │  ├─ 重放 session_queue → callback
    │                                     │  ├─ 更新 agent_sessions
    │  _on_disconnect()                   │  └─ 更新 agent_sessions.offline
    │                                     │
    │  DB Manager (MariaDBConn)          │  ← 连接池、CRUD、事务
    └─────────────────────────────────────┘
```

### 3.2 核心流程

#### Retain 发布流程

```
Agent.publish("agent/board/task/task_001/input", payload, retain=True)

    ┌─ MariaDB ─────────────────────┐
    │ INSERT ... ON DUPLICATE KEY   │  ← UPSERT: topic为主键
    │ UPDATE retained_messages      │
    │ SET payload=..., updated_at=now│
    └───────────────────────────────┘
    
    ┌─ MQTT ───────────────────────┐
    │ PUBLISH topic/input          │  ← 仍发给 EMQX
    │   retain=True                │
    └──────────────────────────────┘
```

#### 重连恢复流程

```
Agent 上线
    │
    ├─ 1. 更新 agent_sessions (online)
    │
    ├─ 2a. 读取 retained_messages 中所有已订阅的 topic
    │      → 逐个调用 callback(topic, payload)
    │
    ├─ 2b. 读取 session_queue 中未送达的离线消息
    │      → 按 seq 顺序调用 callback(topic, payload)
    │      → 标记 delivered = TRUE
    │
    └─ 3. 正常接收 MQTT 实时推送
```

#### 流式消息处理

stdout/stderr 不需要 Retain，但在 Agent 离线期间发送的需要缓存：

```
WorkerA 执行任务中 → 发 stdout seq=3,4,5
    │
    ├─ Master 在线 → MQTT 直接送达 ✅
    │
    └─ Master 离线 → session_queue 缓存
                    └─ Master 上线后按序重放
```

---

## 4. 数据流全景（含持久化）

```
┌─ AgentBoard (Master) ──────────────────────────────────────┐
│                                                             │
│  1. post_task(type, input)                                  │
│     ├─ MariaDB: retained_messages ← {task/input}           │
│     ├─ MQTT:    PUBLISH task/input [retain]                 │
│     └─ MariaDB: session_queue → 如果 Worker 离线则排队     │
│                                                             │
│  2. wait_task(task_id)                                      │
│     ├─ SUB task/output → callback                           │
│     ├─ MariaDB: 先读 retained_messages (可能已完成)        │
│     └─ MariaDB: session_queue (离线期间产出)               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─ WorkerAgent ──────────────────────────────────────────────┐
│                                                             │
│  1. 上线 (connect)                                          │
│     ├─ MariaDB: agent_sessions ← online                    │
│     ├─ MQTT:    SUB task/+/input                           │
│     ├─ MariaDB: 读 retained 恢复已有任务状态               │
│     └─ MariaDB: 读 session_queue 重放离线期间消息          │
│                                                             │
│  2. claim_task(task_id)                                     │
│     ├─ MQTT:  PUBLISH task/claim + task/status=running     │
│     └─ MariaDB: retained_messages ← {status, claim}        │
│                                                             │
│  3. stream_out(data) / stream_err(data)                     │
│     ├─ MQTT:  PUBLISH task/stdout [qos=0, no retain]       │
│     │        (如果订阅者离线，qos=0 消息丢失)               │
│     └─ MariaDB: 可选 — 如需要完整日志，追加到日志表        │
│                                                             │
│  4. complete(result)                                        │
│     ├─ MQTT:  PUBLISH task/output [retain]                 │
│     ├─ MQTT:  PUBLISH task/signal [ROUND_END]              │
│     ├─ MariaDB: retained_messages ← {output, signal}       │
│     └─ MariaDB: 清理 session_queue 中该 task 的缓存       │
│                                                             │
│  5. 下线 (disconnect / LWT)                                 │
│     ├─ MQTT:  LWT → node/worker_01/status = offline        │
│     └─ MariaDB: agent_sessions ← offline                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 表字段详解

### retained_messages

| 字段 | 类型 | 说明 |
|:----|:----|:-----|
| topic | VARCHAR(512) PK | 完整主题，如 `agent/board/task/task_001/input` |
| payload | LONGTEXT | JSON 序列化的消息体（最大4GB） |
| content_type | VARCHAR(64) | 内容类型，默认 `application/json` |
| qos | TINYINT | 发布时的 QoS |
| source_agent | VARCHAR(128) | 发布者 agent_id（用于追踪） |
| created_at | DATETIME(3) | 首次发布时间 |
| updated_at | DATETIME(3) | 最后更新时间（UPSERT 自动更新） |

### session_queue

| 字段 | 类型 | 说明 |
|:----|:----|:-----|
| id | BIGINT PK AUTO_INC | 自增主键 |
| target_agent | VARCHAR(128) | 目标收件人 agent_id |
| topic | VARCHAR(512) | 完整主题 |
| payload | LONGTEXT | JSON 消息体 |
| qos | TINYINT | 建议重放时的 QoS |
| seq | INT | **消息序号** — 保证重放顺序 |
| is_retained | BOOLEAN | 原始消息是否 retain |
| created_at | DATETIME(3) | 入队时间 |
| delivered | BOOLEAN | 是否已送达 |
| delivered_at | DATETIME(3) | 送达时间 |

### agent_sessions

| 字段 | 类型 | 说明 |
|:----|:----|:-----|
| agent_id | VARCHAR(128) PK | 智能体唯一ID |
| last_online | DATETIME(3) | 最后一次上线时间 |
| last_offline | DATETIME(3) | 最后一次下线时间 |
| last_seq | INT | 最后发送的消息序号 |
| status | ENUM | 当前状态 |
| updated_at | DATETIME(3) | 行更新时间 |

---

## 6. 与文件体系的对照

```
文件体系                  MariaDB 持久化                  MQTT 实时层
─────────               ─────────────                 ────────────
input.txt 永久留存  →    retained_messages            PUBLISH input
output.txt 永久留存  →    retained_messages            PUBLISH output
stdout 日志         →    (可选: msg_log 表)           PUBLISH stdout (qos=0)
PID 标识            →    agent_sessions               node/{id}/status
temp/{name}/ 目录   →    topic = agent/board/task/..  PUB/SUB 主题空间
轮询 output.txt     →    读 retained_messages          Subscribe 推送
```

---

## 7. 实现计划

### Phase 1: PersistenceLayer 类

```
文件: mqtt_bbs/persistence.py

class MariaDBConn:
    """MariaDB 连接管理（连接池）"""
    def __init__(self, host, port, user, password, database)
    def execute(sql, params) → cursor
    def executemany(sql, params_list)
    
class BBSClientWithPersistence(BBSClient):
    """带持久化的 BBSClient 装饰器"""
    
    def publish(self, topic, payload, retain=False):
        if retain:
            self._db.upsert_retained(topic, payload, ...)
        super().publish(topic, payload, retain)
        # 如果目标离线，也写入 session_queue
    
    def subscribe(self, topic, callback):
        super().subscribe(topic, callback)
        # 恢复 retained
        for msg in self._db.get_retained(topic):
            callback(msg.topic, msg.payload)
        # 重放离线队列
        for msg in self._db.get_undelivered(agent_id):
            callback(msg.topic, msg.payload)
    
    def _on_connect(self, ...):
        super()._on_connect(...)
        self._db.set_agent_online(agent_id)
        self._replay_session_queue()
    
    def _on_disconnect(self, ...):
        self._db.set_agent_offline(agent_id)
        super()._on_disconnect(...)
```

### Phase 2: 集成到 AgentBoard / WorkerAgent

```
AgentBoardWithPersistence(AgentBoard):
    def __init__(self):
        self._client = BBSClientWithPersistence(...)
        self._db = MariaDBConn(...)

WorkerAgentWithPersistence(WorkerAgent):
    def __init__(self):
        self._client = BBSClientWithPersistence(...)
        self._db = MariaDBConn(...)
```

### Phase 3: 迁移步骤

1. 创建 `mqtt_bbs` 数据库及3张表
2. 实现 `persistence.py`（MariaDBConn + BBSClientWithPersistence）
3. 用 `BBSClientWithPersistence` 替换现有 `BBSClient`
4. 测试: 断线重连后 retained 恢复 + 离线消息重放

---

## 8. 风险与边界

| 风险 | 影响 | 缓解 |
|:----|:----|:-----|
| MariaDB 宕机 | 持久化失效，实时层仍正常 | BBSClientWithPersistence 自动降级为纯内存模式 |
| 公共 EMQX Broker 重置 | 所有 Retain 消息丢失 | MariaDB retained_messages 做安全网 |
| session_queue 膨胀 | 磁盘/性能 | 定期清理（7天TTL）+ 分页读取 |
| 并发重放顺序 | 多个 Agent 同时重放导致乱序 | seq字段排序 + 逐条回调 |
| MariaDB 密码变更 | 连接失败 | 环境变量/配置文件管理 |
