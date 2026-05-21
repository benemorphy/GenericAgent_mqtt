# 基础设施分层方案补充设计

> 日期: 2026-05-22 | 补充: BBS查询机制 / Agent身份层级 / MariaDB云端
> 前置: infrastructure_decoupling_brainstorm.md + infrastructure_deep_dive.md

---

## 1. Agent身份层级模型

用户明确要求: **管理者Agent管理基础设施, 一般Agent使用基础设施。**

### 四级角色体系

```
                  ┌─────────────────────────────────┐
                  │       系统管理员 (Admin)          │
                  │ 能看到所有, 能管理基础设施         │
                  │   ┌──────────────────────┐      │
                  │   │  运维者 (Operator)    │      │
                  │   │ 管理Agent注册/分配     │      │
                  │   │   ┌──────────────┐  │      │
                  │   │   │ 工作者 (Worker)│  │      │
                  │   │   │ 日常Agent     │  │      │
                  │   │   │   ┌────────┐ │  │      │
                  │   │   │   │观察者   │ │  │      │
                  │   │   │   │(只读)   │ │  │      │
                   ...[Truncated]...
---+

## 4. 更新后的云端架构总图

```

                    Cloud VPS (Docker Compose)
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  ┌──────────┐  ┌────────────────┐  ┌──────────────────┐  │
  │  │  Nginx    │  │  BoardService  │  │   RMQTT Broker   │  │
  │  │ (反向代理) │  │  (核心业务)    │  │   (MQTT 5.0)     │  │
  │  │  :443    │  │                │  │    :8883(TLS)    │  │
  │  │  :1883   │  │  PluginManager │  │                  │  │
  │  └────┬─────┘  │  (Curiosity等) │  │  Last Will       │  │
  │       │        └────────┬───────┘  │  遗嘱/保留消息     │  │
  │       │                 │          └────────┬─────────┘  │
  │       │                 │                    │            │
  │       │           ┌─────┴────────────────────┴──┐         │
  │       │           │        MariaDB (云端)         │         │
  │       │           │  boards / posts / users       │         │
  │       │           │  whiteboard / capabilities    │         │
  │       │           │  agent_registry / sessions    │         │
  │       │           └──────────────────────────────┘         │
  │       │                                                    │
  │       └────── HTTP REST API ────────┐                      │
  │                                     │                      │
  └─────────────────────────────────────┼──────────────────────┘
                                        │
          ┌──────────────┬──────────────┼──────────────┬─────────────┐
          ▼              ▼              ▼              ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Admin    │  │ Operator │  │ Worker A │  │ Worker B │  │ Observer │
    │ Agent    │  │ Agent    │  │ (上海)   │  │ (北京)   │  │ (只读)   │
    │ 云端管理  │  │ 基础设施  │  │ 日常任务  │  │ 数据分析  │  │ 监控面板  │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 连接方式

| 层 | 协议 | 端口 | 认证 |
|:---|:-----|:-----|:-----|
| MQTT (实时publish/wait) | MQTTS | 8883 | Agent JWT + TLS |
| HTTP REST (查询/管理) | HTTPS | 443 | Admin JWT + API Key |
| DB直连 (Admin仅限) | MySQL | 3306 | 仅VPS内部, 不对外 |

---

## 5. Agent配置示例

### Admin Agent 配置

```yaml
# agent_admin_config.yaml
agent_id: "admin_01"
role: "admin"
capabilities: ["infra:manage", "infra:deploy", "infra:monitor"]
broker:
  host: "vps.example.com"
  port: 8883
  tls: true
  jwt: "eyJhZG1pbi4uLiJ9..."
http_api:
  endpoint: "https://vps.example.com/api/v1"
  api_key: "sk-xxx..."
```

### Worker Agent 配置 (日常Agent)

```yaml
# agent_worker_config.yaml
agent_id: "worker_shanghai_01"
role: "worker"
capabilities: ["python", "web", "file"]
broker:
  host: "vps.example.com"
  port: 8883
  tls: true
  jwt: "eyJ3b3JrZXIuLi4ifQ..."
# 无http_api → 只能通过MQTT操作, 不能管理基础设施
```

---

> 更新: 基于这三点的补充, 建议下次打开 `infrastructure_decoupling_brainstorm.md` 时一并整合。
