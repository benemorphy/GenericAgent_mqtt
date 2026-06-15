# Phase 3: Goal Nexus — 实施推进方案

> 飞书桥接 + 人机异步协作
> 复杂度: 高 | 预估工期: 3-5 轮

---

## 一、架构概览

```
Feishu 飞书                          本地环境
┌──────────┐    WebHook     ┌──────────────────────┐
│ 飞书群聊  │ ←──────────→ │ feishu_bbs_bridge     │
│          │    双向        │ (已有, fsapp.py)      │
└──────────┘               └────────┬─────────────┘
                                    │ MQTT
                                    ↓
┌───────────────────────────────────────────────────┐
│              MQTT Broker (1883)                    │
└──┬───────────┬───────────┬───────────┬────────────┘
   │           │           │           │
   ↓           ↓           ↓           ↓
Board       Board       Board       Board
goal_nexus  goal_nexus  goal_nexus  goal_pulse
/review     /tasks      /response   /post
(决策点)    (被动任务)   (回复)      (Pulse广播)
   ↑                       ↑
   │                       │
   └─── goal_nexus.py ─────┘
        (reflect 模式)
```

---

## 二、组件清单与实施顺序

### Step 1: Feishu Bot MQTT 增强 (已有基础设施改造)

**已有**: `fsapp.py` + `feishu_connect_sop.md` — 已实现 Board → 飞书 和 飞书 → Board 双向

**需要增强**:

| 改造项 | 说明 | 文件 |
|:-------|:------|:-----|
| 订阅 nexus board topics | 让 bot 监听 `agent/bbs/goal_nexus/review` 和 `/tasks` | `fsapp.py` |
| 支持 @ 指定用户 | 关键决策点飞书加急通知 | `fsapp.py` |
| 格式化 nexus 消息 | 将 Board 的 JSON 渲染为飞书卡片消息 | `fsapp.py` |
| 配置映射 | 多种决策类型 → 不同飞书群聊 | `.env` 或 `nexus_config.json` |

**接入点**: 飞书 Bot 已在 `feishu_connect_sop.md` L103-114 中有 MQTT 桥接配置，需扩展 topic 订阅列表。

### Step 2: Nexus Board 配置

新增 `boards.json` 配置：

```json
{
  "goal_nexus": {
    "name": "Goal Nexus 人机协作枢纽",
    "db": "goal_nexus.db"
  }
}
```

Board `goal_nexus` 下细分 3 个消息路由：
- `agent/bbs/goal_nexus/review` — 决策点（agent → 人类）
- `agent/bbs/goal_nexus/review/response/{corr_id}` — 决策回复（人类 → agent）  
- `agent/bbs/goal_nexus/tasks` — 被动任务（人类 → agent）
- `agent/bbs/goal_nexus/response` — agent 回复（agent → 人类）

### Step 3: `reflect/goal_nexus.py` — Nexus 反射模块

核心 reflect 脚本，继承 goal_mode.py 的 check/on_done 模式。

```
reflect/goal_nexus.py
├── class GoalNexusMode
│   ├── check()          ← 继承 goal_mode 的 check，增加人类决策等待检测
│   ├── on_done()        ← 继承 goal_mode 的 on_done，增加飞书通知
│   ├── ask_human()      ← 阻塞等待人类决策
│   ├── send_feishu()    ← 通过 Board 推送消息到飞书
│   ├── suspend()        ← 保存状态 + 挂起
│   └── resume()         ← 恢复状态 + 继续
└── NexusDecision 数据类
```

**关键决策设计**:

```python
def ask_human(decision_point, options, recommendation, timeout=3600):
    """发布决策到 Board → 阻塞等待飞书回复"""
    corr_id = f"nexus_{uuid4().hex[:8]}"
    bbs.post(board="goal_nexus/review", content={
        "type": "human_review",
        "corr_id": corr_id,
        "decision": decision_point,
        "options": options,
        "recommendation": recommendation,
    })
    # 阻塞: subscribe 到 goal_nexus/review/response/{corr_id}
    result = _wait_response(corr_id, timeout)
    if result is None:
        return recommendation  # 超时兜底: 用推荐方案
    return result["choice"]
```

### Step 4: `memory/goal_nexus_sop.md` — SOP 文档

