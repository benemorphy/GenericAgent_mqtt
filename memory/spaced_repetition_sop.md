# 间隔重复 SOP — 技能复习巩固

> 核心理念: 学过的技能如果不复习, 遗忘曲线会快速衰减
> 间隔重复: 1d -> 3d -> 7d -> 14d -> 30d -> 90d -> 365d
> 每次复习用 assess.py 验证, 通过则进入下一间隔, 失败则缩短间隔

## 复习间隔算法

| 等级 | 间隔   | 说明                 |
|:----:|:------:|:---------------------|
| L0   | 1d     | 刚学完, 次日复习     |
| L1   | 3d     | 短期记忆巩固         |
| L2   | 7d     | 一周后               |
| L3   | 14d    | 两周后               |
| L4   | 30d    | 一个月后             |
| L5   | 90d    | 季度复习             |
| L6   | 365d   | 年度复习 (已掌握)    |

## 等级升降规则

- **通过** (score >= 80): level += 1 (上限 L6)
- **部分通过** (50 <= score < 80): level 不变 (保持当前间隔)
- **失败** (score < 50): level -= 1 (下限 L0)
- **连续失败** (连续2次 score < 50): 重置为 L0, 并标记需补学

## 数据结构

复习跟踪文件: `skills_learning/.review_tracker.json`

```json
{
  "version": 1,
  "last_updated": "2026-05-20",
  "skills": {
    "agentDreaming-rev1": {
      "skill": "agentDreaming",
      "rev": 1,
      "level": 2,
      "last_review": "2026-05-20",
      "next_review": "2026-05-27",
      "last_score": 95,
      "consecutive_fails": 0,
      "history": [
        {"date": "2026-05-19", "score": 100},
        {"date": "2026-05-20", "score": 95}
      ]
    }
  }
}
```

## 工具

复习由 `tools/skill_review.py` 执行，用法:

```bash
# 检查所有到期技能并复习
python tools/skill_review.py

# 仅列出到期技能(不执行复习)
python tools/skill_review.py --list-due

# 强制复习指定技能
python tools/skill_review.py --force agentDreaming docker_compose

# 初始化所有已有技能到跟踪器(首次使用)
python tools/skill_review.py --init

# 查看统计
python tools/skill_review.py --stats
```

## 调用流程

```
定时任务 (sche_tasks/skill_review.json)
  -> 触发 Agent
    -> Agent 运行 python tools/skill_review.py
      -> 读取 .review_tracker.json
      -> 找出所有 next_review <= today 的技能
      -> 对每个到期技能:
          1. 运行 skills_learning/{skill}/rev{N}/tools/assess.py
          2. 解析评分结果
          3. 按升降规则更新等级和 next_review
          4. 记录到 history
      -> 写回 .review_tracker.json
      -> 生成复习报告
    -> Agent 将报告写入 sche_tasks/done/
```

## 避坑指南

1. **不要在同一天重复复习同一技能** — 即使手动触发, 工具也会跳过当天已复习的
2. **assess.py 故障** 时 (如 LLM 不可用), 标记为 "跳过" 并保留原间隔, 不视为失败
3. **新技能自动注册**: 首次运行 `--init` 或每次 `skills_learning_sop` 完成学习后自动调用 `python tools/skill_review.py --register <skill> <rev>`
4. **忘得快的技能**: 如果某技能连续3次在 L0/L1 失败, 输出警告并建议重新学习

## 与现有系统的集成

| 组件 | 关系 |
|:-----|:-----|
| skills_learning_sop | 学习完成后自动调用 `--register` 注册新技能 |
| scheduled_task_sop | 通过 skill_review.json 每日触发复习 |
| agent_dreaming_sop | 梦境中可发现被遗忘的技能, 触发复习 |
| memory_cleanup_sop | 复习成功的模式可压缩进入 L1/L2 |
