# Goal Mode 移植实现会话记录

日期: 2026-06-01

## 背景

将 `D:\00synchronize\GenericAgent`（源项目）的 Goal Mode 5 层架构移植到 `D:\open_claw_agent\Beneh`（Beneh 项目）。

## 关键发现

### 源项目架构（5 层）

| 层 | 组件 | 功能 |
|----|------|------|
| L1 | agentmain.py reflect 循环 | 轮询引擎，INVERVAL=3s，check()→inject→on_done |
| L2 | reflect/goal_mode.py | 状态机，goal_state.json 驱动 |
| L3 | memory/goal_mode_sop.md | 启动 SOP |
| L4 | memory/goal_hive_sop.md + goal_hive_master_duty.md | 多 Worker 协作协议 + 编排哲学 |
| L5 | assets/agent_bbs.py (HTTP BBS) | 进程间通信 |

### Beneh 项目差异

| 方面 | 源项目 | Beneh |
|------|--------|-------|
| BBS 协议 | HTTP BBS (agent_bbs.py) | MQTT BBS (Mqtt_bbs_server + Mqtt_bbs_client) |
| Worker 模式 | agentmain.py + agent_team_worker.py | mqtt_agent_runner.py (MQTT WorkerAgent) |
| reflect 循环 | 存在 | **缺失**（核心缺失） |
| goal_mode.py | 完整 | 缺 done_prompt |
| goal_hive_sop.md | 完整 | 缺失 |
| goal_hive_master_duty.md | 完整 | 缺失 |

## 实施记录

### Step 1: agentmain.py 添加 --reflect 循环

文件: `GA/agentmain.py` (+50 行)

改动:
- 新增 `--reflect SCRIPT` 参数 + `parse_known_args()` + `_reflect_args`
- 新增完整反射轮询循环（热重载、INTERVAL、超时、log 记录、on_done 回调）
- 新增 `from datetime import datetime`

代码位置: `__main__` 中 Subagent 模式之后、MQTT 模式之前

### Step 2: goal_mode.py 同步 done_prompt

文件: `GA/reflect/goal_mode.py` (3 处改动)

- BUDGET_LIMIT_PROMPT 模板末尾添加 `{done_prompt}` 占位符
- format() 调用添加 `done_prompt=state.get('done_prompt', '')`

### Step 2b: goal_mode_sop.md 更新

文件: `GA/memory/goal_mode_sop.md`

- JSON 示例添加 `"done_prompt": ""` 字段

### Step 3: MQTT 适配 goal_hive_sop.md（新文件）

文件: `GA/memory/goal_hive_sop.md` (1717 bytes)

关键适配:
- HTTP BBS 启动 → MQTT Broker + BoardService
- HTTP POST/GET 帖子 → MQTT topic 发布/订阅
- `--base_url` + `--board_key` → `--broker_host` + `--broker_port`
- Worker 启动: `python -m Mqtt_bbs.mqtt_agent_runner`

### Step 4: goal_hive_master_duty.md 复制

文件: `GA/memory/goal_hive_master_duty.md` (9581 bytes)

直接复制（协议无关，控制理论编排哲学）

### Step 5: L1 索引更新

文件: `GA/memory/global_mem_insight.txt`

- 添加 `goal_hive_sop(Hive多Worker)` 和 `goal_hive_master_duty(Master调度)`

## 已推送

PR #163 → commit `9151d87` (squash-merge to main)

7 files changed, 230 insertions(+), 8 deletions(-)

## 验证

### 基础 Goal Mode（单 agent）

```bash
cd D:\open_claw_agent\Beneh\GA
# 创建 goal_state.json
# 启动
set GOAL_STATE=temp/goal_xxx.json
python agentmain.py --reflect reflect/goal_mode.py
# 或指定不同模型
set GOAL_STATE=temp/goal_xxx.json && python agentmain.py --reflect reflect/goal_mode.py --llm_no 1
# 停止：杀进程
# 进度：读 goal_state.json 的 turns_used / status
```

### Hive Mode（多 worker）

```bash
cd D:\open_claw_agent\Beneh
# 1. 启动 MQTT Broker（如未启动）
rmqtt start

# 2. 启动 BoardService
python -m Mqtt_bbs_server.board_service

# 3. 按 goal_hive_sop.md 启动 Hive
```
