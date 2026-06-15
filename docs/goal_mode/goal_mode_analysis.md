# GenericAgent Goal Mode 实现分析

> 分析对象：`D:\00synchronize\GenericAgent`
> 目标：理解其分层架构，为迁移到 Beneh 项目做准备

## 架构总览（5 层）

```
用户输入目标 + 时间预算
        │
        ▼
  ┌─────────────────────────┐
  │  Layer 1: Reflect Loop  │  agentmain.py (反射循环)
  │  每轮 poll → inject     │
  └────────┬────────────────┘
           │ check() 返回 prompt
           ▼
  ┌─────────────────────────┐
  │  Layer 2: goal_mode.py  │  Reflect 脚本（状态机）
  │  goal_state.json 驱动   │
  └────────┬────────────────┘
           │ 读取 SOP 指导行为
           ▼
  ┌─────────────────────────┐
  │  Layer 3: goal_mode_sop │  启动 SOP
  │  + goal_hive_sop       │  多 worker 扩展
  │  + master_duty         │  编排哲学
  └─────────────────────────┘
```

---

## Layer 1: Reflect 循环（引擎层）

**位置**：`agentmain.py` L239-276

**核心代码**（约 38 行）：

```python
# 动态导入 reflect 脚本
spec = importlib.util.spec_from_file_location('reflect_script', args.reflect)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
if hasattr(mod, 'init'):
    mod.init(_reflect_args)

# 轮询循环
while True:
    time.sleep(mod.INTERVAL)        # goal_mode 每 3 秒
    try:
        task = mod.check()          # 检查是否触发
    except Exception as e:
        continue
    if task == '/exit':
        break                       # 退出信号
    if task is None:
        continue                    # 无任务，继续等
    
    # 注入任务到 agent
    dq = agent.put_task(task, source='reflect')
    while 'done' not in (item := dq.get(timeout=1200)):
        pass
    result = item['done']
    
    # 回调
    if (on_done := getattr(mod, 'on_done', None)):
        on_done(result)
```

**关键设计**：
- 基于**轮询**而非事件驱动（每 3 秒调用 `check()`）
- `check()` 返回 **prompt 字符串**直接喂给 LLM
- 脚本可**热重载**（检测文件 mtime 变化）
- `INTERVAL=3` 短间隔确保 agent 跑完立刻下一轮

---

## Layer 2: goal_mode.py — 状态机

**位置**：`reflect/goal_mode.py`

### 状态文件

```json
{
  "objective": "用户目标文本",
  "budget_seconds": 10800,
  "start_time": 1234567890,
  "turns_used": 0,
  "max_turns": 200,
  "status": "running",
  "done_prompt": ""
}
```

### 状态转换

```
                ┌──────────────┐
                │  status !=   │
                │  'running'   │──→ /exit
                └──────┬───────┘
                       │ status == 'running'
                       ▼
              ┌──────────────────┐
              │  budget 耗尽?    │
              │  turns 超限?     │
              └──────┬──┬────────┘
                     │  │
               YES   │  │  NO
                     │  │
                     ▼  ▼
          ┌────────────┐  ┌──────────────────┐
          │ 最后一轮    │  │ 正常推进          │
          │ BUDGET_    │  │ CONTINUATION_    │
          │ LIMIT_     │  │ PROMPT           │
          │ PROMPT     │  │                  │
          └─────┬──────┘  └──────────────────┘
                │
                ▼
         on_done() 标记 done_budget
```

### 两种 Prompt 模板

| Prompt | 触发条件 | 核心指令 |
|--------|---------|---------|
| CONTINUATION_PROMPT | 正常轮 | 禁止提前交付、每轮换角度审视、找薄弱点深入打磨 |
| BUDGET_LIMIT_PROMPT | 预算耗尽 | 最后一轮：总结进展 + 列出未完成 + 清理 |

---

## Layer 3: goal_mode_sop.md — 启动 SOP

```bash
# 写 goal_state.json → 后台启动
start /b python agentmain.py --reflect reflect/goal_mode.py

# 多实例 / 不同模型
set GOAL_STATE=temp/goal_xxx.json && start /b python agentmain.py --reflect reflect/goal_mode.py --llm_no 1
```

---

## Layer 4: Goal Hive — 多 Worker 扩展

通过 **BBS（本地 HTTP 公告板）** 实现多进程协作：

```
                   ┌──────────────┐
                   │   BBS Server │  (agent_bbs.py, 本地端口)
                   │  帖子/任务池 │
                   └──────┬───────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │Hive      │   │Worker 1  │   │Worker 2  │
   │Master    │   │(独立进程) │   │(独立进程) │
   │(调度者)   │   └──────────┘   └──────────┘
   └──────────┘
```

- **Master**: 读 `goal_hive_master_duty.md`，只调度不干活
- **Worker**: `agentmain.py --reflect agent_team_worker.py` 启动
- 最多 5 个 worker

---

## Layer 5: goal_hive_master_duty.md — 编排哲学

用**控制理论隐喻**指导行为：

| 概念 | 含义 |
|------|------|
| x 状态 | 进展、资源、风险、未闭合接口 |
| u 控制 | 分工、调度、增减 worker、纠偏 |
| y 观测 | Worker 输出、文件变化、质量缺陷 |
| J 目标函数 | 真正要优化的用户价值 |

核心方法：J 设计（3 排序问题）→ 边际收益调度 → 冻结接口 → 验收三选一 → 失稳检测 → 恢复动作

---

## 总结

Goal Mode 的本质是**操作系统内核式架构**：

| 组件 | 类比 OS | 功能 |
|------|---------|------|
| Reflect Loop | 进程调度器 | 永不停止的执行框架 |
| goal_state.json | 进程控制块(PCB) | 可中断/可恢复的状态 |
| SOP 体系 | 策略文件 | 指导 LLM 行为原则 |
| Prompt 工程 | 系统调用 | "继续、换角度、不准停"约束 |
| BBS 协议 | IPC | 跨进程多 Agent 协作 |

LLM 不是被代码控制的工具，而是**运行在这个框架上的应用层**。
