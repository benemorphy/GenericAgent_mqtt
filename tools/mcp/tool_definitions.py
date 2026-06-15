"""Tool definitions — extracted from ga.py module-level functions.

Pure functions that perform specific operations (code execution, browser, file ops).
These are called by do_* methods on GenericAgentHandler and by the agent loop.
"""

import os
import sys
import re
import time
import threading
import importlib
import tempfile
import subprocess
import itertools
import collections
import difflib
from pathlib import Path

_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from tools.utils.ga_utils import format_error, smart_format, scan_files

# ---------------------------------------------------------------------------
# Code execution
# ---------------------------------------------------------------------------

def code_run(code, code_type="python", timeout=60, cwd=None, code_cwd=None, stop_signal=None, maxlen=10000):
    """代码执行器
    python: 运行复杂的 .py 脚本（文件模式）
    powershell/bash: 运行单行指令（命令模式）
    优先使用python，仅在必要系统操作时使用powershell"""
    preview = (code[:60].replace('\n', ' ') + '...') if len(code) > 60 else code.strip()
    yield f"[Action] Running {code_type} in {os.path.basename(cwd or _GA_ROOT)}: {preview}\n"
    cwd = cwd or os.path.join(_GA_ROOT, 'temp'); tmp_path = None
    if code_type in ["python", "py"]:
        tmp_file = tempfile.NamedTemporaryFile(suffix=".ai.py", delete=False, mode='w', encoding='utf-8', dir=code_cwd)
        cr_header = os.path.join(_GA_ROOT, 'assets', 'code_run_header.py')
        if os.path.exists(cr_header): tmp_file.write(open(cr_header, encoding='utf-8').read())
        tmp_file.write(code)
        tmp_path = tmp_file.name
        tmp_file.close()
        cmd = [sys.executable, "-X", "utf8", "-u", tmp_path]   
    elif code_type in ["powershell", "bash", "sh", "shell", "ps1", "pwsh"]:
        if os.name == 'nt': cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", code]
        else: cmd = ["bash", "-c", code]
    else:
        return {"status": "error", "msg": f"不支持的类型: {code_type}"}
    print("code run output:") 
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0 # SW_HIDE
    full_stdout = []

    def stream_reader(proc, logs):
        try:
            for line_bytes in iter(proc.stdout.readline, b''):
                try: line = line_bytes.decode('utf-8')
                except UnicodeDecodeError: line = line_bytes.decode('gbk', errors='ignore')
                logs.append(line)
                try: print(line, end="") 
                except OSError: pass
        except OSError: pass

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, cwd=cwd, startupinfo=startupinfo,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
        start_t = time.time()
        t = threading.Thread(target=stream_reader, args=(process, full_stdout), daemon=True)
        t.start()

        while t.is_alive():
            istimeout = time.time() - start_t > timeout
            if istimeout or stop_signal:
                process.kill()
                print("[Debug] Process killed due to timeout or stop signal.")
                if istimeout: full_stdout.append("\n[Timeout Error] 超时强制终止")
                else: full_stdout.append("\n[Stopped] 用户强制终止")
                break
            time.sleep(1)

        t.join(timeout=1)
        exit_code = process.poll()

        stdout_str = "".join(full_stdout)
        status = "success" if exit_code == 0 else "error"
        status_icon = "✅" if exit_code == 0 else "❌"
        if exit_code is None: status_icon = "⏳" 
        output_snippet = smart_format(stdout_str, max_str_len=600, omit_str='\n\n[omitted long output]\n\n')
        output_snippet = re.sub(r'`{4,}', lambda m: m.group(0)[:3] + '\u200b' + m.group(0)[3:], output_snippet)
        yield f"[Status] {status_icon} Exit Code: {exit_code}\n[Stdout]\n{output_snippet}\n"
        if process.stdout: threading.Thread(target=process.stdout.close, daemon=True).start()
        return {
            "status": status,
            "stdout": smart_format(stdout_str, max_str_len=maxlen, omit_str='\n\n[omitted long output]\n\n'),
            "exit_code": exit_code
        }
    except Exception as e:
        if 'process' in locals(): process.kill()
        return {"status": "error", "msg": str(e)}
    finally:
        if code_type == "python" and tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)


# ---------------------------------------------------------------------------
# User interaction
# ---------------------------------------------------------------------------

