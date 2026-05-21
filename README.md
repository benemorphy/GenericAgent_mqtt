<img align="right" src="assets/images/GGA.png" width="240" height="300"/>

---

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
| **CLI Tools** | No unified entry | `skill_learn_from_cases` + `ga` CLI |

All original GenericAgent capabilities (browser automation, self-evolution, 9 atomic tools, vision, ADB, layered memory) remain fully intact.

---

## 🌟 Overview

**GenericAgent** is a minimal (~3K lines core), self-evolving autonomous agent framework. Through **9 atomic tools + a ~100-line Agent Loop**, it gives any LLM system-level control over a local computer — browser, terminal, filesystem, keyboard/mouse, vision, and mobile (ADB).

The core philosophy: **don't preload skills — evolve them.** Every time it solves a new task, the execution path is automatically crystallized into a reusable skill.

This fork inherits all upstream capabilities and upgrades the **inter-agent communication layer** from file-based polling to MQTT event-driven message bus.

---

## 🏗️ Architecture (5-Layer Stack)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTENDS (User Interfaces)                  │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌──────┐ ┌──────────────┐  │
│  │Dashboard │ │Tele- │ │WeChat│ │ QQ │ │Feishu│ │ Desktop Pet  │  │
│  │(Streamlit)│ │gram  │ │      │ │    │ │(Lark)│ │ (PyQt/PyWeb) │  │
│  └──────────┘ └──────┘ └──────┘ └────┘ └──────┘ └──────────────┘  │
│  ga CLI │ launcher_mqtt │ conductor.html │ stapp │ btw_cmd         │
├─────────────────────────────────────────────────────────────────────┤
│                      MQTT BBS LAYER                                  │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  AgentBoard  │ │  WorkerAgent  │ │Dashboard │ │  Capability  │  │
│  │  (Task Pub)  │ │  (Task Exec)  │ │(Monitor) │ │  Registry    │  │
│  ├──────────────┤ ├───────────────┤ ├──────────┤ ├──────────────┤  │
│  │ Persistence  │ │ WhiteboardKV  │ │Scheduler │ │ Plugin Mgmt  │  │
│  │  (MariaDB)   │ │  (CAS KV)     │ │(Cron)    │ │  (Hook Sys)  │  │
│  └──────────────┘ └───────────────┘ └──────────┘ └──────────────┘  │
│              ┌──────────────────────────────────────┐               │
│              │   MQTT Broker (rmqtt / EMQX)         │               │
│              │   agent/board/task/{id}/{...}        │               │
│              │   agent/node/{id}/{status|cap|log}   │               │
│              └──────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│                     CORE AGENT LOOP                                   │
│  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐  │
│  │agentmain │ │agent_loop  │ │  ga.py │ │llmcore.py│ │ mykey.py │  │
│  │ (Entry)  │ │(Loop:40t)  │ │Handler │ │LLM Sess. │ │ API Keys │  │
│  └──────────┘ └────────────┘ └────────┘ └──────────┘ └──────────┘  │
│    9 Atomic Tools: browser(TMWebDriver) | terminal | filesystem      │
│    keyboard/mouse(ljqCtrl) | vision(gui_vision) | ADB(adb_ui)        │
│    memory(R/W) | search(metaso) | code_execution                      │
├─────────────────────────────────────────────────────────────────────┤
│                     MEMORY SYSTEM (4-Layer Hierarchical)              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ L0: META-SOP (memory_management_sop)                           │ │
│  │ L1: Insight (global_mem_insight.txt) — 极简索引                │ │
│  │ L2: Facts (global_mem.txt) — 环境事实/用户偏好                 │ │
│  │ L3: SOPs + Utils — 45+ SOPs, 15+ utility scripts               │ │
│  │ L4: Raw Sessions (L4_raw_sessions/) — 历史会话原文             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                     SKILLS LEARNING (Self-Evolution)                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  37 skills learned (debug, docker_compose, cypher, test, ...)  │ │
│  │  CLI: python -m tools.skill_learn_from_cases_full "<skill>"    │ │
│  │  5-phase: Search → Extract Patterns → Build Test → Verify      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Files

