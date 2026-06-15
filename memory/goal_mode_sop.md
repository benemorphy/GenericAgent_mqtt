# Goal Mode SOP

## 何时使用

用户给出开放目标 + 时间预算（如"花3小时持续优化X"），且不是一次性闭环任务。

## 设置

写 `temp/goal_state.json`（或自定义路径）：

```json
{
  "objective": "用户原话目标",
  "budget_seconds": 10800,
  "start_time": <time.time()>,
  "turns_used": 0,
  "max_turns": 200,
  "status": "running",
  "done_prompt": "__GOAL_COMPLETE__"
}
```

- `budget_seconds`：最少 3 小时（10800），按用户要求调整
- `max_turns`：防空转上限，一般 200 够用
- `status`：必须为 `"running"`
- `done_prompt`：**默认 `__GOAL_COMPLETE__`**，agent 完成目标后自动回复此标记触发终止

## 启动

```bash
# 后台启动（默认路径 temp/goal_state.json）
start /b python agentmain.py --reflect reflect/goal_mode.py

# 自定义路径（多实例）
set GOAL_STATE=temp/goal_xxx.json && start /b python agentmain.py --reflect reflect/goal_mode.py

# 指定模型
set GOAL_STATE=temp/goal_xxx.json && start /b python agentmain.py --reflect reflect/goal_mode.py --llm_no 1
```

## 阻塞等待完成（Pulse 监听）

启动后可调用 `scripts/goal_wait.py` 阻塞等待 Goal 完成：

```bash
# 等默认实例完成（双通道: Pulse + state轮询）
python scripts/goal_wait.py

# 设超时（秒）
python scripts/goal_wait.py --timeout 3600
```

返回码：
- `0`：goal 完成（done_prompt 触发 或 预算耗尽）
- `1`：超时

## 自动终止机制（默认启用）

```
agent 回复末尾含 "__GOAL_COMPLETE__"
  ↓
on_done() 检测到 done_prompt 匹配
  ├── status → "done"
  ├── Pulse → agent/bbs/goal_pulse/post (msg_type=goal_complete)
  ├── Chronicle → 写入最终记录
  └── 下一轮 check() 检测 status!="running" → return '/exit' → 实例退出
  ↓
goal_wait.py 收到 Pulse → 返回码 0 → 启动方知完成
```

## 查看进度

- **Pulse 实时广播**：`mosquitto_sub -t "agent/bbs/goal_pulse/post" -h localhost`
- **状态文件**：`cat temp/goal_state.json` 看 `turns_used` / `status`
- **产出**：查看 `temp/goal_mode_optimization*/` 下文件

## 停止（手动）

若需手动停止，设置 `temp/goal_state.json` 中 `status` 为 `"done"`，或杀进程。
