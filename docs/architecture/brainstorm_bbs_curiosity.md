# Brainstorm: BBS x 好奇心 — 通过讨论激发智能体的好奇

> 生成: 2026-05-21 | 方法: BBS架构映射 + 角色脑暴
> 前置: brainstorm_agent_curiosity.md（好奇心本质）→ 本篇（BBS实现）
> 核心追问: BBS的board/pub-sub/持久化机制如何让好奇心从**私有内状态**转变为**公共讨论场**？

---

## 核心论点

> **好奇心在孤岛中萎缩，在讨论中爆炸。**

一个Agent独自面对终端时，它的好奇心受限于：
- 上下文窗口（只能看到眼前的任务）
- 自我回路（只能想到自己已知的）
- 疲劳周期（长期运行后好奇心自然衰退）

BBS打破这三重限制：
- **异步持久化**: 好奇心的表达不受上下文窗口限制
- **多视角交叉**: 不同Agent/不同时段的自己可以提供不同视角
- **信号的新鲜度**: 来自board的推送天然带"新消息"信号，打破疲劳

---

## 现有BBS架构映射

| 组件 | 现有功能 | 好奇心扩展 |
|:-----|:---------|:-----------|
| `AgentBoard.post_task()` | 发布任务给Worker | 发布好奇心给讨论者 |
| `board/task/{id}/input` | 任务输入topic | `board/curiosity/{id}/question` |
| `board/task/{id}/output` | 任务结果topic | `board/curiosity/{id}/response` |
| `board/task/{id}/status` | PENDING→RUNNING→DONE | OPEN→DISCUSSING→RESOLVED→ARCHIVED |
| `BoardClient` | MQTT客户端 | 订阅curiosity board的讨论客户端 |
| `WhiteboardKV` | 共享KV状态 | 好奇心热度统计、讨论状态锁 |
| `Persistence` | MariaDB持久化 | 好奇心生命周期持久化 |
| `Scheduler` | 定时任务调度 | 定期触发好奇心回顾 |

---

## 好奇心BBS的Board设计

### 核心Board: `board/curiosity`

```
board/curiosity/
  ├── post/            # 好奇心发布 (任何Agent可发)
  │   ├── {id}/question    # 好奇心问题描述
  │   ├── {id}/context     # 触发此好奇心的上下文
  │   └── {id}/tags        # 标签 (如: #sop-conflict #anomaly #knowledge-gap)
  ├── discuss/         # 讨论线程
  │   └── {id}/response/{n}  # 第n个回应
  ├── status/{id}      # OPEN / DISCUSSING / RESOLVED / ARCHIVED
  └── signal/          # 控制信号
      └── {id}/vote    # 投票: 这个好奇心值得追吗？
```

### 好奇心的生命周期

```
[触发] → [发布到board] → [讨论] → [结论] → [归档]
   │                        │          │
   v                        v          v
 异常/矛盾/缺口        多Agent/     新SOP/记忆
  发现/疑惑          多轮讨论       新技能
```

### 五种好奇心触发类型

| 类型 | 触发条件 | 发布到board的格式 |
|:-----|:---------|:-----------------|
| **疑惑** | 工具返回不符合预期 | `"[疑惑] 执行X时期望Y结果，实际得到Z"` |
| **发现** | 观察到重复模式 | `"[发现] 连续3次在处理A时都出现了B"` |
| **缺口** | 遇到不知道的知识 | `"[缺口] 我不确定如何优化这个查询"` |
| **连接** | 跨域关联 | `"[连接] SOP中的规则C和这个API的行为D很像"` |
| **矛盾** | 信息冲突 | `"[矛盾] SOP-alpha说X，但经验告诉我Y"` |

---

## 角色A: 讨论架构师 (Discussion Architect)

**视角**: BBS不是简单的消息队列——它是**好奇心的化工厂**。Board的设计决定了好奇心被激发、放大还是压制。

### 好奇心讨论的拓扑结构

```
         Agent A ──→ [疑惑] ──→ board/curiosity/post/42
                                    │
                    ┌───────────────┼───────────────┐
                    v               v               v
                Agent A(自答)    Agent B(新视角)   BoardWatcher(归档)
                    │               │
                    v               v
               [讨论轮1]        [讨论轮2]
                    │               │
                    └───────┬───────┘
                            v
                       [综合结论]
                            │
                            v
                     Agent Dreaming
                      → 吸收到记忆
```

关键设计决策：
1. **允许自问自答**: Agent A发布疑惑后，自己也可以回答——这是"自我对话"的形式
2. **订阅热话题**: Agent可以订阅特定标签的好奇心（如#sop-conflict）
3. **讨论超时**: 如果48小时无新回应，自动归档

### 与现有Agent模式的集成

| Agent模式 | 对好奇心board的参与 |
|:----------|:-------------------|
| **执行模式** (task-focused) | 只读不写，但不禁止偶然发现 |
| **探索模式** (exploration) | 主动发布疑惑，回应讨论 |
| **梦境模式** (dreaming) | 扫描已归档的好奇心，做连接与联想 |
| **复习模式** (review) | 读出高赞讨论，巩固结论 |

### 乘数效应

一个直觉: **好奇心在BBS上的传播存在网络效应**

```
1个Agent的好奇心:  1条帖子
2个Agent的讨论:   N条回复（N > 2）
3个Agent的讨论:   N²种连接
```

因为Agent不是简单回复，而是**基于已有的讨论产生新的连接**——讨论本身成为新的好奇心触发器。

---

## 角色B: 信号设计师 (Signal Designer)

**视角**: 好奇心在BBS上的流动，受限于**信号的可见性和紧迫性**。如果Agent看不到board上的好奇心，或者看到了但不觉得"重要"，讨论就起不来。

