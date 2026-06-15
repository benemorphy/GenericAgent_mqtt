# 失败驱动学习 SOP — 从错误中学习

> 核心理念: 失败是最好的老师。每次失败都是数据点, 聚类分析后成为可复用的知识。
> 与现有3次失败干预规则无缝衔接: 失败1次→记录, 2次→标记模式, 3次→自动触发学习管道。

## 失败追踪系统

追踪文件: `skills_learning/.failure_tracker.json`

### 单条失败记录

```json
{
  "failure_id": "F_0001",
  "date": "2026-05-20",
  "task": "review_agentDreaming",
  "operation": "force_review",
  "failure_type": "assess_execution_error",
  "severity": "minor|moderate|critical",
  "error_sig": "assess.py timed out waiting for LLM response",
  "signature_hash": "sha256精简特征",
  "context": "agentDreaming assess.py calls LLM for question generation, timeout>60s",
  "root_cause": "LLM call has no timeout parameter",
  "resolution": "retry with explicit timeout flag",
  "pattern_ids": [],
  "session_id": "R27"
}
```

### 失败类型分类

| 类型 | 说明 | 严重度默认 |
|:-----|:-----|:----------|
| assess_execution_error | 验证工具执行失败 | moderate |
| tool_timeout | 工具调用超时 | moderate |
| command_failed | shell命令错误 | minor |
| llm_misunderstanding | LLM理解偏差 | moderate |
| environment_mismatch | 环境配置不对 | critical |
| permission_denied | 权限不足 | critical |
| logic_error | 逻辑错误/算法缺陷 | moderate |
| resource_not_found | 文件/资源找不到 | minor |

## 三阶段失败处理

### 阶段1: 首次失败 (记录)

```
失败发生 → learning_log记录 → 失败追踪器记录
        ↓
重试(最多2次)
```

### 阶段2: 同类失败2次 (标记模式)

```
第2次同类失败 → 失败追踪器检测到重复模式
        ↓
生成"疑似模式" → 标记 pattern.pending
        ↓
建议: 修改策略/读相关SOP/换方案
```

### 阶段3: 同类失败3次 (自动学习)

```
第3次同类失败 → 模式确认
        ↓
自动触发迷你学习管道:
  1. 收集3次失败的完整上下文
  2. 调用 skill_search 查相关方案
  3. 生成 workaround/fix 建议
  4. 更新失败模式为 confirmed
  5. 若严重度高 → 写入全局记忆(RULES)
        ↓
仍然失败 → 请求用户干预 (与原规则一致)
```

## 失败模式生命周期

```
detected → pending(2次) → confirmed(3次) → fixed(解决) → archived(归档)
                          ↓             ↑
                       (更新记忆)    (再次出现→重新激活)
```

Confirmed 的模式可自动写入 `global_mem_insight.txt` 的 RULES 区段, 防止重复踩坑。

## 与现有系统集成

| 组件 | 集成方式 |
|:-----|:---------|
| 现有3次干预规则 | 直接替换: 记录前2次, 第3次触发学习而非仅请求干预 |
| skills_learning_sop | 确认的模式可作为新技能案例 |
| spaced_repetition_sop | 失败率高的技能→增加复习频率 |
| global_mem L1 RULES | 确认的致命模式写入行为规则 |
| inspiration_board | 新确认为灵感条目 |

## 工具使用

```bash
# 记录一次失败
python tools/failure_tracker.py log --type tool_timeout --error "message" --task "task_name"

# 查询当前所有失败模式
python tools/failure_tracker.py patterns

# 查看特定模式的失败记录
python tools/failure_tracker.py pattern P_001

# 清理已修复的模式
python tools/failure_tracker.py archive P_001

# 从 autonomous_reports 扫描历史失败
python tools/failure_tracker.py --scan-history
```


---

## 已验证的经验教训（2026-06-11 会话总结）

*（已删除 — 不合理模式）*
