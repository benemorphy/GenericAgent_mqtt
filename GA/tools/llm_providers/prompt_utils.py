"""Prompt construction utilities — extracted from ga.py GenericAgentHandler methods.

These are standalone functions that take a handler (or its attributes) as parameter
instead of using self directly.
"""

from tools.utils.ga_utils import fold_earlier


def get_anchor_prompt(handler, skip=False):
    """Build the [WORKING MEMORY] anchor prompt section.
    
    Extracted from GenericAgentHandler._get_anchor_prompt.
    """
    if skip:
        return "\n"
    h = handler.history_info
    W = 30
    earlier = f'<earlier_context>\n{fold_earlier(h[:-W])}\n</earlier_context>\n' if len(h) > W else ""
    h_str = "\n".join(h[-W:])
    prompt = f"\n### [WORKING MEMORY]\n{earlier}<history>\n{h_str}\n</history>"
    prompt += f"\nCurrent turn: {handler.current_turn}\n"
    if handler.working.get('key_info'):
        prompt += f"\n<key_info>{handler.working.get('key_info')}</key_info>"
    if handler.working.get('related_sop'):
        prompt += f"\n有不清晰的地方请再次读取{handler.working.get('related_sop')}"
    if getattr(handler.parent, 'verbose', False):
        try:
            print(prompt)
        except Exception:
            pass
    return prompt
