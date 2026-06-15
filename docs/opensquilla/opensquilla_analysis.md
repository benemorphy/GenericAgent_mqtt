# OpenSquilla v0.3.1 — 项目代码深度分析

> 分析日期: 2026-06-12  
> 分析范围: `src/opensquilla/` (源码 646 Python 文件, 7.3 MB)  
> 数据来源: CodeGraph 索引 (30685 节点, 75343 边, 1313 文件索引)

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [目录结构](#3-目录结构)
4. [模块架构总览](#4-模块架构总览)
5. [核心引擎 (Engine)](#5-核心引擎-engine)
6. [Gateway 网关层](#6-gateway-网关层)
7. [SquillaRouter 本地路由](#7-squillarouter-本地路由)
8. [Provider 提供者层](#8-provider-提供者层)
9. [Skills 技能系统](#9-skills-技能系统)
10. [Tools 工具系统](#10-tools-工具系统)
11. [Memory 记忆系统](#11-memory-记忆系统)
12. [Channels 消息通道](#12-channels-消息通道)
13. [Sandbox 沙箱与安全](#13-sandbox-沙箱与安全)
14. [CLI 命令行界面](#14-cli-命令行界面)
15. [Scheduler 调度系统](#15-scheduler-调度系统)
16. [MCP 协议支持](#16-mcp-协议支持)
17. [前端 Web UI](#17-前端-web-ui)
18. [配置模型](#18-配置模型)
19. [关键调用流](#19-关键调用流)
20. [测试概览](#20-测试概览)

---

## 1. 项目概述

OpenSquilla 是一个**令牌高效 (token-efficient) 的微内核 AI Agent 运行时**。核心理念是: **Same budget, more capability, better results.**

- **本地模型路由**: 内置 SquillaRouter，每轮自动选择性价比最高的模型
- **统一运行时**: CLI、Web UI、消息通道共享同一 turn loop
- **持久记忆**: 本地关键词 + 语义搜索，用户事实、笔记、任务痕迹持久化
- **多 Provider**: 支持 OpenRouter、OpenAI、Anthropic、Ollama 等 20+ LLM 提供商
- **MCP 原生**: 内置 MCP (Model Context Protocol) 客户端
- **多层沙箱**: 文件/Shell/网络工具运行在策略层和审批面之后

### 入口点

| 命令 | 入口 |
|------|------|
| `opensquilla` | `opensquilla.cli.main:app` |
| `gateway` | `opensquilla.cli.main:gateway_app` |

---

## 2. 技术栈

**核心语言**: Python 3.12+ (必需), JavaScript (Web UI 前端)

**关键依赖**:

| 类别 | 依赖 |
|------|------|
| Web 框架 | starlette, uvicorn, websockets |
| CLI | typer, rich, prompt-toolkit, questionary |
| 配置/验证 | pydantic, pydantic-settings, sqlmodel |
| HTTP 客户端 | httpx |
| 数据库 | aiosqlite, sqlite-vec (向量) |
| 调度 | apscheduler, croniter |
| 模板 | jinja2 |
| 日志 | structlog |
| 解析 | html2text, readability-lxml, beautifulsoup4, pdfplumber |
| Office | python-docx, python-pptx, openpyxl, pypdf |
| 缓存 | cachetools |
| 序列化 | pyyaml, tomli-w |
| 数据库迁移 | yoyo-migrations |

---

## 3. 目录结构

```
opensquilla/
+-- .codegraph/              # CodeGraph 代码索引 (65MB SQLite)
+-- src/opensquilla/         # 主源码 (646 .py 文件, 7.3 MB)
|   +-- __init__.py
|   +-- cli/                 # CLI (133 文件)
|   +-- engine/              # 核心引擎 (57 文件)
|   +-- gateway/             # Web 网关 (85 文件)
|   +-- skills/              # 技能系统 (95 文件)
|   +-- tools/               # 工具系统 (44 文件)
|   +-- memory/              # 记忆系统 (34 文件)
|   +-- channels/            # 消息通道 (24 文件)
|   +-- scheduler/           # 调度系统 (21 文件)
|   +-- squilla_router/      # 模型路由 (20 文件)
|   +-- provider/            # LLM 提供者层 (19 文件)
|   +-- onboarding/          # 首次配置引导 (18 文件)
|   +-- sandbox/             # 沙箱 (15 文件)
|   +-- session/             # 会话管理 (14 文件)
|   +-- plugins/             # 插件 (8 文件)
|   +-- observability/       # 可观测性 (8 文件)
|   +-- mcp/                 # MCP 客户端 (6 文件)
|   +-- search/              # 搜索 (6 文件)
|   +-- identity/            # Agent 身份 (6 文件)
|   +-- application/         # 审批/向导 (5 文件)
+-- tests/                   # 测试 (592 文件: 589 Python + 2 JS + 1 YAML)
+-- migrations/              # DB 迁移 (15 文件)
+-- docs/                    # 文档
+-- scripts/                 # 构建/工具脚本
+-- assets/                  # 静态资源
+-- service-units/           # 系统服务单元
+-- Formula/                 # Homebrew Formula
+-- pyproject.toml           # 项目配置
+-- Dockerfile               # Docker
+-- compose.yaml             # Docker Compose
```

### 文件统计

| 度量 | 值 |
|------|-----|
| 源码总大小 | 7,470 KB |
| 源码文件数 | 646 .py + 26 .js |
| 测试文件数 | 592 |
| 平均文件大小 | 11.2 KB |
| 最大文件 | 378 KB (config.py) |

### CodeGraph 节点统计

| 节点类型 | 数量 |
|----------|------|
| 函数 (function) | 12,926 |
| 导入 (import) | 7,328 |
| 方法 (method) | 4,724 |
| 变量 (variable) | 2,488 |
| 类 (class) | 1,897 |
| 文件 | 1,298 |
| 常量 | 24 |

### 边统计

| 边类型 | 数量 |
|--------|------|
| 调用 (calls) | 30,934 |
| 包含 (contains) | 29,387 |
| 实例化 (instantiates) | 9,750 |
| 导入 (imports) | 5,117 |
| 继承 (extends) | 155 |

---

## 4. 模块架构总览

```
                          +-----------------------------+
                          |        CLI 入口层           |
                          |  opensquilla / gateway      |
                          +-------------+---------------+
                                        |
                          +-------------v---------------+
                          |     Gateway 网关层          |
                          |  Starlette ASGI App         |
                          |  WebSocket / REST / RPC     |
                          |  Auth / RateLimit / Security |
                          +------+----------+----------+
                                 |          |
                +----------------v--+    +--v----------------+
                |    Engine 核心引擎  |    |  SquillaRouter    |
                |   Agent            |    |  本地路由引擎      |
                |   TurnRunner       |    |  OnnxBGE / V4     |
                |   Pipeline / Hook  |    |  CascadeRouter    |
                +--------+-----------+    +--------+----------+
                         |                         |
                +--------v-----------+    +--------v----------+
                | Channels 消息通道  |    |  Provider 层      |
                | Slack/Feishu/     |    |  OpenRouter/OpenAI |
                | Discord/QQ/       |    |  Anthropic/Ollama |
                | DingTalk/Telegram |    |  20+ Provider     |
                +--------+-----------+    +--------+----------+
                         |                         |
        +----------------+----+       +------------+------+
        |    Tools 工具系统    |       |  Memory 记忆系统   |
        |  Registry / Dispatch |      |  Vector/Session   |
        |  Policy / SSRF       |      |  Flush/Search     |
        +---------------------+       +-------------------+
        +---------------------+       +-------------------+
        |   Sandbox 沙箱      |       |  MCP 协议支持     |
        | Bubblewrap/Seatbelt |       |  SSE/Stdio Client |
        | Approval Gate       |       |  MCPToolDef       |
        +---------------------+       +-------------------+
        +---------------------+       +-------------------+
        |   Skills 技能系统    |       |  Scheduler 调度    |
        |  MetaOrchestrator   |       |  Heartbeat/Cron   |
        |  SOPCompiler        |       |  SessionReaper    |
        |  SkillInstaller     |       |  DeliveryChain    |
        +---------------------+       +-------------------+
```



## 5. 核心引擎 (Engine)

Engine 是 Agent 的运行时核心 (57 文件, `src/opensquilla/engine/`)。

### 关键类

| 类名 | 文件 | 职责 |
|------|------|------|
| `Agent` | agent.py | 显式状态机 + tool loop (500行内) |
| `AgentHook` | hooks/types.py | 钩子系统类型定义 |
| `NoopToolHook` | hooks/defaults.py | 默认空实现 |
| `FallbackPolicy` | fallback.py | 故障转移策略 (Provider 降级) |
| `ProgressWatchdog` | progress_watchdog.py | 进度看门狗 (防止无限循环) |
| `ContextBudgetGovernor` | agent.py | 上下文预算治理器 |
| `ToolResultStore` | tool_result_store.py | 工具结果持久存储 |
| `SessionSanitizeResult` | session_sanitize.py | 会话清理 |

### 调用链

```
Agent.run_turn()
  -> sanitize_session_messages()
  -> LLMProvider.chat()        # 通过 Provider 层
  -> check_response_for_cache_break()
  -> record_prompt_state()
  -> limit_turns() / repair_tool_pairing()
  -> ToolResultStore methods
  -> compact_context()          # 上下文压缩
```

### 热路径 (Top 调用)

| 排名 | 函数 | 调用次数 | 位置 |
|------|------|---------|------|
| 1 | `path()` | 580x | scheduler/heartbeat.py |
| 2 | `print()` | 322x | chat/turn_stream.py |
| 3 | `get()` | 267x | application/approval_queue.py |
| 4 | `get_dispatcher()` | 176x | rpc/registry.py |
| 5 | `parse_meta_plan()` | 172x | skills/compiler.py |

---

## 6. Gateway 网关层

Gateway 是 Web 入口 (85 文件, `src/opensquilla/gateway/`)，基于 **Starlette ASGI** 实现。

### 关键组件

| 类名 | 文件 | 职责 |
|------|------|------|
| `WsConnection` | websocket.py:L87 | WebSocket 连接管理 |
| `ConnectionRegistry` | websocket.py:L428 | 连接注册表 |
| `SubscriptionManager` | websocket.py:L455 | 订阅管理 |
| `UploadStore` | uploads.py:L85 | 上传文件存储 |
| `RpcRegistry` | rpc/registry.py | RPC 方法注册 |

### 特点
- WebSocket 双工通信
- RPC 调用框架
- 文件上传/附件管理
- 审批队列集成
- 速率限制 (rate_limit.py)

---

## 7. SquillaRouter 本地路由

SquillaRouter 是 **本地模型路由引擎** (20 文件, `src/opensquilla/squilla_router/`)。

### 核心架构

```
squilla_router/
  controller.py            # 后处理: Thinking/Prompt 策略
  v4_phase3.py             # V4 Phase3 bundle 适配器
  models/v4.2_phase3_inference/
    runtime_src/src/router/
      predictor.py         # SquillaRouter + CascadeRouter
      bge_onnx.py          # ONNX INT8 BGE 编码器
      v4_features.py       # 390维特征 + BGE×3段
      trajectory.py        # 轨迹分类 (8种走向)
      inference/
        core.py            # 推理核心
        features.py        # 特征捆绑
        heads.py           # 多头推理
        ensemble.py        # 概率融合
```

### 7层推理管线

```
Layer 1: BGE ONNX 编码 (1536维) + 390维手工特征
Layer 2: LightGBM 主模型 → 4-class probs
Layer 3: LightGBM 辅助模型 (校准)
Layer 4: ONNX MLP 校准
Layer 5: 概率融合 (加权平均)
Layer 6: 后处理 (margin upgrade, flag overrides)
Layer 7: Sticky tier (KV-cache 避免频繁切换)
```

### 路由决策输出

```python
FinalDecision:
  route_class: str        # "c0"-"c3"
  thinking_mode: str      # "T0"-"T3"
  prompt_policy: str      # "P0"-"P2"
  selected_model: str     # 映射后的模型名
  sticky_applied: bool    # 是否应用了粘滞策略
```

---

## 8. Provider 提供者层

Provider 层抽象了 20+ LLM 供应商 (19 文件, `src/opensquilla/provider/`)。

### 架构模式

```
LLMProvider (抽象基类)
  +-- OpenRouter
  +-- OpenAI-compatible
  +-- Anthropic
  +-- Ollama
  +-- ...
```

### 能力

| 特性 | 支持情况 |
|------|---------|
| Streaming | 全部支持 |
| Tool Use | 全部支持 |
| Thinking/Reasoning | Anthropic/Ollama |
| Vision/Image | OpenAI/Anthropic |
| 故障转移 | FallbackPolicy |
| 上下文预算 | ContextBudgetGovernor |

---

## 9. Skills 技能系统

Skills 系统 (95 文件, `src/opensquilla/skills/`) 是 OpenSquilla 的可扩展能力单元。

### 关键类

| 类名 | 文件 | 职责 |
|------|------|------|
| `Plan` | plan.py | 技能执行计划 |
| `SubQuestion` | plan.py | 子问题分解 |
| `Result` | search.py | 搜索结果 |
| `Provider` | generate_video.py | 视频生成提供者 |
| `VideoMerger` | generate_video.py | 视频合并 |

### 特点
- 内置技能创建器 (skill-creator)
- SOP 编译器 (SOPCompiler)
- Meta 编排器 (MetaOrchestrator)

---

## 10. Tools 工具系统

Tools 系统 (44 文件, `src/opensquilla/tools/`) 是 Agent 的执行能力层。

### 架构

```
tools/
  registry.py       # 工具注册表
  types.py          # 工具类型定义
  visibility.py     # 工具可见性控制
  policy_runtime.py # 策略运行时
  ssrf.py           # SSRF 防护
  rpc_payload.py    # RPC 载荷
  write_tracking.py # 写入追踪
  builtin/          # 内置工具
```

### 工具调用流
```
User Request → Agent.dispatch_tool() → ToolRegistry.get() → 
  PolicyRuntime.check() → ToolHook.before() → Tool.execute() → 
  ToolHook.after() → ToolResultStore.save()
```

---

## 11. Memory 记忆系统

Memory 系统 (34 文件, `src/opensquilla/memory/`) 实现持久化记忆。

### 记忆类型
- **用户事实** (User Facts)
- **笔记** (Notes) 
- **任务痕迹** (Task Artifacts)
- **语义搜索** (Vector/SQLite-vec)

### 关键模块
```
memory/
  recall.py           # 记忆召回
  store.py            # 记忆存储
  search.py           # 语义搜索
  redaction.py        # 记忆编辑
  dream_factory.py    # 梦境工厂
  migration/          # 迁移
```

---

## 12. Channels 消息通道

Channels 层 (24 文件, `src/opensquilla/channels/`) 连接外部消息平台。

### 支持平台

| Channel | 类名 | 文件 |
|---------|------|------|
| Slack | SlackChannel | slack.py |
| Feishu | FeishuChannel | feishu.py |
| Discord | DiscordChannel | discord.py:L111 |
| QQ | QQChannel | qq.py |
| DingTalk | DingTalkChannel | dingtalk.py |
| Telegram | TelegramChannel | telegram.py |

### 架构模式

```
BaseChannel
  +-- ChannelConfig (pydantic)
  +-- InboundTransport (接收)
  +-- OutboundTransport (发送)
  +-- StatusReactor (状态同步)
```

---

## 13. Sandbox 沙箱与安全

沙箱层 (15 文件, `src/opensquilla/sandbox/`) 提供多层安全隔离。

### 安全层级

| 层级 | 机制 | 范围 |
|------|------|------|
| L1 | Bubblewrap/Linux | 系统调用隔离 |
| L2 | Seatbelt/macOS | 沙箱配置 |
| L3 | Policy Runtime | 策略执行 |
| L4 | Approval Gate | 人工审批 |

---

## 14. CLI 命令行界面

CLI (133 文件, `src/opensquilla/cli/`) 是主要的用户交互入口。

### 入口命令

| 命令 | 入口函数 |
|------|---------|
| `opensquilla` | main.py:app |
| `gateway` | main.py:gateway_app |
| `agent` | main.py:agent (L723) |
| `cost` | cost_cmd.py:cost |
| `dist` | dist_cmd.py:dist |

### TUI 模块
```
cli/tui/
  terminal_chat_adapter.py
  terminal_renderer.py
  terminal_surface.py
  turn_bridge.py
  turn_stream_defaults.py
```

---

## 15. Scheduler 调度系统

Scheduler (21 文件, `src/opensquilla/scheduler/`) 管理定时和周期性任务。

### 关键类

| 类名 | 文件 | 职责 |
|------|------|------|
| `DeliveryReport` | delivery.py:L56 | 投递报告 |
| `DeliveryChain` | delivery.py:L64 | 投递链 |

### 能力
- Heartbeat 心跳检测
- Cron 定时任务
- SessionReaper 会话回收
- DeliveryChain 投递保证

---

## 16. MCP 协议支持

MCP (Model Context Protocol) 支持 (6 文件, `src/opensquilla/mcp/`)。

### 客户端类型

| 客户端 | 文件 | 通信方式 |
|--------|------|---------|
| `MCPClient` | client.py | 抽象基类 |
| `MCPSSEClient` | sse.py | SSE 服务端事件 |
| `MCPStdioClient` | stdio.py | 子进程 stdio |

### 配置

```python
MCPServerConfig(types.py):
  name: str
  command: str
  args: list[str]
  env: dict
```

---

## 17. 前端 Web UI

Gateway 自带 Web UI (少量 JS, 位于 gateway/views/)。

### 功能
- 实时聊天界面
- 文件上传
- 审批界面
- 设置面板

---

## 18. 配置模型

采用 **pydantic-settings** + **pyproject.toml** 分层配置。

### 配置层级

```
1. 默认值 (pyproject.toml)
2. 用户设置 (opensquilla.toml)
3. 环境变量
4. CLI 参数
```

---

## 19. 关键调用流

### 一次完整对话的调用链

```
User Input
  -> CLI/Gateway/Channel
  -> Agent.run_turn()
  -> SquillaRouter.decide()      # 路由选择模型
  -> LLMProvider.chat()          # 调用 LLM
  -> ToolHook.before()           # 工具钩子前
  -> ToolRegistry.dispatch()     # 工具分发
  -> ToolHook.after()            # 工具钩子后
  -> Memory.recall()             # 记忆召回
  -> Memory.store()              # 记忆存储
  -> Agent.turn_end()            # 回合结束
  -> RouterFeedback.update()     # 路由反馈
```

---

## 20. 测试概览

| 指标 | 值 |
|------|-----|
| 测试文件总数 | 592 |
| Python 测试 | 589 |
| JS 测试 | 2 |
| YAML 测试数据 | 1 |
| 数据库迁移 | 15 |

---

> 本文档由 CodeGraph 数据库分析自动生成  
> 分析工具: CodeGraph (30685 nodes, 75343 edges)  
> 项目版本: OpenSquilla v0.3.1  
> 协议: Apache 2.0
