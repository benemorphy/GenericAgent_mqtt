# Deep Analysis: 基础设施上云方案 (补充维度)

> 日期: 2026-05-22 | 补充分析: 全面深化未被覆盖的5个关键维度
> 前置: infrastructure_decoupling_brainstorm.md + infrastructure_plugin_analysis.md

---

## 维度1: BoardClient WAN延迟模式 (最大工程风险）

当前 BoardClient 的核心模式是 **publish + 同步阻塞等待**：

```python
# board_client.py 核心请求模式
def _request(self, topic, payload, timeout=30):
    corr_id = uuid4()
    event = threading.Event()
    self._pending[corr_id] = event      # 注册等待
    self._client.publish(topic, {**payload, "corr_id": corr_id})  # MQTT pub
    event.wait(timeout)                  # 同步阻塞 ← 关键延迟点
    return self._results.pop(corr_id, None)
```

### 延迟模型

| 阶段 | 局域网 (目前) | 广域网 (VPS) |
|:-----|:-------------|:-------------|
| MQTT pub -> Broker | <1ms | 20-50ms |
| Broker -> BoardService | <1ms | <1ms (同在VPS) |
| BoardService处理 | <1ms | <1ms |
| BoardService -> Broker | <1ms | <1ms |
| Broker -> Agent | <1ms | 20-50ms |
| **单次往返** | **~2ms** | **~40-100ms** |

### 对Agent感知-思考-行动循环的影响

Agent每轮会发起多次MQTT请求:

| 操作 | 请求次数 | 局域网 | 广域网 |
|:-----|:--------:|:------:|:------:|
| 发布任务到Board | 1 | 2ms | 50ms |
| 查询任务结果 | 1 | 2ms | 50ms |
| 获取Whiteboard | 1 | 2ms | 50ms |
| 查询新帖推送 | 1 | 2ms | 50ms |
| 好奇心发布(P3) | 1 | 2ms | 50ms |
| **合计/轮** | **~5次** | **~10ms** | **~250ms** |

**结论**: 250ms/轮的MQTT延迟在Agent的"思考时间"(通常3-30秒)面前可忽略。
但有一个例外——**好奇心发布和讨论**是高频率的额外操作，需要考虑批量化。

### 真正的延迟风险: 不是MQTT，是LLM

```
Agent一轮:
  ├─ LLM推理 (3-30秒) ← 真正瓶颈
  ├─ MQTT请求 (10-250ms) ← 可忽略
  ├─ 本地IO (file_read等, 1-100ms)
  └─ 浏览器 (web_scan等, 100-500ms)
```

**MQTT延迟在LLM推理时间面前低2-3个数量级**。所以WAN延迟不是问题。

### 但有一个暗坑: timeout超时

```
局域网: event.wait(timeout=30) → 2ms后收到响应 → 正常
广域网: event.wait(timeout=30) → 50ms后收到响应 → 正常
但:    event.wait(timeout=30) → 网络抖动5秒 → 也能等
     → 但某些场景timeout设置得太小（如心跳检测5秒）→ 误判
```

**需要审查所有 `_request` 调用的 timeout 参数**，确保WAN下不会误超时。

---

## 维度2: 多Agent协作模式 — 云端解锁的能力

当前单机模式下, 多Agent只能在同一台机器上跑。云端后解锁:

### 2.1 跨机器好奇心讨论 (已有基础)

```
Agent A (上海): 发现文件异常 → post好奇到云端Board
Agent B (北京): 订阅Board → 看到好奇 → 回复: "我也遇到过, 试试X方案"
Agent A: 收到回复 → 应用方案
```

**已有基础**: P2的CuriosityBoard已经在云端（如果BoardService在云端）。
**新问题**: Agent B如何"在空闲时"订阅和回复？
→ 需要Agent B在Dreaming模式或任务间隙扫描Board。

### 2.2 任务委托模式

```
Agent A: 当前任务需要Python数据分析能力
       → 发布Task到云端Board (capability: "python_analyst")
Agent B (专职数据分析Worker): 认领任务 → 执行 → 返回结果
Agent A: 收到结果 → 继续主任务
```

**已有基础**: WorkerAgent + capability matching 已存在。
**新价值**: WorkerAgent可以和MasterAgent在不同的机器上。

### 2.3 共享记忆/经验库

