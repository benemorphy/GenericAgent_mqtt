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

import os
import re
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
    except (OSError, re.error):
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


def validator_plan_structure(content, handler):
    """Metagent-P: 符号结构验证 — 检查plan.md格式完整性
    
    检测: 缺少必要章节、步骤编号不连续、缺失[VERIFY]入口
    """
    if not _in_plan_mode(handler):
        return ("", None)
    
    plan_path = _in_plan_mode(handler)
    if not plan_path or not os.path.isfile(plan_path):
        return ("", None)
    
    try:
        with open(plan_path, 'r', encoding='utf-8', errors='replace') as f:
            plan_text = f.read()
    except:
        return ("", None)
    
    issues = []
    
    # 1. 检查必要章节
    required_sections = ['探索态', '执行态', '验证', 'VERIFY']
    missing = [s for s in required_sections if s not in plan_text]
    if missing:
        issues.append(f"缺少必要章节: {', '.join(missing)}")
    
    # 2. 检查步骤编号连续性 (找 ### step)
    steps = re.findall(r'###\s+(?:步骤|Step)\s*(\d+)', plan_text, re.IGNORECASE)
    if steps:
        nums = [int(s) for s in steps]
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            issues.append(f"步骤编号不连续: 预期{expected[0]}~{expected[-1]}, 实际{nums}")
    
    # 3. 检查是否包含文件操作步骤但无路径
    if 'file_read' in plan_text or 'file_write' in plan_text or 'code_run' in plan_text:
        if 'plan_path' not in plan_text and 'working_dir' not in plan_text:
            issues.append("包含文件操作但未定义plan_path/working_dir")
    
    # 4. 检查总数估计与步骤数匹配
    est_match = re.search(r'(\d+)\s*(?:步|回合|turn)', plan_text, re.IGNORECASE)
    step_count = len(steps)
    if est_match and step_count > 1:
        estimated = int(est_match.group(1))
        if abs(estimated - step_count * 3) > step_count * 2:
            issues.append(f"步骤数({step_count})与估计回合数({estimated})不匹配")
    
    if issues:
        msg = "\n".join(f"[Metagent-P] {issue}" for issue in issues[:3])
        return (f"[Warn] Plan结构检查发现{len(issues)}个问题:\n{msg}\n",
                StepOutcome({}, next_prompt=f"⚠️ Plan结构验证: {len(issues)}个问题, 请修复:\n{msg}"))
    
    return ("", None)


def validator_path_references(content, handler):
    """Metagent-P: 路径符号验证 — 检查plan中引用的文件路径是否存在"""
    if not _in_plan_mode(handler):
        return ("", None)
    
    plan_path = _in_plan_mode(handler)
    if not plan_path or not os.path.isfile(plan_path):
        return ("", None)
    
    try:
        with open(plan_path, 'r', encoding='utf-8', errors='replace') as f:
            plan_text = f.read()
    except:
        return ("", None)
    
    # 提取所有代码块外的路径引用
    refs = re.findall(r'(?:`|")((?:\.\.?/)?[\w./\\_-]+\.[a-zA-Z]{2,4})(?:`|")', plan_text)
    missing = []
    for ref in refs:
        # 跳过网络路径、模板路径
        if ref.startswith('http') or ref.startswith('{') or 'template' in ref.lower():
            continue
        if os.path.exists(ref):
            continue
        missing.append(ref)
    
    if len(missing) >= 2:  # 至少2个文件不存在才警告
        msg = f"[Metagent-P] {len(missing)}个引用路径不存在: {', '.join(missing[:3])}"
        return (f"[Warn] {msg}\n",
                StepOutcome({}, next_prompt=f"⚠️ 路径验证: {msg}"))
    
    return ("", None)


def validator_syntax_check(content, handler):
    """Metagent-P: 语法验证 — 检查常见的markdown/plan语法错误
    
    检测: 括号不匹配、无效缩进、不一致的分隔符
    """
    if not _in_plan_mode(handler):
        return ("", None)
    
    plan_path = _in_plan_mode(handler)
    if not plan_path or not os.path.isfile(plan_path):
        return ("", None)
    
    try:
        with open(plan_path, 'r', encoding='utf-8', errors='replace') as f:
            plan_text = f.read()
    except:
        return ("", None)
    
    issues = []
    
    # 1. 检查括号匹配
    lines = plan_text.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.count('(') != stripped.count(')'):
            issues.append(f"第{i}行括号不匹配")
        if stripped.count('[') != stripped.count(']'):
            issues.append(f"第{i}行方括号不匹配")
    
    # 2. 检查代码块闭合
    code_fences = plan_text.count('```')
    if code_fences % 2 != 0:
        issues.append("代码块未闭合(```数量为奇数)")
    
    # 3. 检查table格式一致性
    if '|' in plan_text:
        table_lines = [l for l in lines if l.strip().startswith('|')]
        if len(table_lines) >= 3:
            # 检查分隔行
            has_separator = any(re.match(r'\|[\s:-]+\|', l) for l in table_lines)
            if not has_separator:
                issues.append("表格缺少分隔行")
    
    # 4. 检查无效空行过多
    empty_runs = 0
    max_empty = 0
    for line in lines:
        if not line.strip():
            empty_runs += 1
            max_empty = max(max_empty, empty_runs)
        else:
            empty_runs = 0
    if max_empty > 3:
        issues.append(f"存在连续{max_empty}个空行")
    
    if len(issues) > 2:  # 多个语法问题才警告
        msg = "; ".join(issues[:3])
        return (f"[Warn] 语法检查: {len(issues)}个问题 ({msg})\n",
                StepOutcome({}, next_prompt=f"⚠️ 语法验证: 检测到{len(issues)}个语法问题: {msg}"))
    
    return ("", None)


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
        validator_plan_structure,
        validator_path_references,
        validator_syntax_check,
    ]
    # Register turn policy hook (avoid duplicates on re-registration)
    policy_ref = getattr(handler, '_plan_limit_policy_ref', None)
    if policy_ref is not None and policy_ref in handler._turn_policies:
        return  # already registered
    handler._turn_policies.append(plan_limit_policy)
    handler._plan_limit_policy_ref = plan_limit_policy
