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
---

## 📊 同类工具对比

| 维度 | GenericAgent | OpenClaw | Claude Code |
|------|:---:|:---:|:---:|
| **代码量** | ~3K 行 | ~530,000 行 | 庞大 |
| **部署** | `pip install` + API Key | 多服务编排 | CLI + 订阅 |
| **浏览器操控** | 真实浏览器（会话保持） | 沙箱 / 无头浏览器 | 通过 MCP 插件 |
| **系统操控** | 鼠标/键盘、视觉、ADB | 多 Agent 委托 | 文件 + 终端 |
| **自进化** | 自主技能成长 | 插件生态 | 会话间无状态 |
| **开箱即用** | 几个核心文件 + 初始技能 | 数百个模块 | 丰富 CLI 工具集 |
---

## 📈 五维度评估

> 📂 完整数据集与结果：<https://github.com/JinyiHan99/GA-Technical-Report/tree/main>

| 维度 | 关键问题 | 基准测试 |
|------|---------|---------|
| **任务完成 & Token 效率** | GA 能否比主流 Agent 更低成本完成困难任务？ | SOP-Bench, Lifelong AgentBench, RealFin-Benchmark |
| **工具使用效率** | 极简工具集能否击败专用工具集？ | Tool Efficiency Benchmark（11 简单 + 5 长周期）|
| **记忆系统有效性** | 精炼层级记忆能否击败完整/嵌入式检索？ | SOP-Bench（危险品）, LoCoMo, 20 技能压力测试 |
| **自进化能力** | Agent 能否无干预地将经验固化为可复用 SOP？ | 9 轮 LangChain 学习, 8 任务跨任务 Web 基准 |
| **网页浏览能力** | 能否在开放网络中生存？ | WebCanvas, BrowseComp-ZH, 自定义任务（22）|

基线：**Claude Code**, **OpenAI CodeX**, **OpenClaw** 在 Claude Sonnet 4.6, Claude Opus 4.6, GPT-5.4, MiniMax M2.5 骨干上。
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

启动：rmqtt broker (1883) → MariaDB（可选）→ rmqtt Web UI (8100) → MQTT Dashboard (8501) → 5 个示例 Worker Agent。


### 🔹 gui_vision — 窗口视觉理解（OCR/VLM双后端）

基于 rapidocr 的本地窗口 OCR 识别 + VLM fallback。无需截图上传，直接在内存中截取窗口区域分析。

| 功能 | 说明 |
|------|------|
| 📸 窗口截图 | 仅截目标窗口（**禁止全屏**），自动 DPI 补偿 |
| 🔍 OCR 识别 | rapidocr-onnxruntime 本地 OCR，200+ 元素/10s |
| 📐 坐标转换 | `element_to_screen_coords()` bbox → 屏幕物理坐标 |
| 🖱️ 联动点击 | 识别后直接 `ljqCtrl.Click()` 点击 UI 元素 |
| ⏱️ 超时降级 | 独立超时配置（offline15s/local30s），失败自动降级 |

### 🔹 inspiration_board — 灵感沟通交流板

用户与 Agent 之间的灵感协作板，基于 MQTT BBS 实时同步。

| 功能 | 说明 |
|------|------|
| 💡 添加灵感 | 对话中随时保存想法，自动 MQTT 通知 |
| 🤔 Agent 思考 | 自主空闲时分析灵感并记录笔记 |
| 📦 自动归档 | 活跃上限 20 条，超量自动持久化存档 |
| 🔔 MQTT 通知 | 每次新增/更新发布到 `agent/board/inspiration/{id}/signal` |
| 📡 BBS 后端 | 默认使用 MQTT BBS 持久化，支持 `subscribe()` 实时订阅变更 |

### 🔹 CapabilityRegistry — 能力市场与动态分发

内置在 BoardService 中的 Agent 能力注册表。

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

`file_init` → `file_chunk`(分片) → `file_commit`(合并)，向后兼容。

### 🔹 Bot → BBS 桥接

飞书 `/bbs post` + `/bbs subscribe`，QQ/其他统一命令。BBS 新帖自动推送到飞书群聊。

### 🔹 Feishu Bot 连接 SOP

飞书 Bot 部署指南与运维 SOP，位于 `memory/feishu_connect_sop.md`：
- 配置 `mykey.py` → `fs_app_id` / `fs_app_secret`
- 启动：`python frontends/fsapp.py`
- WebSocket 长连接，自动重连（5s→120s 指数退避）
- 支持文本/图片/音频/文件/卡片消息

### 🔹 MQTT BBS 独立文档

`mqtt_bbs/README.md`（中）/ `mqtt_bbs/README_EN.md`（英）— 包含：
- 完整主题树（25+ 主题）与 Retain/QoS 策略
- AgentBoard / WorkerAgent / Dashboard 三角色使用指南
- 4 个完整代码示例（Master/Worker/Map-Reduce/运行时干预）
- 飞书 Bot 集成方案
- 能力声明与智能匹配


---
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

> 完整配置指南见 [GETTING_STARTED.md](GETTING_STARTED.md)
---

## 💬 机器人接口（上游同）

GenericAgent 支持 Telegram、微信、QQ、飞书、企业微信和钉钉前端：

```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # 微信
python frontends/fsapp.py        # 飞书
```

聊天命令：`/new` — 新建对话；`/continue` — 列出快照；`/continue N` — 恢复快照 N。
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