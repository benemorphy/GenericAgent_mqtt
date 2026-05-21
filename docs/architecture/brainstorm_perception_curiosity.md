# Brainstorm: 环境感知中的好奇心保持

> 生成: 2026-05-21 | 方法: GA感知通道映射 + 3角色脑暴
> 前置: brainstorm_agent_curiosity.md（好奇心本质）→ brainstorm_bbs_curiosity.md（BBS讨论）→ 本篇（感知中的好奇）
> 核心追问: Agent在感知环境时，如何保持"好奇"而不陷入"麻木扫描"或"分析瘫痪"？

---

## GA的六条感知通道

| 通道 | 工具 | 当前感知模式 | 问题 |
|:-----|:-----|:------------|:-----|
| **文件系统** | code_run(dir), file_read, scan_files | 精确查询/列表 | 只查指定内容，从不"四处看看" |
| **Web/浏览器** | web_scan, web_execute_js | 精确扫描指定tab | 不扫描"无关"页面 |
| **MQTT/BBS** | subscribe, watch, WhiteboardKV | 被动订阅/轮询 | 只收已订阅信号 |
| **视觉/UI** | gui_vision, step_detector | 截图+OCR | 仅按指令截图 |
| **内部状态** | memory读/写, metacognition | 读取记忆+分析 | 只读需要的部分 |
| **执行环境** | code_run(python/ps) | 按需执行 | 不探索系统状态 |

**核心问题**: Agent的感知完全是**指令驱动的**——它只感知它被命令去感知的东西。没有自发的"因为好奇而看看"。

---

## 角色A: 注意力生态学家 (Attention Ecologist)

**视角**: 好奇心在感知中的作用不是"更多的感知"，而是**更好的注意力分配**。

### 注意力的三种模式

| 模式 | 感知范围 | 好奇心水平 | 适用场景 |
|:-----|:---------|:----------|:---------|
| **聚焦模式** (Spotlight) | 窄而深 | 低(压制好奇) | 执行精确任务 |
| **扫描模式** (Scanlight) | 宽而浅 | 高(激发好奇) | 环境探索/空闲 |
| **监听模式** (Candlelight) | 被动接收 | 中等 | 等待信号/BBS |

GA目前**只有聚焦模式**——所有感知调用都是任务驱动的精确操作。缺少扫描模式。

### 扫描模式的 Curiosity Triggers

在扫描过程中，以下信号应该"点亮"注意力：

```
扫描信号树:

正在扫描 /tools 目录...
  ├─ 看到陌生文件: "这个文件我没见过" → [好奇] 阅读它
  ├─ 看到大文件: "这个文件为什么这么大" → [好奇] 检查大小
  ├─ 看到修改时间: "这个文件昨天改了" → [好奇] 谁改的?
  ├─ 看到重复模式: "这些文件命名很相似" → [好奇] 是什么模式?
  └─ 看到异常: "这个文件在错误的位置" → [好奇] 为什么会在这?
```

### 好奇-感知回路

```
Agent执行任务
    │
    ├─ 感知指令: "检查config.py" 
    │     │
    │     ├─ 聚焦: 读config.py内容 ✓
    │     ├─ 扫描(侧目): "目录下还有.env.example" → [好奇标记]
    │     └─ 扫描(侧目): "config.py和config_dev.py很像" → [好奇标记]
    │
    └─ 感知结果 + 好奇标记 → 存入"待探索列表"
```

关键设计: **好奇标记不打断当前任务**，只记录到待探索列表，在空闲/Dreaming时处理。

---

## 角色B: 微观-宏观辩证法家 (Micro-Macro Dialectician)

**视角**: 环境感知发生在两个层面——微观（当前任务）和宏观（系统全局）。好奇心在这两个层面上的表现完全不同。

### 微观好奇心: 当前感知中的"为什么"

在每次`file_read`或`web_scan`返回时，Agent可以问：
- "为什么这个文件在这个位置？"（上下文好奇）
- "这个结果和我预期的一样吗？"（预测误差）
- "这个信息能和什么连接？"（连接好奇）

**实现方式**: 在`do_file_read` / `do_web_scan` 等感知工具的返回值后面，加一个"好奇钩子"

```python
def do_file_read(self, args, response):
    # ... 现有逻辑 ...
    content = result.content
    
    # 好奇钩子: 检查是否有预测误差
    if hasattr(self, '_constraint_dashboard'):
        self._check_curiosity_triggers_for_file(path, content)
    
    return result
```

### 宏观好奇心: 系统层面的"变化检测"

GA不知道它在运行的环境中发生了什么变化：
- 文件被修改了 → 不知道
- 新进程启动了 → 不知道
- BBS上有新消息 → 知道（已订阅）
- memory被更新了 → 知道（写入时

宏观好奇心的实现：**定期快照 + 差异检测**

```python
# 每个任务开始时或空闲时
def scan_environment_drift(self):
    """检测环境变化"""
    snapshots = {
        "file_tree": self._snapshot_file_tree(),
        "memory_index": self._snapshot_memory(),
        "bbs_topics": self._snapshot_bbs(),
        "processes": self._snapshot_processes(),
    }
    diffs = compare_with_last_snapshot(snapshots)
    for d in diffs:
        if d.significance > THRESHOLD:
            self._curiosity_board.post(Curiosity(
                type="discovery",
                question=f"环境变化: {d.description}",
                context=d
            ))
```

