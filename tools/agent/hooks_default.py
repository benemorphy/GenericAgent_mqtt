"""Default Turn Policy Hooks and System Prompt Hooks — extracted from ga.py.

Turn policy functions are now in tools/turn_policy.py (standalone, no handler arg).
This module provides system prompt hooks and the unified register_default_hooks().

Usage in ga.py __init__:
    from tools.hooks_default import register_default_hooks
    register_default_hooks(self)

For custom policies, import from tools.turn_policy:
    from tools.agent.turn_policy import register_turn_policies, policy_danger_ask_user
"""

from tools.utils.ga_utils import consume_file
from tools.agent.turn_policy import (
    register_turn_policies,
)


# ── System Prompt Hooks ──

def sph_memory_sop(handler, context):
    """读取memory/SOP文件时注入提示"""
    if context.get('location') == 'file_read':
        path = context.get('path', '')
        if 'memory' in path or 'sop' in path:
            return "\n[SYSTEM TIPS] 正在读取记忆或SOP文件，若决定按sop执行请提取sop中的关键点（特别是靠后的）update working memory."
    return ""


def sph_summary_enforcer(handler, context):
    """缺summary时强制要求"""
    if context.get('location') == 'turn_end' and not context.get('has_summary'):
        return "\n\n\n[SYSTEM] 必须在回复文本中包含<summary>！\n\n"
    return ""


def sph_master_intervention(handler, context):
    """Master干预信息注入（从_intervene文件读取）"""
    if context.get('location') == 'turn_end':
        parent = context.get('parent')
        if parent and hasattr(parent, 'task_dir'):
            injprompt = consume_file(parent.task_dir, '_intervene')
            if injprompt:
                return f"\n\n[MASTER] {injprompt}\n"
    return ""


def sph_gbrain_available(handler, context):
    """告知 Agent 有 gbrain 知识库可用"""
    if context.get('location') == 'system_prompt':
        return """你有 gbrain 知识库可用。它提供以下能力:
  - gbrain_query(query)     → 合成问答，返回带来源引用的答案
  - gbrain_search(query)    → 搜索知识库，返回匹配页面列表
  - gbrain_think(prompt)    → 链式推理，深度分析问题
  - gbrain_graph_query(slug) → 知识图谱遍历，查看实体关系
当需要查阅项目知识、历史记录、做综合推理时优先使用 gbrain。"""
    return ""


def sph_pdca_instruction(handler, context):
    """P0: PDCA 任务复杂度分级 instruction 注入 (Gliding Horse 整合).
    
    在 turn_end 将当前任务的 PDCA 级别和策略注入到下一轮 prompt 中。
    与 get_anchor_prompt 中的 PDCA 分级协同工作（后者注入到 [WORKING MEMORY] 内，
    本钩子作为 fallback: get_anchor_prompt 未触发时自我分级）。
    """
    if context.get('location') != 'turn_end':
        return ""
    pdca_level = handler.working.get('_pdca_level')
    if pdca_level is None:
        # Fallback: 自我分级 (当 get_anchor_prompt 中的分级未触发时)
        try:
            from tools.pdca import classify_task_from_history
            user_task = ""
            h = getattr(handler, 'history_info', [])
            if h:
                pdca_level = classify_task_from_history(h)
                handler.working['_pdca_level'] = pdca_level
        except ImportError:
            return ""
    if pdca_level is not None:
        try:
            from tools.pdca import format_level_badge, get_prompt_instruction, TASK_LEVELS
            badge = format_level_badge(pdca_level)
            max_turns = TASK_LEVELS.get(pdca_level, {}).get('max_turns', 15)
            return (
                f"\n[PDCA 当前级别] {badge} (建议最大 {max_turns} 轮)\n"
            )
        except ImportError:
            pass
    return ""


def register_default_hooks(handler):
    """Register all default hooks onto a GenericAgentHandler instance.
    Sets up _turn_policies (via tools.turn_policy), _system_prompt_hooks, 
    and plan validators (via tools.plan_validator_default).
    Call from __init__: register_default_hooks(self)
    """
    from functools import partial
    from tools.plan_validator_default import register_default_plan_validators
    # Turn policies are now registered via dedicated module
    register_turn_policies(handler)
    handler._system_prompt_hooks = [
        partial(sph_memory_sop, handler),
        partial(sph_summary_enforcer, handler),
        partial(sph_master_intervention, handler),
        partial(sph_gbrain_available, handler),
        partial(sph_pdca_instruction, handler),  # P0: Gliding Horse PDCA
    ]
    register_default_plan_validators(handler)