| File | Role |
|------|------|
| `agentmain.py` | Entry point: GenericAgent class, tool schema loading, memory init |
| `agent_loop.py` | ~100-line agent loop: messages → LLM → tool calls → step outcome |
| `ga.py` | GenericAgentHandler: 9 atomic tool implementations + memory access |
| `llmcore.py` | LLM session management (Claude/OpenAI/Ollama/DeepSeek) |
| `mykey.py` | API key configuration (template: `mykey_template.py`) |
| `TMWebDriver.py` | Browser automation with CDP bridge, session persistence |

---

## 🧬 Self-Evolution Mechanism (Upstream)

```
[New Task] → [Explore] (install deps, write scripts, debug) →
[Path Crystallized as Skill] → [Written to Memory] → [Direct Call Next Time]
```

This is accelerated by the **skill_learn_from_cases** CLI tool — 37 skills learned and counting.

---

## 🛠️ Tool Ecosystem

### 🔹 MQTT BBS — Distributed Agent Collaboration
The fork's core innovation. See `mqtt_bbs/README_EN.md` for:
- Complete topic tree (25+ topics) with Retain/QoS strategy
- AgentBoard / WorkerAgent / Dashboard role guides
- 4 full code examples (Master/Worker/Map-Reduce/Runtime Intervention)
- Capability declaration and smart matching
- WhiteboardKV, BBScheduler, Plugin system, File chunked upload

```python
from mqtt_bbs import AgentBoard, WorkerAgent

# Master: publish a task
board = AgentBoard("master")
task_id = board.post_task("scan", {"target": "10.0.0.0/24"})
result = board.wait_task(task_id)

# Worker: claim and execute
worker = WorkerAgent("worker_01", capabilities=["scan"])
worker.on_task(lambda msg: execute_scan(msg.input))
worker.start()
```

### 🔹 rmqtt Web UI Dashboard
Built-in broker dashboard showing all connected agents, task status, system health — live at port 8100.

### 🔹 Dashboard MQTT — Real-Time Agent Monitor
Streamlit-based monitoring (port 8501): cluster overview, agent cards, live logs, remote intervention, stop signals.

### 🔹 skill_learn_from_cases — Case-Driven Skill Learning CLI
Learn any skill from real-world cases. Zero external dependencies (except search API Key). Dual-path: LLM-enhanced + rule-based.

```bash
# Minimal (rule-only)
python -m tools.skill_learn_from_cases_full debug

# LLM-enhanced
set SKILL_LLM_ENABLE=1
set LLM_API_KEY=sk-xxx
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**37 skills learned** including: debug, docker_compose_production, cypher_programming_language, git_advanced, mqtt_testing, sql, sparql, neo4j_cypher, ontology, satellite_image_identification, and more.

### 🔹 gui_vision — Window Visual Understanding
Local OCR (rapidocr-onnxruntime) + VLM fallback. In-memory window capture, DPI compensation, coordinate conversion, ljqCtrl click integration.

### 🔹 llm_providers — Provider Factory Pattern
Pluggable LLM provider registry (`tools/llm_providers/`). Register any provider (Claude, OpenAI, Gemini, local) via `ProviderRegistry.register(name, cls)`. Decouples session creation from provider-specific SSE parsing and auth.

```python
from tools.llm_providers import ProviderRegistry
sess = ProviderRegistry.create('claude-opus', cfg_dict)
```

### 🔹 turn_policy — Pluggable Turn Strategy Chain
Customizable turn strategy for Agent loop (`tools/turn_policy.py`). Configure tool call budgets, max retries, and step limits per session without modifying core loop logic.

### 🔹 inspiration_board — Agent-User Collaboration Board
MQTT-synced idea board. Add, archive, auto-notify on `agent/board/inspiration/{id}/signal`.

### 🔹 MariaDB Persistence
Optional persistence for Retain messages, agent sessions, offline queues. Enable via `BBSClientWithPersistence` / `AgentBoardWithPersistence`.

### 🔹 Feishu Bot Bridge
`/bbs post` + `/bbs subscribe` commands. BBS posts auto-pushed to Feishu group chats. Deploy: `python frontends/fsapp.py`.

### 🔹 Bot Frontends
```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # WeChat
python frontends/fsapp.py        # Feishu / Lark
python frontends/qqapp.py        # QQ
python frontends/dingtalkapp.py  # DingTalk
python frontends/wecomapp.py     # WeCom
```

---

## 🚀 Quick Start

### Method 1: Clone & Run
```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt
uv venv
uv pip install -e ".[ui]"
cp mykey_template.py mykey.py     # fill in LLM API Key
python launch.pyw
```

### Method 2: With MQTT
```bash
# Start broker (rmqtt recommended)
rmqtt start --daemon