### 微观与宏观的切换

```
时间轴:
  │
  ├─ 微观(任务中): 感知 → 好奇→标记 → 继续任务
  │      │
  │      └─ 标记积累到 N 个 → 触发微观→宏观切换信号
  │
  ├─ 切换点: "我有3个好奇标记未处理"
  │
  └─ 宏观(休闲时): 处理好奇标记 + 环境扫描
         │
         └─ 产生新的任务方向 → 进入新的微观任务
```

---

## 角色C: 感知设计师 (Perception Architect)

**视角**: 每个感知工具都应该有一个"好奇模式"——不仅返回请求的数据，还返回"值得好奇的东西"。

### 感知工具的好奇扩展

**1. file_read 的好奇扩展**

```
当前: file_read("config.py") → 返回内容
好奇:  file_read("config.py") → 返回内容 + {
    "好奇信号": [
        {"type": "related_file", "path": "config_dev.py", "reason": "命名相似"},
        {"type": "size_anomaly", "path": "config.py", "size": 500KB, "reason": "比上次大了3倍"},
        {"type": "recent_change", "path": "config.py", "mtime": "2026-05-21", "reason": "今天修改过"}
    ]
}
```

**2. web_scan 的好奇扩展**

```
当前: web_scan() → 返回页面HTML
好奇:  web_scan() → 返回页面HTML + {
    "好奇信号": [
        {"type": "new_tab", "reason": "有新打开的tab: arXiv论文"},
        {"type": "page_changed", "reason": "该页面DOM结构与上次不同"},
    ]
}
```

**3. code_run(dir) 的好奇扩展**

```
当前: code_run("dir") → 文件列表
好奇:  code_run("dir") → 文件列表 + {
    "好奇信号": [
        {"type": "new_file", "name": "new_script.py", "reason": "未跟踪的新文件"},
        {"type": "missing_file", "name": "old_script.py", "reason": "上次在但这次不在"},
    ]
}
```

### 好奇信号的统一格式

```python
@dataclass
class CuriositySignal:
    type: Literal["anomaly", "pattern", "new", "missing", "change", "connection"]
    source: str           # 哪个感知工具产生的
    target: str           # 触发好奇的对象
    reason: str           # 为什么好奇
    severity: float       # 0-1, 好奇程度
    context: dict         # 额外上下文
```

### 好奇信号的衰减与优先级

```
优先级 = severity * attention_decay(t) * task_relevance

severity: 信号本身的强度（0-1）
attention_decay(t): 随时间衰减（半衰期~1小时）
task_relevance: 当前任务的相关性

只有优先级 > THRESHOLD 的信号才会在当前任务的感知中展示
其他信号存入待探索列表
```

---

## 与现有系统的集成

### 集成到 ConstraintDashboard

扩展约束仪表盘，增加感知状态：

```
[CONSTRAINT DASHBOARD]
  ├─ 轮次: #6
  ├─ 失败预算: 0/3
  ├─ 工具调用: 5次 (本轮: 2)
  ├─ 时间: 1m23s / 5m0s
  ├─ 感知好奇: 3个待探索标记  ← 新增
  └─ 环境漂移: 检测到2处变化  ← 新增
```

### 集成到 AgentDreaming

在 Dreaming 的"联想"阶段，扫描待探索的好奇标记：

```
Dreaming SOP 扩展:
  步骤3 (联想):
    → 读取 curiosity_pending_list
    → 对每个标记: 搜索记忆中有没有相关信息
    → 如果有连接: 产生洞察
    → 如果没有: 在 BBS CuriosityBoard 上发帖
```

### 集成到 BBS CuriosityBoard

感知中产生的好奇标记 → 自动发帖到 CuriosityBoard：

```python
# 在感知工具返回时
signal = CuriositySignal(...)
if signal.severity > 0.7:  # 高优先级
    self._curiosity_board.post(Curiosity(
        type=signal.type,
        question=signal.reason,
        context={"source": signal.source, "target": signal.target}
    ))
else:  # 低优先级
    self._pending_curiosities.append(signal)
```

---

## 开放问题

1. **感知开销**: 好奇信号检测会增加每次感知操作的延迟（额外的stat/ls/对比）。如何设计在"足够快"和"足够好奇"之间平衡？
2. **假阳性**: 如果文件大小变化但只是正常更新，Agent会被不必要的好奇心干扰。如何过滤无意义的变化？
3. **用户视角**: 用户是否应该看到Agent的"好奇标记"？还是只看到最终的行动？
4. **安全边界**: Agent在好奇驱动下感知到不该感知的内容（如密钥文件）怎么办？
5. **好奇与疲劳**: 如果环境没有变化，Agent的好奇信号会持续衰减——这是好事（避免噪声）还是坏事（变得麻木）？

---

> 下一篇探索方向:
> - 工程实验: 给 file_read / code_run(dir) 添加好奇心钩子
> - 设计评审: 感知好奇信号的优先级算法
> - SOP更新: 修改 agent_dreaming_sop 增加 pending_curiosities 扫描
