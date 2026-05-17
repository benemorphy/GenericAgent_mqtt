# Reflect 机制详解

> 生成日期：2026-05-16
> 相关代码：`agentmain.py` L223-L259, `reflect/*.py`, `memory/scheduled_task_sop.md`, `memory/goal_mode_sop.md`

---

## 一、架构总览

Reflect 是 **后台守驻循环**（watchdog/daemon）框架。核心思路：加载一个 Python 模块作为"探测器"，按固定间隔轮询检查条件，条件满足时自动给 Agent 下发任务，等 Agent 执行完后继续下一轮。

```
agentmain.py --reflect reflect/模块.py
       │
       ▼
    ┌─────────────┐     INTERVAL秒     ┌──────────────┐
    │  mod.check()  │ ◄─────────────── │  sleep轮询    │
    │  return: str  │                  │              │
    │  or None      │                  │              │
    │  or '/exit'   │                  │              │
    └──────┬───────┘                  └──────────────┘
           │ task (str)
           ▼
    ┌─────────────┐     put_task()    ┌──────────────┐
    │  Agent执行   │ ────────────────►│  dq.get()等待  │
    │              │ ◄───────────────│  结果返回     │
    └──────┬───────┘   'done'        └──────────────┘
           │ result
           ▼
    ┌─────────────┐
    │ mod.on_done()│  ← 钩子：记录时间/状态
    └─────────────┘
```

## 二、核心代码（agentmain.py, L223-L259）

```python
# ── 加载 reflect 模块 ──
spec = importlib.util.spec_from_file_location('reflect_script', args.reflect)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if hasattr(mod, 'init'): mod.init(_reflect_args)

# ── 主循环 ──
while True:
    # 热重载：检测文件修改则自动重新加载
    if os.path.getmtime(args.reflect) != _mt:
        spec.loader.exec_module(mod)
        if hasattr(mod, 'init'): mod.init(_reflect_args)
            
    # 1. 按 INTERVAL 秒休眠
    time.sleep(getattr(mod, 'INTERVAL', 5))
    
    # 2. 调用 check() 检查条件
    task = mod.check()
    if task == '/exit': break        # 退出信号
    if task is None:   continue      # 无任务，继续休眠
    
    # 3. 有任务 → 派发给 Agent
    dq = agent.put_task(task, source='reflect')
    result = dq.get(timeout=180)     # 等 Agent 执行完（最长3分钟）
    
    # 4. 记录日志
    open(f'temp/reflect_logs/{script_name}_{date}.log', 'a').write(result)
    
    # 5. 回调 on_done()
    if on_done := getattr(mod, 'on_done', None): on_done(result)
    
    # 6. 若 ONCE=True 则只执行一次退出
```

## 三、reflect 模块协议

每个 reflect 模块只需实现 **3个属性 + 2个可选函数**：

| 成员 | 类型 | 必需 | 说明 |
|------|:----:|:----:|------|
| `INTERVAL` | int | ✅ | 轮询间隔（秒） |
| `ONCE` | bool | ✅ | True=执行一次退出，False=持续循环 |
| `check()` | →str\|None | ✅ | 返回任务文本，None=无任务，`/exit`=退出 |
| `init(args)` | - | ❌ | 启动时调用，接收 `--reflect` 后的额外参数 |
| `on_done(result)` | - | ❌ | Agent 执行完后的回调 |

## 四、内置 3 个模块

### 1️⃣ reflect/autonomous.py — 用户离开检测器

**文件位置**: `reflect/autonomous.py`
**文件大小**: 6 行

```python
INTERVAL = 1800        # 30分钟检查一次
ONCE = False

def check():
    return "[AUTO]🤖 用户已经离开超过30分钟，作为自主智能体，请阅读自动化sop，执行自动任务。"
```

**用途**：用户30分钟没交互时，自动唤醒 Agent 执行自主行动（读 autonomous_operation_sop → 创建 TODO → 执行）

---

### 2️⃣ reflect/goal_mode.py — 预算驱动持续工作模式

**文件位置**: `reflect/goal_mode.py`
**文件大小**: 96 行

```python
INTERVAL = 3           # 3秒一检（Agent跑完立刻再唤醒）
ONCE = False

def check():
    state = _load()  # 读 temp/goal_state.json
    if state.get('status') != 'running': return '/exit'
    
    elapsed = time.time() - state['start_time']
    remaining = state['budget_seconds'] - elapsed
    turn = state.get('turns_used', 0) + 1
    
    if remaining <= 0 or turn > max_turns:
        # 预算耗尽 → 收口轮
        state['status'] = 'wrapping_up'
        return BUDGET_LIMIT_PROMPT
    else:
        # 正常继续
        state['turns_used'] = turn
        return CONTINUATION_PROMPT
```

**启动**：
```bash
python agentmain.py --reflect reflect/goal_mode.py
set GOAL_STATE=temp/goal_xxx.json && python agentmain.py --reflect reflect/goal_mode.py
```

**关键设计**：
- 通过 `temp/goal_state.json` 管理状态（objective / budget_seconds / turns_used / status）
- Agent 每轮执行完 → 3秒后立刻再唤醒 → 继续推进，直到预算耗尽
- 预算耗尽时自动进入"收口轮"（总结+列出未完成事项）
- 防空转：`max_turns=200` 上限
- 两种提示模板：`CONTINUATION_PROMPT`（持续推进，禁止说"已完成"）和 `BUDGET_LIMIT_PROMPT`（收口总结）

---

### 3️⃣ reflect/agent_team_worker.py — BBS 任务接单器

**文件位置**: `reflect/agent_team_worker.py`
**文件大小**: 48 行

```python
INTERVAL = 60
ONCE = False

def check():
    # 1. GET /posts?limit=10 查BBS新帖
    # 2. 找到新帖（id > _last_id）则返回任务prompt
    # 3. 无新帖则返回 None
```

**用途**：Agent 团队协作场景，从 BBS 看板接任务并执行
- 从 `agent_team_setting.json` 读取 BBS 配置
- 按 `_last_id` 增量检测新帖
- 120秒冷却防重复触发

---

## 五、定时任务调度器（scheduler.py）

与 Reflect 平级但不同：`scheduler.py` 是独立的轮询器（每60秒），扫描 `sche_tasks/*.json`，按日程表触发定时任务。

| 维度 | Reflect | Scheduler |
|:----|:-------:|:---------:|
| 触发条件 | check() 自定义逻辑 | cron式时间表（daily/weekly/once） |
| 配置方式 | Python 模块 | JSON 文件 |
| 间隔 | 模块自定 | 固定60秒轮询 |
| 热重载 | 自动检测文件修改 | JSON 修改后下一轮生效 |

## 六、热重载特性

Reflect 循环中每轮检测 `.py` 文件的 `mtime`，若有变化→自动 `exec_module()` 重新加载，**无需重启进程**。

```python
if os.path.getmtime(args.reflect) != _mt:
    spec.loader.exec_module(mod)    # 热重载
    if hasattr(mod, 'init'): mod.init(_reflect_args)
```

## 七、启动命令汇总

| 模式 | 命令 |
|:----|------|
| 用户离开检测 | `python agentmain.py --reflect reflect/autonomous.py` |
| 预算持续工作 | `python agentmain.py --reflect reflect/goal_mode.py` |
| BBS任务接单 | `python agentmain.py --reflect reflect/agent_team_worker.py --board_key xxx` |
| 定时任务 | `python scheduler.py` |