```
Agent A: 学会了一个新技巧 → 写入云端Whiteboard
Agent B: 启动时读取Whiteboard → 获取技巧 → 避免重复踩坑
```

**挑战**: Whiteboard已有KV持久化，但"经验同步"需要结构化。
**可能方案**: 用Board+CuriosityBoard作为共享记忆的管道。

### 2.4 监督者模式

```
Supervisor Agent (云端常驻):
  ├─ 监控所有Agent的心跳 (MQTT Last Will)
  ├─ Agent死亡 → 重新指派任务
  ├─ Agent异常 → 重启指令
  └─ 资源分配 → 平衡负载
```

**现状**: 没有Supervisor。但RMQTT的Last Will机制可以检测断连。

---

## 维度3: 数据隐私泄露分析

### 通过MQTT暴露的数据

| 数据类型 | 包含什么 | 敏感度 | 泄露风险 |
|:---------|:---------|:------|:---------|
| 任务输入/输出 | 用户问题、文件内容、代码 | ⚠️ 高 | 需TLS加密传输 |
| 好奇心信号 | 文件名、代码片段、Web页面内容 | ⚠️ 中 | 含文件名和部分内容 |
| Board帖子 | 讨论内容、分析结论 | ⚠️ 中 | Agent之间的交流 |
| Whiteboard | 共享状态、学习记录 | ⚠️ 中 | 团队级共享数据 |
| 工具调用日志 | file_read路径、code_run代码 | ⚠️ 高 | 暴露用户操作内容 |
| 心跳/状态 | Agent在线/离线 | ✅ 低 | 仅元数据 |

### 隐私边界

```
Agent进程内 (本机, 安全的):
  ├─ LLM推理 (Prompt/Response) ← 永远不会离开本机
  ├─ 文件内容 (file_read返回值) ← 只在Agent内存中
  └─ 浏览器状态 (web_scan结果) ← 只在Agent内存中

通过MQTT发往云端 (需TLS):
  ├─ 任务元数据 (capability, board, status)
  ├─ 好奇心信号 (类型、摘要、文件名)
  ├─ Board讨论 (用户发起的话题)
  └─ Whiteboard KV (学习到的经验)
```

**关键原则**: Agent只把"总结/摘要"发到MQTT，**原始内容**（完整文件、完整对话）留在本地。

当前实现是否符合？检查:

1. 好奇心信号: `CuriositySignal.reason` 包含摘要而非原文 → ✅ 安全
2. Board帖子: `content` 是用户写的 → ⚠️ 用户控制
3. 任务输入: AgentBoard.post_task() 的 `input` → ⚠️ 可能包含敏感信息
4. Whiteboard: 手动更新的key-value → ⚠️ Agent自行控制写入什么

**建议**: 增加一个 `--privacy-level` 配置:
```
privacy-level: local        # 全本地, 不连云端 (当前模式)
privacy-level: metadata     # 只传元数据, 不传内容 (推荐云端模式)
privacy-level: full         # 全部传输 (自建VPS或完全信任环境)
```

---

## 维度4: Agent生命周期管理

### 当前(本地)的生命周期

```
1. 启动Agent → 2. 初始化BoardClient (连接127.0.0.1:1883)
3. 注册到Board → 4. 等待/执行任务
5. 用户关闭窗口 → 6. BoardClient断连 → 7. 进程退出
```

### 云端后的生命周期

```
Agent启动:
  1. 加载本地配置 (密钥, endpoint)
  2. BoardClient尝试连接 VPS:8883 (TLS)
     ├─ 成功 → 正常流程
     └─ 失败 → 降级模式 (本地lite Board)
  3. 注册到云端Board (含capability + 身份)
  4. Board分配agent_id (持久化)
  5. 设置Last Will (RMQTT自动检测断连)
  6. 开始执行任务

Agent运行中:
  7. 每轮MQTT交互 (publish/wait)
  8. 如果网络断开 → BoardClient自动重连 (已有重连机制)
  9. 重连后: 拉取离线期间错过的消息

Agent退出:
  10. 正常退出: 发送offline信号 → Board标记离线
  11. 异常崩溃: RMQTT Last Will触发 → Board标记离线
  12. 其他Agent看到offline → 不分配任务给离线Agent
```

### RMQTT Last Will 机制