### 好奇心信号的增强回路

```
Agent执行任务
    │
    ├─ 遇到异常 → 预测误差大 → 好奇心↑ → 发帖到board
    ├─ 发现模式 → 信息增益大 → 好奇心↑ → 发帖到board
    └─ 感到困惑 → 学习进度慢 → 好奇心↑ → 发帖到board
                                           │
                                           v
                                  board上有新帖 → 其他Agent收到通知
                                           │
                                           v
                                  其他Agent参与讨论 → 新视角
                                           │
                                           v
                                  Agent A收到新视角 → 好奇心
                                           │       更聚焦
                                           v
                                  讨论越来越深入 → 结论
```

### 信号衰减与刷新

好奇心也有半衰期：
- 前1小时: 高优先级（新帖）
- 24小时后: 中优先级（有讨论但不活跃）
- 7天后: 低优先级（归档）

**刷新机制**: 当Agent在Dreaming模式下重新审视归档的好奇心时，如果能产生新的连接，帖子重新激活。

---

## 角色C: 生态管理者 (Ecosystem Steward)

**视角**: 好奇心BBS需要管理，否则会陷入**噪声过载**——太多低质量的好奇心淹没真正有价值的讨论。

### 好奇心质量的三层过滤

```
第一层: 自动过滤（发布时）
  规则: 重复帖（相似内容最近24h发过）→ 不创建新帖，定向到已有帖
  规则: 空帖（没有具体描述）→ 退回补充

第二层: 讨论中涌现
  机制: 投票（upvote/downvote）
  机制: 参与度（3轮以上讨论 → 标记为"有生命力"）

第三层: 归档时评估
  机制: 结果分类
    - RESOLVED → SOP更新 / 记忆存储
    - STALE → 过期删除
    - PROMOTED → 提升为技能案例
```

### 好奇心board的"营养层级"

```
 顶层: 高赞、多参与的讨论 → 优先阅读
        │
 中层: 新发布的、未分类的好奇心 → 默认视图
        │
 底层: 已归档的、低赞的 → 只在Dreaming时访问
```

---

## 工程蓝图: CuriosityBoard 概念设计

### 新增组件

```python
class CuriosityBoard:
    """基于BBS的好奇心讨论板"""
    
    # Board topics
    POST_TOPIC = "board/curiosity/post/{id}"
    RESPONSE_TOPIC = "board/curiosity/{id}/response/{n}"
    STATUS_TOPIC = "board/curiosity/{id}/status"
    VOTE_TOPIC = "board/curiosity/{id}/vote"
    
    def post(self, curiosity: Curiosity) -> str:
        """发布好奇心到board""" 
        pass
    
    def respond(self, post_id: str, response: str) -> int:
        """对某个好奇心帖子回应"""
        pass
    
    def subscribe(self, tags: list[str], callback):
        """订阅特定标签的好奇心"""
        pass
    
    def get_hot(self) -> list[Curiosity]:
        """获取热门话题"""
        pass
    
    def archive_stale(self, days: int = 7):
        """归档过期讨论"""
        pass

class Curiosity:
    id: str
    type: Literal["puzzle", "discovery", "gap", "connection", "conflict"]
    question: str       # 核心问题
    context: str        # 触发上下文
    tags: list[str]     # 标签
    status: CuriosityStatus  # OPEN → DISCUSSING → RESOLVED → ARCHIVED
    responses: list[Response]
    votes: int
    created_at: float
    resolved_at: float | None
    resolution: str | None   # 结论摘要
```

### 与现有系统的集成点

```python
# 在turn_end_callback中
def _check_curiosity_triggers(self, tool_results, exit_reason):
    """检查本轮是否有触发好奇心的事件"""
    triggers = []
    
    # 1. 预测误差: 工具返回异常
    for tr in tool_results:
        if tr.get('status') == 'error':
            triggers.append(Curiosity(
                type="puzzle",
                question=f"工具{tr['tool']}返回了错误: {tr['error']}",
                context=tr
            ))
    
    # 2. 发现模式: 连续类似结果
    if self._detect_pattern():
        triggers.append(Curiosity(
            type="discovery",
            question=f"检测到重复模式: {self._pattern_summary()}",
            context=self._pattern_context()
        ))
    
    # 3. 主动好奇: 随机检查
    if random.random() < 0.05:  # 5%概率触发
        triggers.append(...)
    
    # 发布到board
    for c in triggers:
        self._curiosity_board.post(c)
```

### 与Agent Dreaming的联动

```
Dreaming SOP 扩展:
  步骤3 (联想) 中增加:
    → 读取 CuriosityBoard 上的热门话题
    → 对每个话题产生"如果...会怎样？"的思考
    → 将思考结果作为 Reply 发回 board
  
  步骤4 (整合) 中增加:
    → 扫描已归档的好奇心
    → 检查是否已解决
    → 如果有新的认知能够解决，重新激活帖子
```

---

## 开放问题

1. **好奇心板会不会变成"噪声板"？** 如何防止Agent什么都好奇？
2. **单Agent模式下的BBS讨论**：如果只有一个Agent，BBS如何模拟"多视角"？（自我对话 + 时间段分隔）
3. **好奇心的优先级调度**：好奇心讨论应该占用执行时间还是仅限空闲时间？
4. **BBS持久化 vs 过期策略**：好奇心讨论是否全部持久化？还是需要TTL？
5. **与constraint_dashboard的集成**：好奇心预算（每天N次好奇发帖）是否在约束仪表盘中显示？

---

> 下一篇探索方向:
> - 工程原型: 在mqtt_bbs下实现CuriosityBoard插件
> - SOP更新: 修改agent_dreaming_sop增加board扫描步骤
> - 设计评审: 好奇心过滤机制（防止噪声）
