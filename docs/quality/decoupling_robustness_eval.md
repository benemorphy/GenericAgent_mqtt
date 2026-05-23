# 代码解耦改进：鲁棒性评估

评估日期：2026-05-20
评估范围：docs/decoupling_analysis.md 中的14项改进

## 核心判定

大部分改进有利于鲁棒性，但有两个方向（#13 日志统一 / 插件系统本身）需谨慎设计，否则会引入新的脆弱点。

## 一、故障隔离（Fault Isolation）

当前痛点：一个组件的崩溃会连锁扩散到整个Agent。

| 改进项 | 当前故障传播链 | 优化后 | 鲁棒性收益 |
|--------|--------------|--------|-----------|
| #5 LLM Provider工厂 | OpenAI超时 -> MixinSession异常 -> 整个Agent循环崩溃 | 一个Provider挂掉只影响该Provider，可fallback到其他Provider | 高 |
| #10 WebDriver惰性 | TMWebDriver import失败 -> ga.py模块加载崩溃 -> Agent无法启动 | 浏览器挂掉只是 web_scan 报错，文件操作照常 | 高 |
| #6 MQTT Worker独立 | MQTT初始化异常 -> agentmain.py主循环崩溃 | console模式和MQTT模式彻底隔离 | 中高 |
| #2 Plan Mode插件化 | plan校验器异常 -> do_no_tool中断 -> 响应循环挂起 | 插件抛异常只影响plan校验，可以跳过/降级 | 中 |
| #8 mykey配置服务 | mykey热加载失败 -> llmcore模块级崩溃 -> 启动失败 | 配置读取失败返回fallback值，支持热重试 | 中 |
| #1/#4/#9 Hook链 | 策略逻辑中的bug直接影响核心循环 | 有问题的hook可以被单个移除或绕过 | 中 |

最大收益是 #5（Provider隔离）和 #10（可选功能降级）。当前架构下，任何一个LLM Provider的API问题都会让Agent完全不可用。

## 二、优雅降级（Graceful Degradation）

当前痛点：非核心功能损坏时，Agent要么拒绝启动，要么运行时崩溃。

### 当前启动依赖链

```
启动
  +-- llmcore.py import (必须成功)
  |     +-- mykey 加载 (必须成功)
  |     +-- 所有Provider初始化 (全部必须成功)
  +-- ga.py import
  |     +-- TMWebDriver import (必须成功)
  |     +-- simphtml import (必须成功)
  +-- agent_loop.py import (必须成功)
  --> 任何一个失败 = Agent无法启动
```

### 优化后依赖链

```
启动
  +-- kernel/ import (仅核心)
  +-- 服务注册（可选，失败只影响该服务）
  |     +-- LLM Provider Registry
  |     +-- Browser Service (惰性)
  |     +-- Config Service
  |     +-- Plugin Manager
  --> 核心启动成功即可工作，可选服务按需加载
```

### 场景对比

| 场景 | 当前行为 | 优化后行为 |
|------|---------|-----------|
| 浏览器引擎缺失 | Agent无法启动 | Agent正常启动，web_scan返回"浏览器不可用" |
| 某个LLM Provider配额耗尽 | Agent循环崩溃 | Agent自动切换到下一个可用Provider |
| mykey格式错误 | 崩溃 | 使用fallback配置，触发告警 |
| Plan Mode空指针 | 响应循环卡死 | 跳过plan校验，以普通模式执行 |

优化后大部分场景从"崩溃"变为"降级"，这是鲁棒性最本质的提升。

## 三、可恢复性（Recoverability）

| 改进项 | 对可恢复性的影响 |
|--------|----------------|
| #3/#12 工具函数抽出 | 纯重构，不影响运行时。但简化了代码，降低了后续改出bug的概率 |
| #8 mykey配置服务 | 支持运行时reload：改完配置无需重启Agent。当前必须kill -> 改文件 -> 重启，风险高 |
| #5 Provider工厂 | 运行时注册新Provider，不用重启。当前加一个Provider必须改llmcore.py再重启 |
| #1/#4 Hook链 | 策略可以在运行时动态替换（如"切换成更激进的轮次策略"），不用重启 |
| #14 重试装饰器 | 统一的重试语义让系统在瞬态故障后自动恢复，当前部分失败场景直接崩溃 |

## 四、引入的新脆弱点

