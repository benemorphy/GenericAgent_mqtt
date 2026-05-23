# 代码解耦分析报告：非核心功能 Hook/工具化

审查日期：2026-05-20
审查范围：ga.py, agent_loop.py, agentmain.py, llmcore.py, simphtml.py, mqtt_bbs/plugins/

## 一、整体架构扫描

| 文件 | 行数 | 职责 | 核心/非核心 |
|------|------|------|------------|
| ga.py | 589 | 工具实现 + 全局函数 + 生命周期管理 | 核心+非核心混合 |
| agentmain.py | 297 | 主入口 + MQTT Agent + LLM会话管理 | 核心 |
| agent_loop.py | 125 | 运行循环 + 工具调度 + prompt组装 | 核心 |
| llmcore.py | 1032 | LLM客户端 + 流式解析 | 核心 |
| simphtml.py | 873 | HTML简化 + JS执行 + 屏幕捕获 | 非核心(浏览器) |
| mqtt_bbs/ | ~7模块 | MQTT通信层 + BBS协议 | 独立子系统 |
| plugins/ | 2插件 | auto_log, langfuse_tracing | 已有hook范例 |

## 二、现有 Hook/Plugin 基础设施

```python
# ga.py:575 — 已存在的 turn_end hook 点
for hook in getattr(self.parent, '_turn_end_hooks', {}).values():
    hook(locals())

# plugins/langfuse_tracing.py — monkey-patch 解耦模式已成功实践
# 自激活，不修改任何核心文件，通过 import 时插桩实现

# mqtt_bbs/plugin.py + plugin_manager.py — 完整插件框架
# @plugin_hook 装饰器 + PluginBase + PluginContext
```

## 三、七大解耦改进方向

### 1. [P0] Turn轮次策略 -> 可插拔 Policy Hook

**现状：** ga.py:561-568 `turn_end_callback` 中硬编码轮次数值策略:

```python
if turn % 65 == 0: next_prompt += "必须ask_user..."
elif turn % 7 == 0: next_prompt += "危险信号..."
elif turn % 10 == 0: next_prompt += get_global_memory()
if _plan and turn >= 10 and turn % 5 == 0: ...
```

**问题：** 策略逻辑（何时警告、何时注入记忆、plan模式特殊规则）与核心循环深度耦合。

**改进：** 将 turn_policy 注册为 hook，核心保留最小默认值。

```python
for policy in self._turn_policies:
    next_prompt += policy(turn, _plan, next_prompt) or ""
```

**可抽离插件：** policy_default, policy_aggressive, policy_plan

**消除代码行：** ~15行

### 2. [P0] Plan Mode -> 插件化

**现状：** plan模式散落在 ga.py 三处:
- do_no_tool: 完成声明拦截 + 验证要求 (L466-469)
- turn_end_callback: 轮次提示注入 (L567-568)
- GenericAgentHandler: enter/exit/check方法 (L425-433)

**改进：** 注册 `_plan_validator` hook

```python
for v in self._plan_validators:
    result = v(content, self)
    if result: return result
```

**可抽离插件：** plan_validator_default (严格验证), plan_validator_lenient (宽松)

**消除代码行：** ~25行

### 3. [P1] 系统提示注入 -> hook化

**现状：** 多处硬编码注入系统提示:
- ga.py:422 memory读取时SOP提示
- ga.py:556 缺summary时强制要求
- ga.py:571-573 Master干预信息注入

**改进：** 注册 `_system_prompt_hooks`

**可抽离插件：** prompt_memory_sop, prompt_summary_enforcer, prompt_master_intervention

**消除代码行：** ~10行

### 4. [P1] 工具函数剥离 -> tools/utils.py

**现状：** ga.py 顶部混合通用工具函数:
- format_error(), log_memory_access(), expand_file_refs()
- smart_format(), consume_file(), _scan_files()

**改进：** 抽出到 `tools/utils.py`

