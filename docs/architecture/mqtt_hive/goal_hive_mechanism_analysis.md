# GenericAgent Goal Hive 机制原理分析

分析日期: 2026-05-29
来源项目: D:\\00synchronize\\GenericAgent
分析方式: 读取 goal_hive_sop.md + goal_mode_sop.md + goal_hive_master_duty.md + 相关源码(agentmain.py reflect模式, agent_bbs.py, agent_team_worker.py, goal_mode.py)

## 概述

Goal Hive 是 GenericAgent 项目的多 Agent 协作框架。核心思想是**不靠共享内存/进程间通信，而靠公告板 HTTP API + SOP 协议约束来组织多 Agent 系统**。一个 Hive Master 负责任务调度和质量验收，多个 Worker 独立执行子任务，三者通过 BBS（Bulletin Board System）通信。

## 整体架构

```
┌──────────────────────────────────────────────────┐
│              Hive Master(Gaal Mode)                │
│  (agentmain.py --reflect reflect/goal_mode.py)     │
│  职责: 调度/设计子任务/验收/纠偏, 不亲自干活        │
└──────────────────┬───────────────────────────────┘
                   │ HTTP REST API
                   ▼
┌──────────────────────────────────────────────────┐
│              Agent BBS (公告板)                     │
│  (assets/agent_bbs.py - FastAPI + SQLite)          │
│   端点: /register /post /poll /posts /file/...     │
│   每个 Hive session 独立 key + 独立 sqlite db       │
└──────────────────┬───────────────────────────────┘
                   │ workers 轮询 BBS 接单/交成果
                   ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Worker 1  │ │ Worker 2  │ │ Worker 3  │
│ (独立进程) │ │ (独立进程) │ │ (独立进程) │
└──────────┘ └──────────┘ └──────────┘
```

## 核心组件

### 1. --reflect 模式 (agentmain.py)

这是整个系统的运行引擎。`python agentmain.py --reflect SCRIPT` 的流程:

```python
while True:
    time.sleep(mod.INTERVAL)       # 轮询间隔(由反射脚本定义)
    try: task = mod.check()        # 调用反射脚本的check()
    except: continue
    
    if task == '/exit': break       # 退出信号
    if task is None: continue       # 无事可做
    
    dq = agent.put_task(task)       # 提交给LLM执行
    while 'done' not in dq.get(): pass  # 等待LLM完成
    
    if hasattr(mod, 'on_done'):
        mod.on_done(result)         # 状态更新回调
```

关键设计: `check()` 是轻量 Python 代码(不调 LLM)，只有在 check() 返回非空 prompt 时才触发 LLM 调用。Agent 进程空闲时不消耗 token。

### 2. Hive Master (reflect/goal_mode.py + goal_hive_master_duty.md)

- INTERVAL = 3 秒 (Agent 跑完立刻再检查)
- check() 读 goal_state.json → 检查预算/轮次 → 生成 continuation prompt
- 状态流转: running → wrapping_up → done_budget
- Master 职责: 设计子任务, 发布到 BBS, 验收 worker 产出, 发现偏差纠偏
- Master 禁止: 亲自执行子任务(导致 worker 空转), 提前交付(时间用完前不准停)

**调度控制论模型 (来自 master_duty.md):**

- x (状态): 进展, 资源, 风险, 未闭合接口, 不确定性
- u (控制): 分工, 调度, 增减 worker, 重排, 验收, 纠偏
- y (观测): worker 输出, 文件变化, 质量缺陷, 时间消耗, 用户反馈
- J (目标函数): 当前任务真正要优化的用户价值

调度按边际收益排序: 优先派发最能提升 J、解除瓶颈、降低系统性风险的任务。

### 3. Worker (reflect/agent_team_worker.py)

- INTERVAL = 60 秒 (低频轮询, 避免频繁唤醒)
- check() 长轮询 BBS /posts → 比较 last_id → 有新帖则触发任务
- 失败容错: 连续10次连接失败 → /exit 自动退出
- Worker prompt 告知: 查看新帖, 找到适合自己的任务帖, 回复抢单, 执行后汇报, 等待下一轮

### 4. BBS 公告板 (assets/agent_bbs.py)

FastAPI + SQLite 轻量服务, 通过 ApiKeyMiddleware 鉴权:

| 端点 | 方法 | 用途 |
|------|------|------|
| /register | POST | 注册(获取 token) |
| /post | POST | 发帖 |
| /poll?since_id=N | GET | 增量轮询 |
| /posts?limit=N | GET | 获取帖子列表 |
| /posts?author=X | GET | 按作者筛选 |
| /file/upload | POST | 上传文件 |
| /file/{id}/{name} | GET | 下载文件 |

所有请求必须在 Header 或 Query 中带 `key=BOARD_KEY` 鉴权。每个 key 对应独立 SQLite 数据库。

## 启动流程

```
1. 选端口 PORT 和协作 key BOARD_KEY
2. 创建 BBS_CWD = temp/hive_<目标短名>

3. 启动 BBS:
   start /b python assets/agent_bbs.py --cwd <BBS_CWD> --port <PORT> --key <BOARD_KEY>

4. 在 BBS 发第一帖(包含: 任务目标, Hive Master 职责全文, 工作目录说明, 附加说明)

5. 启动 Hive Master:
   set GOAL_STATE=temp/hive_xxx/goal_state.json
   start /b python agentmain.py --reflect reflect/goal_mode.py

6. 启动 Worker(由 Master 按需增加, 通常2-4个, 不超过5个):
   start /b python agentmain.py --reflect reflect/agent_team_worker.py
      --base_url http://127.0.0.1:<PORT>
      --board_key <BOARD_KEY>
      --name hive-worker-N
```

## 与单 Agent Goal Mode 的关系

```
Goal Mode (单 Agent 自驱)
  - 1个 Agent + goal_state.json + goal_mode.py
  - 有时间预算的持续改进循环
  - 适用于个人长时间优化任务

Goal Hive (多 Agent 协作)
  - Goal Mode + BBS + Workers
  - 1个 Master 调度 + N个 Worker 执行
  - 适用于需要分工的大型任务
```

## 关键设计特点

1. **零共享架构**: 所有进程通过 BBS HTTP API 通信, 不共享文件系统/内存/数据库(除 BBS 的 SQLite)
2. **SOP 即代码**: 行为完全由 SOP 文档定义并通过 prompt 注入到 LLM, 没有硬编码调度算法
3. **反射模式防浪费**: --reflect 让轻量 Python check() 决定是否唤醒 LLM, 空闲时不消耗 token
4. **解耦调度/执行**: Master 只设计不执行, Worker 只执行不调度
5. **以文件为中心**: BBS 文件上传用于传递大成果, 帖子用于信息交换
6. **失败隔离**: 单 worker 崩溃不影响系统, Master 验收后才合入核心交付物
7. **失稳信号检测**: Worker 忙而 J 不升、碎片化、功能污染等 6 种失稳状态有明确定义和恢复步骤

## 本分析对应的源码文件

- `memory/goal_hive_sop.md` - Hive 启动流程和操作规范
- `memory/goal_mode_sop.md` - Goal Mode 基础规范(时间预算+状态管理)
- `memory/goal_hive_master_duty.md` - Master 的调度控制论和工作职责
- `assets/agent_bbs.py` - BBS 公告板 HTTP 服务
- `reflect/goal_mode.py` - Master 反射脚本(check/on_done + prompt 生成)
- `reflect/agent_team_worker.py` - Worker 反射脚本(BBS 轮询接单)
- `agentmain.py` (--reflect 模式, 第239-276行) - 反射运行引擎
