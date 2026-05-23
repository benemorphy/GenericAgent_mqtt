# 代码解耦改进：风险评估与执行策略

评估日期：2026-05-20
评估范围：docs/decoupling_analysis.md 中的14项改进

## 一、逐项风险评级

```
风险分级:
  ⚠️⚠️⚠️ = 高风险 (行为可能变更 / 范围广 / 难回滚)
  ⚠️⚠️   = 中风险 (有行为影响但可隔离)
  ⚠️     = 低风险 (纯重构 / 有默认兼容 / 易回滚)
  ✅     = 极低/零风险 (仅移动/重命名)
```

| # | 改进项 | 风险 | 受影响文件 | 回滚难度 | 关键风险点 |
|---|--------|------|-----------|---------|-----------|
| 3 | 工具函数 -> tools/utils | ✅ | ga.py | 极低 | 纯移动，改import路径即可 |
| 12 | 历史折叠 -> 工具库 | ✅ | ga.py | 极低 | 纯移动 |
| 1 | Turn策略 -> Policy Hook | ⚠️ | ga.py | 低 | 默认策略需完全等价于当前行为 |
| 4 | 系统提示注入 -> hook | ⚠️ | ga.py, agent_loop.py | 低 | 同上，默认hook必须零差异 |
| 7 | 历史压缩 -> 插件 | ⚠️ | llmcore.py | 低 | 压缩失败不影响核心执行，只影响上下文长度 |
| 2 | Plan Mode -> 插件化 | ⚠️⚠️ | ga.py | 中 | 3个散布触摸点，漏一个会导致plan行为不一致 |
| 6 | MQTT Worker -> 独立 | ⚠️⚠️ | agentmain.py | 中 | import路径变更，mqtt模式启动会碎 |
| 10 | WebDriver -> 惰性服务 | ⚠️⚠️ | ga.py, simphtml.py | 中 | web_scan/web_execute_js启动时序可能变化 |
| 11 | 斜杠命令 -> 插件 | ⚠️⚠️ | agentmain.py | 中 | 命令注册顺序影响交互体验 |
| 14 | 重试模式 -> 装饰器 | ⚠️⚠️ | llmcore.py | 中 | 重试语义必须完全等价，否则网络错误处理改变 |
| 9 | 全局记忆 -> 独立服务 | ⚠️⚠️⚠️ | ga.py | 高 | 注入时机/格式/频率变化直接改变Agent看到的上下文 |
| 13 | 日志系统 -> 统一 | ⚠️⚠️⚠️ | 所有核心文件 | 高 | 跨越4个文件，print->logging的语义差异 |
| 8 | mykey -> 配置服务 | ⚠️⚠️⚠️ | llmcore+.py, mykey*.py | 高 | API密钥加载失败 -> Agent全死 |
| 5 | LLM Provider -> 工厂 | ⚠️⚠️⚠️ | llmcore.py(~500行) | 最高 | 最大修改量，SSE解析/消息转换/auth流都可能碎 |

## 二、文件冲突地图（瓶颈识别）

```
           ga.py (8项冲突)  ←── 瓶颈文件
           +-- #1 Turn策略
           +-- #2 Plan Mode
           +-- #3 工具函数         ← 必须先做（其他改依赖干净的ga.py）
           +-- #4 系统提示
           +-- #9 全局记忆
           +-- #10 WebDriver
           +-- #12 历史折叠
           +-- #13 日志系统

           llmcore.py (5项冲突)
           +-- #5 LLM Provider    ← 最大单项修改
           +-- #7 历史压缩
           +-- #8 mykey配置
           +-- #13 日志系统
           +-- #14 重试装饰器

           agentmain.py (3项)
           +-- #6 MQTT Worker
           +-- #11 斜杠命令
           +-- #13 日志系统
```

关键结论：ga.py 上同时只能做一件事（8项全部冲突），llmcore.py 同理（5项全部冲突）。

## 三、"交替Agent"策略评估

### 优势

| 维度 | 评估 |
|------|------|
| 安全网 | 一个Agent挂掉不影响另一个，可以修复前一个 |
| 零停机 | 始终有一个可用实例响应请求 |
| 对比验证 | 两个Agent分别跑同一任务，对比输出可检测行为走偏 |
| 自然隔离 | 不同Agent对不同文件做修改，减少单个Agent上下文污染 |

### 关键隐患

#### 隐患1：Git 冲突（最致命）

两个Agent同时对同一文件的不同行做修改时，如果A先提交，B的修改基于旧版本，B提交时会冲突。