```python
from tools.utils import format_error, smart_format, expand_file_refs
```

**消除代码行：** ~60行

### 5. [P2] 全局记忆注入 -> 独立服务

**现状：** get_global_memory() 手动拼接多个文件，注入时机硬编码在 turn_end_callback。

**改进：** 注册为记忆提供者

```python
self._memory_providers.append(lambda: load_global_memory())
```

**可抽离插件：** memory_injector (默认), memory_compact (精简), memory_debug (详细)

**消除代码行：** ~15行

### 6. [P2] WebDriver 生命周期 -> 惰性注入/插件

**现状：** first_init_driver() 是模块级全局函数，每次 web_scan/web_execute_js 检查 driver 状态。浏览器支持是可选功能，不应在 ga.py 加载时就引入 TMWebDriver。

**改进：** 将 WebDriver 初始化封装为惰性服务组件，通过 hook 注册。

**消除代码行：** ~15行

### 7. [P3] 历史折叠 & 摘要提取 -> 独立服务

**现状：** _fold_earlier() 和摘要提取逻辑在 ga.py:519-557。

**改进：** 抽出到 tools/history_fold.py

**消除代码行：** ~30行

## 四、优先级排序

| 优先级 | 改进项 | 消除代码 | 影响范围 | 风险 |
|--------|--------|---------|---------|------|
| P0 | Turn策略 -> Policy Hook | ~15行 | 核心循环行为 | 低 |
| P0 | Plan Mode -> 插件 | ~25行 | Agent行为模式 | 低 |
| P1 | 工具函数 -> tools/utils | ~60行 | 重构无行为变化 | 极低 |
| P1 | 系统提示注入 -> hook | ~10行 | Prompt注入策略 | 低 |
| P2 | 全局记忆 -> 独立服务 | ~15行 | 上下文策略 | 中 |
| P2 | WebDriver -> 惰性服务 | ~15行 | 浏览器功能 | 中 |
| P3 | 历史折叠 -> 工具库 | ~30行 | 纯重构 | 极低 |

## 五、建议实施路线

```
Phase 1 (安全重构):
  工具函数抽出 tools/utils.py -> 零风险，纯移动

Phase 2 (已有模式扩展):
  turn_end hook 增强: 硬编码策略改为可注册 policy chain
  Plan Mode 校验器: 抽出为可注册 validator chain

Phase 3 (独立服务化):
  全局记忆提供者注册制
  WebDriver 惰性注入

Phase 4 (插件生态):
  默认插件包: policy_default, plan_validator_default, memory_injector
  可选插件: policy_aggressive, plan_validator_lenient
```

## 六、总结

ga.py 承担了过多职责。既是工具实现层、又是策略层、还是上下文管理层。现有 _turn_end_hooks 和 langfuse_tracing 的 monkey-patch 模式已验证了"非侵入式解耦"的可行性。

优先将 Turn策略 和 Plan Mode 抽取为可注册 hook chain，只需在 ga.py 中增加 3 行 hook 注册代码，即可消除 ~40 行策略硬编码，使策略层完全可插拔。


---

## 七、补充改进方向（第二轮审查发现）

### 8. [P1] LLM Session 工厂模式 -> Provider Plugin

**文件：** llmcore.py（1032行，项目最大文件）

**现状：** 5种Session类型+2种ToolClient混在同一文件中:

| 类 | 行号 | 职责 |
|------|------|------|
| ClaudeSession | L590 | 旧版Claude API |
| LLMSession | L609 | OpenAI兼容API |
| NativeClaudeSession | L632 | Claude原生SDK |
| NativeOAISession | L704 | OpenAI原生SDK |
| ToolClient | L736 | 工具调用包装(通用) |
| NativeToolClient | L970 | 原生工具调用 |
| MixinSession | L898 | 多Provider路由 |

