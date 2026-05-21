"""Turn Policy Module — pluggable turn strategy chain for GenericAgentHandler.

Extracted from ga.py/turn_end_callback: turn policies are standalone functions
that receive (turn, _plan, next_prompt) and return "" or a string to append.

Auto-activation: register_turn_policies(handler) is called by hooks_default's
register_default_hooks(), which is called in ga.py __init__. For manual use:
    from tools.turn_policy import register_turn_policies
    register_turn_policies(handler)
"""

import os


# ── Turn Policy Functions ──

def policy_danger_ask_user(turn, _plan, next_prompt):
    """每75轮强制ask_user（非plan模式）"""
    if turn % 75 == 0 and (not _plan):
        return (
            "\n\n[DANGER] 已连续执行第 {turn} 轮。"
            "必须总结情况进行ask_user，不允许继续重试。"
        )
    return ""


def policy_danger_retry(turn, _plan, next_prompt):
    """每7轮禁止无效重试"""
    if turn % 7 == 0:
        return (
            "\n\n[DANGER] 已连续执行第 {turn} 轮。禁止无效重试。"
            "若无有效进展，必须切换策略：1. 探测物理边界 "
            "2. 请求用户协助。如有需要，可调用 update_working_checkpoint "
            "保存关键上下文。"
        )
    return ""


def policy_inject_memory(turn, _plan, next_prompt):
    """每10轮注入全局记忆（从ga.py惰性导入以避免循环依赖）"""
    if turn % 10 == 0:
        from ga import get_global_memory
        return get_global_memory()
    return ""


def policy_plan_limit(turn, _plan, next_prompt):
    """Plan模式上限检测"""
    if _plan and turn >= 10 and turn % 5 == 0 and turn <= 110:
        return (
            f"[Plan Hint] 正在计划模式。必须 file_read({_plan}) "
            "确认当前步骤，回复开头引用：当前步骤：...\n\n"
        )
    if _plan and turn >= 120:
        return (
            "\n\n[DANGER] Plan模式已运行 {turn} 轮，已达上限。"
            "必须 ask_user 汇报进度并确认是否继续。"
        )
    return ""


# ── Registration ──

# Default turn policy list — used by register_turn_policies()
DEFAULT_TURN_POLICIES = [
    policy_danger_ask_user,
    policy_danger_retry,
    policy_inject_memory,
    policy_plan_limit,
]

POLICY_NAMES = {
    policy_danger_ask_user: "policy_danger_ask_user",
    policy_danger_retry: "policy_danger_retry",
    policy_inject_memory: "policy_inject_memory",
    policy_plan_limit: "policy_plan_limit",
}


def register_turn_policies(handler, policies=None):
    """Register turn policies onto a GenericAgentHandler instance.
    
    Sets handler._turn_policies. Can be called multiple times
    (idempotent if same policies list is passed).
    
    Args:
        handler: GenericAgentHandler instance
        policies: list of callable(turn, _plan, next_prompt) -> str
                  Defaults to DEFAULT_TURN_POLICIES
    """
    from functools import partial
    if policies is None:
        policies = DEFAULT_TURN_POLICIES
    handler._turn_policies = [
        partial(p, handler) if _needs_handler(p) else p
        for p in policies
    ]


def _needs_handler(policy_func):
    """Check if policy function needs handler as first arg.
    
    Functions defined in this module (DEFAULT_TURN_POLICIES) take
    (turn, _plan, next_prompt) directly. External policy functions
    may take (handler, turn, _plan, next_prompt) with a handler param.
    
    Convention: if function name starts with 'policy_' but is NOT
    in DEFAULT_TURN_POLICIES, assume it needs handler.
    """
    if policy_func in DEFAULT_TURN_POLICIES:
        return False
    # Check signature: if first param is not 'turn', needs handler
    import inspect
    try:
        params = list(inspect.signature(policy_func).parameters.keys())
        return len(params) >= 4 and params[0] != 'turn'
    except (ValueError, TypeError):
        return False
