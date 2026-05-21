# 自驭审计循环：必要性分析与实现构想

> **日期**: 2026-05-21 | **前置**: deep_research_self_harness.md
> **问题**: GA是否需要一个"自驭审计循环"？如果需要，如何实现？

---

## 1. 现有机制盘点

| 机制 | 类型 | 作用时机 | 解决的问题 |
|:-----|:------|:---------|:-----------|
| `_turn_policies` (policy chain) | 前瞻约束 | 每轮开始前 | 注入行为规则（如3次失败规则、danger_ask_user） |
| `_system_prompt_hooks` (3个) | 上下文注入 | 系统提示组装时 | 添加记忆提示、summary强制、master干预 |
| `_plan_validators` | 前瞻校验 | 规划生成时 | 校验计划的安全性/合理性 |
| `_done_hooks` | 回调 | 完成时 | 清理/通知 |
| `metacognition_sop` | 反应式+周期 | 学习日志+每周 | 记录学习、每周元分析 |
| `failure_driven_learning_sop` | 反应式 | 3次失败后 | 从失败中学习模式 |
| `spaced_repetition_sop` | 周期复习 | 间隔触发 | 复习已知技能防止遗忘 |
| `agent_dreaming_sop` | 空闲发散 | 空闲时 | 自由联想/跨域关联 |

**发现**: GA已经有一个相当完整的自我调节体系，覆盖了"事前→事中→事后→周期"四个时间维度。

---

## 2. 必要性分析: 审计循环真的需要吗？

### 2.1 审计循环的定义

所谓"审计循环"，是指 Agent **主动审视自身行为是否遵守已制定的SOP**，并在偏离时自我修正。

### 2.2 判断: 低必要性

**理由1: 3-failure规则已经是隐式的审计回路**

GA现有的"3次失败→触发学习"机制，本质上就是**结果驱动的审计**。如果Agent偏离SOP导致失败，失败本身就会触发修正。这是一个闭环。

```
用户请求 → Agent行动 → (如果成功) → 继续
                       → (如果失败) → 记录失败次数
                                   → (3次) → 触发学习
```

**理由2: turn_policies 是前瞻约束，不是事后审计**

GA的 `_turn_policies` 在每轮开始前注入行为约束（如"最多失败3次"）。这是**预防性**的，不是**审计性**的。而审计是事后检查——两种不同的哲学。

**理由3: 显式审计的开销 > 收益**

每轮让Agent检查"我遵守SOP了吗？"需要消耗token和时间去"反省"。在没有检测到违规的轮次，这笔开销是纯浪费的。

**结论: 不需要一个独立的"审计循环"。** 如果要改进，应该在现有机制的基础上做增量优化，而不是增加新循环。

---

## 3. 真正的缺口: 约束状态感知

### 3.1 来自Deep Research的核心发现

CoStrict 和 INTENT 的研究表明：

> **当Agent感知到自己还剩多少"资源"时，其行为质量显著提升。** 
> — INTENT论文: 无预算控制时超支率65%+，有预算控制后不仅不超支，任务完成率还提升。

### 3.2 GA当前的"不透明状态"

```
Agent执行时知道：
  ✅ 当前轮次
  ✅ 当前任务
  ✅ 可用工具

Agent执行时不知道：
  ❌ 已失败几次（还剩几次机会）
  ❌ 已调用多少次工具
  ❌ 距上次SOP复习已过多久
  ❌ 哪条SOP可能已过时
```

**这就是真正的缺口：Agent没有"仪表盘"意识。**

问题不是"审计"（事后检查），而是**缺乏执行中的自我感知**。

### 3.3 具体设计: Constraint Dashboard（约束仪表盘）

在每个turn的policy chain末尾注入一段**约束状态报告**，格式类似：

```
[CONSTRAINT DASHBOARD]
├─ 失败预算: 已用2/3 (剩余1次, 超限后触发学习)
├─ 工具调用: 5次本次任务
├─ 时间预算: 45s/120s
├─ SOP状态: 最近复习: 3天前 (spaced_repetition_sop推荐复习间隔: 2天)
└─ 活跃SOP数: 12条 (其中可能过时: 2条)
```

**实现方式**: 在 `_turn_policies` 链末尾新增一个 `policy_constraint_dashboard`，从handler上读取统计数据，生成纯文本报告注入到下一轮的prompt中。

**改动粒度**: 
- 新增 `tools/turn_policy/policy_constraint_dashboard.py` (约50行)
- 在 `tools/turn_policy/__init__.py` 中注册到默认策略链
- 在 `GenericAgentHandler` 上增加计数器字段

---

## 4. 第二缺口: SOP健康检查

### 4.1 问题

SOP会过时、会冲突、会膨胀，但GA没有任何机制去**主动审视SOP体系本身的健康度**。

### 4.2 判断: 中等价值，但不需要新机制

**方案**: 在现有的 `spaced_repetition_sop` 中加入"SOP健康检查"作为复习内容的一部分——每次复习时不只复习技能，也复习SOP本身是否仍然有效。

**实现**: 
- 在 `spaced_repetition_sop.md` 的复习模板中增加一条: "检查一条随机SOP: 它是否仍适用? 是否与现有其他SOP冲突?"
- 不需要独立的新循环

---

## 5. 综合建议

| 方案 | 价值 | 实现成本 | 优先级 |
|:-----|:-----|:---------|:-------|
| **A. 独立审计循环** | 低(已有覆盖) | 中(新hook+检查逻辑) | ❌ 不要做 |
| **B. 约束仪表盘** | 高(研究验证) | 低(新增policy约50行) | ⭐ 推荐做 |
| **C. SOP健康检查** | 中 | 极低(复用spaced_repetition) | ✅ 可做 |

### 推荐路径

1. **立即做**: 约束仪表盘 — 让Agent在执行中感知自己的"预算状态"，从CoStrict/INTENT研究中已验证有效
2. **顺便做**: SOP健康检查并入spaced_repetition — 改动极小
3. **不做**: 独立审计循环 — 成本收益不划算

---

## 6. 实现草图: 约束仪表盘

### 数据结构

```python
# 在 GenericAgentHandler 或 parent 上
class ConstraintState:
    fail_count: int = 0          # 当前任务已失败次数
    max_fails: int = 3           # 最大失败次数
    tool_call_count: int = 0     # 本轮工具调用次数
    max_tool_calls: int = 20     # 工具调用上限
    start_time: float = 0        # 任务开始时间
    timeout: float = 120.0       # 超时秒数
    last_sop_review: str = ""    # 上次SOP复习时间
```

### policy注入

```python
def policy_constraint_dashboard(turn, plan, context):
    """在每轮prompt末尾注入约束仪表盘"""
    state = get_constraint_state(context)
    budget_remaining = state.max_fails - state.fail_count
    return f"""
[约束仪表盘]
  失败预算: {state.fail_count}/{state.max_fails}
  工具调用: {state.tool_call_count}次
  时间: {elapsed}/{state.timeout}s
"""
```

---

> 下一步: 如果确定方向，可以进入工程实现阶段。
