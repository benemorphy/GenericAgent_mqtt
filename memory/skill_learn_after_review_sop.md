# skill_learn_after_review_sop — 每轮总结后触发技能学习
#
# 适用: 任何一轮任务完成后，总结出经验教训时，立即提取技能关键词并使用CLI工具学习
# 触发条件: [每轮结束后] 有明确的经验教训/失败原因/新发现可提炼为技能
# 关联: skills_learning_sop (CLI工具详情)

## 1. Usage(使用方式)
#
# 命令格式:
#   1. 从经验教训中提取技能关键词（中文名，简短精准，如"网络服务错误链条排查"）
#   2. 调用 CLI 工具：
#      python -m tools.skill_learn_from_cases_full "技能名"
#   3. 可选参数：
#      --dry-run  预览（确认技能目录名和流程）
#      --list     查看已学技能
#      --force    强制刷新案例缓存
#
# 示例（来自今日实操）:
#   python -m tools.skill_learn_from_cases_full "网络服务错误链条排查"
#   python -m tools.skill_learn_from_cases_full "服务端与客户端通信链路与程序调用关系"

## 2. Workflow(工作流 — 核心)

### Phase A: 触发 — 总结经验教训后立即评估
#
#   条件: 当前轮次结束，有经验教训产出
#   执行:
#     [若经验教训涉及可被系统化的知识/模式]
#       1. 从经验教训中提取 1-3 个技能关键词
#       2. 每个关键词应是独立、可学习的技能领域
#       3. 关键词命名原则：简短精准的中文名，不超过15字
#       -> 进入 Phase B
#     [若纯属一次性偶发问题，无可复现模式]
#       -> 跳过，仅记录到 memory
#
#   注意:
#     - 不要强行学习，只对确实有模式总结价值的经验触发
#     - 同一会话中已学过的技能不再重复
#     - 今日（2026-05-30）已学两个技能可作为参考示例

### Phase B: 技能学习执行
#
#   1. 对每个提取的技能关键词，依次执行:
#      python -m tools.skill_learn_from_cases_full "技能名"
#
#   2. 首次学习前建议先用 --dry-run 确认:
#      python -m tools.skill_learn_from_cases_full "技能名" --dry-run
#
#   条件分支:
#     [分支 A — 全新技能]: CLI 自动创建 skills_learning/{skill}/rev1/
#       等待完成（通常 60-300s），检查最终评分
#     [分支 B — 已有技能续学]: CLI 自动创建 revN+1，继承已有模式再扩展
#       等待完成，检查评分是否提升
#     [分支 C — CLI 超时/报错]:
#       -> 检查 tools/skill_learn_from_cases_full/ 模块是否存在
#       -> 检查虚拟环境依赖是否齐全
#       -> 降级：手动执行其各 Phase

### Phase C: 结果确认与记录
#
#   条件分支:
#     [评分 >= 80]: 技能学习成功
#       - 记录技能名称、版本、评分到全局记忆
#       - 技能报告位置: skills_learning/{skill}/revN/reports/
#     [评分 < 80]: 学习质量不足
#       - 评估原因（案例不足？命名不合适？）
#       - 考虑调整技能关键词重新学习
#     [完全失败]: CLI 报错
#       - 记录错误到 memory
#       - 不阻塞主流程，继续后续任务

## 3. 错误处理
#
#   [CLI 找不到模块]
#     原因: PYTHONPATH 未包含 GA 根目录
#     处理: cd GA_ROOT && python -m tools.skill_learn_from_cases_full "技能名"
#
#   [CLI 超时 (300s)]
#     原因: Phase 2 案例采集时网络请求阻塞
#     处理: 重试；若持续超时则降级跳过
#
#   [技能名含特殊字符导致路径异常]
#     处理: 用简短中文名，避免 / \ : * ? " < > | 等字符
#
#   [评分低但经验教训确实有价值]
#     处理: 尝试用更精准的关键词或英文名重新学习
#
#   [非归因经验] 经验教训无法映射到可学习技能
#     处理: 直接归档为记忆，不触发学习

## 4. 输出格式
#
#   学习完成后输出摘要:
#
#   ## 技能学习: {技能名} rev{N}
#   - 评分: {score}/100
#   - 模式数: {N}个
#   - 报告: skills_learning/{skill}/rev{N}/reports/learning_report.md
#   - 关键模式: (列出 Top 3 最有价值模式)
#
#   同时更新全局记忆：
#   ../memory/global_mem.txt 的 L1/L2 层级追加技能索引

## 5. Approval Gates(批准门)
#
#   [执行学习] - 可直接做（CLI 只读+创建技能文件，不影响运行环境）
#   [更改技能库文件] - 需确认
#   [多个技能连续学习] - 如果超过 3 个技能，先询问用户优先级
#
#   [写操作] 技能学习工具会自动在 skills_learning/ 下创建目录
#            这是预期行为，无需额外确认

## 6. Reference(参考)
#
# - skills_learning_sop: CLI 工具详细说明和各 Phase 解释
# - 今日示例:
#   * "网络服务错误链条排查" → rev1, 100分, 11个模式
#   * "服务端与客户端通信链路与程序调用关系" → rev2, 100分, 13个模式
# - 工具位置: tools/skill_learn_from_cases_full/