MQTT 5.0 支持 Last Will: Agent连接时设置一个"遗嘱消息", 当Broker检测到Agent断连时自动发布该消息。这比心跳检测更可靠——不需要Agent主动发心跳。

```python
# 伪代码: Agent连接时设置Last Will
client = MQTTClient(agent_id)
client.set_will(
    topic=f"agent/{agent_id}/status",
    payload={"status": "offline", "last_seen": timestamp},
    qos=2,
    retain=True
)
```

### Agent身份模型

云端后，每个Agent需要唯一身份:

```yaml
# agent_a_identity.yaml
agent_id: "home_pc_01"
group: "personal"
capabilities: ["python", "web", "file_analysis"]
jwt: "eyJ..."  # 从agent.env读取
```

```yaml
# agent_b_identity.yaml
agent_id: "vps_worker_01"
group: "workers"
capabilities: ["python", "data_analysis"]
jwt: "eyJ..."
```

**身份管理的关键问题**:
- 谁签发JWT？→ 部署BoardService时生成CA，每个Agent发放独立Token
- 如何撤销Agent身份？→ Token过期或加入黑名单
- Agent可以自注册吗？→ 可以，但需要管理员审批

---

## 维度5: 网络分区与故障模型

### 所有可能的故障模式

| 故障 | 现象 | 影响 | 恢复 |
|:-----|:------|:------|:------|
| VPS宕机 | 所有Agent连不上Broker | Agent集体降级 | VPS恢复后重连 |
| 网络中断 | Agent断连, 其他Agent正常 | 单个Agent降级 | 自动重连 |
| 云服务商故障 | VPS网络不可达 | 全部降级 | 等待云商修复 |
| DNS解析失败 | Agent找不到Broker地址 | 启动失败 | 用IP替代 |
| TLS证书过期 | 连接被拒绝 | 启动失败 | 自动续签 |
| MariaDB满载 | BoardService响应慢 | 全部变慢 | 扩展数据库 |
| RMQTT OOM | Broker崩溃 | 全部断连 | 自动重启 |

### 降级策略详细

```

Agent正常模式:
  连云端Broker → 全功能

Agent检测到连接失败:
  ├─ 第1次重试 (3秒后) → 成功? 继续 失败? 
  ├─ 第2次重试 (9秒后) → 成功? 继续 失败?
  ├─ 第3次重试 (27秒后) → 成功? 继续 失败?
  └─ 进入降级模式:
       ├─ 创建本地LiteBoard (内存级, 无持久化)
       ├─ 日志写本地文件 (等恢复后同步)
       ├─ 显示黄色警告 (UI通知用户)
       ├─ 继续执行当前任务 (不中断)
       └─ 每60秒重试连接

网络恢复:
  ├─ Agent检测到Broker可达
  ├─ 重连云端Broker
  ├─ 同步离线期间的日志/任务状态
  ├─ 关闭LiteBoard
  └─ 恢复正常模式
```

### 脑裂保护 (Split-brain)

如果Agent A的网络断开但以为自己还在线:

- **Agent A** 认为: "我还有连接, 继续执行"
- **云端** 认为: "Agent A 已离线"
- **后果**: 如果Supervisor重新分配了任务给Agent B, 两个Agent可能做同一件事

**保护措施**:
1. **Last Will**: Agent断连后Broker自动发布offline, 其他Agent看到后知道它离线
2. **乐观锁**: BoardService的任务分配用version/timestamp, 避免重复分配
3. **幂等设计**: 任务处理应该是幂等的 (多次执行同一任务结果相同)

---

## 汇总: 风险评估

| 维度 | 风险等级 | 应对 |
|:-----|:--------|:------|
| MQTT WAN延迟 | ✅ 低 (被LLM时间淹没) | 审查timeout参数 |
| 多Agent协作 | ✅ 低 (已有基础) | 增加Dreaming扫描Board |
| 数据隐私 | ⚠️ 中 | 加privacy-level配置, 摘要代替原文 |
| Agent生命周期 | ✅ 低 (Last Will+重连) | 实现身份管理 |
| 网络分区 | ⚠️ 中 | 降级模式 + 幂等设计 |

---

> 下一步: 可以基于这些分析更新 infrastructure_decoupling_brainstorm.md 的风险评估部分。
> 或者直接进入实证: 阶段1——买VPS, 部署RMQTT, 改MQTT_HOST验证连接。
