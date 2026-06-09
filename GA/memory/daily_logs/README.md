# L3.5 Daily Decision Logs — 默认记忆层级

> **默认行为**：每轮任务收尾时，Agent 必须显式判断是否需要写 L3.5 日志。
> 这是 GA Agent 的默认记忆层级（Rule #15），位于 L3 SOP/工具层 与 L4 原始会话层 之间。

# L3.5 Daily Decision Logs

> 位于 L3 SOP/工具层 与 L4 原始会话层 之间的 reviewed 日志层。

## 定位

- 每天一个文件：`YYYY-MM-DD.md`
- 只记已验证结论、明确决策点、任务完成闭环、未来可复用规则候选
- 不记完整对话、工具流水账、未验证猜测、密钥信息

## 单条日志模板

```markdown
## HH:MM:SS | 主题

meta:
  type: daily_decision_log
  date: YYYY-MM-DD
  topic: 主题
  tags: [tag1, tag2]
  status: decided
  upgrade: none

### 结论
一句话最终结论

### 关键决策
- 决策1
- 决策2

### 后续行动
- 下一步1
- 下一步2

### 候选升级
- none / L2 / L3 / L1
```

## 升级规则

- 出现1次 → 留日志
- 跨会话长期有效 → 候选 L2 事实
- 可复用流程 / 重复2+次 → 候选 L3 SOP
- 高频行为红线 → 候选 L1 RULES

## 检索策略

用户问历史决策时优先查 `daily_logs/`，再查 L4 raw sessions。
