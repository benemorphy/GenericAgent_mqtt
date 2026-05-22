# P0 改进: 统一消息 Payload Schema

> 基于 `brainstorm_mqtt_multiagent_infrastructure.md` 的 P0实施记录
> Implemented: 2026-05-22

---

## 改进动机

脑暴识别的 P0 速赢项（共3项）:
1. **响应槽预订阅** — 已半完成（board_client.py 有 `_reply_to`，board_service.py 已支持）
2. **统一 Payload Schema** — `_build_payload` 已定义但未使用
3. **去中心化心跳** — LWT 已在 client.py 实现

本次实现: **P0.3 Payload Schema 统一** + P0.1 响应槽完善。

---

## 改动的文件

| 文件 | 改动行数(约) | 说明 |
|------|-------------|------|
| `mqtt_bbs/client.py` | +20 | 新增 `BBSClient.build_payload()` 静态方法，供全模块使用 |
| `mqtt_bbs/board_client.py` | ~+60/-50 | 6个方法全部改用 `_build_payload()` + 添加 `action` 字段 |
| `mqtt_bbs/bbs.py` | ~+30/-20 | AgentBoard 任务发布/路由分发/能力查询用信封 |
| `mqtt_bbs/whiteboard.py` | ~+10/-6 | StateKV.set()/cas() 用信封 |

---

## 统一消息信封格式

```python
BBSClient.build_payload(
    source="agent_alpha",
    corr_id="agent_alpha_a1b2c3d4",
    reply_to="v2/agent/agent_alpha/rpc/res/",
    action="register",
    # 业务字段通过 **extra 传入
    agent_id="agent_alpha",
    name="my_agent",
)
```

产出:
```json
{
  "v": 1,
  "action": "register",
  "source": "agent_alpha",
  "corr_id": "agent_alpha_a1b2c3d4",
  "reply_to": "v2/agent/agent_alpha/rpc/res/",
  "agent_id": "agent_alpha",
  "name": "my_agent"
}
```

### 字段约定

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `v` | int | Yes | 协议版本，当前为 1 |
| `action` | str | No | 操作类型: register/post/query/task_input/state_set 等 |
| `source` | str | Yes | 发送方 agent_id |
| `corr_id` | str | Yes | 请求-响应的关联 ID |
| `reply_to` | str | No | 响应槽前缀（空=用旧版 topic 模式） |
| `...extra` | any | - | 业务字段，保持向后兼容 |

---

## 各模块改动详情

### 1. client.py — 新增基类方法

```python
@staticmethod
def build_payload(source: str, corr_id: str, reply_to: str = "",
                  action: str = "", **extra) -> dict:
```

所有下游模块直接引用 `BBSClient.build_payload(...)`，不再各自构造 dict。

### 2. board_client.py — 全部请求用信封

| 方法 | action 值 |
|------|-----------|
| `register()` | `"register"` |
| `post()` | `"post"` |
| `query_posts()` | `"query"` |
| `poll()` | `"query"` |
| `count_posts()` | `"query"` |
| `list_authors()` | `"query"` |
| `upload_file()` | `"file_chunk"` |

业务字段 (`agent_id`, `name`, `token`, `content`, `params` 等) 全部通过 `**extra` 传入，**向后完全兼容**——BoardService 的 `payload.get("agent_id")` 依然正常工作。

### 3. bbs.py — 任务消息 + 能力查询

| 方法 | 信封使用方式 |
|------|-------------|
| `post_task()` | v2/task 双写时用信封包裹原始 payload |
| `post_task_routed()` | 定向分发消息用信封 |
| `query_capabilities()` | 能力查询请求用信封 |

旧 topic `board/task/{id}/input` 保持原始格式不变，确保旧版 WorkerAgent 向后兼容。

### 4. whiteboard.py — 状态变更

| 方法 | action 值 |
|------|-----------|
| `StateKV.set()` | `"state_set"` |
| `StateKV.cas()` | `"state_cas"` |

---

## 验证

4 文件全部通过 `py_compile` 语法检查，无语法错误。

```python
OK: mqtt_bbs/client.py
OK: mqtt_bbs/board_client.py
OK: mqtt_bbs/bbs.py
OK: mqtt_bbs/whiteboard.py
```

---

## 待做

1. **压测验证** — 运行 `board_stress_sop.md` 验证消息格式向后兼容
2. **Git 推送** — `scripts/git_push.py` 审计+PR
3. **P1 核心改进** — 命名空间迁移 / 过滤器链插件 / 状态空间独立化

---

## 关联文档

- `docs/architecture/brainstorm_mqtt_multiagent_infrastructure.md` — 脑暴文档
- `memory/board_stress_sop.md` — 压测 SOP
- `memory/emqtt_design_principles.md` — EMQTT 设计原则
