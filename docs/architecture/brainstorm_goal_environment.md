# Multiple Agents Brainstorm: Goal-Aimed Agent + Environment Sense

> Generated: 2026-05-22
> Context: 基于现有 goal_mode.py / autonomous_operation_sop.md / dream_engine / vision_sop 的架构演进分析

---

## 一、现状评估

### Goal-Aimed Agent 现状

| 组件 | 当前能力 | 缺失 |
|------|---------|------|
| `reflect/goal_mode.py` | 扁平循环：读 state → 生成 prompt → agent 执行 → 重复 | 无目标分解；无子目标管理；无进展评估 |
| `memory/goal_mode_sop.md` | 设置预算/轮次上限、收口逻辑 | 无目标结构；无中间里程碑 |
| `memory/autonomous_operation_sop.md` | TODO 队列 + 轨迹录制 | TODO=平面列表，无优先级/依赖/分类 |
| `tools/dream_engine.py` | 事后记忆消化 + 跨域联想 | 与主动目标追求脱钩 |

**核心问题**: 当前 Agent 是**反应式**的——"收到任务 → 执行 → 报告完成"。没有真正的**目标驱动**——即"我有一个目标，主动决定下一步做什么来实现它"。

### Environment Sense 现状

| 组件 | 当前能力 | 缺失 |
|------|---------|------|
| `memory/vision_sop.md` | 按需截图+窗口枚举 | 无持续感知；无环境模型 |
| subagent 文件探测 | file_read + glob | ad-hoc，无结构化抽象 |
| MQTT 心跳 | node/{id}/heartbeat 活性 | 仅限于 agent→broker，不是 agent→环境 |
| `memory/procmem_scanner_sop.md` | 进程内存扫描 | 特定场景，非通用 |

**核心问题**: 环境感知是**ad-hoc 的**——Agent 每次从零探测环境，没有持久的环境模型，无法检测变化、无法推理环境状态。

---

## 二、Goal-Aimed Agent 架构方案

### 方案 A: 层次化目标分解 (Hierarchical Goal Network)

```
Goal "优化性能"
  ├── Subgoal "识别瓶颈" [ACTIVE]
  │    ├── Subtask "CPU 性能采样" [DONE]
  │    └── Subtask "内存分析" [PENDING]
  ├── Subgoal "优化瓶颈" [BLOCKED by "识别瓶颈"]
  │    ├── Subtask "修改代码" [PENDING]
  │    └── Subtask "验证改进" [PENDING]
  └── Subgoal "确认优化效果" [BLOCKED by "优化瓶颈"]
       └── Subtask "回归测试" [PENDING]
```

**数据结构**:
```python
class GoalNode:
    id: str                    # goal_001
    description: str           # "识别性能瓶颈"
    status: GoalStatus         # PENDING | ACTIVE | BLOCKED | COMPLETED | FAILED
    priority: int              # 1-5
    parent: Optional[str]      # parent goal id
    depends_on: list[str]      # 依赖的其他 goal id
    milestones: list[Milestone]  # 进展里程碑
    created_at: float
    updated_at: float
```

**存储位置**: `v2/state/goal/{agent_id}/{goal_id}` (StateKV MQTT topic)

**优势**: 
- 目标可分解、可追踪
- BLOCKED 状态自然暴露依赖阻塞
- 结合 MQTT 通知 → 跨 Agent 可见

---

### 方案 B: 目标生命周期机 (Goal State Machine)

```
           user/agent 创建
                │
                ▼
┌─────────┐  decompose  ┌─────────┐
│ PENDING  │ ──────────→│ ACTIVE   │
└─────────┘             └─────────┘
    ▲                       │  │
    │                       │  ├──→ BLOCKED (依赖未就绪)
    │                       │  │       │
    │                       │  │       ▼
    │                       │  │   WAITING
    │                       │  │       │
    │                       │  │       │ (依赖就绪)
    │                       │  │       ▼
    │                       │  └──→ ACTIVE
    │                       │
    │                       ├──→ COMPLETED
    │                       │       │
    │                       │       ├──→ report + archive
    │                       │       └──→ trigger next goal
    │                       │
    │                       └──→ FAILED
    │                               │
    │                               ├──→ retry (回到 ACTIVE)
    │                               └──→ abandon (永久归档)
    │
    └───────────────────────────────── (re-evaluate)
```

**实现位置**: 扩展 `goal_mode.py` 为状态机引擎，而非简单的 prompt 循环。

**状态变更事件**: 每个状态变更通过 MQTT 发布至 `v2/goal/{agent_id}/{goal_id}/status`，供 BoardClient 实时监控。

---

### 方案 C: Means-Ends 推理 (目标-手段分析)

Agent 收到目标时，不是直接开始"做"，而是先推理:

```
Goal: "优化 MQTT 发布延迟到 <10ms"

Means-Ends Analysis:
  ┌─ 手段1: 修改 QoS (最快, 效果有限)
  ├─ 手段2: 批量发送 (中等复杂度, 效果好)
  ├─ 手段3: 改异步发送 (高复杂度, 效果最好)
  └─ 手段4: 换 Rust MQTT 客户端 (最慢, 可能不必要)

决策: 先手段1 → 验证 → 不够再手段2 → 递归
```

**实现**: goal_mode.py 在开始执行前先调用 LLM 做一层 means-ends reasoning，生成候选方案树。

**评估标准**:
```
effort (人力成本) × impact (预期效果) / risk (失败风险) = priority_score
```

---

### 方案 D: 跨 Agent 目标协商

多 Agent 场景下，目标需要协商而非独裁:

```
Agent A: "我想优化 MQTT 发布性能" → 发布到 v2/goal/negotiate/
Agent B: "我需要改 BoardService 来处理新消息格式" 
          → 检测到冲突: 改了同一个文件
          → 提出: "你改客户端我改服务端，互不冲突"
```

**协商协议** (MQTT 主题):

| 主题 | 用途 |
|------|------|
| `v2/goal/propose/{agent_id}` | 提议新目标 |
| `v2/goal/negotiate/{agent_id}` | 目标协商消息 |
| `v2/goal/conflict/{agent_id}` | 冲突检测通知 |
| `v2/goal/delegate/{from}/{to}` | 目标委托 |

**冲突检测**: 基于 StateKV 的共享资源锁 (`whiteboard.py` 已有的分布式锁)

---

## 三、Environment Sense 架构方案

### 方案 E: 传感器抽象层 (Sensor Abstraction Layer)

```
┌─────────────────────────────────────────────────────┐
│                    Agent Core                        │
│  "环境当前状态是..."                                  │
└──────────────┬──────────────────────────────────────┘
               │  query("sensor:filesystem:/tmp/log/")
               ▼
┌─────────────────────────────────────────────────────┐
│              Sensor Registry                         │
│  sensor_registry = {                                 │
│    "filesystem": FileSystemSensor,                   │
│    "vision":     WindowVisionSensor,                 │
│    "mqtt":       MQTTBrokerSensor,                   │
│    "process":    ProcessMemorySensor,                │
│    "web":        WebPageSensor,                      │
│    "clipboard":  ClipboardSensor,                    │
│  }                                                   │
└──────────────┬──────────────────────────────────────┘
               │
     ┌─────────┼─────────┬──────────┐
     ▼         ▼         ▼          ▼
 FileSys   Window    MQTTBroker   Process
Sensor    Sensor    Sensor       Sensor
```

**传感器接口**:
```python
class Sensor(ABC):
    name: str
    description: str
    
    @abstractmethod
    def sense(self, params: dict) -> SensorReading:
        """采集一次环境数据"""
    
    @abstractmethod
    def interpret(self, reading: SensorReading) -> str:
        """将原始数据转化为自然语言描述"""
    
    def diff(self, old: SensorReading, new: SensorReading) -> str:
        """对比两次读数，返回变化描述"""
```

**优势**:
- 统一的 `sense()` 接口，Agent 不需要知道具体实现
- `interpret()` 将原始数据(截图/文件/内存转储)转化为自然语言
- `diff()` 实现变化检测——"这个文件在上次读取后新增了 50 行"
- 新传感器只需实现一个类，注册即用

---

### 方案 F: 环境模型 (World Model / Environment Model)

当前: 每次读取后信息丢失。

改进: 持久化的环境模型，自动增量更新:

```python
class EnvironmentModel:
    """Agent 对环境的认知模型"""
    
    files: dict[Path, FileSnapshot]    # 文件快照
    windows: dict[str, WindowState]    # 窗口状态
    processes: dict[int, ProcessInfo]  # 进程列表
    mqtt_topics: dict[str, TopicState] # MQTT 主题状态
    web_pages: dict[str, PageSnapshot] # 网页状态
    
    def snapshot(self) -> ModelSnapshot:
        """主动采集环境快照"""
    
    def diff(self, baseline: ModelSnapshot) -> ModelDelta:
        """对比基线，只返回变化"""
    
    def query(self, query: str) -> str:
        """自然语言查询环境状态"""
```

**存储位置**: `v2/state/env/{agent_id}/model` (StateKV, retain=True)

**变化推送**: 传感器周期采集 → diff 发现变化 → 主动推送 `v2/agent/{id}/env/change`

---

### 方案 G: 感知-行动循环 (Perception-Action Cycle)

将 Goal Mode 的扁平循环升级为感知-行动闭环:

```
                 ┌──────────────────────────────────────┐
                 │           Goal State Machine          │
                 │  (目标分解 / 状态管理 / 进展评估)      │
                 └──────────────┬───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Perceive (感知)      │
                    │  • 主动扫描环境变化      │
                    │  • 传感器 diff 对比基线  │
                    │  • 异常/变化检测         │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Reason (推理)        │
                    │  • 环境变化对目标的影响  │
                    │  • 下一步决策            │
                    │  • 是否需要调整目标?     │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Act (行动)           │
                    │  • 执行子任务            │
                    │  • 或: 委托 subagent    │
                    │  • 更新环境模型          │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Reflect (反思)       │
                    │  • 本次行动有效吗?      │
                    │  • 目标进展如何?        │
                    │  • 更新目标状态          │
                    └───────────┬───────────┘
                                │
                                ▼
                          (循环或结束)
```

---

### 方案 H: 环境好奇心驱动探索 (Curiosity-Driven Sensing)

不是所有环境变化都需要感知，由**好奇心预算**控制:

```
好奇心预算: 100/turn

感知操作成本:
  scan filesystem (*.py)     → cost 10
  read large file            → cost 15
  screenshot + vision        → cost 25
  scan MQTT topics           → cost 5
  query web API              → cost 20

Agent 决策: 用有限的预算选择最高价值信息的感知操作
```

**好奇心分值计算**:
```
curiosity_score = 
  prediction_error(预期 vs 实际环境状态) × 
  information_gain(能获取的新信息) / 
  sensing_cost(感知成本)
```

---

## 四、与 MQTT 基础设施的集成

| 方案 | 集成的 MQTT 组件 | 新增主题 |
|------|-----------------|---------|
| A 目标分解 | StateKV | `v2/state/goal/{agent_id}/{goal_id}` |
| B 状态机 | BoardClient + 推送 | `v2/goal/{agent_id}/{goal_id}/status` |
| C Means-Ends | subagent | - (纯 LLM 推理) |
| D 协商 | WhiteboardKV 分布式锁 | `v2/goal/propose/+/+` |
| E 传感器层 | PluginSystem | `v2/sensor/{agent_id}/{sensor}/reading` |
| F 环境模型 | StateKV | `v2/state/env/{agent_id}/model` |
| G 感知-行动 | BBS 任务系统 | - (复用 task 协议) |
| H 好奇心 | CapabilityRegistry | `v2/sensor/curiosity/budget` |

---

## 五、演进路线图

### P0 (基于现有的增量改进)

1. **Goal node 数据结构** — 将 `goal_mode.py` 的扁平 state 升级为结构化 GoalNode（含 status/depends_on/milestones）
2. **FileSystemSensor** — 将 ad-hoc 的 file_read 封装为可复用的传感器（sense → interpret → diff）
3. **Perception-Action 循环** — goal_mode 的 prompt 模板中增加"感知环境"前置步骤

### P1 (核心能力)

4. **目标分解** — 收到目标后用 means-ends 推理生成子目标树
5. **环境模型** — 持久化的 env state，增量更新
6. **变化检测** — sensor diff → 自动推送环境变更事件

### P2 (多 Agent 协同)

7. **跨 Agent 目标协商协议** — propose/negotiate/conflict/delegate 四主题
8. **资源冲突检测** — 基于 WhiteboardKV 分布式锁的目标冲突发现
9. **好奇心驱动感知** — 预算分配 + 信息价值评估

### P3 (前沿)

10. **预测性感知** — Agent 预测环境的变化方向，主动验证假设
11. **共享世界模型** — 多 Agent 共享同一个环境模型，通过 StateKV 同步
12. **元目标** — Agent 自动生成"改进自身目标管理能力"的元目标

---

## 六、与现有 SOP/工具的集成

| 现有组件 | 与脑暴的关系 |
|---------|------------|
| `goal_mode.py` | 重构为 Goal State Machine 引擎 |
| `autonomous_operation_sop.md` | TODO 队列升级为 GoalNode 依赖图 |
| `dream_engine.py` | 新增"目标反思"阶段——复盘目标完成质量 |
| `vision_sop.md` | 封装为 VisionSensor，实现 sensor 接口 |
| `procmem_scanner_sop.md` | 封装为 ProcessMemorySensor |
| `board_stress_sop.md` | 压测目标分解后的多 Agent 目标协商 |
| `subagent.md` | GoalNode 的子任务自动委托 subagent 执行 |
| WhiteboardKV | 共享目标状态 + 分布式锁 |
| BBS 任务系统 | 子目标 → WorkerAgent 执行 → 结果聚合 |

---

## 七、开放问题

1. **目标分解的粒度控制**: 什么程度该分解，什么程度该直接执行？过度分解产生"分析瘫痪"。
2. **环境模型的一致性**: 当实际环境变化而 Agent 不知道时（文件被外部修改），如何检测"认知偏差"？
3. **多 Agent 的权威层级**: 当两个 Agent 的目标冲突且无法协商时，用优先级还是用户裁决？
4. **好奇心预算的消耗策略**: 环境感知 vs 目标执行的资源分配比例如何动态调整？
5. **与 Goal Mode 的兼容性**: 新增的 structured goal 系统应该替代还是扩展现有的 `goal_state.json`？
