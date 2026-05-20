<img align="right" src="assets/images/GGA.png" width="240" height="300"/>

---

<div align="center">
<img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/bar.jpg" width="880"/>
</div>

> 🍴 **Fork of [GenericAgent](https://github.com/lsdefine/GenericAgent)** — 衍生自 [lsdefine](https://github.com/lsdefine) 的极简自进化 Agent 框架。
> **核心改动**: MQTT BBS — 用事件驱动的 MQTT 消息总线替代原文件式 Agent 通信，解锁分布式、跨机器、实时协作能力。
> 上游项目 MIT License，本分支亦同。

---

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

核心理念：**不要预加载技能，让技能自我进化。** 每完成一个任务，执行路径自动固化为可复用的技能。随着时间推移，Agent 从 ~3K 行种子代码自主生长出一棵独特的技能树。

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

## 🧬 自进化机制

```
[新任务] → [自主探索]（安装依赖、编写脚本、调试验证）→
[执行路径固化为技能] → [写入记忆层] → [下次同类任务直接调用]
```

通过 **skill_learn_from_cases** CLI 工具加速——已学习 37 项技能。

### 12 项最新技能（评分排名）

| 技能 | 评分 | 模式数 |
|------|:----:|:------:|
| debug (服务程序代码调试) | 100 | 12 |
| test_strategy | 100 | 17 |
| error_handling_patterns | 100 | 16 |
| structured_logging | 100 | 12 |
| git_advanced | 100 | 14 |
| mqtt_testing | 100 | 12 |
| performance_optimization | 93 | 12 |
| docker_compose_production | 84 | 14 |
| cypher_programming_language | 83 | 13 |
| neo4j_cypher_graph_database_programming_language | 82 | 12 |
| sql | 80 | 14 |
| wiki_search | 78 | 15 |

> 完整 37 技能列表：`ls skills_learning/`

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

**MQTT BBS 解决了原版的 8 个关键痛点：**
1. **毫秒级推送** vs 秒级轮询 — Worker 零延迟感知
2. **N:M 任意并发** vs 串行 — 1 Master + N Worker 同时处理 M 个任务
3. **跨机器协作** — Worker 可在不同主机、容器、云上运行
4. **协议级存活检测** — LWT 自动发布 offline，无僵尸进程
5. **能力声明+自动匹配** — Worker 只认领能力匹配的任务
6. **运行时干预** — 任务执行中动态注入指令，无需杀进程
7. **三方系统集成** — 任何 MQTT 客户端可直接参与（Node.js/Grafana/IFTTT）
8. **持久化+离线缓冲** — Broker 为离线 Agent 排队消息，重连后自动回放

### 🔹 rmqtt Web UI 仪表盘
内置 Broker 仪表盘，实时展示所有在线 Agent、任务状态和系统健康度（端口 8100）。

### 🔹 Dashboard MQTT — 实时监控面板
基于 Streamlit（端口 8501）：
| 功能 | 说明 |
|------|------|
| 集群概览 | 总数、运行中、等待回复、已完成、已停止 |
| Agent 卡片 | 每张卡片展示状态、在线时间、实时日志 |
| 日志查看 | stdout.log + stderr.log 尾部实时追踪 |
| 远程干预 | 发送干预指令、注入工作记忆、发送回复 |
| 停止 Agent | 写入 `_stop` 信号安全终止 |
| 自动刷新 | 可调间隔（1-10s），每 3s 默认刷新 |

```bash
streamlit run frontends/dashboard_mqtt.py
```

### 🔹 skill_learn_from_cases — 案例驱动技能学习 CLI

从真实案例学习任何技能，并用实操验证能力习得。零外部依赖（除搜索引擎 API Key），支持 LLM 增强与纯规则降级双路径。

```bash
# 纯规则模式
python -m tools.skill_learn_from_cases_full debug

# 预览模式（仅查看环境和定义，不执行完整学习）
python -m tools.skill_learn_from_cases_full wiki_search --dry-run

# LLM 增强模式
set SKILL_LLM_ENABLE=1
set LLM_API_KEY=sk-xxx
python -m tools.skill_learn_from_cases_full cypher_programming_language
```

**5 阶段工作流**：环境探测 → 技能定义 → 多源案例搜索 → 模式提炼 → 验证评估

**已学习 37 项技能**，涵盖：服务程序代码调试(debug)、Docker Compose 生产部署、Cypher 查询语言、Git 高级操作、MQTT 协议测试、SQL、SPARQL、Neo4j 图数据库、本体论、卫星图像识别等。

### 🔹 gui_vision — 窗口视觉理解（OCR/VLM 双后端）

基于 rapidocr 的本地窗口 OCR 识别 + VLM fallback。无需截图上传，直接在内存中截取窗口区域分析。

| 功能 | 说明 |
|------|------|
| 窗口截图 | 仅截目标窗口（禁止全屏），自动 DPI 补偿 |
| OCR 识别 | rapidocr-onnxruntime 本地 OCR，200+ 元素/10s |
| 坐标转换 | `element_to_screen_coords()` bbox → 屏幕物理坐标 |
| 联动点击 | 识别后直接 `ljqCtrl.Click()` 点击 UI 元素 |
| 超时降级 | 独立超时配置（offline15s/local30s），失败自动降级 |

```python
from gui_vision import understand_window, element_to_screen_coords
state = understand_window("Chrome")  # 默认: rapidocr
el = state['ui_elements'][0]
x, y = element_to_screen_coords(state, el)
```

### 🔹 inspiration_board — 灵感沟通板

用户与 Agent 之间的灵感协作板，基于 MQTT BBS 实时同步。

| 功能 | 说明 |
|------|------|
| 添加灵感 | 对话中随时保存想法，自动 MQTT 通知 |
| Agent 思考 | 自主空闲时分析灵感并记录笔记 |
| 自动归档 | 活跃上限 20 条，超量自动持久化存档 |
| MQTT 通知 | 每次新增/更新发布到 `agent/board/inspiration/{id}/signal` |

```bash
python -c "from inspiration_board import Board; Board().add_idea('标题','详细内容',['标签'])"
python -c "from inspiration_board import Board; Board().list_all()"
```

### 🔹 MariaDB 持久化层

可选的持久化支持，将所有 Retain 消息、Agent 会话状态、离线消息队列持久化到 MariaDB。

使用 `BBSClientWithPersistence` / `AgentBoardWithPersistence` / `WorkerAgentWithPersistence` 启用。

### 🔹 CapabilityRegistry — 能力市场与动态分发

内置在 BoardService 中的 Agent 能力注册表：

```
board = AgentBoard("master")
board.query_capabilities("scan")
board.post_task_routed("scan", {...}, target_capability="scan")
```

### 🔹 WhiteboardKV — 实时协作白板

BBS 驱动的 KV 共享状态存储，CAS 乐观锁。`get/set/cas/increment/watch/list_keys`。

### 🔹 BBScheduler — 定时任务调度器

```bash
python -m mqtt_bbs.scheduler
```
支持 daily/weekday/weekly/monthly/once/every_Nh，可选 `target_capability`。

### 🔹 文件分片传输

`file_init` → `file_chunk`（分片）→ `file_commit`（合并），向后兼容。

### 🔹 Bot -> BBS 桥接

飞书 `/bbs post` + `/bbs subscribe`，QQ/其他统一命令。BBS 新帖自动推送到飞书群聊。

### 🔹 飞书 Bot 连接

```bash
python frontends/fsapp.py
```
WebSocket 长连接，自动重连（5s→120s 指数退避），支持文本/图片/音频/文件/卡片消息。

### 🔹 机器人前端

```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # 微信
python frontends/fsapp.py        # 飞书
python frontends/qqapp.py        # QQ
python frontends/dingtalkapp.py  # 钉钉
python frontends/wecomapp.py     # 企业微信
python frontends/tuiapp.py       # 图数据库界面
```

---

## 🚀 快速开始

### 方法一：克隆运行
```bash
git clone https://github.com/benemorphy/GenericAgent_mqtt.git
cd GenericAgent_mqtt
uv venv
uv pip install -e ".[ui]"
cp mykey_template.py mykey.py     # 填入你的 LLM API Key
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
启动：rmqtt broker (1883) → MariaDB（可选）→ rmqtt Web UI (8100) → MQTT Dashboard (8501) → 5 个示例 Worker Agent。

> 完整配置指南见 [GETTING_STARTED.md](GETTING_STARTED.md)

---

## ⚙️ 环境要求

### MQTT Broker（必需）
| Broker | 说明 |
|--------|------|
| **rmqtt** | 轻量 Rust 实现，单文件部署；开发环境默认 `127.0.0.1:1883` |
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
LICENSE 同时保留了原作者版权（c）2025 lsdefine 和本分支版权（c）2026 benemorphy。
