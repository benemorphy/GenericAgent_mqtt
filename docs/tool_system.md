# GenericAgent 工具系统

## 概述

GenericAgent 的 AI 通过**函数调用（Function Calling）**机制与系统环境交互。工具定义采用 OpenAI 标准格式，集中管理在一个 JSON 文件中。

---

## 一、工具定义位置

**`assets/tools_schema.json`**

所有工具的**名字、描述、参数结构**都写在这个 JSON 文件里，采用 OpenAI Function Calling 格式：

```json
{"type": "function", "function": {
  "name": "工具名",
  "description": "工具功能描述",
  "parameters": {"type": "object", "properties": {
    "参数1": {"type": "string", "description": "参数说明"},
    "参数2": {"type": "integer", "description": "参数说明"}
  }}
}}
```

当前内置工具（共 9 个）：

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

---

## 二、加载机制

**`agentmain.py`** 在启动时读取 JSON 文件：

```python
TS = open('assets/tools_schema.json', 'r', encoding='utf-8').read()
TOOLS_SCHEMA = json.loads(TS if os.name == 'nt' else TS.replace('powershell', 'bash'))
```

- Windows 系统直接加载
- Linux/Mac 自动把 `powershell` 替换为 `bash`
- 支持后缀变体：`tools_schema_no_browser.json` 等

---

## 三、调用流程

```
用户输入
  ↓
LLM 收到 tools=TOOLS_SCHEMA
  ↓
LLM 决定调用哪个工具 → 返回 function_call
  ↓
agent_runner_loop() 解析调用
  ↓
映射到同名 Python 函数 → 执行
  ↓
结果送回 LLM → 继续推理或输出回复
```

**`agent_loop.py` 中核心调用：**

```python
def agent_runner_loop(client, system_prompt, user_input, handler, tools_schema, ...):
    messages = [...]
    response_gen = client.chat(messages=messages, tools=tools_schema)
    # LLM 返回 function_call → 执行 → 结果回传
```

---

## 四、如何添加新工具

不需要注册代码，只需两步：

1. **在 `assets/tools_schema.json` 中添加定义**
   - 工具名、描述、参数结构

2. **在 `ga.py`（或对应模块）中写同名 Python 函数**
   - 函数名与 JSON 中 `name` 一致
   - 接收 JSON 中定义的参数

**不需要：** 修改 agent_loop.py、注册路由、重启服务（JSON 热加载）

---

## 五、关键设计原则

- **描述即行为约束**：工具的 `description` 直接影响 LLM 的使用决策，比代码本身还重要
- **参数驱动**：所有交互通过参数传递，不依赖全局状态
- **一次执行一个工具**：每轮 LLM 只输出一个工具调用（或纯回复）
- **失败回溯**：工具出错时 LLM 会看到错误信息，自主决定重试或换方案---

## 六、根据任务需要"造工具"

### 能做的 ✅ — 脚本级工具

通过 `code_run` + `file_write`，可以在运行时创建脚本级别的工具：

| 实际例子 | 做法 |
|---------|------|
| `imgbed.py` 图床服务（端口8053） | `file_write` 创建脚本 → `code_run` 启动为后台服务 |
| OCR调试脚本 | 运行时临时写一段Python测试代码直接执行 |
| 封装 `memory/clipboard_ocr.py` | 已存在 → `from memory.clipboard_ocr import _ocr_request` 直接调用 |

**本质：`code_run` 是万能工具——能写能跑任何Python代码。** 对于需要重复使用的能力，写成 `.py` 模块放在 `memory/` 下；一次性任务直接用内联代码。

### 不能做的 ❌ — 动态注册 Function Calling 工具

无法在对话中途向 LLM 的 `tools=[]` 参数追加新条目：

```json
// 这个列表在对话开始时一次性发给 LLM，中途不能追加
tools = [
  {"type": "function", "function": {"name": "code_run", ...}},
  {"type": "function", "function": {"name": "file_read", ...}},
  // ← 不能中途插入新工具
]
```

如果想加一个像 `ocr_screenshot` 这样的专用 Function Calling 工具，需要：
1. 编辑 `assets/tools_schema.json` 添加定义
2. 在 `ga.py`（或对应模块）写同名的 Python 实现函数
3. **下次新会话才会生效**

### 实际策略

| 场景 | 做法 |
|------|------|
| **反复使用**的能力 | 写成 `.py` 模块放在 `memory/` 下 |
| **一次性**任务 | 直接用 `code_run` 写内联代码 |
| **持久化服务**（如图床） | `file_write` 创建 → `code_run` 启动后台进程 |