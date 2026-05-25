# GenericAgent_mqtt

基于 [GenericAgent](https://github.com/lsdefine/GenericAgent)（MIT License）的衍生分支。
核心改动：以 MQTT 消息总线替换原文件式 Agent 通信，实现分布式跨机器实时协作。

---

## 项目结构（三大模块）

```
GenericAgent_mqtt/
├── Part 1: 智能体核心        ← 你日常交互的部分
├── Part 2: MQTT 基础设施     ← 放 VPS 上运行的服务
└── Part 3: GA_viewer          ← 独立查看/格式转换工具
```

---

## Part 1: 智能体核心

与上游 GenericAgent 一脉相承的智能体系统，新增 MQTT 通信能力。

| 组件 | 说明 |
|------|------|
| `agentmain.py` | 主入口，交互式 Agent CLI |
| `ga.py` / `ga_cli/` | `ga agent`, `ga gui`, `ga list`, `ga web`, `ga hub` 等命令 |
| `llmcore.py` | LLM 核心：多Provider工厂、Mixin会话、工具调用 |
| `frontends/` | 前端接入：飞书Bot / Telegram / Web网关 |
| `memory/` | 记忆系统：SOP、技能、工作记忆 |
| `agents/` | WorkerAgent 实现 |
| `skills_learning/` | 案例驱动的技能学习体系 |
| `tools/` | 智能体工具集（见下表） |

### 智能体工具 (tools/)

| 工具 | 说明 |
|------|------|
| `dream_engine.py` | Agent Dreaming 记忆消化与跨域联想 |
| `reflection_engine.py` | 任务后反思与技能提取 |
| `brainstorm_swarm.py` | 脑暴集群：Round Robin + Delphi 多Agent创意生成 |
| `curiosity_engine.py` | 好奇引擎：主动探测式学习 |
| `inspiration_board.py` | 灵感板 — MQTT 驱动的创意协作 |
| `gui_vision.py` | GUI 视觉感知与 OCR |
| `feishu_reminder.py` | 飞书Bot集成：定时提醒与群聊 |
| `file_search.py` | 文件搜索 (pathlib + Everything SDK) |
| `security_audit.py` | 推送前安全审计 |
| `llm_providers/` | LLM Provider统一接口 |
| `simphml_rs/` | Rust HTML 简化引擎 |

---

## Part 2: MQTT 基础设施（VPS 部署）

独立部署的通信层服务，未来放在 VPS 上运行。

| 组件 | 说明 | 部署方式 |
|------|------|----------|
| `mqtt_bbs/` | BoardService + BBSClient + 持久化 + 调度 | `python -m mqtt_bbs.board_service` |
| `tools/board_service_rs/` | Rust 版高性能 BoardService | 独立二进制 |
| `tools/mqtt_bbs_rs/` | Rust MQTT BBS 组件 | 独立二进制 |
| `tools/rmqtt_webui.py` | MQTT Broker Web 管理面板 | `python tools/rmqtt_webui.py` |
| `tools/rmqtt_webui_rs/` | Rust 版 Web 管理面板 | 独立二进制 |
| `tools/rmqtt_auth_rs/` | Rust MQTT 认证扩展 | 独立二进制 |
| `tools/gen_jwt.py` | JWT 令牌生成 | 工具脚本 |
| `tools/secrets.py` | 密钥管理 | 工具脚本 |
| `docker/` / `Dockerfile.*` | Docker 部署配置 | `docker-compose up` |
| `k8s/` | Kubernetes 部署配置 | `kubectl apply -f k8s/` |

### MQTT BBS 主题协议

| 类别 | 主题 | 说明 |
|------|------|------|
| 公告板 | `v2/board/{name}/register\|post\|query` | Agent注册/发帖/查询 |
| 任务 | `v2/task/{id}/input\|output\|status` | 任务分发与状态跟踪 |
| 状态 | `v2/state/{ns}/{key}` | 共享状态（CAS乐观锁） |
| 响应槽 | `v2/agent/{id}/rpc/res/#` | 预订阅RPC响应 |

### 快速部署

```bash
# 1. 启动 MQTT Broker
rmqtt start

# 2. 启动 BoardService（Python版）
python -m mqtt_bbs.board_service

# 3. 或使用 Rust 版（高性能）
cd GA_viewer && md_server_rs/target/release/board_service_rs
```

---

## Part 3: GA_viewer（独立工具集）

与本项目主体无关的查看/格式转换工具，可独立使用。

| 工具 | 说明 |
|------|------|
| `md_to_ppt_pipeline.py` | Markdown → PPT 转换管道 |
| `echart_ppt_pipeline.py` | ECharts HTML预览 → pyecharts → PPT |
| `html_slides.py` | HTML 幻灯片生成 |
| `md_server_rs/` | Rust 高性能 Markdown 文档服务器 |
| `patch_echarts.py` | Chart.js 替换为 ECharts |
| `benchmark.py` | 性能基准测试 |
| `file_sync_agent.py` | 文件同步工具 |

---

## 与上游对比

| 维度 | GenericAgent (上游) | GenericAgent_mqtt |
|------|--------------------|-------------------|
| Agent 通信 | 文件读写 + 轮询 | MQTT Pub/Sub + 实时推送 |
| 机器边界 | 单机 | 跨机器，通过 Broker 互联 |
| 实时性 | 秒级 | 毫秒级 |
| 并行度 | 1:1 | N:M 任意并发 |
| 状态共享 | 无 | WhiteboardKV（CAS乐观锁） |
| 能力发现 | 无 | CapabilityRegistry |
| 任务分发 | 文件目录约定 | 公告板 + DAG 工作流 |

---

## 快速开始

```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt && pip install -e .
# 配置环境变量（优先）或 mykey.py
set DEEPSEEK_API_KEY=sk-xxx
ga agent    # 交互式 Agent
```

启用 MQTT 模式：

```bash
rmqtt start && python -m mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

---

## 许可

MIT License — 与上游 [GenericAgent](https://github.com/lsdefine/GenericAgent) 相同。
