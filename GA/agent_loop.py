import json
import re
import os
import logging
from dataclasses import dataclass
from typing import Any, Optional

# P4: Lineage 审计导入 (try/except 确保不阻塞)
try:
    from tools.observability.lineage_tracer import lt as _lt
    _LINEAGE_AVAIL = True
except Exception:
    _LINEAGE_AVAIL = False

# ── SquillaRouter 集成 ──────────────────────────────────
_ROUTER_ENABLED = False  # 可通过环境变量 SQUILLA_ROUTER=1 开启
_ROUTER = None

def _init_router():
    global _ROUTER, _ROUTER_ENABLED
    if _ROUTER is not None:
        return
    try:
        from squilla_router import CascadeRouter, get_router
        _ROUTER = get_router()
        _ROUTER_ENABLED = os.environ.get("SQUILLA_ROUTER", "").lower() in ("1", "true", "yes")
        if _ROUTER_ENABLED:
            logging.getLogger(__name__).info("[Router] SquillaRouter enabled")
    except ImportError as e:
        logging.getLogger(__name__).debug(f"[Router] squilla_router not available: {e}")
        _ROUTER = None
@dataclass
class StepOutcome:
    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False
def try_call_generator(func, *args, **kwargs):
    ret = func(*args, **kwargs)
    if hasattr(ret, '__iter__') and not isinstance(ret, (str, bytes, dict, list)): ret = yield from ret
    return ret

class BaseHandler:
    def tool_before_callback(self, tool_name, args, response): pass
    def tool_after_callback(self, tool_name, args, response, ret): pass
    def turn_end_callback(self, response, tool_calls, tool_results, turn, next_prompt, exit_reason): return next_prompt
    def dispatch(self, tool_name, args, response, index=0, tool_num=1):
        # P1: Registry 优先查找
        try:
            from tools.agent.registry import TOOL as _TOOL
            _reg_fn = _TOOL.get_function(tool_name)
            if _reg_fn:
                args['_index'] = index; args['_tool_num'] = tool_num
                prer = yield from try_call_generator(self.tool_before_callback, tool_name, args, response)
                ret = _reg_fn(args, response)
                if hasattr(ret, '__next__') or hasattr(ret, '__iter__'):
                    ret = yield from ret
                _ = yield from try_call_generator(self.tool_after_callback, tool_name, args, response, ret)
                # P4: Lineage 审计
                if _LINEAGE_AVAIL:
                    try:
                        _lt.trace(turn_id=str(time.time()), action=f"tool_{tool_name}",
                                  agent="reg", context={}, result=str(ret)[:100], duration_ms=0)
                    except Exception:
                        pass
                return ret
        except ImportError:
            pass
        
        method_name = f"do_{tool_name}"
        if hasattr(self, method_name):
            args['_index'] = index; args['_tool_num'] = tool_num
            prer = yield from try_call_generator(self.tool_before_callback, tool_name, args, response)
            ret = yield from try_call_generator(getattr(self, method_name), args, response)
            _ = yield from try_call_generator(self.tool_after_callback, tool_name, args, response, ret)
            # P4: Lineage 审计
            if _LINEAGE_AVAIL:
                try:
                    _lt.trace(turn_id=str(time.time()), action=f"tool_{tool_name}",
                              agent="handler", context={"method": method_name},
                              result=str(ret)[:100], duration_ms=0)
                except Exception:
                    pass
            return ret
        elif tool_name == 'bad_json': return StepOutcome(None, next_prompt=args.get('msg', 'bad_json'), should_exit=False)
        else:
            yield f"未知工具: {tool_name}\n"
            return StepOutcome(None, next_prompt=f"未知工具 {tool_name}", should_exit=False)

def json_default(o): return list(o) if isinstance(o, set) else str(o)
def exhaust(g):
    try: 
        while True: next(g)
    except StopIteration as e: return e.value

def get_pretty_json(data):
    if isinstance(data, dict) and "script" in data:
        data = data.copy(); data["script"] = data["script"].replace("; ", ";\n  ")
    return json.dumps(data, indent=2, ensure_ascii=False).replace('\\n', '\n')

