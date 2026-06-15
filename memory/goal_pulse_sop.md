# Goal Pulse / Goal Chronicle SOP

> 基于 MQTT BBS 的实时状态广播与持久化编年史
> 前置条件: Mosquitto Broker 运行中 (localhost:1883), BoardService 运行中 (8000)

---

## 概述

| 模式 | 解决的问题 | 原理 |
|:-----|:----------|:-----|
| **Goal Pulse** | goal mode 执行时用户只能等最终报告，看不到中间过程 | 每轮完成时通过 MQTT BBS 广播脉冲消息到 `board/goal_pulse` |
| **Goal Chronicle** | 每次 goal session 独立，上次发现不能用于下次 | 启动时查询 `board/goal_chronicle` 的历史记录，执行时持续存储决策点 |

## 架构

```
goal_mode.py  (reflect loop)
    │
    ├── init() → goal_bbs.bbs_init()
    │                ├── connect MQTT broker
    │                ├── register to board=goal_pulse
    │                └── bbs_chronicle('query') ← 查询历史
    │
    ├── check() → 返回 prompt
    │                └── bbs_pulse('turn_start')
    │
    └── on_done() → 处理结果
                     ├── bbs_pulse('turn_complete')  ← 实时广播
                     └── bbs_chronicle('store')      ← 持久化
```

## 降级策略

BBS 不可用时（MQTT broker 未启动 / BoardService 未运行 / 导入失败），
goal_bbs 模块静默降级，goal_mode.py 退化为原始文件模式。

```
bbs_init() → try:
    BoardClient.connect()  ← 失败则 _enabled=False, 返回 False
               ↓
on_done() → if _enabled: post_pulse()  ← 跳过
               else: 不执行任何操作
```

## Pulse Board 消息格式

所有脉冲消息发布到 Board `goal_pulse`，格式：

```json
{
  "v": 1,
  "type": "turn_complete | turn_start | goal_started | wrapping_up | goal_complete",
  "agent": "goal_hostname_pid_timestamp",
  "timestamp": 1748736000.0,
  "turn": 5,
  "focus": "审计代码错误处理路径",
  "progress": "60%",
  "remaining_min": 24.5
}
```

## Chronicle Board 消息格式

编年记录发布到 Board `goal_chronicle`，格式：

```json
{
  "v": 1,
  "type": "chronicle_entry | goal_summary",
  "agent": "goal_hostname_pid_timestamp",
  "timestamp": 1748736000.0,
  "entry": "Turn 5: 发现gateway_structure_design.md中3处未处理的异常...",
  "turn": 5,
  "phase": "progress | start | wrap_up | complete"
}
```

## 观察进度

### 订阅脉冲流（实时监控）

```python
# 订阅所有 pulse 消息
from Mqtt_bbs_client.board_client import BoardClient

with BoardClient("observer", board="goal_pulse") as bbs:
    bbs.register("observer")
    
    def on_post(post):
        data = json.loads(post["content"])
        print(f"[{data['type']}] Turn {data.get('turn')}: {data.get('focus', '')}")
    
    bbs.subscribe_posts(on_post)
    input("按 Enter 退出...")
```

### 查询编年史

```python
from Mqtt_bbs_client.board_client import BoardClient

with BoardClient("reader", board="goal_chronicle") as bbs:
    bbs.register("reader")
    posts = bbs.query_posts(limit=50)
    for p in posts:
        print(f"  [{p['created_at']}] {p['content'][:100]}")
```

## 启动示例

```bash
cd /d D:\open_claw_agent\Beneh\GA

# 创建 goal_state.json（含目标+预算）
# ...

# 启动（自动启用 Pulse + Chronicle）
start /b python agentmain.py --reflect reflect/goal_mode.py
```

Pulse/Chronicle 自动启用，无需额外参数。BBS 不可用时自动降级。