包含：
- 启动方式
- 飞书群聊配置
- 决策点预设规则
- 超时兜底策略
- 与 Sentinel/Hive 的组合用法

---

## 三、技术决策

### 决策 1: 阻塞 vs 非阻塞

| 方案 | 说明 | 选择 |
|:-----|:------|:-----|
| **阻塞(mqtt subscribe)** | agent 发布决策后 subscribe 到回复 topic，收到才继续 | **优先** — 简单可靠 |
| 非阻塞(轮询 Board) | 定期 query Board 看是否回复 | 备选 — 增加延迟+负担 |

**选阻塞**：MQTT 本身就是 pub/sub 模型，subscribe 等待是最自然的用法。超时可以降级。

### 决策 2: 飞书消息格式

| 类型 | 格式 | 示例 |
|:-----|:------|:------|
| 决策通知 | 飞书消息卡片 | "Agent 需要决定: 是否删除缓存? [确认] [拒绝]" |
| Pulse 摘要 | 文本消息 | "[Phase 3] 轮次 5/200 | 60% | 当前: 分析CI失败" |
| 任务完成 | 文本+链接 | "审查完成! 33个发现 → temp/..." |

### 决策 3: 超时兜底

| 超时时间 | 触发条件 | 兜底行为 |
|:---------|:---------|:---------|
| 5 分钟 | 决策不关键 | 用 recommendation 自动执行 |
| 30 分钟 | 决策中等重要 | 第二次推送 + 飞书 @所有人 |
| 60 分钟 | 决策高风险 | 暂停(pause) + 记录到 Chronicle 等人工处理 |

### 决策 4: 状态挂起/恢复

```
suspend():
  ├── 保存当前上下文到 Board (goal_nexus/snapshots)
  ├── 在 Pulse 发布 "SUSPENDED: 等待人类决策"
  └── agent 进入等待状态

resume():
  ├── 从 Board 查询最新 snapshot
  ├── 恢复 objective / 进度 / 产出
  ├── 在 Pulse 发布 "RESUMED: 收到人类回复"
  └── 继续 reflect 循环
```

---

## 四、实施步骤总结

| 步骤 | 组件 | 预计轮次 | 前置条件 |
|:-----|:------|:---------|:---------|
| 1 | Feishu Bot 增强 — 订阅 nexus/tasks 和 nexus/review | 1 轮 | feishu Bot 正常运行 |
| 2 | `boards.json` 添加 `goal_nexus` board | 0.5 轮 | BoardService 运行中 |
| 3 | `reflect/goal_nexus.py` — ask_human / wait_response | 1-2 轮 | Pulse + Chronicle 可用 |
| 4 | `reflect/goal_nexus.py` — suspend/resume 状态管理 | 1 轮 | Step 3 完成 |
| 5 | 飞书消息格式化 + 卡片渲染 | 1 轮 | Step 1 完成 |
| 6 | `memory/goal_nexus_sop.md` + 测试 | 1 轮 | Steps 1-5 完成 |
| 7 | 端到端集成测试 | 1 轮 | 全部完成 |

**总预估**: 约 5-7 轮

---

## 五、测试计划

| 测试项 | 覆盖内容 | 工具 |
|:-------|:---------|:-----|
| 飞书→Board 路由 | 飞书消息是否写入 nexus Board | 手动发飞书消息 |
| Board→飞书推送 | Board 新帖是否推送到飞书群 | 手动 post 到 Board |
| ask_human 阻塞 | 发布决策→等待→回复→继续 | 单元测试 + MQTT mock |
| ask_human 超时 | 超时后是否降级用 recommendation | 单元测试 |
| suspend/resume | 保存状态→恢复→不丢上下文 | 集成测试 |
| 全链路 | 飞书→Board→agent→Board→飞书 | 端到端测试 |

---

## 六、依赖清单

| 依赖 | 状态 | 说明 |
|:-----|:------|:------|
| Mosquitto (MQTT Broker) | ✅ 运行中 | 端口 1883 |
| BoardService | ✅ 运行中 | 已修复 token 列 + reply_to |
| feishu_bbs_bridge (fsapp.py) | ✅ 已部署 | MQTT 用户已配置 |
| Pulse/Chronicle | ✅ Phase 1 | 用于通知和记录 |
| Sentinel | ✅ Phase 2 | 可选 — 监控 Nexus agent 存活 |
