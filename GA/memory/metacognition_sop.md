# 元认知 SOP — 学习日志与策略反思

> 核心理念: 不仅学什么, 更要追踪"怎么学"——哪些策略有效, 哪些模式浪费了时间
> 元认知是学习的学习: 记录策略 → 分析模式 → 优化方法

## 学习日志结构

每次任务/会话结束后记录一条日志到 `memory/learning_log/YYYY/MM/` 下。

### 日志格式 (JSON)

```json
{
  "date": "2026-05-20",
  "session_id": "R27",
  "task": "简短任务描述",
  "category": "code|browser|data|system|research|planning",
  "result": "success|partial|fail",
  "learning_strategy": "probe-first|read-sop|trial-error|plan-first|ask-user",
  "strategies_used": ["file_read_sop", "code_run_test", "web_scan"],
  "what_worked": [],
  "what_didnt": [],
  "key_insight": "一句话关键洞察",
  "time_spent_min": 30,
  "satisfaction": 3,
  "failure_count": 0,
  "tools_used": ["code_run", "file_read", ...]
}
```

### 分类体系

| 类别 | 说明 |
|:-----|:-----|
| code | 编码/调试/重构 |
| browser | 浏览器操作/网页交互 |
| data | 数据分析/处理/可视化 |
| system | 系统配置/环境/部署 |
| research | 调研/学习新知识 |
| planning | 规划/任务分解 |

| 学习策略 | 说明 |
|:---------|:-----|
| probe-first | 先探测环境再行动 |
| read-sop | 先读SOP再执行 |
| trial-error | 快速试错迭代 |
| plan-first | 先做规划再执行 |
| ask-user | 频繁请示用户 |
| subagent-delegate | 委托subagent执行 |

## 每周元分析

每周自动运行 `python tools/learning_log.py --weekly` 生成周报:

1. 统计成功率和满意度的变化趋势
2. 分析哪些策略组合成功率最高
3. 识别耗时最多的任务类型
4. 推荐优化方向 (例如: "code类任务用trial-error策略成功率高但耗时长, 建议改用probe-first")

## 与现有系统集成

| 组件 | 集成方式 |
|:-----|:---------|
| autonomous_operation_sop | 每个任务收尾时自动调用 learning_log 记录会话 |
| plan_sop | 规划态结束后记录一次 "planning" 日志 |
| skills_learning_sop | 每次学习完成后记录策略有效性 |
| inspiration_board | 元分析产出的建议写入灵感板 |

## 元认知仪表盘

运行 `python tools/learning_log.py --dashboard` 输出:

```
=== 元认知仪表盘 ===
最近7天: 12次会话, 成功率75%
最佳策略: "read-sop + probe-first" (成功率100%, 5次)
最耗时: browser类 (平均45min/次)
趋势: 满意度从2.5→4.0 (上升中)
建议: browser类任务建议先读SOP再操作
```

## 初始数据导入

首次运行:
```bash
python tools/learning_log.py --import-history
```
从 `temp/autonomous_reports/history.txt` 解析已有的74条历史记录作为基线。
