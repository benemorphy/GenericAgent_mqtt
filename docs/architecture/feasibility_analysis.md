# 三项能力实现可行性分析

> 基于: `deep_research_code_and_rumination.md` 5.2节改进方向
> 分析日期: 2026-05-21 | 代码基线: commit 0d2e079

---

## 总览

| 能力 | 参考来源 | 可行性 | 预估工作量 | 优先级 |
|:----|:---------|:------|:----------|:------|
| MASC实时步骤级检测 | arXiv Oct 2025 | **高** | 1-2天 | P1 |
| MUSE能力置信度评估 | arXiv 2025 | **高** | 1天 | P2 |
| Metagent-P神经符号约束 | ACL 2025 | **中** | 2-3天 | P3 |
| 量化评估基准 | SICA体系 | **高** | 1天 | P0 |

---

## 1. MASC: 实时步骤级检测

### 当前状态

| 现有组件 | 功能 | 集成点 |
|:---------|:-----|:-------|
| `agent_loop.py:BaseHandler` | 提供 `tool_before_callback` / `tool_after_callback` / `turn_end_callback` | **直接插入点** |
| `verify_sop.md` | 事后验证规则（对抗性探测、边界测试） | 规则可复用 |
| `failure_driven_learning_sop` | 3阶段失败追踪+模式聚类 | 可作为下游 |
| `code_review_principles.md` | 13条代码审查原则 | 静态分析依据 |

### 实现方案

```
步骤检测器架构:

LLM输出 → 工具调用
              │
              ▼
    tool_before_callback ──→ 步骤检测器 (step_detector.py)
              │                    │
              ▼                    ▼
    工具执行结果           ╔═══════════════════╗
              │           ║ 实时模式匹配引擎    ║
              ▼           ║                    ║
    tool_after_callback ──→║ ① 空结果检测        ║
              │           ║ ② 异常退出码检测     ║
              ▼           ║ ③ 超时检测          ║
    turn_end_callback ────→║ ④ 连续失败检测      ║
                          ║ ⑤ 模式重复检测      ║
                          ╚═══════════════════╝
                                │
                          ┌─────┴─────┐
                          ▼           ▼
                   注入纠正提示     记录到失败追踪器
```

### 关键技术点

**检测模式库**（可扩展）:
```python
# step_detector.py 核心模式
PATTERNS = {
    "empty_result": {
        "match": lambda r: r is None or (isinstance(r, dict) and not r),
        "severity": "minor",
        "action": "warn"
    },
    "permission_denied": {
        "match": lambda r: "denied" in str(r).lower() or "access" in str(r).lower() and "denied" in str(r).lower(),
        "severity": "critical",
        "action": "stop_and_retry"
    },
    "same_error_repeated": {
        "match": lambda ctx: ctx.same_error_count >= 2,
        "severity": "moderate",
        "action": "suggest_sop_check"
    },
    "timeout_silence": {
        "match": lambda r: r is None and ctx.time_since_last_tool > 30,
        "severity": "moderate",
        "action": "ping_and_retry"
    },
    "tool_output_truncated": {
        "match": lambda r: isinstance(r, str) and r.endswith("..."),
        "severity": "minor",
        "action": "warn_incomplete"
    }
}
```

### 集成方式

```python
# agent_loop.py 中插入（约10行变更）
class StepDetectingHandler(BaseHandler):
    def __init__(self):
        self.step_detector = StepDetector()
    
    def tool_after_callback(self, tool_name, args, response, ret):
        anomalies = self.step_detector.analyze(tool_name, args, ret)
        for a in anomalies:
            if a.severity == "critical":
                raise StepDetectionInterrupt(a)  # 阻断执行
            elif a.severity == "moderate":
                self._pending_corrections.append(a.to_prompt())  # 注入纠正
```

### 风险与边界

| 风险 | 缓解 |
|:-----|:-----|
| 误报导致正常执行被打断 | 只对 `critical` 级别自动阻断，`minor` 仅记录 |
| 检测器本身出错 | 用 try/except 包裹，失败时降级为不检测 |
| 增加每轮延迟 | 检测器用纯规则（无LLM），<1ms/次 |

### 可行性结论: 高

- `BaseHandler` 预留的回调接口就是为此设计的
- 纯规则的检测引擎无外部依赖，轻量可靠
- 现有 `failure_driven_learning_sop` 可直接作为下游消费端

---

## 2. MUSE: 能力置信度评估

### 当前状态

| 现有组件 | 可用数据 | 缺什么 |
|:---------|:---------|:-------|
| `learning_log.py` | 347行的完整日志系统，含 category/result/failure_count | 无按类别的置信度计算 |
| `metacognition_sop.md` | 仪表盘框架（7天/策略/耗时/趋势） | 无失败概率预测 |
| `.tracker.json` | session-by-session 记录 | 无滑动窗口统计 |

