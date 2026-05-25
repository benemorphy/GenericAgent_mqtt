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
| `tools/llm_providers/` | LLM Provider工厂：多模型统一接口（Claude/OpenAI等，注册表模式） |
| `tools/security_audit.py` | 安全审计：推送前自动扫描密钥泄露 |
| `tools/brainstorm_swarm.py` | 脑暴集群：Round Robin + Delphi 多Agent创意生成 |
| `tools/curiosity_engine.py` | 好奇引擎：主动探测式学习与信号检测 |
| `tools/reflection_engine.py` | 反省引擎：任务后反思与技能提取 |
| `tools/dream_engine.py` | Agent Dreaming 记忆消化与跨域联想 |
| `tools/inspiration_board.py` | 灵感板 — MQTT 驱动的创意协作 |
| `tools/gui_vision.py` | GUI 视觉感知与 OCR |
| `tools/ljqCtrl_sop+.py` | 键鼠自动化操作 |
| `tools/tmwebdriver_sop+.py` | 浏览器自动化（文件上传/截图/CDP） |
| `tools/feishu_reminder.py` | 飞书Bot集成：定时提醒与群聊交互 |
| `tools/board_service_rs/` | Rust BoardService：高性能MQTT服务 |
| `tools/md_server_rs/` | Rust文档服务器：高性能Markdown渲染 |
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
export DB_PASSWORD=your_password
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

## Web 网关 (FastAPI)

统一登录入口，访问所有公开内容：

```bash
python -m frontends.gateway.main
# → http://localhost:8000/
```

| 路由 | 功能 | 认证 |
|------|------|------|
| `/login`, `/register` | 登录/注册 | 否 |
| `/boards` | 6个公开板块：灵感/脑暴/BBS帖/任务/梦境/Deep Research | 是 |
| `/agents` | Agent 在线状态列表与详情 | 是 |
| `/dashboard` | 实时 MQTT 仪表盘 (WebSocket) | 是 |
| `/docs/ROADMAP.md` | Markdown 文档 (Rust md_server_rs 代理) | 是 |

---

## 许可 & 致谢

MIT License — 与上游 [GenericAgent](https://github.com/lsdefine/GenericAgent) 相同。

## 路线图

详见 [ROADMAP.md](./ROADMAP.md)
