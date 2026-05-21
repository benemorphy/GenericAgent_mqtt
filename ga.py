import sys, os, re, json, time
from tools.ga_utils import format_error, log_memory_access, expand_file_refs, smart_format, consume_file, scan_files, fold_earlier, extract_robust_content
from tools.prompt_utils import get_anchor_prompt
from tools.tool_definitions import code_run, ask_user, web_scan, web_execute_js, file_patch, file_read
if sys.stdout is None: sys.stdout = open(os.devnull, "w")
if sys.stderr is None: sys.stderr = open(os.devnull, "w")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_loop import BaseHandler, StepOutcome, json_default
script_dir = os.path.dirname(os.path.abspath(__file__))
class GenericAgentHandler(BaseHandler):
    '''Generic Agent 工具库，包含多种工具的实现。工具函数自动加上了 do_ 前缀。实际工具名没有前缀。'''
    def __init__(self, parent, last_history=None, cwd='./temp'):
        self.parent = parent
        self.working = {}
        self.cwd = cwd;  self.current_turn = 0
        self.history_info = last_history if last_history else []
        self.code_stop_signal = []
        self._done_hooks = []
        # Register default hooks (turn policies, system prompt hooks, plan validators)
        from tools.hooks_default import register_default_hooks
        register_default_hooks(self)
        # 约束仪表盘 — 执行中的预算状态感知
        from tools.constraint_dashboard import ConstraintDashboard
        self._constraint_dashboard = ConstraintDashboard()

    def _get_abs_path(self, path):
        if not path: return ""
        return os.path.abspath(os.path.join(self.cwd, path))   

    def _extract_code_block(self, response, code_type):
        code_type = {'python':'python|py', 'powershell':'powershell|ps1|pwsh', 'bash':'bash|sh|shell'}.get(code_type, re.escape(code_type))
        matches = re.findall(rf"```(?:{code_type})\n(.*?)\n```", response.content, re.DOTALL)
        return matches[-1].strip() if matches else None

    def do_code_run(self, args, response):
        '''执行代码片段，有长度限制，不允许代码中放大量数据，如有需要应当通过文件读取进行。'''
        code_type = args.get("type", "python")
        code = args.get("code") or args.get("script")
        if not code:
            code = self._extract_code_block(response, code_type)
            if not code: return StepOutcome("[Error] Code missing. Must use reply code block or 'script' arg.", next_prompt="\n")
        try: timeout = int(args.get("timeout", 60))
        except (ValueError, TypeError): timeout = 60
        raw_path = os.path.join(self.cwd, args.get("cwd", './'))
        cwd = os.path.normpath(os.path.abspath(raw_path))
        code_cwd = os.path.normpath(self.cwd)
        maxlen = 10000 // args.get('_tool_num', 1)
        if code_type == 'python' and args.get("inline_eval"):
            ns = {'handler':self, 'parent':self.parent, 'history':json.dumps(self.parent.llmclient.backend.history)}
            old_cwd = os.getcwd()
            try:
                os.chdir(cwd)
                try:
                    try: result = repr(eval(code, ns))
                    except SyntaxError: exec(code, ns); result = ns.get('_r', 'OK')
                except Exception as e: result = f'Error: {e}'
            finally: os.chdir(old_cwd)
        else: result = yield from code_run(code, code_type, timeout, cwd, code_cwd=code_cwd, stop_signal=self.code_stop_signal, maxlen=maxlen)
        next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
        return StepOutcome(result, next_prompt=next_prompt)
    
    def do_ask_user(self, args, response):
        question = args.get("question", "请提供输入：")
        candidates = args.get("candidates", [])
        result = ask_user(question, candidates)
        yield f"Waiting for your answer ...\n"
        return StepOutcome(result, next_prompt="", should_exit=True)
    
    def do_web_scan(self, args, response):
        '''获取当前页面内容和标签页列表。也可用于切换标签页。
        注意：HTML经过简化，边栏/浮动元素等可能被过滤。如需查看被过滤的内容请用execute_js。
        tabs_only=true时仅返回标签页列表，不获取HTML（省token）'''
        tabs_only = args.get("tabs_only", False)
        switch_tab_id = args.get("switch_tab_id", None)
        text_only = args.get("text_only", False)
        maxlen = 35000 // args.get('_tool_num', 1)
        result = web_scan(tabs_only=tabs_only, switch_tab_id=switch_tab_id, text_only=text_only, maxlen=maxlen)
        content = result.pop("content", None)
        yield f'[Info] {str(result)}\n'
        if content: result = json.dumps(result, ensure_ascii=False, default=json_default) + f"\n```html\n{content}\n```"
        next_prompt = "\n"
        return StepOutcome(result, next_prompt=next_prompt)
    
    def do_web_execute_js(self, args, response):
        '''web情况下的优先使用工具，执行任何js达成对浏览器的*完全*控制。支持将结果保存到文件供后续读取分析。'''
        script = args.get("script", "") or self._extract_code_block(response, "javascript")
        if not script: return StepOutcome("[Error] Script missing. Use ```javascript block or 'script' arg.", next_prompt="\n")
        abs_path = self._get_abs_path(script.strip())
        if os.path.isfile(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f: script = f.read()
        save_to_file = args.get("save_to_file", "")
        switch_tab_id = args.get("switch_tab_id") or args.get("tab_id")
        no_monitor = args.get("no_monitor", False)
        result = web_execute_js(script, switch_tab_id=switch_tab_id, no_monitor=no_monitor)
        if save_to_file and "js_return" in result:
            content = str(result["js_return"] or '')
            abs_path = self._get_abs_path(save_to_file)
            result["js_return"] = smart_format(content, max_str_len=170)
            try:
                with open(abs_path, 'w', encoding='utf-8') as f: f.write(str(content))
                result["js_return"] += f"\n\n[已保存完整内容到 {abs_path}]"
            except OSError: result['js_return'] += f"\n\n[保存失败，无法写入文件 {abs_path}]"
        show = smart_format(json.dumps(result, ensure_ascii=False, indent=2, default=json_default), max_str_len=300)
        try: print("Web Execute JS Result:", show)
        except Exception: pass
        yield f"JS 执行结果:\n{show}\n"
        next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
        result = json.dumps(result, ensure_ascii=False, default=json_default)
        maxlen = 8000 // args.get('_tool_num', 1)
        return StepOutcome(smart_format(result, max_str_len=maxlen), next_prompt=next_prompt)
    
    def do_file_patch(self, args, response):
        path = self._get_abs_path(args.get("path", ""))
        yield f"[Action] Patching file: {path}\n"
        old_content = args.get("old_content", "")
        new_content = args.get("new_content", "")
        try: new_content = expand_file_refs(new_content, base_dir=self.cwd)
        except ValueError as e:
            yield f"[Status] ❌ 引用展开失败: {e}\n"
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")
        result = file_patch(path, old_content, new_content)
        yield f"\n{str(result)}\n"
        next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
        return StepOutcome(result, next_prompt=next_prompt)
    
    def do_file_write(self, args, response):
        '''用于对整个文件的大量处理，精细修改要用file_patch。
        需要将要写入的内容放在<file_content>标签内，或者放在代码块中'''
        path = self._get_abs_path(args.get("path", ""))
        mode = args.get("mode", "overwrite")  # overwrite/append/prepend
        action_str = {"prepend": "Prepending to", "append": "Appending to"}.get(mode, "Overwriting")
        yield f"[Action] {action_str} file: {os.path.basename(path)}\n"

        content = args.get('content') or extract_robust_content(response.content)
        if not content:
            yield f"[Status] ❌ 失败: 未在回复中找到<file_content>代码块内容\n"
            return StepOutcome({"status": "error", "msg": "No content found. Blank is not supported. Put content inside <file_content>...</file_content> tags in your reply body before call file_write."}, next_prompt="\n")
        try:
            new_content = expand_file_refs(content, base_dir=self.cwd)
            if mode == "prepend":
                old = open(path, 'r', encoding="utf-8").read() if os.path.exists(path) else ""
                open(path, 'w', encoding="utf-8").write(new_content + old)
            else:
                with open(path, 'a' if mode == "append" else 'w', encoding="utf-8") as f: f.write(new_content)
            yield f"[Status] ✅ {mode.capitalize()} 成功 ({len(new_content)} bytes)\n"
            next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
            return StepOutcome({"status": "success", 'writed_bytes': len(new_content)}, next_prompt=next_prompt)
        except Exception as e:
            yield f"[Status] ❌ 写入异常: {str(e)}\n"
            return StepOutcome({"status": "error", "msg": str(e)}, next_prompt="\n")
        
    def do_file_read(self, args, response):
        '''读取文件内容。从第start行开始读取。如有keyword则返回第一个keyword(忽略大小写)周边内容'''
        path = self._get_abs_path(args.get("path", ""))
        yield f"\n[Action] Reading file: {path}\n"
        start = args.get("start", 1)
        count = args.get("count", 200)
        keyword = args.get("keyword")
        show_linenos = args.get("show_linenos", True)
        result = file_read(path, start=start, keyword=keyword,
                           count=count, show_linenos=show_linenos)
        if show_linenos and not result.startswith("Error:"): result = '由于设置了show_linenos，以下返回信息为：(行号|)内容 。\n' + result 
        if ' ... [TRUNCATED]' in result: result += '\n\n（某些行被截断，如需完整内容可改用 code_run 读取）'
        maxlen = 15000 // args.get('_tool_num', 1)
        result = smart_format(result, max_str_len=maxlen, omit_str='\n\n[omitted long content]\n\n')
        next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
        log_memory_access(path)
        for hook in self._system_prompt_hooks:
            next_prompt += hook({'location': 'file_read', 'path': path}) or ""
        return StepOutcome(result, next_prompt=next_prompt)
    
    def enter_plan_mode(self, plan_path): 
        """Public API: enter plan mode. Called via code_run inline_eval per plan_sop."""
        self.working['in_plan_mode'] = plan_path; self.max_turns = 100
        print(f"[Info] Entered plan mode with plan file: {plan_path}"); return plan_path
    
    def do_update_working_checkpoint(self, args, response):
        '''为整个任务设定后续需要临时记忆的重点。'''
        key_info = args.get("key_info", "")
        related_sop = args.get("related_sop", "")
        if "key_info" in args: self.working['key_info'] = key_info
        if "related_sop" in args: self.working['related_sop'] = related_sop
        self.working['passed_sessions'] = 0
        yield f"[Info] Updated key_info and related_sop.\n"
        next_prompt = get_anchor_prompt(self, skip=args.get('_index', 0) > 0)
        #next_prompt += '\n[SYSTEM TIPS] 此函数一般在任务开始或中间时调用，如果任务已成功完成应该是start_long_term_update用于结算长期记忆。\n'
        return StepOutcome({"result": "working key_info updated"}, next_prompt=next_prompt)

    def _retry_or_exit(self, prompt):
        self._empty_ct = getattr(self, '_empty_ct', 0) + 1
        if self._empty_ct >= 3: return StepOutcome({}, should_exit=True)
        return StepOutcome({}, next_prompt=prompt)

    def do_no_tool(self, args, response):
        '''这是一个特殊工具，由引擎自主调用，不要包含在TOOLS_SCHEMA里。
        当模型在一轮中未显式调用任何工具时，由引擎自动触发。
        二次确认仅在回复几乎只包含<thinking>/<summary>和一段大代码块时触发。'''
        content = getattr(response, 'content', '') or ""
        thinking = getattr(response, 'thinking', '') or ""
        if not response or (not content.strip() and not thinking.strip()):
            yield "[Warn] LLM returned an empty response. Retrying...\n"
            return self._retry_or_exit("[System] Blank response, regenerate and tooluse")
        if '[!!! 流异常中断' in content[-100:] or '!!!Error:' in content[-100:]:
            return self._retry_or_exit("[System] Incomplete response. Regenerate and tooluse.")
        if 'max_tokens !!!]' in content[-100:]:
            return self._retry_or_exit("[System] max_tokens limit reached. Use multi small steps to do it.")
        
        # Plan validators chain — pluggable validation for plan mode
        for v in self._plan_validators:
            msg, outcome = v(content, self)
            if msg:
                yield msg
            if outcome is not None:
                return outcome
            
        # 2. 检测"包含较大代码块但未调用工具"的情况
        # 关键特征：恰好1个大代码块 + 代码块直接结尾（后面只有空白）
        code_block_pattern = r"```[a-zA-Z0-9_]*\n[\s\S]{50,}?```"
        blocks = re.findall(code_block_pattern, content)
        if len(blocks) == 1:
            m = re.search(code_block_pattern, content)
            after_block = content[m.end():]
            if not after_block.strip():
                residual = content.replace(m.group(0), "")
                residual = re.sub(r"<thinking>[\s\S]*?</thinking>", "", residual, flags=re.IGNORECASE)
                residual = re.sub(r"<summary>[\s\S]*?</summary>", "", residual, flags=re.IGNORECASE)
                clean_residual = re.sub(r"\s+", "", residual)
                if len(clean_residual) <= 30:
                    yield "[Info] Detected large code block without tool call and no extra natural language. Requesting clarification.\n"
                    next_prompt = (
                        "[System] 检测到你在上一轮回复中主要内容是较大代码块，且本轮未调用任何工具。\n"
                        "如果这些代码需要执行、写入文件或进一步分析，请重新组织回复并显式调用相应工具"
                        "（例如：code_run、file_write、file_patch 等）；\n"
                        "如果只是向用户展示或讲解代码片段，请在回复中补充自然语言说明，"
                        "并明确是否还需要额外的实际操作。"
                    )
                    return StepOutcome({}, next_prompt=next_prompt)
                
        yield "[Info] Final response to user.\n"
        return StepOutcome(response, next_prompt=None)
    
    def do_start_long_term_update(self, args, response):
        '''Agent觉得当前任务完成后有重要信息需要记忆时调用此工具。'''
        prompt = '''### [总结提炼经验] 既然你觉得当前任务有重要信息需要记忆，请提取最近一次任务中【事实验证成功且长期有效】的环境事实、用户偏好、重要步骤，更新记忆。
本工具是标记开启结算过程，若已在更新记忆过程或没有值得记忆的点，忽略本次调用。
**如果没有经验证的，未来能用上的信息，忽略本次调用！**
**只能提取行动验证成功的信息**：
- **环境事实**（路径/凭证/配置）→ `file_patch` 更新 L2，同步 L1
- **复杂任务经验**（关键坑点/前置条件/重要步骤）→ L3 精简 SOP（只记你被坑得多次重试的核心要点）
**禁止**：临时变量、具体推理过程、未验证信息、通用常识、你可以轻松复现的细节、只是做了但没有验证的信息
**操作**：严格遵循提供的L0的记忆更新SOP。先 `file_read` 看现有 → 判断类型 → 最小化更新 → 无新内容跳过，保证对记忆库最小局部修改。\n
''' + get_global_memory()
        yield "[Info] Start distilling good memory for long-term storage.\n"
        path = './memory/memory_management_sop.md'
        if os.path.exists(path): result = 'This is L0:\n' + file_read(path, show_linenos=False)
        else: result = "Memory Management SOP not found. Do not update memory."
        return StepOutcome(result, next_prompt=prompt)

    def turn_end_callback(self, response, tool_calls, tool_results, turn, next_prompt, exit_reason):
        _c = re.sub(r'```.*?```|<thinking>.*?</thinking>', '', response.content, flags=re.DOTALL)
        rsumm = re.search(r"<summary>(.*?)</summary>", _c, re.DOTALL)
        if rsumm: summary = rsumm.group(1).strip()
        else:
            tc = tool_calls[0]; tool_name, args = tc['tool_name'], tc['args']   # at least one because no_tool
            clean_args = {k: v for k, v in args.items() if not k.startswith('_')}
            summary = f"调用工具{tool_name}, args: {clean_args}"
            if tool_name == 'no_tool': summary = "直接回答了用户问题"
        summary = smart_format(summary.replace('\n', ''), max_str_len=80)
        self.history_info.append(f'[Agent] {summary}')
        _plan = self.working.get('in_plan_mode')

        # 约束仪表盘更新 — 在policy chain前更新计数器
        if hasattr(self, '_constraint_dashboard'):
            self._constraint_dashboard.update(tool_calls, exit_reason)

        # Policy hook chain - each policy returns "" or a string to append
        for policy in self._turn_policies:
            next_prompt += policy(turn, _plan, next_prompt) or ""

        injkeyinfo = consume_file(self.parent.task_dir, '_keyinfo')
        if injkeyinfo: self.working['key_info'] = self.working.get('key_info', '') + f"\n[MASTER] {injkeyinfo}"
        for hook in self._system_prompt_hooks:
            next_prompt += hook({'location': 'turn_end', 'has_summary': bool(rsumm), 'parent': self.parent}) or ""
        for hook in getattr(self.parent, '_turn_end_hooks', {}).values(): hook(locals())  # current readonly
        return next_prompt

def get_global_memory():
    prompt = "\n"
    try:
        suffix = '_en' if os.environ.get('GA_LANG', '') == 'en' else ''
        with open(os.path.join(script_dir, 'memory/global_mem_insight.txt'), 'r', encoding='utf-8', errors='replace') as f: insight = f.read()
        with open(os.path.join(script_dir, f'assets/insight_fixed_structure{suffix}.txt'), 'r', encoding='utf-8') as f: structure = f.read()
        prompt += f'cwd = {os.path.join(script_dir, "temp")} (./)\n'
        prompt += f"\n[Memory] (../memory)\n"
        prompt += structure + '\n../memory/global_mem_insight.txt:\n'
        prompt += insight + "\n"
    except FileNotFoundError: pass
    return prompt
