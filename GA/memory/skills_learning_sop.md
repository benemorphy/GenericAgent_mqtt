# skill_learn SOP — 案例驱动技能学习CLI工具
#
# 位置: tools/skill_learn_from_cases_full/
# 调用: python -m tools.skill_learn_from_cases_full "skill_name"
# 依赖: skill_search (105K+ skill卡), metaso_search (Web搜索)
#
# 功能: 5阶段全自动学习
#   Phase 0: 创建 skills_learning/{skill}/revN/ 目录
#   Phase 1: skill_search 查前置知识
#   Phase 2: 双渠道案例采集(skill_search + metaso_search)
#   Phase 3: 提炼知识模式(继承历史+新增)
#   Phase 4: 生成验证工具(tools/assess.py)
#   Phase 5: 运行验证 → 评分报告
#
# 使用示例:
#   python -m tools.skill_learn_from_cases_full "docker_compose_production"
#   python -m tools.skill_learn_from_cases_full --list
#   python -m tools.skill_learn_from_cases_full "xxx" --dry-run
#
# 技能库: GA根目录/skills_learning/{skill_name}/revN/
# 已有技能: docker_compose_production (rev1~7)