同时混杂了各Provider特有的SSE解析函数:
- `_parse_claude_sse` (L119) / `_parse_claude_json` (L111)
- `_parse_openai_sse` (L202) / `_parse_openai_json` (L310)
- `_msgs_claude2oai` (L465) / `openai_tools_to_claude` (L710)

**问题：** 增加新Provider（如Gemini、Groq）需要修改llmcore.py。Provider特有的消息格式转换、SSE解析、认证方式与核心循环耦合。

**改进：** 注册式 Provider 工厂

```python
# tools/llm_providers/ 目录结构
llm_providers/
  __init__.py       # ProviderRegistry
  claude.py         # ClaudeSession + SSE解析
  openai.py         # OpenAISession + SSE解析  
  gemini.py         # (未来扩展)
  
# 注册:
ProviderRegistry.register('claude', ClaudeProvider)
ProviderRegistry.register('openai', OpenAIProvider)

# 使用:
session = ProviderRegistry.create(cfg_name, cfg)
```

**消除代码行：** ~500行可移出llmcore.py

### 9. [P1] agentmain.py MQTT Worker Agent -> 独立模块/插件

**文件：** agentmain.py L262-297

**现状：** agentmain.py末尾有一段完整的MQTT Worker Agent初始化:

```python
def _mqtt_handler(msg):
    ...
    worker = WorkerAgent(...)
    worker.on_task(_mqtt_handler)
    worker.start(block=True)
```

这实际上定义了**第二种运行模式**（MQTT Agent vs 控制台Agent），却在同一个入口文件里用 `if args.mqtt:` 分支处理。

**问题：** 增加了agentmain.py的理解成本。MQTT模式和交互模式共享了GenericAgent类但初始化路径完全不同。

**改进：** 抽出为 `mqtt_agent.py`

```python
# mqtt_agent.py
def run_mqtt_agent(config):
    worker = WorkerAgent(...)
    worker.start(block=True)

# agentmain.py 只保留:
if args.mqtt:
    from mqtt_agent import run_mqtt_agent
    run_mqtt_agent(args)
```

**消除代码行：** ~35行核心入口 -> 独立模块

### 10. [P2] 历史压缩策略 -> Hook/Plugin

**文件：** llmcore.py L33-65

**现状：** `compress_history_tags()` 硬编码了压缩策略:
- keep_recent=10条不压缩
- max_len=800字符截断
- interval=5轮压缩一次
- 特定标签（thinking, tool_use, tool_result）的截断规则

**问题：** 压缩策略是token优化策略，与LLM核心调用无关。不同模型有不同的上下文窗口，需要不同的压缩参数。

**改进：** 注册式压缩器

```python
self._compressors.append(lambda msgs: default_compress(msgs, keep_recent=10))
```

**可抽离插件：** compressor_default, compressor_aggressive（小窗口模型）, compressor_light（大窗口模型）

**消除代码行：** ~30行核心代码 -> 插件

### 11. [P2] mykey 配置系统 -> 配置服务层

**文件：** mykey.py (476行) + mykey_internet.py (480行) + mykey_inner.py (122行) + mykey_inner_vlm.py (76行) = **1154行配置代码**

**现状：** 配置系统分布在4个文件中，包含：
- API密钥定义
- 模型配置（各provider的endpoint/model名）
- 环境-specific覆盖（inner/internet/vlm）
- mykey.json 文件加载

**问题：** 配置管理与核心逻辑耦合。`llmcore.py` 通过 `reload_mykeys()` 热加载密钥，`ga.py` 也隐式依赖mykey。

**改进：** 配置服务层

```python
# tools/config_service.py
class ConfigService:
    def get(self, key, default=None): ...
    def get_model_config(self, provider): ...
    def on_change(self, callback): ...  # 热加载事件
```

**消除耦合：** llmcore.py 不再直接 `import mykey`，通过配置服务接口访问

### 12. [P2] 斜杠命令 -> Plugin

**文件：** agentmain.py L110 `_handle_slash_cmd()`

