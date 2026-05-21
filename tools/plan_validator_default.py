"""Default Plan Mode validators and policy — pluggable validation chain for GenericAgentHandler

Each validator receives (content, handler) and returns a tuple:
  (yield_message: str, StepOutcome_or_None)
- yield_message: string to yield (empty string if none)
- StepOutcome: short-circuit with this outcome (None to continue chain)

Usage in ga.py __init__:
    from tools.plan_validator_default import register_default_plan_validators
    register_default_plan_validators(self)

This registers both do_no_tool validators and the turn policy hook.
"""

import os, re
from agent_loop import StepOutcome


def _in_plan_mode(handler):
    """Check if handler is in plan mode (stateless utility)."""
    return handler.working.get('in_plan_mode')


def _check_plan_completion(handler):
    """Check plan.md for remaining [ ] items (stateless utility)."""
    plan_path = _in_plan_mode(handler)
    if not plan_path or not os.path.isfile(plan_path):
        return None
    try:
        with open(plan_path, 'r', encoding='utf-8', errors='replace') as f:
            return len(re.findall(r'\[ \]', f.read()))
    except:
        return None


def validator_completion_declaration(content, handler):
    """Intercept premature completion declarations in plan mode.
    
    Detects when agent claims completion without proper VERDICT/VERIFY step.
    """
    if not _in_plan_mode(handler):
        return ("", None)
    if any(kw in content for kw in ['任务完成', '全部完成', '已完成所有', '\U0001f3c1']):
        if 'VERDICT' not in content and '[VERIFY]' not in content and '验证subagent' not in content:
            return ("[Warn] Plan模式完成声明拦截。\n",
                    StepOutcome({}, next_prompt="\u26d4 [验证拦截] 检测到你在plan模式下声称完成，但未执行[VERIFY]验证步骤。请先按plan_sop \u00a7四启动验证subagent，获得VERDICT后才能声称完成。"))
    return ("", None)


def validator_completion_check(content, handler):
    """Check plan.md for remaining incomplete items.
    
    If plan.md has 0 remaining [ ] items, auto-exit plan mode.
    Passes through to allow final response after message.
    """
    if not _in_plan_mode(handler):
        return ("", None)
    remaining = _check_plan_completion(handler)
    if remaining == 0:
        handler.working.pop('in_plan_mode', None)
        return ("[Info] Plan完成：plan.md中0个[ ]残留，退出plan模式。\n", None)
    return ("", None)


def plan_limit_policy(turn, _plan, next_prompt):
    """Plan mode turn limit policy — registered into _turn_policies.
    
    - Every 5 turns after 10: remind agent to check plan.md
    - At 120+ turns: force ask_user for continuation decision
    """
    if _plan and turn >= 10 and turn % 5 == 0 and turn <= 110:
        return f"[Plan Hint] 正在计划模式。必须 file_read({_plan}) 确认当前步骤，回复开头引用：\U0001f4cc 当前步骤：...\n\n"
    if _plan and turn >= 120:
        return f"\n\n[DANGER] Plan模式已运行 {turn} 轮，已达上限。必须 ask_user 汇报进度并确认是否继续。"
    return ""


def register_default_plan_validators(handler):
    """Register all default plan mode plugins onto a GenericAgentHandler instance.
    
    Creates or replaces handler._plan_validators with default set:
        1. validator_completion_declaration — intercept premature completion claims
        2. validator_completion_check — auto-exit plan mode when plan complete
    
    Also registers plan_limit_policy into handler._turn_policies (idempotent).
    """
    # Register do_no_tool validators
    handler._plan_validators = [
        validator_completion_declaration,
        validator_completion_check,
    ]
    # Register turn policy hook (avoid duplicates on re-registration)
    policy_ref = getattr(handler, '_plan_limit_policy_ref', None)
    if policy_ref is not None and policy_ref in handler._turn_policies:
        return  # already registered
    handler._turn_policies.append(plan_limit_policy)
    handler._plan_limit_policy_ref = plan_limit_policy
