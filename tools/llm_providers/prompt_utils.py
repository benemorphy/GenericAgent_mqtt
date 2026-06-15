"""Prompt construction utilities — extracted from ga.py GenericAgentHandler methods.

These are standalone functions that take a handler (or its attributes) as parameter
instead of using self directly.
"""

from tools.utils.ga_utils import fold_earlier


def get_anchor_prompt(handler, skip=False):
    """Build the [WORKING MEMORY] anchor prompt section.
    
    Extracted from GenericAgentHandler._get_anchor_prompt.
    Now includes PDCA task complexity classification and 5W2H display
    (Gliding Horse design integration — P0).
    """
    if skip:
        return "\n"
    h = handler.history_info
    W = 30
    earlier = f'<earlier_context>\n{fold_earlier(h[:-W])}\n</earlier_context>\n' if len(h) > W else ""
    h_str = "\n".join(h[-W:])
    prompt = f"\n### [WORKING MEMORY]\n{earlier}<history>\n{h_str}\n</history>"
    prompt += f"\nCurrent turn: {handler.current_turn}\n"

    # ── P0: PDCA 任务复杂度分级 (Gliding Horse) ──
    pdca_level = handler.working.get('_pdca_level')
    if pdca_level is not None:
        # 检查是否有新用户任务出现（自动重置机制）
        _last_seen = handler.working.get('_last_user_task_idx', -1)
        user_indices = [i for i, e in enumerate(h) if e.startswith('[USER]')]
        if user_indices and user_indices[-1] != _last_seen:
            pdca_level = None  # 新任务到达，重新分级
    if pdca_level is None:
        # 首次或新任务到达: 从 history 中提取用户原始任务描述进行分类
        try:
            from tools.pdca import classify_task_from_history, format_level_badge, get_prompt_instruction, TASK_LEVELS
            pdca_level = classify_task_from_history(h)
            handler.working['_pdca_level'] = pdca_level
            # 记录最后一个用户消息的索引
            user_indices = [i for i, e in enumerate(h) if e.startswith('[USER]')]
            if user_indices:
                handler.working['_last_user_task_idx'] = user_indices[-1]
            badge = format_level_badge(pdca_level)
            instruction = get_prompt_instruction(pdca_level)
            max_turns = TASK_LEVELS.get(pdca_level, {}).get('max_turns', 15)
            prompt += (
                f"\n<PDCA_level>{badge}</PDCA_level>\n"
                f"<PDCA_instruction>\n{instruction}\n</PDCA_instruction>\n"
                f"<PDCA_max_turns>{max_turns}</PDCA_max_turns>\n"
            )
        except ImportError:
            pass  # pdca_classifier not available, skip

    if handler.working.get('key_info'):
        prompt += f"\n<key_info>{handler.working.get('key_info')}</key_info>"

    # ── P0: 5W2H 任务本体 (Gliding Horse) ──
    five_w2h = handler.working.get('five_w2h')
    if five_w2h:
        prompt += "\n<5W2H>\n"
        if isinstance(five_w2h, dict):
            for key in ['what', 'why', 'who', 'when', 'where', 'how', 'how_much']:
                val = five_w2h.get(key)
                if val:
                    prompt += f"  {key}: {val}\n"
        else:
            prompt += f"  {five_w2h}\n"
        prompt += "</5W2H>\n"

    if handler.working.get('related_sop'):
        prompt += f"\n有不清晰的地方请再次读取{handler.working.get('related_sop')}"

    if getattr(handler.parent, 'verbose', False):
        try:
            print(prompt)
        except Exception:
            pass
    return prompt