**现状：** 交互式命令（/help, /model, /history, /save等）硬编码在agentmain.py中，与核心Agent逻辑耦合。

**改进：** 注册式命令

```python
self._slash_commands = {}
def register_command(self, name, handler, help_text):
    self._slash_commands[name] = (handler, help_text)
```

**可抽离插件：** cmds_basic（help/model/history）, cmd_debug（/dump, /inspect）

### 13. [P3] 日志系统 -> 统一接口

**现状：** 项目内日志方式混乱:
- `print()` — ga.py, agentmain.py, llmcore.py
- `logging.getLogger()` — mqtt_bbs/ 模块
- `safeprint()` — llmcore.py L85
- `log.info/warn/error` — mqtt_bbs/plugin*.py

**问题：** 无法统一控制日志级别、输出目标、格式化。

**改进：** 统一日志服务

```python
# tools/log_service.py
logger = LogService("ga")
logger.info("...")  # 统一输出，支持级别控制
```

### 14. [P3] 重试模式 -> 装饰器

**现状：** 多处有重试逻辑:
- llmcore.py L353 `_stream_with_retry()` — API流式重试
- llmcore.py L355 `_delay()` — 退避策略
- agent_loop.py 隐式重试逻辑

**改进：** 统一重试装饰器

```python
@retry(max_attempts=3, backoff=exponential, catch=(HTTPError, ConnectionError))
def stream_api_call(...):
    ...
```

## 八、完整优先级总表

| 优先级 | 改进项 | 消除代码 | 影响范围 | 风险 |
|--------|--------|---------|---------|------|
| **P0** | Turn策略 -> Policy Hook | ~15行 | 核心循环行为 | 低 |
| **P0** | Plan Mode -> 插件 | ~25行 | Agent行为模式 | 低 |
| **P1** | LLM Provider -> 插件工厂 | **~500行** | LLM核心 | 中（需设计接口） |
| **P1** | 工具函数 -> tools/utils | ~60行 | 重构无行为变化 | 极低 |
| **P1** | MQTT Worker -> 独立模块 | ~35行 | 入口文件 | 低 |
| **P1** | 系统提示注入 -> hook | ~10行 | Prompt注入策略 | 低 |
| **P2** | mykey -> 配置服务 | ~耦合消除 | 配置系统 | 中 |
| **P2** | 历史压缩 -> 插件 | ~30行 | Token优化 | 低 |
| **P2** | 全局记忆 -> 独立服务 | ~15行 | 上下文策略 | 中 |
| **P2** | WebDriver -> 惰性服务 | ~15行 | 浏览器功能 | 中 |
| **P2** | 斜杠命令 -> 插件 | ~20行 | 交互UI | 低 |
| **P3** | 历史折叠 -> 工具库 | ~30行 | 纯重构 | 极低 |
| **P3** | 日志系统 -> 统一接口 | ~全局 | 运维 | 中 |
| **P3** | 重试模式 -> 装饰器 | ~20行 | 错误处理 | 低 |

## 九、关键设计建议

### 架构分层目标
```
plugins/          <-- 策略层（可插拔、热加载）
  policy_default.py
  plan_validator.py
  memory_injector.py
  cmds_basic.py
  compressor_default.py

tools/            <-- 服务层（接口稳定）
  utils.py
  history_fold.py
  config_service.py
  log_service.py
  llm_providers/   <-- Provider插件

ga.py             <-- 核心层（精简）
agent_loop.py
agentmain.py
```

### 渐进式重构路径
```
Step 1 (现版本):  ga.py 589行，llmcore.py 1032行，混合严重
Step 2 (Phase1): ga.py ~500行（抽出工具函数），llmcore.py ~900行（不变）
Step 3 (Phase2): ga.py ~450行（策略hook化），llmcore.py ~850行（不变）
Step 4 (Phase3): ga.py ~400行，llmcore.py ~400行（Provider分离）
Step 5 (目标):   ga.py ~350行，llmcore.py ~350行，各服务独立
```
