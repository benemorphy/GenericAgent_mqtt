<div align="center">
<img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/bar.jpg" width="880"/>
</div>

> 🍴 **Fork of [GenericAgent](https://github.com/lsdefine/GenericAgent)** — 衍生自 [lsdefine](https://github.com/lsdefine) 的极简自进化 Agent 框架。  
> **主要改动**: MQTT BBS 模式替代原 file_io_bbs，实现分布式/跨机器 Agent 通信。  
> 上游项目采用 MIT License，本分支亦同。

---

<p align="center">
  <a href="#english">English</a> | <a href="#chinese">中文</a>
</p>

---

<a name="english"></a>

## 🍴 What's Different in This Fork

| Feature | Original (GenericAgent) | This Fork (GenericAgent_mqtt) |
|---------|------------------------|-------------------------------|
| **BBS Mode** | `file_io_bbs` (file-based blackboard) | `mqtt_bbs` (MQTT-based messaging) |
| **Communication** | Local file I/O between processes | MQTT broker for distributed/cross-machine |
| **Use Case** | Single machine | Multi-machine / IoT / cloud-edge scenarios |

All original capabilities (browser automation, self-evolution, tool chain, vision, ADB, etc.) remain fully intact.

---

## 🌟 Overview

**GenericAgent** is a minimal, self-evolving autonomous agent framework. Its core is just **~3K lines of code**. Through **9 atomic tools + a ~100-line Agent Loop**, it grants any LLM system-level control over a local computer — covering browser, terminal, filesystem, keyboard/mouse input, screen vision, and mobile devices (ADB).

Its design philosophy: **don't preload skills — evolve them.**

Every time GenericAgent solves a new task, it automatically crystallizes the execution path into an skill for direct reuse later. The longer you use it, the more skills accumulate — forming a skill tree that belongs entirely to you, grown from 3K lines of seed code.

> **🤖 Self-Bootstrap Proof** — Everything in this repository, from installing Git and running `git init` to every commit message, was completed autonomously by GenericAgent. The author never opened a terminal once.

## 📋 Core Features
- **Self-Evolving**: Automatically crystallizes each task into an skill. Capabilities grow with every use, forming your personal skill tree.
- **Minimal Architecture**: ~3K lines of core code. Agent Loop is ~100 lines. No complex dependencies, zero deployment overhead.
- **Strong Execution**: Injects into a real browser (preserving login sessions). 9 atomic tools take direct control of the system.
- **High Compatibility**: Supports Claude / Gemini / Kimi / MiniMax and other major models. Cross-platform.
- **Token Efficient**: <30K context window — a fraction of the 200K–1M other agents consume. Layered memory ensures the right knowledge is always in scope. Less noise, fewer hallucinations, higher success rate — at a fraction of the cost.


## 🧬 Self-Evolution Mechanism

This is what fundamentally distinguishes GenericAgent from every other agent framework.

```
[New Task] --> [Autonomous Exploration] (install deps, write scripts, debug & verify) -->
[Crystallize Execution Path into skill] --> [Write to Memory Layer] --> [Direct Recall on Next Similar Task]
```

| What you say | What the agent does the first time | Every time after |
|---|---|---|
| *"Read my WeChat messages"* | Install deps → reverse DB → write read script → save skill | **one-line invoke** |
| *"Monitor stocks and alert me"* | Install mootdx → build screener → config cron → save skill | **one-line invoke** |

After a few weeks, your agent instance will have a unique skill tree that no one else has, all grown from ~3K lines of seed code.

<!-- | *"Email this file via Gmail"* | Config OAuth → write send script → save skill | **one-line invoke** | -->

#### 🎯 Demo Showcase

| 🧋 Order Bubble Tea | 📈 Quantitative Stock Picking |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/order_tea.gif" width="100%" alt="Order Tea"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/selectstock.gif" width="100%" alt="Stock Selection"> |
| *"Order me a milk tea"* — Auto-navigate delivery app, select and checkout | *"Find GEM stocks with EXPMA golden cross, turnover > 5%"* — Quantitative screening |
| 🌐 Autonomous Web Exploration | 💰 Expense Tracking | 💬 Batch Messaging |
| <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/autonomous_explore.png" width="100%" alt="Web Exploration"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/alipay_expense.png" width="100%" alt="Alipay Expense"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/wechat_batch.png" width="100%" alt="WeChat Batch"> |
| Autonomous browsing with scheduled summaries | *"Find expenses > ¥2K in last 3 months"* via ADB-driven Alipay | Batch WeChat messaging via full client automation |


## 📅 What's New

- **2026-04-21:** 📄 [Technical Report on arXiv](https://arxiv.org/abs/2604.17091) — *GenericAgent: A Token-Efficient Self-Evolving LLM Agent via Contextual Information Density Maximization*
- **2026-04-11:** Introduced **L4 session archive memory** and cron scheduling
- **2026-03-23:** WeChat personal account as Bot frontend
- **2026-03-10:** [Released million-level Skill library](https://mp.weixin.qq.com/s/q2gQ7YvWoiAcwxzaiwpuiQ?scene=1&click_id=7)
- **2026-03-08:** [Dintal Claw powered by GenericAgent](https://mp.weixin.qq.com/s/eiEhwo-j6S-WpLxgBnNxBg)
- **2026-03-01:** [GenericAgent featured on Machine Heart](https://mp.weixin.qq.com/s/uVWpTTF5I1yzAENV_qm7yg)
- **2026-01-16:** GenericAgent V1.0 public release

---

## 🚀 Quick Start

### Method 1: One-click Install (Recommended)

One-click install prepares an isolated Python environment, Git, project files and desktop launcher without polluting the system.

**Windows PowerShell**

```powershell
powershell -ExecutionPolicy Bypass -c "irm http://fudankw.cn:9000/files/ga_install.ps1 | iex"
```

**Linux / macOS**

```bash
curl -fsSL http://fudankw.cn:9000/files/ga_install.sh | bash
```

After installation, double-click to start:

```text
frontends/GenericAgent.exe
```

### Method 2: Python Install (Developer)

```bash
git clone https://github.com/lsdefine/GenericAgent.git
cd GenericAgent
uv venv
uv pip install -e ".[ui]"        # core + UI dependencies
cp mykey_template.py mykey.py     # fill in your LLM API Key
python launch.pyw
```

> GenericAgent recommends bootstrapping via the agent itself rather than manually installing all dependencies upfront.

Full setup guide at [GETTING_STARTED.md](GETTING_STARTED.md).

📖 Beginner's Guide (图文版): [Feishu Doc](https://my.feishu.cn/wiki/CGrDw0T76iNFuskmwxdcWrpinPb)

📘 Complete Tutorial (Datawhale): [Hello GenericAgent](https://datawhalechina.github.io/hello-generic-agent/) · [GitHub](https://github.com/datawhalechina/hello-generic-agent)

---

## 🖥️ Frontend Options

### Desktop App

One-click install comes with a desktop launcher, double-click:

```text
frontends/GenericAgent.exe
```

### Terminal UI

Lightweight keyboard-driven interface based on [Textual](https://github.com/Textualize/textual). Supports multiple concurrent sessions and real-time streaming.

```bash
python frontends/tuiapp_v2.py
```

### Streamlit UI

```bash
python launch.pyw
```

---

## 💬 Bot Interface (IM)

GenericAgent also supports IM frontends such as Telegram, WeChat, QQ, Feishu / Lark, WeCom, and DingTalk.

Typical usage:

```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # WeChat
python frontends/qqapp.py        # QQ
python frontends/fsapp.py        # Feishu / Lark
python frontends/wecomapp.py     # WeCom
python frontends/dingtalkapp.py  # DingTalk
```

For detailed setup, ask GenericAgent itself.

Common chat commands:

- `/new` - start a fresh conversation and clear the current context
- `/continue` - list recoverable conversation snapshots
- `/continue N` - restore the `N`th recoverable conversation

## 📊 Comparison with Similar Tools

| Feature | GenericAgent | OpenClaw | Claude Code |
|---------|:---:|:---:|:---:|
| **Codebase** | ~3K lines | ~530,000 lines | Open-sourced (large) |
| **Deployment** | `pip install` + API Key | Multi-service orchestration | CLI + subscription |
| **Browser Control** | Real browser (session preserved) | Sandbox / headless browser | Via MCP plugin |
| **OS Control** | Mouse/kbd, vision, ADB | Multi-agent delegation | File + terminal |
| **Self-Evolution** | Autonomous skill growth | Plugin ecosystem | Stateless between sessions |
| **Out of the Box** | A few core files + starter skills | Hundreds of modules | Rich CLI toolset |


## 📈 Evaluation — Five Dimensions

> 📂 Full evaluation datasets and results: <https://github.com/JinyiHan99/GA-Technical-Report/tree/main>

| Dimension | Question | Benchmarks used |
|-----------|----------|-----------------|
| **1. Task Completion & Token Efficiency** | Can GA complete hard tasks more cheaply than leading agents? | SOP-Bench, Lifelong AgentBench, RealFin-Benchmark |
| **2. Tool-Use Efficiency** | Can a minimal atomic toolset solve what specialized toolsets solve, with less overhead? | Tool Efficiency Benchmark (11 simple + 5 long-horizon tasks) |
| **3. Memory System Effectiveness** | Does condensed hierarchical memory beat full/redundant memory and embedding-based retrievers? | SOP-Bench (dangerous goods), LoCoMo, 20-skill stress test |
| **4. Self-Evolution Capability** | Can the agent distill experience into reusable SOPs and code, without intervention? | 9-round LangChain longitudinal study, 8-task cross-task web benchmark |
| **5. Web Browsing Capability** | Does density-driven design survive the open web? | WebCanvas, BrowseComp-ZH, Custom Tasks (22) |

Baselines across these dimensions include **Claude Code**, **OpenAI CodeX**, and **OpenClaw**, evaluated under *Claude Sonnet 4.6*, *Claude Opus 4.6*, *GPT-5.4*, and *MiniMax M2.7* backbones.

<table>
  <tr>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/result_radar.png" width="100%" alt="Tool-use efficiency radar"/><br/>
      <sub><b>Tool-use efficiency radar.</b> GA dominates token, request, and tool-call axes while preserving quality across four task dimensions.</sub>
    </td>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/result_convergence.png" width="100%" alt="Cross-task self-evolution convergence"/><br/>
      <sub><b>Cross-task self-evolution.</b> Second- and third-run GA executions converge to a stable low-cost regime across eight web tasks, while OpenClaw shows no such convergence.</sub>
    </td>
  </tr>
</table>


## 🧠 How It Works

GenericAgent accomplishes complex tasks through **Layered Memory × Minimal Toolset × Autonomous Execution Loop**, continuously accumulating experience during execution.

1️⃣ **Layered Memory System**
> _Memory crystallizes throughout task execution, letting the agent build stable, efficient working patterns over time._

- **L0 — Meta Rules**: Core behavioral rules and system constraints of the agent
- **L1 — Insight Index**: Minimal memory index for fast routing and recall
- **L2 — Global Facts**: Stable knowledge accumulated over long-term operation
- **L3 — Task Skills / SOPs**: Reusable workflows for completing specific task types
- **L4 — Session Archive**: Archived task records distilled from finished sessions for long-horizon recall

2️⃣ **Autonomous Execution Loop**

> _Perceive environment state → Task reasoning → Execute tools → Write experience to memory → Loop_

The entire core loop is just **~100 lines of code** (`agent_loop.py`).

3️⃣ **Minimal Toolset**
> _GenericAgent provides only **9 atomic tools**, forming the foundational capabilities for interacting with the outside world._

| Tool | Function |
|------|----------|
| `code_run` | Execute arbitrary code |
| `file_read` | Read files |
| `file_write` | Write files |
| `file_patch` | Patch / modify files |
| `web_scan` | Perceive web content |
| `web_execute_js` | Control browser behavior |
| `ask_user` | Human-in-the-loop confirmation |

> Additionally, 2 **memory management tools** (`update_working_checkpoint`, `start_long_term_update`) allow the agent to persist context and accumulate experience across sessions.

4️⃣ **Capability Extension Mechanism**
> _Capable of dynamically creating new tools._

Via `code_run`, GenericAgent can dynamically install Python packages, write new scripts, call external APIs, or control hardware at runtime — crystallizing temporary abilities into permanent tools.

<div align="center">
  <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/workflow.jpg" alt="GenericAgent Workflow" width="400"/>
  <br><em>GenericAgent Workflow Diagram</em>
</div>


## 📄 License

MIT License — see [LICENSE](LICENSE)

This project is a fork of [GenericAgent](https://github.com/lsdefine/GenericAgent) by [lsdefine](https://github.com/lsdefine) (MIT License).  
The LICENSE file includes both the original copyright (© 2025 lsdefine) and the fork copyright (© 2026 benemorphy).

---

<a name="chinese"></a>

## 🍴 本分支差异

| 特性 | 原版 (GenericAgent) | 本分支 (GenericAgent_mqtt) |
|------|--------------------|---------------------------|
| **BBS 模式** | `file_io_bbs`（文件黑板） | `mqtt_bbs`（MQTT 消息通信） |
| **通信方式** | 本地进程间文件 I/O | 通过 MQTT Broker 跨机器通信 |
| **适用场景** | 单机使用 | 多机 / IoT / 云边协同 |

所有原版能力（浏览器操控、自我进化、工具链、视觉、ADB 等）完好保留。

---

## 🌟 项目简介

**GenericAgent** 是一个极简、可自我进化的自主 Agent 框架。核心仅 **~3K 行代码**，通过 **9 个原子工具 + ~100 行 Agent Loop**，赋予任意 LLM 对本地计算机的系统级控制能力，覆盖浏览器、终端、文件系统、键鼠输入、屏幕视觉及移动设备。

它的设计哲学是：**不预设技能，靠进化获得能力。**

每解决一个新任务，GenericAgent 就将执行路径自动固化为 Skill，供后续直接调用。使用时间越长，沉淀的技能越多，形成一棵完全属于你、从 3K 行种子代码生长出来的专属技能树。

> **🤖 自举实证** — 本仓库的一切，从安装 Git、`git init` 到每一条 commit message，均由 GenericAgent 自主完成。作者全程未打开过一次终端。

## 📋 核心特性
- **自我进化**: 每次任务自动沉淀 Skill，能力随使用持续增长，形成专属技能树
- **极简架构**: ~3K 行核心代码，Agent Loop 约百行，无复杂依赖，部署零负担
- **强执行力**: 注入真实浏览器（保留登录态），9 个原子工具直接接管系统
- **高兼容性**: 支持 Claude / Gemini / Kimi / MiniMax 等主流模型，跨平台运行
- **极致省 Token**: 上下文窗口不到 30K，是其他 Agent（200K–1M）的零头。分层记忆让关键信息始终在场——噪声更少，幻觉更低，成功率反而更高，而成本低一个数量级。

## 🧬 自我进化机制

这是 GenericAgent 区别于其他 Agent 框架的根本所在。

```
[遇到新任务]-->[自主摸索](安装依赖、编写脚本、调试验证)-->
[将执行路径固化为 Skill]-->[写入记忆层]-->[下次同类任务直接调用]
```

| 你说的一句话 | Agent 第一次做了什么 | 之后每次 |
|---|---|---|
| *"监控股票并提醒我"* | 安装 mootdx → 构建选股流程 → 配置定时任务 → 保存 Skill | **一句话启动** |
| *"用 Gmail 发这个文件"* | 配置 OAuth → 编写发送脚本 → 保存 Skill | **直接可用** |

用几周后，你的 Agent 实例将拥有一套任何人都没有的专属技能树，全部从 3K 行种子代码中生长而来。

#### 🎯 实例展示

| 🧋 外卖下单 | 📈 量化选股 |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/order_tea.gif" width="100%" alt="Order Tea"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/selectstock.gif" width="100%" alt="Stock Selection"> |
| *"Order me a milk tea"* — 自动导航外卖 App，选品并完成结账 | *"Find GEM stocks with EXPMA golden cross, turnover > 5%"* — 量化条件筛股 |
| 🌐 自主网页探索 | 💰 支出追踪 | 💬 批量消息 |
| <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/autonomous_explore.png" width="100%" alt="Web Exploration"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/alipay_expense.png" width="100%" alt="Alipay Expense"> | <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/demo/wechat_batch.png" width="100%" alt="WeChat Batch"> |
| 自主浏览并定时汇总网页信息 | *"查找近 3 个月超 ¥2K 的支出"* — 通过 ADB 驱动支付宝 | 批量发送微信消息，完整驱动微信客户端 |


## 📅 最新动态

- **2026-04-21:** 📄 [技术报告已发布至 arXiv](https://arxiv.org/abs/2604.17091) — *GenericAgent: A Token-Efficient Self-Evolving LLM Agent via Contextual Information Density Maximization*
- **2026-04-11:** 引入 **L4 会话归档记忆**，并接入 scheduler cron 调度
- **2026-03-23:** 支持个人微信接入作为 Bot 前端
- **2026-03-10:** [发布百万级 Skill 库](https://mp.weixin.qq.com/s/q2gQ7YvWoiAcwxzaiwpuiQ?scene=1&click_id=7)
- **2026-03-08:** [发布以 GenericAgent 为核心的"政务龙虾" Dintal Claw](https://mp.weixin.qq.com/s/eiEhwo-j6S-WpLxgBnNxBg)
- **2026-03-01:** [GenericAgent 被机器之心报道](https://mp.weixin.qq.com/s/uVWpTTF5I1yzAENV_qm7yg)
- **2026-01-16:** GenericAgent V1.0 公开版本发布

---

## 🚀 快速开始

### 方法一：一键安装（推荐）

一键安装会自动准备独立 Python 环境、Git、项目文件和桌面端，不污染系统环境。

**Windows PowerShell**

```powershell
powershell -ExecutionPolicy Bypass -c "irm http://fudankw.cn:9000/files/ga_install.ps1 | iex"
```

**Linux / macOS**

```bash
curl -fsSL http://fudankw.cn:9000/files/ga_install.sh | bash
```

安装完成后，双击启动：

```text
frontends/GenericAgent.exe
```

### 方法二：Python 安装（开发者）

```bash
git clone https://github.com/lsdefine/GenericAgent.git
cd GenericAgent
uv venv
uv pip install -e ".[ui]"        # 核心 + UI 依赖
cp mykey_template.py mykey.py     # 填入你的 LLM API Key
python launch.pyw
```

> GenericAgent 更推荐由 Agent 在使用中自举环境，而不是预先手动装完整依赖。

完整引导流程见 [GETTING_STARTED.md](GETTING_STARTED.md)。

📖 新手使用指南（图文版）：[飞书文档](https://my.feishu.cn/wiki/CGrDw0T76iNFuskmwxdcWrpinPb)

📘 完整入门教程（Datawhale 出品）：[Hello GenericAgent](https://datawhalechina.github.io/hello-generic-agent/) · [GitHub](https://github.com/datawhalechina/hello-generic-agent)

---

## 🖥️ 前端启动方式

### 桌面端

一键安装自带桌面端，双击：

```text
frontends/GenericAgent.exe
```

### 终端 UI

基于 [Textual](https://github.com/Textualize/textual) 的轻量键盘驱动界面。支持多会话并发、实时流式输出，有终端就能跑。

```bash
python frontends/tuiapp_v2.py
```

### Streamlit UI

```bash
python launch.pyw
```

---

## 💬 Bot 接口（IM）

GenericAgent 支持 Telegram、微信、QQ、飞书 / Lark、企业微信、钉钉等 IM 前端。

常用启动方式：

```bash
python frontends/tgapp.py        # Telegram
python frontends/wechatapp.py    # 微信
python frontends/qqapp.py        # QQ
python frontends/fsapp.py        # 飞书 / Lark
python frontends/wecomapp.py     # 企业微信
python frontends/dingtalkapp.py  # 钉钉
```

详细配置直接问 GenericAgent。

通用聊天命令：

- `/new` - 开启新对话并清空当前上下文
- `/continue` - 列出可恢复会话快照
- `/continue N` - 恢复第 `N` 个可恢复会话

## 📊 与同类产品对比

| 特性 | GenericAgent | OpenClaw | Claude Code |
|------|:---:|:---:|:---:|
| **代码量** | ~3K 行 | ~530,000 行 | 已开源（体量大） |
| **部署方式** | `pip install` + API Key | 多服务编排 | CLI + 订阅 |
| **浏览器控制** | 注入真实浏览器（保留登录态） | 沙箱 / 无头浏览器 | 通过 MCP 插件 |
| **OS 控制** | 键鼠、视觉、ADB | 多 Agent 委派 | 文件 + 终端 |
| **自我进化** | 自主生长 Skill 和工具 | 插件生态 | 会话间无状态 |
| **出厂配置** | 几个核心文件 + 少量初始 Skills | 数百模块 | 丰富 CLI 工具集 |


## 📈 评测 — 五大维度

> 📂 完整的评测数据集以及评测结果见：<https://github.com/JinyiHan99/GA-Technical-Report/tree/main>

| 维度 | 核心问题 | 使用的基准 |
|------|---------|-----------|
| **1. 任务完成度与 Token 效率** | GA 能否以更低成本完成高难度任务？ | SOP-Bench、Lifelong AgentBench、RealFin-Benchmark |
| **2. 工具使用效率** | 最小原子工具集能否以更低开销替代专用工具集？ | Tool Efficiency Benchmark |
| **3. 记忆系统有效性** | 精简分层记忆能否超越冗余记忆和基于 Embedding 的检索器？ | SOP-Bench、LoCoMo、20-skill 压力测试 |
| **4. 自我进化能力** | Agent 能否在无人干预下将经验提炼为可复用的 SOP 与代码？ | 9 轮 LangChain 纵向研究、8 任务跨任务 Web 基准 |
| **5. 网页浏览能力** | 信息密度驱动设计能否适应开放网页？ | WebCanvas、BrowseComp-ZH、自定义任务 |

以上维度的基线包括 **Claude Code**、**OpenAI CodeX** 和 **OpenClaw**，分别在 *Claude Sonnet 4.6*、*Claude Opus 4.6*、*GPT-5.4* 和 *MiniMax M2.7* 底座上进行评测。

<table>
  <tr>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/result_radar.png" width="100%" alt="工具使用效率雷达图"/><br/>
      <sub><b>工具使用效率雷达图。</b>GA 在 Token、请求数和工具调用轴上全面领先，同时在四个任务维度上保持质量。</sub>
    </td>
    <td align="center" width="50%">
      <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/result_convergence.png" width="100%" alt="跨任务自我进化收敛曲线"/><br/>
      <sub><b>跨任务自我进化。</b>GA 的第二轮和第三轮执行在 8 个 Web 任务上收敛至稳定的低成本区间。</sub>
    </td>
  </tr>
</table>


## 🧠 工作机制

GenericAgent 通过**分层记忆 × 最小工具集 × 自主执行循环**完成复杂任务，并在执行过程中持续积累经验。

1️⃣ **分层记忆系统**
> 记忆在任务执行过程中持续沉淀，使 Agent 逐步形成稳定且高效的工作方式

- **L0 — 元规则（Meta Rules）**：Agent 的基础行为规则和系统约束
- **L1 — 记忆索引（Insight Index）**：极简索引层，用于快速路由与召回
- **L2 — 全局事实（Global Facts）**：在长期运行过程中积累的稳定知识
- **L3 — 任务 Skills / SOPs**：完成特定任务类型的可复用流程
- **L4 — 会话归档（Session Archive）**：从已完成任务中提炼出的归档记录，用于长程召回

2️⃣ **自主执行循环**

> 感知环境状态  →  任务推理  →  调用工具执行  →  经验写入记忆  →  循环

整个核心循环仅 **约百行代码**（`agent_loop.py`）。

3️⃣ **最小工具集**
> GenericAgent 仅提供 **9 个原子工具**，构成与外部世界交互的基础能力

| 工具 | 功能 |
|------|------|
| `code_run` | 执行任意代码 |
| `file_read` | 读取文件 |
| `file_write` | 写入文件 |
| `file_patch` | 修改文件 |
| `web_scan` | 感知网页内容 |
| `web_execute_js` | 控制浏览器行为 |
| `ask_user` | 人机协作确认 |

> 此外，还有 2 个**记忆管理工具**（`update_working_checkpoint`、`start_long_term_update`），使 Agent 能够跨会话积累经验、维持持久上下文。

4️⃣ **能力扩展机制**
> 具备动态创建新的工具能力

通过 `code_run`，GenericAgent 可在运行时动态安装 Python 包、编写新脚本、调用外部 API 或控制硬件，将临时能力固化为永久工具。

<div align="center">
  <img src="https://raw.githubusercontent.com/lsdefine/GenericAgent/main/assets/images/workflow.jpg" alt="GenericAgent 工作流程" width="400"/>
  <br><em>GenericAgent 工作流程图</em>
</div>


---

## 🚀 本分支新增特性

### 1. MQTT Agent BBS — 智能体协作消息总线

用 **MQTT Pub/Sub** 模型替代原 `file_io_bbs` 文件协议，实现跨机器、分布式的智能体间任务分发与结果收集。

| 文件协议（原版） | MQTT BBS（本分支） |
|:---|:---|
| `temp/{task}/input.txt` | `board/task/{id}/input` [Retain] |
| `temp/{task}/output.txt` | `board/task/{id}/output` [Retain] |
| `[ROUND END]` 轮询检测 | `board/task/{id}/signal` 推送 |
| PID 标识进程 | `node/{agent}/status` LWT 自动离线 |
| sleep 轮询等待 | subscribe 实时推送 |
| 需共享存储 (NFS) 跨机器 | 网络 MQTT Broker 任意跨域 |

**核心模块** — `mqtt_bbs/` 目录：
- [`client.py`](mqtt_bbs/client.py) — 底层 MQTT 客户端，封装 paho-mqtt，对标文件读写语义
- [`bbs.py`](mqtt_bbs/bbs.py) — 业务层：`AgentBoard`（主智能体发布任务）+ `WorkerAgent`（工作智能体认领执行）
- [`persistence.py`](mqtt_bbs/persistence.py) — MariaDB 持久化层，支持 Retain 消息持久化 + 离线消息队列重放
- [`config.py`](mqtt_bbs/config.py) — 默认配置（Broker 地址、QoS 策略、DB 配置）

**快速使用**：
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

### 2. `ga` CLI 命令行工具

全局命令入口，通过 `ga <命令>` 快速启动所有前端和服务。

```bash
# 安装后即可使用
ga gui          # 启动桌面 GUI (PyQt5)
ga web          # 启动 Web 增强版
ga tui          # 启动终端 TUI (Textual)
ga cli          # 启动 CLI 对话 (agentmain)
ga hub          # 启动 Hub 管理器
ga launch       # 启动 webview 桌面壳
ga list         # 列出所有可用命令
ga status       # 检查运行状态
ga update       # git pull + pip install 更新
```

实现位于 [`ga_cli/cli.py`](ga_cli/cli.py)，支持 Windows GBK 终端兼容、参数透传等。

---

### 3. Subagent Dashboard — 集群监控面板

基于 **Streamlit** 的实时监控面板，用于查看、控制和干预所有后台运行的 subagent。

- **文件位置**: `frontends/subagent_dashboard.py`（原项目）  
- **MQTT 版**: `frontends/dashboard_mqtt.py`（本分支新增，订阅 MQTT 主题实时展示）

**启动方式**：
```bash
streamlit run frontends/subagent_dashboard.py
```

**核心功能**：
| 功能 | 说明 |
|:---|:---|
| 📊 集群概览 | 总数、运行中、等待回复、已完成、已停止 |
| 🃏 Agent 卡片 | 每张卡片展示状态 🟢🟠🔵⚪、PID、运行时长、实时日志 |
| 📋 日志查看 | stdout.log + stderr.log 尾部实时追踪 |
| ✏️ 远程干预 | 发送干预指令、注入工作记忆、发送回复 |
| 🛑 停止 Agent | 写入 `_stop` 信号安全终止 |
| 🔄 自动刷新 | 可调间隔（1-10s），每 3s 默认刷新 |

**MQTT Dashboard 数据源** (`dashboard_mqtt.py`)：
- 订阅 `board/task/+/input|output|status|stdout|stderr` 
- 订阅 `node/+/status|capability`
- 本地缓存 + 统一接口 `get_tasks()` / `get_agents()`

---

### 4. MariaDB 持久化层

可选的持久化支持，将所有 Retain 消息、Agent 会话状态持久化到 MariaDB。

**使用的表结构**：

```sql
-- Retain 消息持久化（UPSERT 语义）
CREATE TABLE retained_messages (
    topic        VARCHAR(255) PRIMARY KEY,
    payload      JSON,
    qos          INT DEFAULT 1,
    source_agent VARCHAR(64),
    created_at   DATETIME(3),
    updated_at   DATETIME(3)
);

-- Agent 在线状态追踪
CREATE TABLE agent_sessions (
    agent_id     VARCHAR(64) PRIMARY KEY,
    status       ENUM('online','offline') DEFAULT 'offline',
    last_online  DATETIME(3),
    last_offline DATETIME(3),
    updated_at   DATETIME(3)
);

-- 离线消息队列（断线重连后重放）
CREATE TABLE session_queue (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    topic        VARCHAR(255),
    payload      JSON,
    seq          INT DEFAULT 0,
    target_agent VARCHAR(64),
    delivered    BOOLEAN DEFAULT FALSE,
    created_at   DATETIME(3) DEFAULT NOW(3),
    delivered_at DATETIME(3)
);
```

使用方法：改用 `BBSClientWithPersistence` / `AgentBoardWithPersistence` / `WorkerAgentWithPersistence` 替代无持久化版本。

---

## ⚙️ 启动环境要求

### MQTT Broker（必需）

需要一个 MQTT 5.0/3.1.1 Broker，推荐选项：

| Broker | 说明 |
|:---|:---|
| **rmqtt** | 推荐，轻量 Rust 实现，单文件部署；本项目开发环境使用 `127.0.0.1:1883` |
| **EMQX** | 功能最全的企业级 Broker，支持 Dashboard 管理 |
| **broker.emqx.io** | 公共测试 Broker（无需注册，仅限开发测试） |

**rmqtt 快速启动（Windows）**：
```bash
# 下载 rmqtt 单文件版，直接运行
rmqtt start --daemon
# 默认监听 1883 (MQTT) + 11883 (内部管理)
```

### MariaDB（可选，仅持久化模式需要）

兼容 MySQL 5.7+ / MariaDB 10.5+。

**默认连接配置**（定义在 [`mqtt_bbs/config.py`](mqtt_bbs/config.py)）：
```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "mariadb",
    "database": "mqtt_bbs",
    "charset": "utf8mb4",
}
```

**MariaDB 初始化**：
```sql
CREATE DATABASE IF NOT EXISTS mqtt_bbs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 表结构见上方「MariaDB 持久化层」章节
```

### 环境变量配置（[`.env`](.env)）

```ini
SKILL_LLM_ENABLE=1
LLM_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=60
```

### 与本分支的差异要点

| 维度 | 原版 GenericAgent | 本分支 GenericAgent_mqtt |
|:---|:---|:---|
| 智能体通信 | file_io_bbs（本地文件读写 + 轮询） | **mqtt_bbs**（MQTT Pub/Sub + 推送） |
| 跨机器 | 需 NFS 共享存储 | MQTT Broker 网络直连 |
| 在线检测 | PID 检查（可能僵尸） | CONNECT/LWT 协议级 |
| 持久化 | 无（删 temp/ 即丢失） | MariaDB 可选持久化 |
| 监控面板 | subagent_dashboard（文件扫描） | + **dashboard_mqtt**（MQTT 实时订阅） |
| CLI 工具 | 无统一入口 | `ga` 命令分发器 |

---

## 📄 许可

MIT License — 详见 [LICENSE](LICENSE)

本项目是 [GenericAgent](https://github.com/lsdefine/GenericAgent) by [lsdefine](https://github.com/lsdefine) 的衍生 fork（MIT License）。  
LICENSE 同时保留了原作者版权（© 2025 lsdefine）和本分支版权（© 2026 benemorphy）。
