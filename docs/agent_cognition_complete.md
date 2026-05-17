# GenericAgent 认知架构完整说明

## 概述

本文档综合说明 GenericAgent 的 AI 如何**感知环境、使用工具、解决问题**，以及在**多智能体场景**下的协作机制。

---

## 第一部分：工具系统

### 1.1 工具定义位置

**`assets/tools_schema.json`** — 采用 OpenAI Function Calling 格式：

```json
{"type": "function", "function": {
  "name": "工具名",
  "description": "工具功能描述",
  "parameters": {"type": "object", "properties": {
    "参数1": {"type": "string", "description": "参数说明"}
  }}
}}
```

当前内置工具（9个）：

| 工具名 | 功能 |
|--------|------|
| `code_run` | 执行 Python/PowerShell 代码 |
| `file_read` | 读取文件内容 |
| `file_patch` | 精确替换文件内容 |
| `file_write` | 创建/覆盖/追加文件 |
| `web_scan` | 获取浏览器页面 HTML/Tab 列表 |
| `web_execute_js` | 在浏览器中执行 JavaScript |
| `update_working_checkpoint` | 更新短期工作记忆 |
| `ask_user` | 中断任务向用户提问 |
| `start_long_term_update` | 整理写入长期记忆 |

### 1.2 加载机制

`agentmain.py` 在启动时读取 JSON：

```python
TS = open('assets/tools_schema.json', 'r', encoding='utf-8').read()
TOOLS_SCHEMA = json.loads(TS if os.name == 'nt' else TS.replace('powershell', 'bash'))
```

- Windows 直接加载，Linux/Mac 自动替换 `powershell` → `bash`
- 支持后缀变体（如 `tools_schema_no_browser.json`）

### 1.3 调用流程

```
用户输入
  ↓
LLM 收到 tools=TOOLS_SCHEMA
  ↓
LLM 决定调用哪个工具 → 返回 function_call
  ↓
agent_runner_loop() 解析 → 映射到同名 Python 函数
  ↓
执行结果送回 LLM → 继续推理或输出回复
```

核心代码（`agent_loop.py`）：

```python
response_gen = client.chat(messages=messages, tools=tools_schema)
```

---

## 第二部分：添加与创建工具

### 2.1 添加正式 Function Calling 工具

需要两步：
1. 编辑 `assets/tools_schema.json` 添加定义（名字、描述、参数）
2. 在 `ga.py`（或对应模块）写同名 Python 函数
3. **下次新会话生效**

**不需要：** 修改 agent_loop.py、注册路由、重启服务（JSON 热加载）

### 2.2 运行时创建脚本级工具 ✅

通过 `code_run` + `file_write` 可在运行时创建脚本工具：

| 实际例子 | 做法 |
|---------|------|
| `imgbed.py` 图床服务（端口8053） | `file_write` 创建 → `code_run` 启动后台进程 |
| OCR 调试脚本 | 运行时写内联 Python 代码直接执行 |
| 调用 `memory/clipboard_ocr.py` | `from memory.clipboard_ocr import _ocr_request` |

**本质：`code_run` 是万能工具——能写能跑任何 Python 代码。**

### 2.3 不能做的 ❌

**不能动态注册 Function Calling 工具**——`tools=[]` 参数在对话开始时一次性发送，中途不能追加：

```json
// 这个列表对话开始时固定，中途不能插入新工具
tools = [
  {"type": "function", "function": {"name": "code_run", ...}},
  {"type": "function", "function": {"name": "file_read", ...}},
]
```

### 2.4 实际策略

| 场景 | 做法 |
|------|------|
| **反复使用**的能力 | 写成 `.py` 模块放 `memory/` 下 |
| **一次性**任务 | 直接用 `code_run` 写内联代码 |
| **持久化服务**（如图床） | `file_write` 创建 → `code_run` 启动后台进程 |

### 2.5 设计原则

- **描述即行为约束**：工具的 `description` 直接影响 LLM 使用决策，比代码本身还重要
- **参数驱动**：所有交互通过参数传递，不依赖全局状态
- **一次执行一个工具**：每轮 LLM 只输出一个工具调用（或纯回复）
- **失败回溯**：工具出错时 LLM 看到错误信息，自主决定重试或换方案

---

## 第三部分：环境感知

### 3.1 静态上下文（System Prompt）

每次对话注入：

| 信息来源 | 内容 |
|---------|------|
| **CONSTITUTION** | 9条行为铁律 |
| **RULES** | 操作规则：禁猜路径、交叉验证等 |
| **Global Memory Insight** | 内存索引 L0~L4 |
| **Tool Definitions** | 9个工具的签名+描述 |

### 3.2 动态上下文（运行时注入）

| 来源 | 内容 |
|------|------|
| `cwd` | 当前工作目录 |
| `Today` | 当前日期 |
| **Working Memory** | `update_working_checkpoint` 保存的短期上下文 |
| **会话历史** | 前几轮对话摘要 |

### 3.3 探测手段

```
直接感知:
  file_read  → 读文件内容
  web_scan   → 获知浏览器 Tab + 页面 HTML
  code_run   → 执行 Python 探测系统状态

间接感知:
  错误信息 → 从工具返回值理解环境限制
  用户反馈 → 提问/纠偏
```