# Launch monitoring dashboard
streamlit run frontends/dashboard_mqtt.py

# Start MQTT-enabled agent
python frontends/launcher_mqtt.py
```

### One-Click Start
```bash
start_all.bat
```
Launches: rmqtt broker (1883) → MariaDB (optional) → rmqtt Web UI (8100) → MQTT Dashboard (8501) → 5 sample workers.

> Full setup guide: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## ⚙️ Environment Requirements

### MQTT Broker (Required)
| Broker | Notes |
|--------|-------|
| **rmqtt** | Lightweight Rust, single binary; default `127.0.0.1:1883` |
| **EMQX** | Enterprise-grade, full Dashboard |
| **broker.emqx.io** | Public test broker (dev only) |

### MariaDB (Optional, for persistence)
Compatible with MySQL 5.7+ / MariaDB 10.5+. Config in [`mqtt_bbs/config.py`](mqtt_bbs/config.py).

### Environment Variables ([`.env`](.env))
```ini
SKILL_LLM_ENABLE=1
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=60
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

This project is a fork of [GenericAgent](https://github.com/lsdefine/GenericAgent) by [lsdefine](https://github.com/lsdefine) (MIT License).
Both original copyright (c) 2025 lsdefine and fork copyright (c) 2026 benemorphy are retained.

---

<a name="chinese"></a>

---

<div align="center">
<img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/bar.jpg" width="880"/>
</div>

## 🍴 本分支特色

| 维度 | 原版 GenericAgent | 本分支 GenericAgent_mqtt |
|------|-------------------|--------------------------|
| **Agent 通信** | `file_io_bbs` — 文件读写 + 轮询 | `mqtt_bbs` — MQTT 发布/订阅 + 推送 |
| **跨机器** | 单机（NFS 脆弱） | 网络 Broker 直连 |
| **实时性** | 秒级（轮询间隔） | 毫秒级（事件驱动推送） |
| **并行性** | 串行（每 Agent 单任务） | N:M 任意并发 |
| **存活检测** | PID 检查（僵尸进程风险） | CONNECT/LWT 协议级 |
| **持久化** | 无（删 temp/ 即丢失） | MariaDB 可选（Retain + 离线队列） |
| **CLI 工具** | 无统一入口 | `skill_learn_from_cases` + `ga` CLI |

所有上游能力（浏览器操控、自进化、9原子工具集、视觉识别、ADB、分层记忆）完整保留。

---

## 🌟 概述

GenericAgent 是一个极简（~3K 行核心代码）的自进化自主 Agent 框架。通过 **9 个原子工具 + ~100 行的 Agent Loop**，赋予任何 LLM 对本地计算机的系统级控制力——涵盖浏览器、终端、文件系统、键鼠输入、屏幕视觉和移动设备 (ADB)。

核心理念：**不要预加载技能，让技能自我进化。** 每完成一个任务，执行路径自动固化为可复用的技能。

本分支继承上述全部能力，并将 **Agent 间通信层**从基于文件的轮询升级为 MQTT 事件驱动消息总线。

---

## 🏗️ 系统架构（5层堆栈）

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端层 (用户界面)                            │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌──────┐ ┌──────────────┐  │
│  │仪表盘    │ │Tele- │ │微信   │ │ QQ │ │飞书   │ │ 桌面宠物     │  │
│  │(Streamlit)│ │gram  │ │      │ │    │ │(Lark)│ │ (PyQt/PyWeb) │  │
│  └──────────┘ └──────┘ └──────┘ └────┘ └──────┘ └──────────────┘  │
│  ga CLI │ launcher_mqtt │ conductor.html │ stapp │ btw_cmd         │
├─────────────────────────────────────────────────────────────────────┤
│                         MQTT BBS 通信层                               │
│  ┌──────────────┐ ┌───────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  AgentBoard  │ │  WorkerAgent  │ │ 监控面板  │ │  能力注册表   │  │
│  │  (任务发布)   │ │  (任务执行)   │ │(实时订阅) │ │  Capability  │  │
│  ├──────────────┤ ├───────────────┤ ├──────────┤ ├──────────────┤  │
│  │ MariaDB持久化│ │  WhiteboardKV │ │ 定时调度  │ │  插件管理系统  │  │
│  │   (可选)     │ │  (CAS KV)     │ │(Cron)    │ │  (Hook Sys)  │  │
│  └──────────────┘ └───────────────┘ └──────────┘ └──────────────┘  │
│              ┌──────────────────────────────────────┐               │
│              │   MQTT Broker (rmqtt / EMQX)         │               │
│              │   agent/board/task/{id}/{...}        │               │
│              │   agent/node/{id}/{status|cap|log}   │               │
│              └──────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────────────────┤
│                        核心 Agent 循环                                 │
│  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐  │
│  │agentmain │ │agent_loop  │ │  ga.py │ │llmcore.py│ │ mykey.py │  │
│  │ (入口)   │ │ (循环40轮) │ │处理器   │ │LLM会话   │ │ API 密钥 │  │
│  └──────────┘ └────────────┘ └────────┘ └──────────┘ └──────────┘  │
│    9个原子工具: 浏览器(TMWebDriver) | 终端 | 文件系统                  │
│    键鼠(ljqCtrl) | 视觉(gui_vision) | ADB(adb_ui)                    │
│    记忆(读写) | 搜索(metaso) | 代码执行                                │
├─────────────────────────────────────────────────────────────────────┤
│                        记忆系统 (4层层级)                              │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ L0: 元SOP (memory_management_sop)                             │ │
│  │ L1: 洞察索引 (global_mem_insight.txt) — 极简索引              │ │
│  │ L2: 事实 (global_mem.txt) — 环境事实/用户偏好                  │ │
│  │ L3: SOP + 工具 — 45+ SOP, 15+ 工具脚本                        │ │
│  │ L4: 原始会话 (L4_raw_sessions/) — 历史对话原文                 │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                        技能学习 (自我进化)                             │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  已学习 37 项技能 (debug, docker_compose, cypher, test, ...)   │ │
│  │  CLI: python -m tools.skill_learn_from_cases_full "<技能名>"   │ │
│  │  5阶段: 搜索 → 提炼模式 → 构建测试 → 验证 → 评分               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心文件说明

| 文件 | 职责 |
|------|------|
| `agentmain.py` | 入口：GenericAgent类，工具架构加载，记忆初始化 |
| `agent_loop.py` | ~100行Agent循环：消息 → LLM → 工具调用 → 步骤结果 |
| `ga.py` | GenericAgentHandler：9原子工具实现 + 记忆访问 |
| `llmcore.py` | LLM会话管理 (Claude/OpenAI/Ollama/DeepSeek) |
| `mykey.py` | API密钥配置 (模板: `mykey_template.py`) |
| `TMWebDriver.py` | 浏览器自动化，CDP桥接，会话保持 |

---

## 🧬 自进化机制（上游同）

```
[新任务] → [自主探索]（安装依赖、编写脚本、调试验证）→
[执行路径固化为技能] → [写入记忆层] → [下次同类任务直接调用]
```

通过 **skill_learn_from_cases** CLI 工具加速——已学习 37 项技能。

### 技能评分 Top 12

| 技能 | 评分 | 模式数 |
|------|:----:|:------:|
| debug (服务程序调试) | 100 | 12 |
| test_strategy | 100 | 17 |
| error_handling_patterns | 100 | 16 |
| structured_logging | 100 | 12 |
| git_advanced | 100 | 14 |
| mqtt_testing | 100 | 12 |
| performance_optimization | 93 | 12 |
| docker_compose_production | 84 | 14 |
| cypher_programming_language | 83 | 13 |
| neo4j_cypher_graph_database | 82 | 12 |
| sql | 80 | 14 |
| wiki_search | 78 | 15 |

> 完整列表：`ls skills_learning/`

---

## 🛠️ 工具生态

### 🔹 MQTT BBS — 分布式 Agent 协作
本分支核心创新。详见 `mqtt_bbs/README.md`：
- 完整主题树（25+ 主题）与 Retain/QoS 策略
- AgentBoard / WorkerAgent / 监控面板 三角色使用指南
- 4 个完整代码示例（Master/Worker/Map-Reduce/运行时干预）
- 能力声明与智能匹配
- WhiteboardKV, BBScheduler, 插件系统, 文件分片传输

```python
from mqtt_bbs import AgentBoard, WorkerAgent

# 主智能体：发布任务
board = AgentBoard("master")
task_id = board.post_task("scan", {"target": "10.0.0.0/24"})
result = board.wait_task(task_id)

# 工作智能体：认领执行
worker = WorkerAgent("worker_01", capabilities=["scan"])
worker.on_task(lambda msg: execute_scan(msg.input))
worker.start()
```

**MQTT BBS 相比 File BBS 解决的 8 个关键痛点：**
1. **毫秒推送** vs 秒级轮询 — 零延迟任务感知
2. **N:M 任意并发** vs 串行 — 1 个 Master + N 个 Worker 处理 M 个任务
3. **跨机器** — Worker 可在不同主机、容器、云上运行
4. **协议级存活检测** — LWT 自动发布离线事件，无僵尸进程
5. **基于能力的路由** — Worker 仅认领匹配的任务
6. **运行时干预** — 任务执行中注入指令，无需杀进程
7. **第三方集成** — 任何 MQTT 客户端均可参与 (Node.js/Grafana/IFTTT)
8. **持久化 + 离线缓冲** — Broker 为离线 Agent 排队，上线后自动重放

### 🔹 rmqtt Web UI 仪表盘
内置 Broker 仪表盘，实时展示所有在线 Agent、任务状态和系统健康度（端口 8100）。

### 🔹 Dashboard MQTT — 实时监控面板
基于 Streamlit（端口 8501）：
| 功能 | 说明 |
|------|------|
| 集群概览 | 总计、运行中、等待中、已完成、已停止 |
| Agent 卡片 | 状态、在线时长、实时日志 |
| 日志查看器 | 实时 tail stdout.log + stderr.log |
| 远程干预 | 发送指令、注入工作记忆 |
| 停止 Agent | 写入 `_stop` 信号优雅关闭 |
| 自动刷新 | 可配置 1-10s 间隔 |

```bash
streamlit run frontends/dashboard_mqtt.py
```

### 🔹 skill_learn_from_cases — 案例驱动技能学习 CLI
从真实案例学习技能。零外部依赖（除搜索引擎 API Key）。双路径：LLM 增强 + 纯规则降级。

```bash
# 纯规则模式
python -m tools.skill_learn_from_cases_full debug

# LLM 增强模式
set SKILL_LLM_ENABLE=1
set LLM_API_KEY=sk-xxx
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**已学习 37 项技能**，包括：debug、docker_compose_production、cypher_programming_language、git_advanced、mqtt_testing、sql、sparql、neo4j_cypher、ontology、satellite_image_identification 等。

### 🔹 gui_vision — 窗口视觉理解 (OCR/VLM)
本地 OCR (rapidocr-onnxruntime) + VLM 降级。内存窗口截取，DPI 补偿，坐标转换，ljqCtrl 点击联动。

| 特性 | 说明 |
|------|------|
| 窗口截取 | 仅目标窗口（非全屏），自动 DPI 补偿 |
| OCR 引擎 | rapidocr-onnxruntime 本地 OCR，200+ 元素/10s |
| 坐标转换 | `element_to_screen_coords()` bbox → 物理屏幕坐标 |
| 点击联动 | 识别 → `ljqCtrl.Click()` 即时点击 |
| 降级链路 | 独立超时（离线15s/本地30s），自动降级 |

```python
from gui_vision import understand_window, element_to_screen_coords
state = understand_window("Chrome")  # default: rapidocr
el = state['ui_elements'][0]
x, y = element_to_screen_coords(state, el)
```

### 🔹 inspiration_board — 灵感沟通板
基于 MQTT 实时同步的灵感协作板，支持添加、归档、自动通知。

### 🔹 MariaDB 持久化层
可选的 Retain 消息、Agent 会话、离线队列持久化。使用 `BBSClientWithPersistence` / `AgentBoardWithPersistence` 启用。

### 🔹 CapabilityRegistry — Agent 能力市场
BoardService 内置的能力注册表：
```
board = AgentBoard("master")
board.query_capabilities("scan")
board.post_task_routed("scan", {...}, target_capability="scan")
```

### 🔹 WhiteboardKV — 实时协作白板
基于 BBS 的 KV 存储，支持 CAS 乐观锁。`get/set/cas/increment/watch/list_keys`。

### 🔹 BBScheduler — 类 Cron 定时调度
```bash
python -m mqtt_bbs.scheduler
```
支持 daily/weekday/weekly/monthly/once/every_Nh 多种调度模式，可选 `target_capability` 参数。

### 🔹 文件分片上传
`file_init` -> `file_chunk` (顺序传输) -> `file_commit` (合并)。向后兼容。

### 🔹 Bot -> BBS 桥接
飞书 `/bbs post` + `/bbs subscribe`、QQ 等统一 `/bbs post` 命令。BBS 新帖自动推送到已订阅群聊。

### 🔹 飞书 Bot 连接
```bash
python frontends/fsapp.py
```
WebSocket 长连接，自动重连（5s->120s 退避）。支持文本/图片/音频/文件/卡片消息。

### 🔹 机器人前端
```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # 微信
python frontends/fsapp.py        # 飞书
python frontends/qqapp.py        # QQ
python frontends/dingtalkapp.py  # 钉钉
python frontends/wecomapp.py     # 企业微信
python frontends/tuiapp.py       # TUI
```

聊天命令：`/new` — 新建对话；`/continue` — 列出快照；`/continue N` — 恢复快照 N。

---

## 🚀 快速开始

### 方法一：克隆运行
```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt
uv venv
uv pip install -e ".[ui]"
cp mykey_template.py mykey.py     # 填入 LLM API Key
python launch.pyw
```

### 方法二：启用 MQTT
```bash
# 启动 MQTT Broker（推荐 rmqtt）
rmqtt start --daemon

# 启动实时监控面板
streamlit run frontends/dashboard_mqtt.py

# 启动支持 MQTT 的 Agent
python frontends/launcher_mqtt.py
```

### 一键启动
```bash
start_all.bat
```
启动顺序：rmqtt broker (1883) → MariaDB（可选）→ rmqtt Web UI (8100) → MQTT Dashboard (8501) → 5 个示例 Worker Agent。

> 完整配置指南见 [GETTING_STARTED.md](GETTING_STARTED.md)

---

## ⚙️ 环境要求

### MQTT Broker（必需）
| Broker | 说明 |
|--------|------|
| **rmqtt** | 轻量 Rust 实现，单文件部署；默认 `127.0.0.1:1883` |
| **EMQX** | 企业级 Broker，功能最全，支持 Dashboard |
| **broker.emqx.io** | 公共测试 Broker（仅限开发测试） |

### MariaDB（可选，仅持久化模式需要）
兼容 MySQL 5.7+ / MariaDB 10.5+。配置见 [`mqtt_bbs/config.py`](mqtt_bbs/config.py)。

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
LICENSE 同时保留了原作者版权（c）2025 lsdefine 和本分支版权（c）2026 benemorphy。
