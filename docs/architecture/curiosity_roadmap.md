# 好奇心驱动Agent — 实施路线图

> 基于: deep_research_agent_curiosity.md (2026-05-21)
> 状态: 第1阶段进行中
> 系列: brainstorm_agent_curiosity.md → bbs_curiosity.md → perception_curiosity.md → deep_research_agent_curiosity.md → 本篇

---

## 路线图总览

| 阶段 | 优先级 | 任务 | 基于 | 状态 |
|:----|:-------|:-----|:-----|:-----|
| **1** | **P0** | **好奇心仪表盘 (CuriosityDashboard)** | SuS + CDE | **进行中** |
| 2 | P1 | 感知工具好奇心钩子 (CuriositySignal) | perception_curiosity.md | 待启动 |
| 3 | P2 | BBS CuriosityBoard插件 | CAMEL + MAD | 待启动 |
| 4 | P3 | 好奇心预算管理 (CuriosityBudget) | CDE动态衰减 | 待启动 |

---

## 阶段1: 好奇心仪表盘 (P0)

**目标**: 扩展 `tools/constraint_dashboard.py` → 同时跟踪好奇心信号

### 设计

```python
class ConstraintDashboard:
    # 现有属性...
    # 新增:
    curiosity_signals: List[CuriositySignal]  # 待探索的好奇信号
    curiosity_budget: int = 3                 # 每任务最多3个好奇标记
```

### 仪表盘输出扩展

```
[CONSTRAINT DASHBOARD]
  ├─ 轮次: #6
  ├─ 失败预算: 0/3
  ├─ 工具调用: 5次 (本轮: 2)
  ├─ 时间: 1m23s / 5m0s
  ├─ 感知好奇: 3个待探索标记  ← 新增
  └─ 环境漂移: 检测到2处变化  ← 新增
```

### 依赖
- 已有: `tools/constraint_dashboard.py`
- 已有: `tools/turn_policy.py` 的注册机制
- 已有: `ga.py` 的初始化 + 更新埋点

### 验收标准
- [x] CuriositySignal数据类定义
- [ ] ConstraintDashboard增加curiosity_signals列表
- [ ] `register_curiosity()` 方法
- [ ] Dashboard格式化含好奇心状态

---

## 阶段2: 感知工具好奇心钩子 (P1)

**目标**: 在 `file_read`、`web_scan`、`code_run(dir)` 等感知工具返回时，产生并注册 CuriositySignal

### 设计

```python
# 在 do_file_read 返回时
def do_file_read(self, args, response):
    content = result.content
    if hasattr(self, '_constraint_dashboard'):
        signal = self._detect_curiosity_for_file(path, content)
        if signal:
            self._constraint_dashboard.register_curiosity(signal)
    return result
```

### 验收标准
- [ ] 3个感知工具的好奇心钩子实现
- [ ] CuriositySignal优先级过滤
- [ ] 主任务prompt中高优信号可见
- [ ] 低优信号存入pending list

---

## 阶段3: BBS CuriosityBoard (P2)

**目标**: 基于MQTT BBS的CuriosityBoard插件

### 设计

```python
class CuriosityBoardPlugin:
    POST_TOPIC = "board/curiosity/post/{id}"
    def post(self, curiosity: CuriositySignal): ...
    def respond(self, post_id, response): ...
    def get_hot(self, min_score=3): ...
```

### 集成点
- `agent_dreaming_sop`: 扫描CuriosityBoard
- `spaced_repetition_sop`: 好奇心讨论纳入复习

### 验收标准
- [ ] CuriosityBoard插件可发帖/回复
- [ ] Dreaming模式扫描board
- [ ] 讨论结果归档到记忆

---

## 阶段4: 好奇心预算管理 (P3)

**目标**: 基于CDE的动态衰减机制

### 设计

```
curiosity_budget = max_budget * decay_rate^task_count
```

任务开始时高预算 → 进行中递减 → 失败时重置

### 验收标准
- [ ] 好奇心预算随任务轮次递减
- [ ] 超预算好奇信号自动降级
- [ ] Dashboard显示剩余好奇心预算

---

## 进度跟踪

| 日期 | 阶段 | 完成项 | 备注 |
|:-----|:-----|:--------|:-----|
| 2026-05-21 | 1 | 路线图创建 + 启动P0 | 基于4份文档 |