def ask_user(question, candidates=None):
    """question: 向用户提出的问题。candidates: 可选的候选项列表"""
    return {"status": "INTERRUPT", "intent": "HUMAN_INTERVENTION",
        "data": {"question": question, "candidates": candidates or []}}


# ---------------------------------------------------------------------------
# Browser operations
# ---------------------------------------------------------------------------

from tools.mcp.browser_service import browser_service
import simphtml

def web_scan(tabs_only=False, switch_tab_id=None, text_only=False, maxlen=35000):
    """获取当前页面的简化HTML内容和标签页列表"""
    try:
        if not browser_service.available:
            err = browser_service.init_error or "浏览器服务不可用"
            return {"status": "error", "msg": err}
        sessions = browser_service.get_all_sessions()
        if len(sessions) == 0:
            return {"status": "error", "msg": "没有可用的浏览器标签页"}
        tabs = []
        for sess in sessions: 
            sess.pop('connected_at', None)
            sess.pop('type', None)
            sess['url'] = sess.get('url', '')[:50] + ("..." if len(sess.get('url', '')) > 50 else "")
            tabs.append(sess)
        if switch_tab_id: browser_service.default_session_id = switch_tab_id
        result = {
            "status": "success",
            "metadata": {
                "tabs_count": len(tabs), "tabs": tabs,
                "active_tab": browser_service.default_session_id
            }
        }
        if not tabs_only: 
            importlib.reload(simphtml); result["content"] = simphtml.get_html(browser_service.driver, cutlist=True, maxchars=maxlen, text_only=text_only)
            if text_only: result['content'] = smart_format(result['content'], max_str_len=maxlen//3, omit_str='\n\n[omitted long content]\n\n')
        return result
    except Exception as e:
        return {"status": "error", "msg": format_error(e)}


def web_execute_js(script, switch_tab_id=None, no_monitor=False):
    """执行 JS 脚本来控制浏览器，并捕获结果和页面变化"""
    try:
        if not browser_service.available:
            err = browser_service.init_error or "浏览器服务不可用"
            return {"status": "error", "msg": err}
        if len(browser_service.get_all_sessions()) == 0: return {"status": "error", "msg": "没有可用的浏览器标签页"}
        if switch_tab_id: browser_service.default_session_id = switch_tab_id
        driver = browser_service.driver
        last_html = None
        if not no_monitor:
            try:
                last_html = simphtml.get_html(driver, cutlist=False, extra_js=simphtml.temp_monitor_js, maxchars=9999999)
            except Exception:
                pass
        result = None
        error_msg = None
        reloaded = False
        newTabs = []
        try:
            before_sids = set(driver.get_session_dict().keys())
            response = driver.execute_js(script)
            result = response['data'] if isinstance(response, dict) and 'data' in response else response.get('result') if isinstance(response, dict) else response
            if isinstance(response, dict) and response.get('closed', 0) == 1:
                reloaded = True
            time.sleep(1)
        except Exception as e:
            error = e.args[0] if e.args else str(e)
            if isinstance(error, dict):
                error.pop('stack', None)
            error_msg = str(error)
        rr = {"status": "failed" if error_msg else "success", "js_return": result, "tab_id": getattr(driver, 'default_session_id', None)}
        if reloaded:
            rr['reloaded'] = reloaded
        if isinstance(response, dict) and response.get('newTabs'):
            rr['newTabs'] = response['newTabs']
        else:
            try:
                after = driver.get_session_dict()
                before = before_sids if not error_msg else set()
                new_sids = {k: v for k, v in after.items() if k not in before}
                if new_sids:
                    rr['newTabs'] = [{'id': k, 'url': v} for k, v in new_sids.items()]
                    rr['suggestion'] = "页面已刷新，以上新标签页在执行期间连接。"
            except Exception:
                pass
        if error_msg:
            rr['error'] = error_msg
        if no_monitor:
            return rr
        if not reloaded:
            try:
                rr['transients'] = simphtml.get_temp_texts(driver)
            except Exception:
                rr['transients'] = []
        if not reloaded and len(newTabs) == 0:
            try:
                current_html = simphtml.get_html(driver, cutlist=False, maxchars=9999999)
                if last_html is not None:
                    diff_data = simphtml.find_changed_elements(last_html, current_html)
                    change_count = diff_data.get('changed', 0)
                    top_change = diff_data.get('top_change', '')
                    diff_summary = f"DOM变化量: {change_count}"
                    if top_change:
                        diff_summary += f"\n最显著变化:\n{top_change}"
                    if change_count == 0 and not rr.get('transients', []) and len(newTabs) == 0:
                        diff_summary += " (页面无变化)"
                        rr['suggestion'] = "页面无明显变化"
                    rr['diff'] = diff_summary
            except Exception:
                rr['diff'] = "页面变化监控不可用"
        return rr
    except Exception as e: return {"status": "error", "msg": format_error(e)}


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def file_patch(path: str, old_content: str, new_content: str):
    """在文件中寻找唯一的 old_content 块并替换为 new_content"""
    path = str(Path(path).resolve())
    try:
        if not os.path.exists(path): return {"status": "error", "msg": "文件不存在"}
        with open(path, 'r', encoding='utf-8') as f: full_text = f.read()
        if not old_content: return {"status": "error", "msg": "old_content 为空，请确认 arguments"}
        count = full_text.count(old_content)
        if count == 0: return {"status": "error", "msg": "未找到匹配的旧文本块，建议：先用 file_read 确认当前内容，再分小段进行 patch。若多次失败则询问用户，严禁自行使用 overwrite 或代码替换。"}
        if count > 1: return {"status": "error", "msg": f"找到 {count} 处匹配，无法确定唯一位置。请提供更长、更具体的旧文本块以确保唯一性。建议：包含上下文行来增强特征，或分小段逐个修改。"}
        updated_text = full_text.replace(old_content, new_content)
        with open(path, 'w', encoding='utf-8') as f: f.write(updated_text)
        return {"status": "success", "msg": "文件局部修改成功"}
    except Exception as e: return {"status": "error", "msg": str(e)}


_read_dirs = set()

def file_read(path, start=1, keyword=None, count=200, show_linenos=True):
    """读取文件内容。从第start行开始读取。如有keyword则返回第一个keyword附近内容。"""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            stream = ((i, l.rstrip('\r\n')) for i, l in enumerate(f, 1))
            stream = itertools.dropwhile(lambda x: x[0] < start, stream)
            if keyword:
                before = collections.deque(maxlen=count//3)
                for i, l in stream:
                    if keyword.lower() in l.lower():
                        res = list(before) + [(i, l)] + list(itertools.islice(stream, count - len(before) - 1))
                        break
                    before.append((i, l))
                else: return f"Keyword '{keyword}' not found after line {start}. Falling back to content from line {start}:\n\n" \
                               + file_read(path, start, None, count, show_linenos)
            else: res = list(itertools.islice(stream, count))
            realcnt = len(res); L_MAX = min(max(100, 256000//max(realcnt,1)), 8000); TAG = " ... [TRUNCATED]"
            remaining = sum(1 for _ in itertools.islice(stream, 5000))
            total_lines = (res[0][0] - 1 if res else start - 1) + realcnt + remaining
            tl_str = f"{total_lines}+" if remaining >= 5000 else str(total_lines)
            partial = total_lines > realcnt
            total_tag = f"[FILE] {tl_str} lines" + (f" | PARTIAL showing {realcnt}; assess need for more" if partial else "") + "\n"
            res = [(i, l if len(l) <= L_MAX else l[:L_MAX] + TAG) for i, l in res]
            result = "\n".join(f"{i}|{l}" if show_linenos else l for i, l in res)
            if show_linenos: result = total_tag + result
            elif partial: result += f"\n\n[FILE PARTIAL: showing {realcnt}/{tl_str} lines; assess need for more]"
            _read_dirs.add(os.path.dirname(os.path.abspath(path)))
            return result
    except FileNotFoundError:
        msg = f"Error: File not found: {path}"
        try:
            tgt = os.path.basename(path); scan = os.path.dirname(os.path.dirname(os.path.abspath(path)))
            roots = [scan] + [d for d in _read_dirs if not d.startswith(scan)]
            cands = list(itertools.islice((c for base in roots for c in scan_files(base)), 2000))
            top = sorted([(difflib.SequenceMatcher(None, tgt.lower(), c[0].lower()).ratio(), c) for c in cands[:2000]], key=lambda x: -x[0])[:5]
            top = [(s, c) for s, c in top if s > 0.3]
            if top: msg += "\n\nDid you mean:\n" + "\n".join(f"  {c[1]}  ({s:.0%})" for s, c in top)
        except Exception: pass
        return msg
    except Exception as e: return f"Error: {str(e)}"
