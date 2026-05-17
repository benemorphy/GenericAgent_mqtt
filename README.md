<div align="center">
<img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/bar.jpg" width="880"/>
</div>

> 🍴 **Fork of [GenericAgent](https://github.com/lsdefine/GenericAgent)** — 衍生自 [lsdefine](https://github.com/lsdefine) 的极简自进化 Agent 框架。  
> **核心改动**: MQTT BBS — 用事件驱动的 MQTT 消息总线替代原文件式 Agent 通信，解锁分布式、跨机器、实时协作能力。  
> 上游项目 MIT License，本分支亦同。

---

<p align="center">
  <a href="#english">English</a> | <a href="#chinese">中文</a>
</p>

---

<a name="english"></a>

## 🍴 What's Different in This Fork

| Feature | Original (GenericAgent) | This Fork (GenericAgent_mqtt) |
|---------|------------------------|-------------------------------|
| **Agent Communication** | `file_io_bbs` — file read/write + polling | `mqtt_bbs` — MQTT Pub/Sub + push |
| **Machine Boundary** | Single machine (NFS hacky) | Cross-machine via network broker |
| **Real-time** | Seconds (polling interval) | Milliseconds (event-driven push) |
| **Parallelism** | Serial (1 task/agent) | N:M arbitrary concurrency |
| **Liveness Detection** | PID check (zombie-prone) | CONNECT/LWT protocol-level |
| **Persistence** | None (delete `temp/` = data loss) | MariaDB optional (Retain + offline queue) |
| **CLI Tools** | No unified entry | `skill_learn_from_cases` + `dashboard_mqtt` |

All original GenericAgent capabilities (browser automation, self-evolution, 9 atomic tools, vision, ADB, memory system) remain fully intact.

---

## 🌟 Overview

**GenericAgent** is a minimal (~3K lines core), self-evolving autonomous agent framework. Through **9 atomic tools + a ~100-line Agent Loop**, it gives any LLM system-level control over a local computer — browser, terminal, filesystem, keyboard/mouse, vision, and mobile (ADB).

The core philosophy: **don't preload skills — evolve them.** Every time it solves a new task, the execution path is automatically crystallized into a reusable skill. Over time, the agent builds a unique skill tree grown from 3K lines of seed code.

> 🤖 **Self-Bootstrap Proof** — Everything in this repository, from `git init` to every commit, was done autonomously by GenericAgent. The author never opened a terminal.

This fork inherits all of the above, and upgrades the **agent-to-agent communication layer** from file-based polling to MQTT event-driven messaging — enabling multi-agent, cross-machine, real-time collaboration.

---

## 🧬 Self-Evolution Mechanism (Upstream)

```
[New Task] → [Autonomous Exploration] (installs deps, writes scripts, debugs & verifies) →
[Crystallize Execution Path into Skill] → [Write to Memory Layer] → [Direct Recall on Next Similar Task]
```

| What you say | First time | Every time after |
|---|---|---|
| *"Read my WeChat messages"* | Install deps → reverse DB → write script → save skill | **one-line invoke** |
| *"Monitor stocks and alert me"* | Install libs → build screener → config cron → save skill | **one-line invoke** |

> 📄 [Technical Report on arXiv](https://arxiv.org/abs/2604.17091) — *GenericAgent: A Token-Efficient Self-Evolving LLM Agent via Contextual Information Density Maximization*

---

## 📊 Comparison with Similar Tools

| Feature | GenericAgent | OpenClaw | Claude Code |
|---------|:---:|:---:|:---:|
| **Codebase** | ~3K lines | ~530,000 lines | Large |
| **Deployment** | `pip install` + API Key | Multi-service orchestration | CLI + subscription |
| **Browser Control** | Real browser (session preserved) | Sandbox / headless browser | Via MCP plugin |
| **OS Control** | Mouse/kbd, vision, ADB | Multi-agent delegation | File + terminal |
| **Self-Evolution** | Autonomous skill growth | Plugin ecosystem | Stateless between sessions |
| **Out of the Box** | A few core files + starter skills | Hundreds of modules | Rich CLI toolset |

---

## 📈 Evaluation — Five Dimensions

> 📂 Full datasets & results: <https://github.com/JinyiHan99/GA-Technical-Report/tree/main>

| Dimension | Key Question | Benchmarks |
|-----------|-------------|------------|
| **Task Completion & Token Efficiency** | Can GA complete hard tasks cheaper than leading agents? | SOP-Bench, Lifelong AgentBench, RealFin-Benchmark |
| **Tool-Use Efficiency** | Does a minimal toolset beat specialized toolsets? | Tool Efficiency Benchmark (11 simple + 5 long-horizon) |
| **Memory System Effectiveness** | Does condensed hierarchical memory beat full/embedding-based retrieval? | SOP-Bench (dangerous goods), LoCoMo, 20-skill stress test |
| **Self-Evolution Capability** | Can the agent distill experience into reusable SOPs without intervention? | 9-round LangChain study, 8-task cross-task web benchmark |
| **Web Browsing Capability** | Can it survive the open web? | WebCanvas, BrowseComp-ZH, Custom Tasks (22) |

Baselines: **Claude Code**, **OpenAI CodeX**, **OpenClaw** under Claude Sonnet 4.6, Claude Opus 4.6, GPT-5.4, MiniMax M2.5 backbones.

---

## 🚀 Deep Dive: MQTT BBS — Why MQTT Beats File-Based Agent Communication

The original GenericAgent uses `file_io_bbs`: agents communicate by writing/reading files (`input.txt` / `output.txt`) with polling for completion detection. This works for single-machine setups but hits hard limits in distributed, real-time, or parallel scenarios.

**MQTT BBS** replaces this with a publish/subscribe message bus over MQTT protocol, enabling a fundamentally new class of capabilities.

### 8-Dimension Comparison

| Dimension | file_io_bbs (Original) | MQTT BBS (This Fork) |
|-----------|------------------------|-----------------------|
| **Communication Model** | Polling: read file → parse → write file | Event-driven: publish → subscribe |
| **Space** | Single machine | Cross-network (WAN/LAN) |
| **Task Dispatch** | Manual agent directory assignment | Capability declaration + auto-matching |
| **Latency** | Seconds (polling interval) | Milliseconds (push) |
| **Concurrency** | Serial (1 task per agent) | N:M arbitrary concurrency |
| **Liveness Detection** | None (process dies silently) | Will Message (LWT) auto-notification |
| **Message Reliability** | None (half-written file on crash) | QoS 0/1/2 three-level guarantee |
| **Third-Party Integration** | Must access filesystem directly | Any MQTT client can join |

### 8 Things file_io_bbs Can't Do

**1. 🔗 Cross-Machine Collaboration** — MQTT lets agents span machines:
```
Desktop AgentBoard ── Internet ── Laptop WorkerAgent (GPU)
                                    └── Phone Dashboard
```
Submit long tasks on desktop, workers run on GPU-equipped laptop, phone monitors progress — all through a network broker.

**2. 🎯 Capability Declaration & Smart Matching** — Worker agents broadcast their abilities on connect:
```json
// node/agent_alpha/status → "online" with capabilities
{ "capabilities": ["python", "data_analysis", "pandas"],
  "load": 0.3, "max_concurrency": 2 }
```
The board auto-matches the best agent for each task. No manual routing.

**3. 📡 Real-Time Streaming Output** — Workers push results line-by-line:
```
node/agent_alpha/stdout → "Processing page 1/100..."
node/agent_alpha/stdout → "Found pattern A, confidence 85%"
```
Dashboard shows live logs like `tail -f`. No more waiting 10 minutes with zero feedback.

**4. 🔀 Map-Reduce Parallel Dispatch** — Wildcard subscriptions collect results:
```python
board.subscribe("agent/board/task/+/output")
board.post_task("Analyze File A")  # → Worker-1
board.post_task("Analyze File B")  # → Worker-2
board.post_task("Analyze File C")  # → Worker-3
results = wait_all()  # parallel → aggregate
```
No need to manually manage N directories + N processes + merge logic.

**5. 📢 Broadcast / Multicast — Global Commands** — One message reaches all agents:
```python
board.publish("agent/board/global/signal", "[SUSPEND]")
```
All subscribed agents pause simultaneously. No need to edit every agent's input.txt.

**6. 🩸 Runtime Intervention — Scalpel-Level Control** — Inject commands mid-execution:
```python
board.publish(f"agent/board/task/{task_id}/signal", "[CANCEL]")
board.publish(f"agent/board/task/{task_id}/intervene", "Skip step 3, analyze attachment")
```
File BBS can't intervene mid-task; killing the process is the only option.

**7. 🔌 Third-Party System Integration** — Any MQTT client participates:
```
Node.js → listens agent/board/task/+/status ← Dashboard
Grafana → receives agent/node/+/metrics
IFTTT → done signal → Slack notification
```
No filesystem access, no format coupling. True language-agnostic ecosystem.

**8. 📦 Persistence & Offline Buffer** — Broker queues messages for offline agents:
- Agent disconnects → messages queued
- Agent reconnects → auto-replay backlog
- QoS 2 ensures exactly-once delivery

File BBS: crashed mid-write = corrupted output.txt. No rollback, no retry, no at-least-once semantics.

### Architecture Overview

```
┌──────────────────────────────────────────────────┐
│                  MQTT Broker                      │
│           (rmqtt / EMQX / broker.emqx.io)         │
│    agent/board/task/{id}/{input|output|signal}    │
│    agent/node/{id}/{status|capability|log}        │
└─────┬──────────────────────┬──────────────────────┘
      │                      │
┌─────▼──────┐      ┌──────▼───────┐      ┌───────────┐
│ AgentBoard  │      │  WorkerAgent  │      │ Dashboard  │
│ (Master)    │◄────►│  (Worker)    │◄────►│ (Monitor)  │
│ Posts tasks │      │  Claims &    │      │ Real-time  │
│ Collects    │      │  Executes    │      │ Subscribe  │
│ Results     │      │  Reports     │      │ Web UI     │
└─────────────┘      └──────────────┘      └───────────┘
```

### Quick Code Demo

```python
from mqtt_bbs import AgentBoard, WorkerAgent

# Master: post a task
board = AgentBoard("master")
task_id = board.post_task("scan_network", {"target": "10.0.0.0/24"})
result = board.wait_task(task_id)

# Worker: claim and execute
worker = WorkerAgent("worker_01", capabilities=["scan_network"])
worker.on_task(lambda msg: execute_scan(msg.input))
worker.start()
```

---

## 🛠️ Current Tool Ecosystem

### 🔹 rmqtt Web UI Dashboard

The built-in rmqtt broker provides a real-time web dashboard showing all connected agents, task status, and system health:

<p align="center">
  <img src="assets/images/mqtt_webui_dashboard.png" width="100%" alt="rmqtt Web UI Dashboard"/>
  <br/>
  <sub><b>rmqtt Web UI</b> — Live view of 5 connected agents, 16 completed tasks, broker status</sub>
</p>

### 🔹 Dashboard MQTT — Real-Time Agent Monitor

`dashboard_mqtt.py` is a Streamlit-based real-time monitoring panel that subscribes to MQTT topics and displays:

| Feature | Description |
|---------|-------------|
| 📊 Cluster Overview | Total, running, waiting, completed, stopped counts |
| 🃏 Agent Cards | Status 🟢🟠🔵⚪, online time, live logs per agent |
| 📋 Log Viewer | Tail stdout.log + stderr.log in real-time |
| ✏️ Remote Intervention | Send commands, inject working memory, send replies |
| 🛑 Stop Agent | Write `_stop` signal for graceful shutdown |
| 🔄 Auto-Refresh | Configurable interval (1-10s), default 3s |

```bash
python frontends/dashboard_mqtt.py
```

### 🔹 skill_learn_from_cases — Case-Driven Skill Learning CLI

Learn any skill from real-world cases and verify through hands-on execution. Zero external dependencies (except search API Key), with LLM-enhanced and rule-based dual paths.

```bash
# Minimal usage (rule-only mode)
python -m tools.skill_learn_from_cases_full docker_compose_production

# Preview: environment/domain/hooks
python -m tools.skill_learn_from_cases_full wiki_search --dry-run

# LLM-enhanced mode
set SKILL_LLM_ENABLE=1
set LLM_API_BASE=https://api.deepseek.com/v1
set LLM_MODEL=deepseek-chat
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**6-stage workflow**: Launch → Environment Detection (Neo4j/Docker/SQLite/Git) → Definition (LLM/Wikipedia) → Multi-source Search → Pattern Extraction (LLM/Rules) → Hands-on Build → Verification

> The tool has completed **5 meta-learning loops**, retrofitting itself (structured_logging → cli_ux_design → test_strategy → wiki_search → error_handling).

### 🔹 MariaDB Persistence Layer

Optional persistence for all Retain messages, agent session states, and offline message queues:

```sql
-- Retain message persistence (UPSERT semantics)
CREATE TABLE retained_messages (
    topic        VARCHAR(255) PRIMARY KEY,
    payload      JSON,        qos          INT DEFAULT 1,
    source_agent VARCHAR(64), created_at   DATETIME(3),
    updated_at   DATETIME(3)
);

-- Agent online status tracking
CREATE TABLE agent_sessions (
    agent_id     VARCHAR(64) PRIMARY KEY,
    status       ENUM('online','offline') DEFAULT 'offline',
    last_online  DATETIME(3), last_offline DATETIME(3)
);

-- Offline message queue (replay on reconnect)
CREATE TABLE session_queue (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    topic        VARCHAR(255), payload      JSON,
    seq          INT DEFAULT 0, target_agent VARCHAR(64),
    delivered    BOOLEAN DEFAULT FALSE, created_at   DATETIME(3)
);
```

Use `BBSClientWithPersistence` / `AgentBoardWithPersistence` / `WorkerAgentWithPersistence` to enable.

### 🔹 One-Click Startup

```bash
# Start everything (broker + dashboard + sample agents)
start_all.bat
```

This launches: rmqtt broker (port 1883) → MariaDB (optional) → MQTT dashboard (port 8100) → 5 sample worker agents.

---

## 🚀 Quick Start

### Method 1: Clone and Run

```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt
uv venv
uv pip install -e ".[ui]"
cp mykey_template.py mykey.py     # fill in your LLM API Key
python launch.pyw
```

### Method 2: With MQTT

```bash
# Start the MQTT broker (rmqtt recommended)
rmqtt start --daemon

# Start the dashboard
streamlit run frontends/dashboard_mqtt.py

# Launch agents with MQTT support
python frontends/launcher_mqtt.py
```

> Full setup guide at [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 💬 Bot Interface (Upstream)

GenericAgent supports Telegram, WeChat, QQ, Feishu/Lark, WeCom, and DingTalk frontends:

```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # WeChat
python frontends/fsapp.py        # Feishu / Lark
```

Chat commands: `/new` — fresh conversation; `/continue` — list snapshots; `/continue N` — restore snapshot N.

---

<a name="chinese"></a>

---

# 中文

## 🍴 本分支特色

| 维度 | 原版 GenericAgent | 本分支 GenericAgent_mqtt |
|------|-------------------|--------------------------|
| **Agent 通信** | `file_io_bbs` — 文件读写 + 轮询 | `mqtt_bbs` — MQTT 发布/订阅 + 推送 |
| **跨机器** | 单机（NFS 脆弱） | 网络 Broker 直连 |
| **实时性** | 秒级（轮询间隔） | 毫秒级（事件驱动推送） |
| **并行性** | 串行（每 Agent 单任务） | N:M 任意并发 |
| **存活检测** | PID 检查（僵尸进程风险） | CONNECT/LWT 协议级 |
| **持久化** | 无（删 temp/ 即丢失） | MariaDB 可选（Retain + 离线队列） |
| **CLI 工具** | 无统一入口 | `skill_learn_from_cases` + `dashboard_mqtt` |

所有上游能力（浏览器操控、自进化、9原子工具集、视觉识别、ADB、分层记忆）完整保留。

---

## 🌟 概述

GenericAgent 是一个极简（~3K 行核心代码）的自进化自主 Agent 框架。通过 **9 个原子工具 + ~100 行的 Agent Loop**，赋予任何 LLM 对本地计算机的系统级控制力——涵盖浏览器、终端、文件系统、键鼠输入、屏幕视觉和移动设备 (ADB)。

核心理念：**不要预加载技能，让技能自我进化。** 每完成一个任务，执行路径自动固化为可复用的技能。

本分支继承上述全部能力，并将 **Agent 间通信层**从基于文件的轮询升级为 MQTT 事件驱动消息总线。

---

## 🧬 自进化机制（上游同）

```
[新任务] → [自主探索]（安装依赖、编写脚本、调试验证）→
[执行路径固化为技能] → [写入记忆层] → [下次同类任务直接调用]
```

---

## 🚀 MQTT BBS 深度解析

### 8 个维度对比

| 维度 | file_io_bbs（原版） | MQTT BBS（本分支） |
|------|---------------------|--------------------|
| **通信模型** | 轮询：读文件→解析→写文件 | 事件驱动：发布/订阅 |
| **空间范围** | 单机 | 跨网络（广域网/局域网） |
| **任务分发** | 手动指定 agent 目录 | 能力声明 + 自动匹配 |
| **实时性** | 秒级（轮询间隔） | 毫秒级（推送） |
| **并行性** | 串行（每 agent 单任务） | N:M 任意并发 |
| **存活检测** | 无（进程死=静默） | Will Message 自动通知 |
| **消息可靠性** | 无（文件写一半崩溃即丢失） | QoS 0/1/2 三级保证 |
| **第三方集成** | 必须直接读写文件系统 | 任何 MQTT 客户端皆可接入 |

### file_io_bbs 做不到的 8 件事

**1. 🔗 跨机器协作** — 文件被单机锁死。MQTT 让 agent 跨越机器边界：
```
台式机 AgentBoard ──── 互联网 ──── 笔记本 WorkerAgent（有 GPU）
                                    └── 手机 Dashboard
```

**2. 🎯 能力声明与智能匹配** — Worker 上线时自动广播能力清单，AgentBoard 自动匹配最适合的 agent。

**3. 📡 实时流式输出** — Worker 逐行推送结果，Dashboard 像 `tail -f` 一样实时展示。无需干等 10 分钟。

**4. 🔀 Map-Reduce 并行分发** — 通配符订阅 `board/task/+/output` 一行代码收集所有并行任务结果。

**5. 📢 广播/组播** — 一条消息通知所有 agent 暂停/恢复，无需逐个编辑输入文件。

**6. 🩸 运行时干预** — 对正在运行的 agent 动态注入指令（跳过步骤、修改参数、强制停止）。

**7. 🔌 第三方集成** — 任何 MQTT 客户端（Node.js/Grafana/IFTTT）都能参与生态，不依赖 Python 或本代码库。

**8. 📦 持久化与离线缓冲** — Broker 自带消息持久化，离线 agent 上线后自动接收积压消息，QoS 2 确保恰好一次。

### 架构示意

```
┌──────────────────────────────────────────────────┐
│                  MQTT Broker                      │
│           (rmqtt / EMQX / broker.emqx.io)         │
│    agent/board/task/{id}/{input|output|signal}    │
│    agent/node/{id}/{status|capability|log}        │
└─────┬──────────────────────┬──────────────────────┘
      │                      │
┌─────▼──────┐      ┌──────▼───────┐      ┌───────────┐
│ AgentBoard  │      │  WorkerAgent  │      │ Dashboard  │
│ (主智能体)   │◄────►│  (工作智能体)  │◄────►│ (监控面板)  │
│ 发布任务     │      │  认领执行     │      │  实时订阅   │
│ 收集结果     │      │  报告进度     │      │  Web 界面   │
└─────────────┘      └──────────────┘      └───────────┘
```

### 快速代码示例

```python
from mqtt_bbs import AgentBoard, WorkerAgent

# 主智能体：发布任务
board = AgentBoard("master")
task_id = board.post_task("scan", {"target": "10.0.0.0/24"})
result = board.wait_task(task_id)

# 工作智能体：认领并执行
worker = WorkerAgent("worker_01", capabilities=["scan"])
worker.on_task(lambda msg: execute_scan(msg.input))
worker.start()
```

---

## 🛠️ 当前工具生态

### 🔹 rmqtt Web UI 仪表盘

内置的 rmqtt Broker 提供实时 Web 仪表盘，展示所有在线 Agent、任务状态和系统健康度：

<p align="center">
  <img src="assets/images/mqtt_webui_dashboard.png" width="100%" alt="rmqtt Web UI 仪表盘"/>
  <br/>
  <sub><b>rmqtt Web UI</b> — 实时显示 5 个已连接 Agent、16 个已完成任务</sub>
</p>

### 🔹 Dashboard MQTT — 实时 Agent 监控面板

基于 Streamlit 的 MQTT 实时监控面板，订阅 MQTT 主题并在本地缓存后统一展示：

| 功能 | 说明 |
|------|------|
| 📊 集群概览 | 总数、运行中、等待回复、已完成、已停止 |
| 🃏 Agent 卡片 | 每张卡片展示状态 🟢🟠🔵⚪、在线时间、实时日志 |
| 📋 日志查看 | stdout.log + stderr.log 尾部实时追踪 |
| ✏️ 远程干预 | 发送干预指令、注入工作记忆、发送回复 |
| 🛑 停止 Agent | 写入 `_stop` 信号安全终止 |
| 🔄 自动刷新 | 可调间隔（1-10s），每 3s 默认刷新 |

```bash
streamlit run frontends/dashboard_mqtt.py
```

### 🔹 skill_learn_from_cases — 案例驱动技能学习 CLI

从真实案例学习一项技能，并用实操验证能力习得。零外部依赖（除搜索引擎 API Key），支持 LLM 增强与纯规则降级双路径。

```bash
# 最简用法（纯规则模式）
python -m tools.skill_learn_from_cases_full docker_compose_production

# 启用 LLM 增强
set SKILL_LLM_ENABLE=1
set LLM_API_BASE=https://api.deepseek.com/v1
set LLM_API_KEY=sk-xxx
set LLM_MODEL=deepseek-chat
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**6 阶段工作流**: 启动 → 环境探测（Neo4j/Docker/SQLite/Git）→ 定义（LLM/Wikipedia）→ 多源搜索 → 模式提取（LLM/规则）→ 实操构建 → 验证评估

> 已完成 5 轮元学习闭环（structured_logging → cli_ux_design → test_strategy → wiki_search → error_handling）。

### 🔹 MariaDB 持久化层

可选的持久化支持，将所有 Retain 消息、Agent 会话状态持久化到 MariaDB。使用 `BBSClientWithPersistence` / `AgentBoardWithPersistence` 启用。

### 🔹 一键启动

```bash
# 启动全部：Broker + 仪表盘 + 示例 Agent
start_all.bat
```

启动：rmqtt broker (1883) → MariaDB（可选）→ MQTT 仪表盘 (8100) → 5 个示例 Worker Agent。

---

## ⚙️ 启动环境要求

### MQTT Broker（必需）

| Broker | 说明 |
|--------|------|
| **rmqtt** | ⭐ 推荐，轻量 Rust 实现，单文件部署；开发环境默认 `127.0.0.1:1883` |
| **EMQX** | 企业级 Broker，功能最全，支持 Dashboard |
| **broker.emqx.io** | 公共测试 Broker（无需注册，仅限开发测试） |

```bash
# rmqtt 快速启动（Windows）
rmqtt start --daemon
```

### MariaDB（可选，仅持久化模式需要）

兼容 MySQL 5.7+ / MariaDB 10.5+。默认配置见 [`mqtt_bbs/config.py`](mqtt_bbs/config.py)。

### 环境变量（[`.env`](.env)）

```ini
SKILL_LLM_ENABLE=1
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=60
```

---

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)

本项目是 [GenericAgent](https://github.com/lsdefine/GenericAgent) by [lsdefine](https://github.com/lsdefine) 的衍生 fork（MIT License）。  
LICENSE 同时保留了原作者版权（© 2025 lsdefine）和本分支版权（© 2026 benemorphy）。
