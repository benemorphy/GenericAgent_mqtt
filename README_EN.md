<img align="right" src="assets/images/GGA.png" width="240" height="300"/>

---

<div align="center">
<img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/bar.jpg" width="880"/>
</div>

> 🍴 **Fork of [GenericAgent](https://github.com/lsdefine/GenericAgent)** — A fork of [lsdefine](https://github.com/lsdefine)'s minimalist self-evolving agent framework.
> **Core Change**: MQTT BBS — event-driven MQTT message bus replaces file-based agent communication, unlocking distributed, cross-machine, real-time collaboration.
> Upstream project under MIT License, this fork as well.

---

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

The core philosophy: **don't preload skills — evolve them.** Every time it solves a new task, the execution path is automatically crystallized into a reusable skill. Over time, the agent grows a unique skill tree from ~3K lines of seed code.

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
│  │ L1: Insight (global_mem_insight.txt) — minimal index           │ │
│  │ L2: Facts (global_mem.txt) — env facts/user preferences        │ │
│  │ L3: SOPs + Utils — 45+ SOPs, 15+ utility scripts               │ │
│  │ L4: Raw Sessions (L4_raw_sessions/) — historical conversations  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                     SKILLS LEARNING (Self-Evolution)                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  37 skills learned (debug, docker_compose, cypher, test, ...)  │ │
│  │  CLI: python -m tools.skill_learn_from_cases_full "<skill>"    │ │
│  │  5-phase: Search -> Extract Patterns -> Build Test -> Verify   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Files

| File | Role |
|------|------|
| `agentmain.py` | Entry point: GenericAgent class, tool schema loading, memory init |
| `agent_loop.py` | ~100-line agent loop: messages -> LLM -> tool calls -> step outcome |
| `ga.py` | GenericAgentHandler: 9 atomic tool implementations + memory access |
| `llmcore.py` | LLM session management (Claude/OpenAI/Ollama/DeepSeek) |
| `mykey.py` | API key configuration (template: `mykey_template.py`) |
| `TMWebDriver.py` | Browser automation with CDP bridge, session persistence |

---

## 🧬 Self-Evolution Mechanism

```
[New Task] -> [Explore] (install deps, write scripts, debug) ->
[Path Crystallized as Skill] -> [Written to Memory] -> [Direct Call Next Time]
```

Accelerated by the **skill_learn_from_cases** CLI tool — 37 skills learned and growing.

### Top 12 Skills by Score

| Skill | Score | Patterns |
|-------|:-----:|:--------:|
| debug (Service Program Debugging) | 100 | 12 |
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

> Full list: `ls skills_learning/`

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

**MQTT BBS solves 8 critical pain points vs File BBS:**
1. **Millisecond push** vs second-level polling — zero-latency task awareness
2. **N:M arbitrary concurrency** vs serial — 1 Master + N Workers process M tasks
3. **Cross-machine** — Workers on different hosts, containers, clouds
4. **Protocol-level liveness** — LWT auto-publishes offline, no zombies
5. **Capability-based routing** — Workers only claim matching tasks
6. **Runtime intervention** — Inject commands mid-execution, no process kill
7. **Third-party integration** — Any MQTT client participates (Node.js/Grafana/IFTTT)
8. **Persistence + offline buffering** — Broker queues for offline agents, auto-replay

### 🔹 rmqtt Web UI Dashboard
Built-in broker dashboard (port 8100): live view of all connected agents, task status, system health.

### 🔹 Dashboard MQTT — Real-Time Agent Monitor
Streamlit-based (port 8501):
| Feature | Description |
|---------|-------------|
| Cluster Overview | Total, running, waiting, completed, stopped |
| Agent Cards | Status, online time, live logs per agent |
| Log Viewer | Tail stdout.log + stderr.log in real-time |
| Remote Intervention | Send commands, inject working memory |
| Stop Agent | Write `_stop` signal for graceful shutdown |
| Auto-Refresh | Configurable 1-10s interval |

```bash
streamlit run frontends/dashboard_mqtt.py
```

### 🔹 skill_learn_from_cases — Case-Driven Skill Learning CLI
Learn any skill from real-world cases and verify through hands-on execution. Zero external dependencies (except search API Key), with LLM-enhanced and rule-based dual paths.

```bash
# Minimal (rule-only mode)
python -m tools.skill_learn_from_cases_full debug

# Preview mode
python -m tools.skill_learn_from_cases_full wiki_search --dry-run

# LLM-enhanced mode
set SKILL_LLM_ENABLE=1
set LLM_API_KEY=sk-xxx
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**5-phase workflow**: Environment Detection -> Skill Definition -> Multi-source Search -> Pattern Extraction -> Verification & Scoring

**37 skills learned** including: debug, docker_compose_production, cypher_programming_language, git_advanced, mqtt_testing, sql, sparql, neo4j_cypher, ontology, satellite_image_identification, and more.

### 🔹 gui_vision — Window Visual Understanding (OCR/VLM)
Local OCR (rapidocr-onnxruntime) + VLM fallback. In-memory window capture, DPI compensation, coordinate conversion, ljqCtrl click integration.

| Feature | Description |
|---------|-------------|
| Window Capture | Target window only (no fullscreen), auto DPI compensation |
| OCR Engine | rapidocr-onnxruntime local OCR, 200+ elements/10s |
| Coordinate Conversion | `element_to_screen_coords()` bbox -> physical screen coords |
| Click Integration | Recognize -> `ljqCtrl.Click()` instantly |
| Degradation Chain | Independent timeouts (offline15s/local30s), auto fallback |

```python
from gui_vision import understand_window, element_to_screen_coords
state = understand_window("Chrome")  # default: rapidocr
el = state['ui_elements'][0]
x, y = element_to_screen_coords(state, el)
```

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

```bash
python -c "from inspiration_board import Board; Board().add_idea('title','details',['tag'])"
python -c "from inspiration_board import Board; Board().list_all()"
```

### 🔹 MariaDB Persistence Layer
Optional persistence for Retain messages, agent sessions, offline queues. Enable via `BBSClientWithPersistence` / `AgentBoardWithPersistence` / `WorkerAgentWithPersistence`.

### 🔹 CapabilityRegistry — Agent Capability Market
Built-in agent capability registry in BoardService:
```
board = AgentBoard("master")
board.query_capabilities("scan")
board.post_task_routed("scan", {...}, target_capability="scan")
```

### 🔹 WhiteboardKV — Real-Time Collaborative Whiteboard
BBS-backed KV store with CAS optimistic locking. `get/set/cas/increment/watch/list_keys`.

### 🔹 BBScheduler — Cron-like Task Scheduler
```bash
python -m mqtt_bbs.scheduler
```
Supports daily/weekday/weekly/monthly/once/every_Nh schedule, optional `target_capability`.

### 🔹 File Chunked Upload
`file_init` -> `file_chunk` (sequential) -> `file_commit` (merge). Backward compatible.

### 🔹 Bot -> BBS Bridge
Feishu `/bbs post` + `/bbs subscribe`, QQ/others unified `/bbs post`. BBS posts auto-pushed to subscribed Feishu chats.

### 🔹 Feishu Bot Connection
```bash
python frontends/fsapp.py
```
WebSocket persistent connection, auto-reconnect (5s->120s backoff). Supports text/image/audio/file/card messages.

### 🔹 Bot Frontends
```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # WeChat
python frontends/fsapp.py        # Feishu / Lark
python frontends/qqapp.py        # QQ
python frontends/dingtalkapp.py  # DingTalk
python frontends/wecomapp.py     # WeCom
python frontends/tuiapp.py       # TUI
```

Chat commands: `/new` — fresh conversation; `/continue` — list snapshots; `/continue N` — restore snapshot N.

---

## 🚀 Quick Start

### Method 1: Clone & Run
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
Launches: rmqtt broker (1883) -> MariaDB (optional) -> rmqtt Web UI (8100) -> MQTT Dashboard (8501) -> 5 sample workers.

> Full setup guide: [GETTING_STARTED.md](GETTING_STARTED.md)

---

## ⚙️ Environment Requirements

### MQTT Broker (Required)
| Broker | Notes |
|--------|-------|
| **rmqtt** | Lightweight Rust, single binary; default `127.0.0.1:1883` |
| **EMQX** | Enterprise-grade, full Dashboard |
| **broker.emqx.io** | Public test broker (dev only) |

```bash
# rmqtt quick start (Windows)
rmqtt start --daemon
```

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
