# GenericAgent_mqtt

基于 [GenericAgent](https://github.com/lsdefine/GenericAgent)（MIT License）的衍生分支。
核心改动：以 MQTT 消息总线替换原文件式 Agent 通信，实现分布式跨机器实时协作。

---

## 项目结构（三大模块）

```
GenericAgent_mqtt/
├── Part 1: 智能体核心        ← 你日常交互的部分
├── Part 2: MQTT 基础设施     ← 放 VPS 上运行的服务
└── Part 3: GA_tools          ← 独立查看/格式转换工具
```

---

## Part 1: 智能体核心

与上游 GenericAgent 一脉相承的智能体系统，新增 MQTT 通信能力。

| 组件 | 说明 |
|------|------|
| `agentmain.py` / `ga.py` | 主入口，`ga agent` / `ga gui` / `ga web` |
| `ga_cli/` | CLI 命令集合 |
| `llmcore.py` | LLM 核心：多 Provider 工厂、Mixin Session、工具调用 |
| `frontends/` | 前端：飞书 Bot / Telegram / Web Gateway |
| `memory/` | 记忆系统：SOP / 技能 / 工作记忆 |
| `agents/` | WorkerAgent 实现 |
| `skills_learning/` | 案例驱动的技能学习 |
| `tools/` | 智能体工具集（见下方） |

### 智能体工具 (tools/)

| 工具 | 说明 |
|------|------|
| `dream_engine.py` | Agent Dreaming：记忆消化与跨域联想 |
| `reflection_engine.py` | 任务后反思与技能提取 |
| `brainstorm_swarm.py` | 脑暴集群：Round Robin + Delphi 多Agent创意生成 |
| `curiosity_board_client.py` | 好奇引擎：主动探测式学习与信号检测（客户端） |
| `curiosity_hooks.py` | 好奇引擎钩子集成 |
| `curiosity_trigger.py` | 好奇引擎触发策略 |
| `inspiration_board.py` | 灵感板 — MQTT 驱动的创意协作 |
| `gui_vision.py` | GUI 视觉感知与 OCR |
| `feishu_reminder.py` | 飞书Bot集成：定时提醒与群聊交互 |
| `file_search.py` | 文件搜索（pathlib + Everything SDK）|
| `security_audit.py` | 推送前安全审计 |
| `agent_runner.py` | 独立 Agent 运行器：`python agent_runner.py name cap1,cap2` |
| `config_service.py` | 统一配置加载与热重载 |
| `constraint_dashboard.py` | 约束状态感知仪表盘 |
| `failure_tracker.py` | 失败驱动学习跟踪器 |
| `hitl_approval.py` | 人在回路审批管理 |
| `observability.py` | 结构化日志 + Prometheus 指标 |
| `pii_masker.py` | LLM 调用前私域信息脱敏中间层 |
| `session_compactor.py` | 后台自动压缩 L4 原始历史会话 |
| `skill_review.py` | 间隔重复技能复习 |
| `step_detector.py` | 实时步骤检测：运行时追踪工具执行异常 |
| `turn_policy.py` | 可插拔回合策略链 |
| `llm_providers/` | LLM Provider 工厂：多模型统一接口 |
| `simphtml_rs/` | Rust HTML 简化引擎 |
| `metaso_search.py` | Metaso 搜索：联网搜索与知识获取 |
| `browser_service.py` | 浏览器自动化服务 |
| `todo_manager.py` | 待办事项管理 |
| `diagnosis_agent.py` | 诊断代理：系统问题排查 |

---

## Part 2: MQTT 基础设施（VPS 部署）

独立通信层服务，设计用于 VPS 部署。

| 组件 | 说明 | 部署方式 |
|------|------|----------|
| `Mqtt_bbs/` | BoardService + BBSClient + Persistence + Scheduler | `python -m Mqtt_bbs.board_service` |
| `tools/rmqtt_webui.py` | MQTT Broker Web 仪表盘 | `python tools/rmqtt_webui.py` |
| `tools/gen_jwt.py` | JWT Token 生成 | 工具脚本 |
| `tools/secrets.py` | 机密管理 | 工具脚本 |
| `docker/` / `Dockerfile.*` | Docker 部署 | `docker-compose up` |
| `k8s/` | Kubernetes 部署 | `kubectl apply -f k8s/` |

### MQTT BBS 主题协议

| 类别 | 主题 | 说明 |
|------|------|------|
| Board | `v2/board/{name}/register\|post\|query` | Agent 注册/发布/查询 |
| Task | `v2/task/{id}/input\|output\|status` | 任务分发与状态 |
| State | `v2/state/{ns}/{key}` | 共享状态（CAS 乐观锁）|
| 响应槽 | `v2/agent/{id}/rpc/res/#` | 预订阅 RPC 响应 |

### 快速部署

```bash
# 1. 启动 MQTT Broker
rmqtt start

# 2. 启动 BoardService
python -m Mqtt_bbs.board_service
```

---

## Part 3: GA_tools（独立工具集）

与智能体无关的独立查看/格式转换工具。

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
| Agent 通信 | 文件读写 + 轮询 | MQTT Pub/Sub + 实时推 |
| 机器边界 | 单机 | 跨机 via Broker |
| 实时性 | 秒级 | 毫秒级 |
| 并发度 | 1:1 | N:M 任意并发 |
| 共享状态 | 无 | WhiteboardKV（CAS 乐观锁）|
| 能力发现 | 无 | CapabilityRegistry |
| 任务分发 | 文件目录约定 | Board + DAG Workflow |

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
rmqtt start && python -m Mqtt_bbs.board_service
python agentmain.py --broker-host 127.0.0.1
```

---

## 许可

MIT License — 与上游 [GenericAgent](https://github.com/lsdefine/GenericAgent) 相同。
