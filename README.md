# GenericAgent_mqtt

基于 [GenericAgent](https://github.com/lsdefine/GenericAgent)（MIT License）的衍生分支。
核心改动：以 MQTT 消息总线替换原文件式 Agent 通信，实现分布式跨机器实时协作。
感谢上游作者 lsdefine 的开源贡献。

---

## 与上游对比

| 维度 | GenericAgent (上游) | GenericAgent_mqtt |
|------|--------------------|-------------------|
| Agent 通信 | 文件读写 + 轮询 | MQTT Pub/Sub + 实时推送 |
| 机器边界 | 单机（NFS 勉强跨机） | 跨机器，通过 Broker 互联 |
| 实时性 | 秒级（轮询间隔） | 毫秒级（事件驱动） |
| 并行度 | 1:1（单 Agent 单任务） | N:M 任意并发 |
| 状态共享 | 无 | WhiteboardKV（CAS 乐观锁） |
| 能力发现 | 无 | CapabilityRegistry（注册中心） |
| 任务分发 | 文件目录约定 | 公告板 + DAG 工作流 |

---

## 架构（5层）

| 层 | 说明 |
|----|------|
| 编排层 | LangGraph / AgentBoard / DAGWorkflow |
| 业务层 | AgentBoard+WorkerAgent / WhiteboardKV / CapabilityRegistry |
| **通信层** | **BoardClient / BoardService / PluginSystem / Persistence** |
| 中间件 | MQTT Broker (Mosquitto / RMQTT / EMQX) |
| 核心层 | GA Handler / Tool System / LLM Core / Memory / SOP |

---

## 核心工具

| 工具 | 说明 |
|------|------|
| `mqtt_bbs/` | MQTT 通信层，核心差异点 |
| `ga_cli/` | CLI 命令：`ga gui`, `ga agent`, `ga list`, `ga web`, `ga hub` |
| `tools/dream_engine.py` | Agent Dreaming 记忆消化与跨域联想 |
| `tools/inspiration_board.py` | 灵感板 — MQTT 驱动的创意协作 |
| `tools/gui_vision.py` | GUI 视觉感知与 OCR |
| `tools/ljqCtrl_sop+.py` | 键鼠自动化操作 |
| `tools/tmwebdriver_sop+.py` | 浏览器自动化（文件上传/截图/CDP） |
| `skills_learning/` | 案例驱动的技能学习体系 |

---

## MQTT BBS 主题协议

| 类别 | 主题 | 说明 |
|------|------|------|
| 公告板 | `v2/board/{name}/register|post|query` | Agent注册/发帖/查询 |
| 任务 | `v2/task/{id}/input|output|status` | 任务分发与状态跟踪 |
| 状态 | `v2/state/{ns}/{key}` | 共享状态（CAS乐观锁） |
| 响应槽 | `v2/agent/{id}/rpc/res/#` | 预订阅RPC响应，消除动态订阅 |

---

## 持久化

支持 MariaDB 持久化，配置方式：

```bash
export DB_HOST=127.0.0.1
export DB_PASSWORD=mariadb
python -m mqtt_bbs.board_service   # BoardService 自带持久化
python -m mqtt_bbs.persistence_worker  # 全量消息日志 Worker（可选）
```

也可使用 SQLite（默认，无需配置）。

---

## 快速开始

```bash
git clone https://github.com/your-repo/GenericAgent_mqtt.git
cd GenericAgent_mqtt && pip install -e .
ga config   # 配置 API Key
ga agent    # 交互式 Agent
```

启用 MQTT：

```bash
rmqtt start && python -m mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

环境变量：`MQTT_HOST`、`MQTT_PORT`、`MQTT_USERNAME`、`MQTT_PASSWORD`、`DB_HOST`、`DB_PASSWORD`

---

## 许可 & 致谢

MIT License — 与上游 [GenericAgent](https://github.com/lsdefine/GenericAgent) 相同。

## 路线图

详见 [ROADMAP.md](./ROADMAP.md)