def agent_runner_loop(client, system_prompt, user_input, handler, tools_schema, max_turns=40, verbose=True, initial_user_content=None, yield_info=False):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_user_content if initial_user_content is not None else user_input}
    ]
    turn = 0;  handler.max_turns = max_turns
    _init_router()
    while turn < handler.max_turns:
        turn += 1; turnstr = f'LLM Running (Turn {turn}) ...'
        if handler.parent.task_dir: turnstr = f'Turn {turn} ...'
        if verbose: turnstr = f'**{turnstr}**'
        if yield_info: yield {'turn': turn}
        yield f"\n\n{turnstr}\n\n"

        # ── SquillaRouter: 每轮自动路由决策 ──────────────────
        if _ROUTER_ENABLED and _ROUTER is not None:
            try:
                # 提取本轮文本做路由
                curr_text = ""
                for m in reversed(messages):
                    if isinstance(m.get('content'), str):
                        curr_text = m['content']
                        break
                    elif isinstance(m.get('content'), list):
                        for block in m['content']:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                curr_text = block.get('text', '')
                                break
                        if curr_text:
                            break
                decision = _ROUTER.decide(
                    current_text=curr_text,
                    history_texts=[str(m.get('content',''))[:200] for m in messages[-6:-1]],
                )
                # 如果路由推荐的模型与当前不同，切换模型
                if decision.model != client.model:
                    old_model = client.model
                    client.switch_model(decision.model, decision.tier)
                    if verbose:
                        latency = f"{decision.latency_ms:.0f}" if decision.latency_ms else "?"
                        yield f"[Router] {old_model} -> {decision.model} (tier={decision.tier}, traj={decision.trajectory}, {latency}ms)\n\n"
                else:
                    # 埋点: 路由决策但无需切换
                    if verbose:
                        yield f"[Router] keep {client.model} (tier={decision.tier}, traj={decision.trajectory})\n\n"
            except Exception as e:
                logging.getLogger(__name__).warning(f"[Router] decision error: {e}")

        if turn%10 == 0: client.last_tools = ''  # 每10轮重置一次工具描述，避免上下文过大导致的模型性能下降
        response_gen = client.chat(messages=messages, tools=tools_schema)
        if verbose:
            response = yield from response_gen
            yield '\n\n'
        else:
            response = exhaust(response_gen)
            cleaned = _clean_content(response.content)
            if cleaned: yield cleaned + '\n'

        if not response.tool_calls: tool_calls = [{'tool_name': 'no_tool', 'args': {}}]
        else: tool_calls = [{'tool_name': tc.function.name, 'args': json.loads(tc.function.arguments), 'id': tc.id}
                          for tc in response.tool_calls]
       
        tool_results = []; next_prompts = set(); exit_reason = {}
        for ii, tc in enumerate(tool_calls):
            tool_name, args, tid = tc['tool_name'], tc['args'], tc.get('id', '')
            if tool_name == 'no_tool': pass
            else: 
                if verbose: yield f"🛠️ Tool: `{tool_name}`  📥 args:\n````text\n{get_pretty_json(args)}\n````\n"
                else: yield f"🛠️ {tool_name}({_compact_tool_args(tool_name, args)})\n\n\n"
            handler.current_turn = turn
            gen = handler.dispatch(tool_name, args, response, index=ii, tool_num=len(tool_calls))
            try:
                v = next(gen)
                def proxy(): yield v; return (yield from gen)
                if verbose: yield '`````\n'
                outcome = (yield from proxy()) if verbose else exhaust(proxy())
                if verbose: yield '`````\n'
            except StopIteration as e: outcome = e.value
            
            if outcome.should_exit: 
                exit_reason = {'result': 'EXITED', 'data': outcome.data}; break
            if not outcome.next_prompt: 
                exit_reason = {'result': 'CURRENT_TASK_DONE', 'data': outcome.data}; break
            if outcome.next_prompt.startswith('未知工具'): client.last_tools = ''
            if outcome.data is not None and tool_name != 'no_tool': 
                datastr = json.dumps(outcome.data, ensure_ascii=False, default=json_default) if type(outcome.data) in [dict, list] else str(outcome.data) 
                tool_results.append({'tool_use_id': tid, 'content': datastr})
            next_prompts.add(outcome.next_prompt)
        if len(next_prompts) == 0 or exit_reason:
            if len(handler._done_hooks) == 0 or exit_reason.get('result', '') == 'EXITED': break
            next_prompts.add(handler._done_hooks.pop(0))
        next_prompt = handler.turn_end_callback(response, tool_calls, tool_results, turn, '\n'.join(next_prompts), exit_reason)
        messages = [{"role": "user", "content": next_prompt, "tool_results": tool_results}]   # just new message, history is kept in *Session
    if exit_reason: handler.turn_end_callback(response, tool_calls, tool_results, turn, '', exit_reason)
    return exit_reason or {'result': 'MAX_TURNS_EXCEEDED'}

def _clean_content(text):
    if not text: return ''
    def _shrink_code(m):
        lines = m.group(0).split('\n')
        lang = lines[0].replace('```','').strip()
        body = [l for l in lines[1:-1] if l.strip()]
        if len(body) <= 6: return m.group(0)
        preview = '\n'.join(body[:5])
        return f'```{lang}\n{preview}\n  ... ({len(body)} lines)\n```'
    text = re.sub(r'```[\s\S]*?```', _shrink_code, text)
    for p in [r'<file_content>[\s\S]*?</file_content>', r'<tool_(?:use|call)>[\s\S]*?</tool_(?:use|call)>', r'(\r?\n){3,}']:
        text = re.sub(p, '\n\n' if '\\n' in p else '', text)
    return text.strip()

def _compact_tool_args(name, args):
    a = {k: v for k, v in args.items() if k != '_index'}
    for k in ('path',): 
        if k in a: a[k] = os.path.basename(a[k])
    if name == 'update_working_checkpoint': s = a.get('key_info', ''); return (s[:60]+'...') if len(s)>60 else s
    if name == 'ask_user':
        q = str(a.get('question', ''))
        cs = a.get('candidates') or []
        if cs: q += '\ncandidates:\n' + '\n'.join(f'- {c}' for c in cs)
        return q
    s = json.dumps(a, ensure_ascii=False); return (s[:120]+'...') if len(s)>120 else s
