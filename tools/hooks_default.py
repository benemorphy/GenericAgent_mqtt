"""Default Turn Policy Hooks and System Prompt Hooks — extracted from ga.py.

These are standalone functions that take (handler, ...) instead of (self, ...).
ga.py __init__ uses functools.partial to bind handler when registering.

Usage in ga.py __init__:
    from functools import partial
    from tools.hooks_default import (
        policy_danger_ask_user, policy_danger_retry, policy_inject_memory,
        sph_memory_sop, sph_summary_enforcer, sph_master_intervention,
    )
    self._turn_policies = [
        partial(policy_danger_ask_user, self),
        partial(policy_danger_retry, self),
        partial(policy_inject_memory, self),
    ]
    self._system_prompt_hooks = [
        partial(sph_memory_sop, self),
        partial(sph_summary_enforcer, self),
        partial(sph_master_intervention, self),
    ]
"""

import os
from tools.ga_utils import consume_file


# ── Turn Policy Hooks ──

def policy_danger_ask_user(handler, turn, _plan, next_prompt):
    """每75轮强制ask_user（非plan模式）"""
    if turn % 75 == 0 and (not _plan):
        return f"\n\n[DANGER] 已连续执行第 {turn} 轮。必须总结情况进行ask_user，不允许继续重试。"
    return ""


def policy_danger_retry(handler, turn, _plan, next_prompt):
    """每7轮禁止无效重试"""
    if turn % 7 == 0:
        return f"\n\n[DANGER] 已连续执行第 {turn} 轮。禁止无效重试。若无有效进展，必须切换策略：1. 探测物理边界 2. 请求用户协助。如有需要，可调用 update_working_checkpoint 保存关键上下文。"
    return ""


def policy_inject_memory(handler, turn, _plan, next_prompt):
    """每10轮注入全局记忆"""
    if turn % 10 == 0:
        return _get_global_memory()
    return ""


def _get_global_memory():
    """读取全局记忆并格式化（原 ga.py 模块级函数 get_global_memory）"""
    prompt = "\n"
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        suffix = '_en' if os.environ.get('GA_LANG', '') == 'en' else ''
        with open(os.path.join(script_dir, 'memory/global_mem_insight.txt'), 'r', encoding='utf-8', errors='replace') as f:
            insight = f.read()
        with open(os.path.join(script_dir, f'assets/insight_fixed_structure{suffix}.txt'), 'r', encoding='utf-8') as f:
            structure = f.read()
        prompt += f'cwd = {os.path.join(script_dir, "temp")} (./)\n'
        prompt += f"\n[Memory] (../memory)\n"
        prompt += structure + '\n../memory/global_mem_insight.txt:\n'
        prompt += insight + "\n"
    except FileNotFoundError:
        pass
    return prompt


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
    Sets up _turn_policies, _system_prompt_hooks, and plan validators.
    Call from __init__: register_default_hooks(self)
    """
    from functools import partial
    from tools.plan_validator_default import register_default_plan_validators
    handler._turn_policies = [
        partial(policy_danger_ask_user, handler),
        partial(policy_danger_retry, handler),
        partial(policy_inject_memory, handler),
    ]
    handler._system_prompt_hooks = [
        partial(sph_memory_sop, handler),
        partial(sph_summary_enforcer, handler),
        partial(sph_master_intervention, handler),
    ]
    register_default_plan_validators(handler)
