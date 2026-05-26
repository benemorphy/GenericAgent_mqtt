"""Default Turn Policy Hooks and System Prompt Hooks — extracted from ga.py.

Turn policy functions are now in tools/turn_policy.py (standalone, no handler arg).
This module provides system prompt hooks and the unified register_default_hooks().

Usage in ga.py __init__:
    from tools.hooks_default import register_default_hooks
    register_default_hooks(self)

For custom policies, import from tools.turn_policy:
    from tools.turn_policy import register_turn_policies, policy_danger_ask_user
"""

import os
from tools.ga_utils import consume_file
from tools.turn_policy import (
    register_turn_policies,
    DEFAULT_TURN_POLICIES,
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
    ]
    register_default_plan_validators(handler)