---

## 第四部分：资源定位

### 4.1 记忆层级

```
L0 (META-SOP)  memory_management_sop.md        ← 写记忆前必读
L1 (Insight)   global_mem_insight.txt           ← 每次注入，极简索引
L2 (Facts)     global_mem.txt                   ← 持久化事实
L3 (SOP/Utils) memory/*.md / memory/*.py        ← 操作指南+工具函数
L4 (History)   memory/L4_raw_sessions/          ← 历史会话
```

**典型流程：** `收到任务 → 读L1 Insight → 发现SOP名 → 读L3 SOP → 按SOP执行`

### 4.2 搜索优先级

| 优先级 | 方法 | 适用场景 |
|--------|------|---------|
| 1 | 查 Global Memory Insight | 知已知彼 |
| 2 | 读 SOP / import Utils | 有现成方案 |
| 3 | `code_run` 探测 | 检查系统状态、文件存在性 |
| 4 | Metaso API 搜索 | 查技术文档/API |
| 5 | 浏览器 Bing 搜索 | 兜底 |

**搜索铁律：** `搜文件名严禁不用es(禁PS递归/禁dir遍历)`——优先搜索索引，不暴力遍历。

---

## 第五部分：问题解决循环

```
                   ┌──────────────┐
                   │  接收用户任务  │
                   └──────┬───────┘
                          ↓
                   ┌──────────────┐
                   │  查记忆/读SOP │ ← 先查再动手
                   └──────┬───────┘
                          ↓
                   ┌──────────────┐
                   │  探测环境状态  │ ← 不空想，用工具
                   └──────┬───────┘
                          ↓
                   ┌──────────────┐
            ┌──────│  执行一步操作  │──────┐
            │      └──────┬───────┘      │
            │             ↓              │
            │      ┌──────────────┐     │
            │      │   验证结果    │     │
            │      └──────┬───────┘     │
            │         ┌──┴──┐          │
            │         ↓     ↓          │
            │       成功   失败         │
            │         │     │          │
            │         │  ┌─┴──────┐    │
            │         │  │升级策略 │    │
            │         │  │1次:读错│    │
            │         │  │2次:探环│    │
            │         │  │3次:换方│    │
            │         │  │ 或问用户│   │
            │         │  └─┬──────┘    │
            │         │    │           │
            └─────────┴────┴───────────┘
                          ↓
                   ┌──────────────┐
                   │   闭环确认    │
                   │ (保存记忆/Git)│
                   └──────────────┘
```

### 5.1 核心原则

| 原则 | 说明 |
|------|------|
| **探测优先** | 不空想结果，先用工具获取真实信息 |
| **分步执行** | 限制失败半径，小步快跑 |
| **失败升级** | 1次→读错误 2次→探环境 3次→问用户，禁止无新信息的重复操作 |
| **交叉验证** | 不信摘要，数值进详情页核实 |
| **闭环** | 物理模拟后确认，Git完整闭环 |

---

## 第六部分：多智能体场景（Subagent）

### 6.1 架构

主 Agent 通过**文件系统**与 Subagent 通信，不共享上下文，无直接 IPC：

```
主 Agent
    │
    ├── 创建 task/{name}/ 目录
    ├── 写 input.txt（任务描述）
    ├── 启动: python agentmain.py --task {name} [--bg]
    │
    ▼
Subagent (独立进程)
    ├── 读 input.txt
    ├── 执行任务（完整 agent 能力）
    ├── 写 output.txt（[ROUND END] 标记轮次）
    │   可选: reply.txt（继续对话）
    │   可选: output1.txt, output2.txt（多轮输出）
    └── 退出（10分钟无 reply 自动退出）
```

### 6.2 通信协议

| 文件 | 方向 | 用途 |
|------|------|------|
| `input.txt` | 主→子 | 任务目标+约束 |
| `output.txt` | 子→主 | 结果输出 |
| `reply.txt` | 主→子 | 继续对话/追加指令 |
| `_stop` | 主→子 | 当轮结束后退出 |
| `_keyinfo` | 主→子 | 注入 working memory |
| `_intervene` | 主→子 | 追加干预指令 |

### 6.3 两种模式

**串行委派：** 适合有依赖关系的多步骤任务
```
主agent → subagent A → 等完成 → 读结果 → subagent B → ...
```

**Map-Reduce（并行）：** 适合独立同构子任务的批量处理
```
主agent:
  1. 准备 N 个独立输入文件
  2. 对每个输入启动一个 subagent（--bg 后台）
  3. 等所有完成 → 读取各输出 → 汇总结果
```

### 6.4 监控与干预

主 Agent 不应无脑 sleep 轮询：

```
while True:
    读 output.txt 检查进度
    if 需要纠偏 → 写 _intervene 文件
    if 完成 → break
    sleep(2)
```

### 6.5 工具与资源边界

| 能力 | 范围 |
|------|------|
| **可以直接用** | 9个 Function Calling 工具 |
| **可以创建** | 脚本级工具（`file_write` + `code_run`） |
| **不可以** | 动态注册新的 Function Calling 工具 |
| **可以直接 import** | `memory/` 下的 Python 模块（已在 PATH） |