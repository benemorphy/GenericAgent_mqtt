# 47秒之隙 — 系统架构概览

## 项目定位

AI辅助文学创作项目，基于"创造者悖论"主题，使用多Agent协作生成小说。同时运行一套完整的MQTT消息服务（BBS协议），连接飞书Bot、GA智能体、BoardService、MariaDB等组件。

---

## 系统拓扑（核心5服务）

```
                    Mosquitto (MQTT Broker :1883)
                            |
       +--------------------+--------------------+
       |                    |                    |
   BoardService        Feishu Bot          GA Handler
    (Rust :2999)        (fsapp.py)          (ga.py)
       |                    |                    |
       +-------- MariaDB (:3306) ---------------+
```

```
Mosquitto (MQTT broker :1883)
  ├── BoardService (Rust :2999)
  │   └── MariaDB (:3306) — 持久化
  ├── Feishu Bot (fsapp.py)
  │   └── 用户飞书消息 <-> GA响应
  ├── GA Handler (ga.py)
  │   └── LLM推理 + 记忆系统
  ├── Dashboard (streamlit :8501)
  │   └── 实时可视化
  └── Worker Agents (按需)
      └── 分布式任务执行
```

### 各服务角色

| 服务 | 技术栈 | 职责 | 当前状态 |
|------|--------|------|----------|
| **Mosquitto** | MQTT v5 | 消息枢纽，所有服务通过它发布/订阅通信 | 运行中(250连接) |
| **BoardService** | Rust | 认证网关(JWT)+持久化网关，BBS协议服务端 | 未运行 |
| **MariaDB** | MySQL 兼容 | 持久化存储(帖文/订阅/节点注册) | 运行中 |
| **Feishu Bot** | Python/fsapp.py | 飞书IM入口，用户消息->MQTT->GA->回复 | 手动启动 |
| **GA Handler** | Python/ga.py | 智能体核心，LLM推理+工具调用+记忆管理 | 运行中 |

### 辅助组件

- **Worker Agents** (按需) — 分布式子任务执行
- **Dashboard** (Streamlit :8501) — 实时可视化监控
- **simphtml** — 简易前端页面(未运行)

---

## MQTT 主题空间

```
bbs/   (协议层 — BoardService 管控)
├── register / register/response    — 客户端注册JWT
├── subscribe / unsubscribe         — 订阅管理
├── publish / publish/ack / notify  — 帖文CRUD
└── heartbeat                       — 心跳检测

board/ (应用层)
├── curiosity        — 好奇心讨论板
├── inspiration      — 灵感板
├── agent/*          — 各Agent专属
└── stream/*         — 数据流推送
```

---

## 三条核心数据流

### 1. 用户发消息到飞书 -> AI回复
```
飞书App -> (飞书API) -> fsapp.py -> (MQTT bbs/request/ga)
  -> ga.py Handler -> (LLM推理) -> (MQTT bbs/response/ga)
  -> fsapp.py -> (飞书API) -> 飞书App -> 用户
```

### 2. 灵感板操作 (/inspired)
```
飞书 /inspired add -> fsapp.py -> (MQTT board/inspiration)
  -> BoardService -> (验证JWT + 持久化MariaDB)
  -> (MQTT board/inspiration/response) -> fsapp.py -> 飞书
```

### 3. Agent 分布式执行
```
GA Handler -> (MQTT board/agent/task) -> Worker Agent
  Worker -> (执行任务) -> (MQTT board/agent/result) -> GA Handler
```

---

## 启动顺序 (start_all.ps1)

1. **MariaDB** — 数据库后台服务
2. **Mosquitto** — MQTT Broker
3. **BoardService** — Rust二进制 (board_service_rs)
4. Dashboard — Streamlit (可选)
5. **Feishu Bot** — 手动在.venv中启动 fsapp.py
6. **GA Handler** — ga.py (主智能体)

> **关键约束**: BoardService 必须在 Feishu Bot 和 GA 之前启动，否则客户端无法注册JWT，MQTT连接会超时。

---

## 设计原则

1. **MQTT为中心**: 所有服务不直连，全部通过 Mosquitto 间接通信
2. **统一认证**: BoardService 签发JWT，所有客户端需注册才能发布/订阅
3. **持久化隔离**: 仅 BoardService 直连 MariaDB，其他服务通过MQTT间接读写
4. **可替换前端**: 飞书Bot是当前入口，可替换为其他IM(如Discord/Telegram)

---