### 实现方案

```
置信度计算模型 (learning_log.py 扩展):

现有: 仪表盘展示 → 成功率/策略有效性/趋势
新增: 能力置信度矩阵

┌─────────────────────────────────────────┐
│          能力置信度仪表盘                  │
├────────────┬──────┬──────┬──────┬───────┤
│ 类别       │ 样本数│成功率 │置信度 │ 建议   │
├────────────┼──────┼──────┼──────┼───────┤
│ code       │  42  │ 83%  │ 0.78 │ 自主   │
│ browser    │  18  │ 44%  │ 0.35 │ 谨慎   │
│ data       │  12  │ 75%  │ 0.62 │ 可行   │
│ planning   │   8  │ 88%  │ 0.70 │ 自主   │
│ research   │  15  │ 60%  │ 0.48 │ 需确认  │
└────────────┴──────┴──────┴──────┴───────┘
```

### 关键技术点

**置信度计算**:
```python
def compute_confidence(category_sessions, window_days=30):
    """
    confidence = (success_count * 1.0 + partial_count * 0.5) / total_count
              * min(1.0, total_count / 5)  # 样本量惩罚
              * (1 - recent_failure_trend)  # 趋势惩罚
    """
    recent = [s for s in category_sessions 
              if (datetime.now() - parse_date(s['date'])).days <= window_days]
    if not recent:
        return 0.0, "无数据"
    
    successes = sum(1 for s in recent if s['result'] == 'success')
    partials = sum(1 for s in recent if s['result'] == 'partial')
    total = len(recent)
    
    base = (successes + partials * 0.5) / total
    sample_penalty = min(1.0, total / 5)  # <5样本时降权
    trend = _compute_failure_trend(recent)  # 近期失败趋势(0-1)
    
    confidence = base * sample_penalty * (1 - trend * 0.3)
    return round(confidence, 2), _advice(confidence)
```

**集成点**:
- `learning_log.py --dashboard` 输出中增加置信度矩阵
- 可在 `agentmain.py` 的 system prompt 中动态注入置信度信息（让Agent知道自己擅长什么）

### 风险

| 风险 | 缓解 |
|:-----|:-----|
| 小样本导致置信度不可靠 | 样本量<5时标记为"数据不足" |
| 类别定义漂移 | 复用已有 `CATEGORIES` 常量 |
| 过度依赖历史预测未来 | 置信度仅作参考，不阻断执行 |

### 可行性结论: 高

- 数据基础已有（tracker.json存了所有session记录）
- 只需扩展 `learning_log.py` 的 dashboard 函数
- 置信度注入 system prompt 只需几行代码

---

## 3. Metagent-P: 神经符号约束

### 当前状态

| 现有组件 | 功能 | 缺什么 |
|:---------|:-----|:-------|
| `plan_sop.md` | 262行的完整规划SOP | 无形式化验证 |
| `plan_XXX/plan.md` | 自由格式markdown计划 | 无结构约束 |
| `plan_validator_default.py` | 存在但... | 检查一下 |

### 现有 validator 检查

让我检查一下现有的 plan_validator：

<need to check tools/plan_validator_default.py>

### 实现方案

```
符号验证层架构:

plan.md (LLM生成)
    │
    ▼
┌──────────────────────────────────────┐
│  plan_validator.py (符号验证引擎)     │
│                                      │
│  ▸ 结构验证:                          │
│    - markdown章节完整性               │
│    - 步骤编号连续性                    │
│    - [ ]/[✓]/[VERIFY] 标记一致       │
│                                      │
│  ▸ 路径验证:                          │
│    - 文件路径格式 (Unix/Windows)      │
│    - 目录是否存在                      │
│    - 文件名合法性                      │
│                                      │
│  ▸ 依赖验证:                          │
│    - 步骤依赖是否有环                  │
│    - [D]标记的subagent步骤是否独立     │
│    - SOP引用是否存在                   │
│                                      │
│  ▸ 语法验证:                          │
│    - 命令格式 (bash/python/PS1)       │
│    - 工具调用参数格式                  │
│    - 条件分支完整性                    │
└──────────────────────────────────────┘
    │
    ├── 通过 → 进入执行态
    └── 失败 → 返回错误+修正建议 → LLM重新生成
```

### 关键技术点

**"符号" vs "神经"的实用划分**:

| 层面 | 方法 | 实现 |
|:-----|:-----|:-----|
| **符号** (Symbolic) | 规则引擎+正则 | plan_structure_validator, path_checker |
| **神经** (Neural) | LLM辅助 | 语义验证（"这个步骤合理吗？"） |
| 混合 | 先符号过滤→再神经评估 | 符号层捕获明显错误，神经层处理模糊判断 |

**P0可实现的验证规则**:
```python
RULES = [
    # 结构规则
    {"id": "S001", "check": "has_section('执行态')", "msg": "缺少执行态章节"},
    {"id": "S002", "check": "steps_sequential()", "msg": "步骤编号不连续"},
    {"id": "S003", "check": "no_orphan_brackets()", "msg": "存在未闭合的[ ]标记"},
    {"id": "S004", "check": "verify_tags_present()", "msg": "缺少[VERIFY]步骤"},
    
    # 路径规则
    {"id": "P001", "check": "paths_valid_format()", "msg": "包含非法文件路径"},
    {"id": "P002", "check": "no_absolute_paths()", "msg": "禁止硬编码绝对路径"},
    
    # 依赖规则
    {"id": "D001", "check": "no_circular_deps()", "msg": "步骤存在循环依赖"},
    {"id": "D002", "check": "subagent_tasks_independent()", "msg": "subagent任务应独立"},
    
    # SOP引用规则
    {"id": "R001", "check": "referenced_sops_exist()", "msg": "引用的SOP文件不存在"},
]
```

### 集成方式

在 `plan_sop.md` 的"规划态→执行态"门控处增加验证步骤：

```markdown
### [VERIFY] 符号验证（plan_sop新增加）
执行前运行:
```bash
python tools/plan_validator.py plan_XXX/plan.md
```
输出:
- PASS → 进入执行态
- FAIL → 返回错误列表，修正后重新验证
```

### 风险

| 风险 | 缓解 |
|:-----|:-----|
| 规则过严导致频繁打断 | 先做P0基础规则，逐步放宽 |
| LLM抗拒严格的格式约束 | 用温和验证+建议模式，非强制阻断 |
| 验证器本身成为维护负担 | 规则从简，用函数式写法 | 

### 可行性结论: 中

- **符号层**: 简单可行（正则+路径检查，1天）
- **神经层**: 需要LLM调用，复杂度较高（2-3天）
- **建议**: 先实现符号层（计划结构+路径+标记验证），神经层作为P3后续

---

## 4. 量化评估基准 (5.3节)

### 实现方案

**5个指标的计算方式**:

| 指标 | 计算方法 | 数据来源 | 可行性 |
|:-----|:---------|:---------|:-------|
| CI首次通过率 | 统计GitHub Actions: 首次push通过数/总push数 | GitHub API + CI日志 | **高** |
| 反刍循环次数 | git log分析: 从失败commit到修复commit的平均步数 | `git log --oneline` | **高** |
| SOP存活率 | git历史: SOP创建后3月未修改的比例 | `git log --follow memory/*.md` | **高** |
| 技能复习通过率 | spaced_repetition结果: 首次复习通过数/总复习数 | `skills_learning/` 数据 | **高** |
| 失败模式覆盖率 | SOP覆盖的失败类型/总失败类型 | failure_tracker.json | **高** |

**工具实现** `tools/benchmark_metrics.py`:
```python
def ci_first_pass_rate():
    """查询GitHub API获取CI状态"""
    ...

def rumination_cycle_count():
    """git log分析失败→修复模式"""
    ...

def sop_survival_rate():
    """分析SOP文件的git修改历史"""
    ...

def skill_review_pass_rate():
    """读取skills_learning复习结果"""
    ...

def failure_pattern_coverage():
    """failure_tracker vs SOP覆盖对比"""
    ...
```

### 可行性结论: 高

- 所有数据已在仓库中（CI日志、git历史、tracker文件）
- 只需写一个统计脚本，无外部依赖
- 可集成到 `agentmain.py --reflect` 模式中定期输出

---

## 总结与路径建议

### 推荐实施顺序

```
P0 ── 量化评估基准 (1天)
  │     建立基线才能衡量改进
  │
  ▼
P1 ── MASC实时步骤检测 (1-2天)
  │     直接提高执行质量
  │
  ▼
P2 ── MUSE能力置信度 (1天)
  │     让Agent了解自身边界
  │
  ▼
P3 ── Metagent-P符号约束 (2-3天)
       先做符号层, 后做神经层
```

### 一句话总结

```
3项能力中:
- MASC(实时检测) 和 MUSE(置信度) 实现难度低,收益明显,基础设施已就绪
- Metagent-P(符号约束) 需合理裁剪范围,先符号后神经
- 量化基准是评估所有改进效果的前提,建议最先建立
```