| 新脆弱点 | 涉及的改进 | 严重程度 | 缓解措施 |
|---------|-----------|---------|---------|
| Plugin加载失败 | #1/#2/#4/#7/#11 | 中 | try/except包围所有插件调用，单个插件加载失败不影响核心 |
| Hook执行顺序依赖 | #1/#4/#9 | 中高 | Hook不承诺执行顺序，每个hook应为幂等设计 |
| Runtime hook注入导致状态不一致 | #1/#2/#4 | 中 | 限制hook只能在turn边界处注入，不允许在对话中途动态变更 |
| import路径变更导致找不到模块 | #3/#6/#12 | 中 | 保持sys.path一致性，写测试确认导入成功 |

最关键的设计约束：核心循环必须能在零插件下运行。

```python
# 正确设计：
try:
    for hook in self._turn_policies:
        next_prompt += hook(turn, _plan, next_prompt) or ""
except Exception as e:
    log(f"Policy hook failed (skipped): {e}")  # 降级，不崩溃
```

## 五、逐项净收益总表

```
改进项             故障隔离  优雅降级  可恢复性  新脆弱点    净鲁棒性收益
                    (+/0/-)  (+/0/-)  (+/0/-)  (0~3个)  

#3 工具函数抽出    0       0        +        0       轻微正面（维护性）
#12 历史折叠工具化  0       0        +        0       轻微正面（维护性）
#1 Turn策略Hook    +       +        0        1       正面（需try包围）
#4 系统提示Hook    +       +        0        1       正面
#7 历史压缩插件    +       0        0        1       轻微正面
#2 Plan Mode插件  ++      +        +        1       正面（隔离价值大）
#6 MQTT独立       ++      0        0        1       正面
#10 WebDriver惰性 ++      ++       0        0       显著正面
#11 斜杠命令插件  +       0        +        1       轻微正面
#14 重试装饰器    0       +        ++       0       正面
#9 全局记忆服务   ++      +        0        1       正面（需注意时机）
#8 mykey配置服务  ++      ++       ++       1       显著正面
#5 Provider工厂  +++     ++       ++       1       最显著正面
#13 日志统一      +       +        +        2       需谨慎：print->logging语义差异
```

## 六、关键风险提醒

### 1. 日志统一可能降低鲁棒性

当前 print() 是行缓冲，崩溃时最后一行日志不会丢失。logging默认行缓冲，崩溃时日志丢失。

```python
# 当前：print 即时刷出
print("正在调用API...")  # 崩溃时可见
api_call()  # crash here

# 优化后必须保持flush语义
log = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
handler.flush = True  # 关键！
```

### 2. Hook链需要断路器模式

```python
class CircuitBreaker:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.failures = 0
        
    def call(self, hook, *args):
        try:
            result = hook(*args)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            log(f"Hook {hook.__name__} failed: {e}")
            if self.failures > 3:
                self.remove(hook)  # 熔断移除
            return None  # 降级
```

## 七、总结

14项改进整体有利于鲁棒性，但收益分布不均。

最关键的三项：
1. #5 LLM Provider工厂：将一个Provider的故障隔离，防止连锁崩溃
2. #10 WebDriver惰性化：可选功能降级，浏览器坏了Agent仍然可用
3. #8 mykey配置服务：配置错误不再阻止启动，支持运行时热恢复

需要警惕的两点：
1. 日志统一（#13）需保持 flush=True，否则崩溃时日志丢失反而降低可诊断性
2. Hook/插件系统本身必须有 try/except 保护 + 断路器，否则改进手段本身变成新的脆弱点

| 鲁棒性维度 | 优化前 | 优化后 | 变化 |
|-----------|-------|-------|------|
| 非核心功能崩溃是否影响核心 | 是（连锁崩溃） | 否（故障隔离） | 显著提升 |
| 可选组件不可用是否影响启动 | 是（拒绝启动） | 否（降级运行） | 显著提升 |
| 配置错误是否可运行时修复 | 否（必须重启） | 是（热重载） | 提升 |
| 运行时故障是否可自动恢复 | 部分（仅retry） | 大部分（retry+fallback+熔断） | 提升 |
| 系统故障是否可诊断 | 中等（print日志） | 强（结构化日志） | 需谨慎实施 |
| 系统复杂度引入的新脆弱点 | 0 | 1-3个（插件加载/hook链/import路径） | 需要警惕 |
