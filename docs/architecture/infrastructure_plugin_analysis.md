# 深度分析: Plugin System 应该上云还是留本地？

> 追问: "为什么要把 Plugin System 搬到云端？"
> 核心: Plugin System 的归属取决于它的本质——它是谁的扩展？

---

## 1. 先看事实: Plugin 的实际能力

PluginContext 只提供三个核心能力：

| 方法 | 能力 |
|:-----|:------|
| `subscribe(topic, cb)` | 订阅MQTT主题 → 被动接收消息 |
| `publish(topic, payload)` | 发布到MQTT → 主动发送消息 |
| `get_config(key)` / `set_config(key, value)` | 读/写配置 |

**Plugin 不能做的事情：**
- 不能调用 `do_file_read` / `do_code_run` / `do_web_scan`
- 不能访问 Agent 的内部状态（dashboard, memory, working）
- 不能操作本地文件系统
- 不能调用 LLM
- 不能操作浏览器

**结论: Plugin = pure MQTT message handler。** 它不知晓本地资源，不依赖进程内状态。

---

## 2. 再溯源头: Plugin System 绑定在哪儿？

看注册链路：

```
BoardService.__init__()
  → self._client = MQTTClient()         # BoardService 创建自己的MQTT连接
  → self._plugin_mgr = PluginManager(self._client)  # PluginManager 用同一个client
    → mgr.discover_and_load()            # 发现 plugins/*.py
      → plugin.on_load(PluginContext(client, config))  # 传入MQTT client
```

**关键事实: PluginManager 是 BoardService 内部组件。** 它是 BoardService 的"扩展点"，不是 Agent 的扩展点。Plugin 的生命周期 = BoardService 的生命周期。

所以"Plugin System 上云"不是独立决策——它是 **"BoardService 上云"的自然结果**。

---

## 3. 真正的决策树

```
你决定 BoardService 放哪里？
  │
  ├─ 本地 → PluginManager 自然也本地 (当前状态)
  │
  └─ 云端 → PluginManager 随 BoardService 上云
       │
       ├─ 这是否合理？→ 合理，因为：
       │   • Plugin = pure MQTT handler，没有本地资源依赖
       │   • CuriosityBoard 在云端更合理（全局讨论板）
       │   • auto_log 在云端更合理（集中式日志）
       │
       └─ 有什么风险？→ 未来风险：
           如果 future plugin 需要访问本地资源
           （例如"检测到文件变化时MQTT通知"→这种其实是Agent做的，不是Plugin）
```

---

## 4. 一个更准确的框架: 两套扩展机制

GA 实际有两种完全不同"扩展"：

| | Board Plugin | Agent Hook/Tool |
|:----|:-------------|:----------------|
| **宿主** | BoardService (MQTT消息处理器) | GA Handler (Agent进程) |
| **能力** | subscribe/publish MQTT | file_read/code_run/LLM/浏览器 |
| **资源** | 纯网络，无本地依赖 | 本地文件/LLM/浏览器 |
| **适合** | 跨Agent逻辑、全局状态 | 单Agent能力扩展 |
| **当前例子** | auto_log, curiosity_board | 所有 do_* 方法, turn_policies |
| **上云?** | ✅ 随BoardService | ❌ 必须本地 |

**问题澄清了**: "Plugin System" 其实是 Board Plugin System。它上云是因为它附属于 BoardService，而不是因为它本身有什么上云的理由。如果把 BoardService 留在本地，Plugin System 自然也不用动。

---

## 5. 重新审视云端架构图

修正后的分层：

```
Cloud VPS (Infrastructure Layer)
  ┌─────────────────────────────────┐
  │  RMQTT Broker (消息管道)         │
  │  MariaDB (持久化)               │
  │  BoardService (业务逻辑)         │
  │    ├─ Whiteboard (共享KV)       │
  │    ├─ Scheduler (任务调度)       │
  │    └─ PluginManager (扩展)       │
  │        ├─ auto_log              │
  │        └─ curiosity_board       │
  └─────────────────────────────────┘
           ↑ MQTT over TLS

Local Machine A                  Local Machine B
  GA Agent                         GA Agent
  ├─ Agent Hooks/Tools             同左
  ├─ LLM / Browser / FS
  └─ BoardClient → 云端

Agent Hook/Tool = Agent的扩展机制 → 本地
Board Plugin    = BoardService的扩展机制 → 随BoardService上云
```

这两套机制是**正交**的，互不替代。Agent 通过 Agent Hook/Tool 扩展自身能力，通过 BoardClient 连接到云端 BoardService 获取基础设施服务。

---

## 6. 修正文档

要不要更新 `infrastructure_decoupling_brainstorm.md` 中的"Plugin System 上云"描述，加上这个分析？