解决办法：每次只让一个Agent操作 ga.py 或 llmcore.py。另一个Agent只能操作无冲突的文件。

#### 隐患2：共享状态污染

两个Agent共享 mykey 中的API密钥配置。如果Agent B正在改造mykey系统时Agent A启动了新会话，A可能读到不完整的状态。

解决办法：改造配置服务期间，另一个Agent用缓存/快照版本。

#### 隐患3：进程争抢

两个Agent都写 temp/ 和 sche_tasks/，可能互相覆盖文件。

解决办法：为每个Agent分配独立工作目录 temp_A/ temp_B/，通过环境变量切换。

### 交替策略的最佳姿势

```
  Agent A（稳定版）          Agent B（实验版）
  ------------              -------------
  git checkout main          git checkout -b feature/xxx
  运行中，处理用户请求       修改代码，跑验证测试
  只读不写核心文件           改完push，通知A测试
  收到"[VERIFY] OK"信号     B的任务完成 -> 等评审
  合并B的PR到main           切到下一个feature分支
```

## 四、推荐执行顺序

### Batch 1: 零风险起手

```
[ ] #3  工具函数 -> tools/utils        ✅   纯移动
[ ] #12 历史折叠 -> 工具库             ✅   纯移动
```
这两个纯移动，无行为变更，可并行做。分给一个Agent，一小时内完成。

### Batch 2: Additive Hook（巩固ga.py底座）

```
[ ] #1  Turn策略 -> Policy Hook        ⚠️   先于 #2
[ ] #4  系统提示注入 -> hook           ⚠️
[ ] #9  全局记忆 -> 独立服务          ⚠️⚠️
```
先加hook注册点，再抽离默认实现。关键：默认Policy必须完全等价现有逻辑。

### Batch 3: ga.py 改造

```
[ ] #2  Plan Mode -> 插件化           ⚠️⚠️  基于Batch 2的hook基础设施
[ ] #10 WebDriver -> 惰性服务        ⚠️⚠️
```

### Batch 4: 独立子系统（可分配不同Agent，但冲突项必须串行）

```
[ ] #6  MQTT Worker独立    ⚠️⚠️   -> agentmain.py
[ ] #11 斜杠命令插件      ⚠️⚠️   -> agentmain.py（与#6冲突！串行做）
[ ] #7  历史压缩插件       ⚠️     -> llmcore.py
[ ] #14 重试装饰器        ⚠️⚠️   -> llmcore.py（与#7冲突！串行做）
```

### Batch 5: 高风险改造

```
[ ] #8  mykey -> 配置服务          ⚠️⚠️⚠️  需要支持运行时reload
[ ] #5  LLM Provider -> 工厂       ⚠️⚠️⚠️  最大单项，建议拆子步骤
[ ] #13 日志系统 -> 统一           ⚠️⚠️⚠️  最后做，影响面最广
```

## 五、安全措施

### 验证检查点（每次改进后必须通过）

```python
def verify_after_refactor():
    # 启动测试
    assert 可以正常启动
    assert 启动后能响应至少1条用户消息
    
    # 核心工具
    assert code_run 正常
    assert file_read/file_write/file_patch 正常
    
    # 浏览器（如果改了 WebDriver）
    if 修改涉及 web_scan/web_execute_js:
        assert web_scan 正常
        assert web_execute_js 正常
    
    # 行为一致性
    assert turn_end_callback 触发策略与改前一致
```

### git 分支策略

```
main         <- 始终可用的稳定版
+-- feat/hook-infra        # Batch 1+2 (ga.py 基础设施)
+-- feat/plan-extract      # Batch 3 (Plan Mode 插件化)
+-- feat/provider-factory  # Batch 5 (LLM Provider 工厂)
+-- ...
```

每个 feat 分支由 Agent B 创建和修改，完成后 Agent A（运行版）审查并合并到 main。

### 交替节奏

```
Agent A (运行中) -> 用户正常使用
Agent B (实验)   -> 改 Batch N，完成后通知
Agent A          -> git pull feat/N，本地测试，确认OK后合并
Agent A          -> 重启，变成改进版
Agent B          -> 切到 Batch N+1
```

## 六、总结

你的"交替Agent"策略是有效的，但关键在于：

1. **ga.py 和 llmcore.py 是单线程瓶颈文件**，每次只能一个Agent操作它们
2. 其他文件（agentmain.py、mykey*.py）可以交替并行
3. 建议从 Batch 1（零风险纯移动）开始，让两个Agent都热手
4. 每批次完成后必须运行验证检查点，确认0行为偏差后再提交
