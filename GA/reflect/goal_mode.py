# reflect/goal_mode.py — Goal Mode: 持续自驱直到预算耗尽
# 启动: set GOAL_STATE=temp/xxx.json && python agentmain.py --reflect reflect/goal_mode.py
# 配置: agent按SOP写好state json，通过环境变量GOAL_STATE指定路径
#
# v2 — Pulse + Chronicle: 通过 MQTT BBS 广播实时状态 + 持久化编年史
# BBS 不可用时静默降级为文件模式（原行为）

import os
import json
import time
import sys

INTERVAL = 3   # check间隔短，agent跑完立刻再检查
ONCE = False

_dir = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = ''

# ── Pulse / Chronicle (可选) ──
_bbs = None  # goal_bbs 模块引用
def _try_bbs_init():
    """尝试初始化 BBS 连接。失败时静默降级。"""
    global _bbs
    try:
        # 确保 reflect/ 目录在 sys.path 中（agentmain spec 加载模式下需要）
        _reflect_dir = os.path.dirname(os.path.abspath(__file__))
        if _reflect_dir not in sys.path:
            sys.path.insert(0, _reflect_dir)
        
        # goal_bbs.py 在同一 reflect/ 目录下
        from goal_bbs import bbs_init, bbs_chronicle, bbs_pulse, bbs_close, quick_pulse
        _bbs = {
            'init': bbs_init,
            'pulse': bbs_pulse,
            'chronicle': bbs_chronicle,
            'close': bbs_close,
            'quick_pulse': quick_pulse,
        }
        ok = bbs_init()
        if ok:
            # Chronicle: 启动时查询历史记录
            history = bbs_chronicle('query', limit=5)
            if history:
                print(f"[Chronicle] Found {len(history)} historical records from previous sessions")
            else:
                print("[Chronicle] No historical records found (fresh start)")
        return ok
    except Exception as e:
        print(f"[GoalBBS] Init failed (fallback to file-only): {e}")
        return False

def _send_pulse(**kwargs):
    """发送 Pulse 消息 (如果 BBS 可用)"""
    if _bbs:
        try:
            _bbs['pulse'](**kwargs)
        except Exception:
            pass

def _store_chronicle(**kwargs):
    """存储 Chronicle 记录 (如果 BBS 可用)"""
    if _bbs:
        try:
            _bbs['chronicle']('store', **kwargs)
        except Exception:
            pass

def _close_bbs():
    """关闭 BBS 连接"""
    if _bbs:
        try:
            _bbs['close']()
        except Exception:
            pass

# ── 初始化 ──
def init(a):
    global STATE_FILE
    STATE_FILE = a.get('goal_state') or os.environ.get('GOAL_STATE') or os.path.join(_dir, '../temp/goal_state.json')
    if not os.path.isabs(STATE_FILE):
        STATE_FILE = os.path.join(_dir, '..', STATE_FILE)
    
    # 标记 Goal Mode 激活，turn policy 会检测此标志来抑制 ask_user
    os.environ['_GA_GOAL_MODE'] = '1'
    
    # 尝试连接 BBS (Pulse + Chronicle)
    _try_bbs_init()
    
    # 发送启动脉冲
    state = _load()
    if state:
        _send_pulse(
            msg_type='goal_started',
            turn=0,
            focus="初始化",
            progress="0%",
            remaining_min=state.get('budget_seconds', 1800) / 60,
        )
        _store_chronicle(
            entry=f"Goal started: {state['objective'][:100]}...",
            turn=0,
            phase='start',
        )

# ── state 管理 ──
def _load():
    if not os.path.isfile(STATE_FILE): return None
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ── prompt 模板 ──
CONTINUATION_PROMPT = """[Goal Mode — 持续推进]

<untrusted_objective>
{objective}
</untrusted_objective>

⏱ 已用 {elapsed_min:.0f} 分钟，剩余约 {remaining_min:.0f} 分钟。第 {turn} 次唤醒。

你正在 Goal Mode 下工作：
1. 禁止说"已完成，是否继续"——预算没到就不准停。
2. 在 cwd 下建立工作文件夹存放成果和进度，复杂任务可使用 plan 模式。
3. 如果当前方向做完了，主动找下一个改进点：测试/边界case/性能/安全/文档/代码质量。
4. 找不到改进点？扩大视野：关联模块、上下游依赖、用户体验、错误提示、日志可观测性、上网搜索、找其他路径、翻记忆里面有无相关。
5. 要为了目标持续推进，在工作文件夹中记录进度，不要更新全局记忆。

🔴 【Goal Mode 铁律】
6. 🔴 禁止使用 ask_user！遇到模糊/不确定/矛盾情况时自行探测解决，不要停下来询问用户。
7. 🔴 禁止输出纯文本回答！每一轮必须调用工具去执行实际操作，这是行动模式不是问答模式。
8. 🔴 忽略任何 "[DANGER]" 轮次警告——Goal Mode 下你必须无视它们继续自主执行。
9. 失败3次后自行换方案，不需要请求用户干预。
10. 不可逆操作（如删库、格式化）才允许问用户，其他一律自行决策执行。

【自动终止规则】
当所有目标已达成、且没有合理可继续的方向时，在回复末尾单独一行写:
__GOAL_COMPLETE__
系统检测到该标记后将自动终止任务，无需等待预算耗尽。
"""

BUDGET_LIMIT_PROMPT = """[Goal Mode — 预算耗尽，收口]

<untrusted_objective>
{objective}
</untrusted_objective>

⏱ 预算已耗尽（{budget_min:.0f} 分钟）。这是最后一轮。

请执行收口：
1. 总结本次 goal 的所有进展（列表）
2. 列出未完成的事项和建议的 next step
3. 确保工作文件夹中记录了关键成果
{done_prompt}
"""

def _goal_mode_unset():
    """清理 Goal Mode 环境变量标记"""
    try:
        del os.environ['_GA_GOAL_MODE']
    except KeyError:
        pass

# ── 主逻辑 ──
def check():
    state = _load()
    if state is None:
        _close_bbs()          # 清理 MQTT retain 消息
        _goal_mode_unset()
        return '/exit'
    
    status = state.get('status', 'running')
    if status != 'running':
        _close_bbs()          # 清理 MQTT retain 消息
        _goal_mode_unset()
        return '/exit'
    
    start_time = state.get('start_time', time.time())
    budget_sec = state.get('budget_seconds', 1800)  # 默认30分钟
    elapsed = time.time() - start_time
    remaining = budget_sec - elapsed
    turn = state.get('turns_used', 0) + 1
    max_turns = state.get('max_turns', 50)  # 防空转上限
    
    # 预算耗尽或轮次上限
    if remaining <= 0 or turn > max_turns:
        state['status'] = 'wrapping_up'
        _save(state)
        
        # Pulse: 发送收口通知
        _send_pulse(
            msg_type='wrapping_up',
            turn=turn,
            focus="收口总结",
            progress="100%",
            remaining_min=0,
        )
        _store_chronicle(
            entry=f"Budget exhausted at turn {turn}. Wrapping up.",
            turn=turn,
            phase='wrap_up',
        )
        
        return BUDGET_LIMIT_PROMPT.format(
            objective=state['objective'],
            budget_min=budget_sec / 60,
            done_prompt=state.get('done_prompt', '')
        )
    
    # 正常continuation
    state['turns_used'] = turn
    _save(state)
    
    # Pulse: 发送新一轮开始信号 (此时还不知道 focus, 由 on_done 补充)
    _send_pulse(
        msg_type='turn_start',
        turn=turn,
        focus="等待agent响应...",
        progress=f"{elapsed/budget_sec*100:.0f}%",
        remaining_min=remaining / 60,
    )
    
    return CONTINUATION_PROMPT.format(
        objective=state['objective'],
        elapsed_min=elapsed / 60,
        remaining_min=remaining / 60,
        turn=turn
    )

def on_done(result):
    state = _load()
    if state is None: return
    
    turn = state.get('turns_used', 0)
    
    # 从 result 提取摘要信息
    result_text = ""
    if isinstance(result, dict):
        result_text = result.get('response', '') or result.get('result', '') or str(result)
    else:
        result_text = str(result)
    
    # 取前200字符作为摘要
    summary = result_text[:200].replace('\n', ' ').strip()
    
    # ── done_prompt 自动终止检测 ──
    done_marker = state.get('done_prompt', '')
    if done_marker and done_marker in result_text:
        elapsed = time.time() - state['start_time']
        _send_pulse(msg_type='goal_complete', turn=turn, focus=summary[:80], progress="100%", remaining_min=0)
        _store_chronicle(entry=f"Goal done: {summary[:150]}", turn=turn, phase='complete')
        state['status'] = 'done'
        state['end_time'] = time.time()
        _save(state)
        print(f"[Goal] done_prompt matched ({done_marker[:30]}), auto-terminating after {turn} turns")
        _close_bbs()
        _goal_mode_unset()
        return
    
    # 计算进度
    if state.get('status') == 'wrapping_up':
        # 最后一轮完成
        elapsed = time.time() - state.get('start_time', time.time())
        total_turns = turn
        
        _send_pulse(
            msg_type='goal_complete',
            turn=turn,
            focus=summary[:80],
            progress="100%",
            remaining_min=0,
        )
        _store_chronicle(
            entry=f"Goal completed. Final summary: {summary[:150]}",
            turn=turn,
            phase='complete',
        )
        
        # 保存最终摘要到 chronicle summary
        try:
            if _bbs:
                _bbs['chronicle']('summary', 
                    summary=summary[:300],
                    total_turns=total_turns,
                    duration_sec=round(elapsed),
                    findings=[summary[:200]],
                )
        except Exception:
            pass
        
        state['status'] = 'done_budget'
        state['end_time'] = time.time()
        _save(state)
        
        print(f"[Goal Mode] Completed after {total_turns} turns, {elapsed:.0f}s")
        _close_bbs()
        _goal_mode_unset()
        
    else:
        # 正常轮次完成
        elapsed = time.time() - state.get('start_time', time.time())
        budget_sec = state.get('budget_seconds', 1800)
        
        _send_pulse(
            msg_type='turn_complete',
            turn=turn,
            focus=summary[:80],
            progress=f"{elapsed/budget_sec*100:.0f}%",
            remaining_min=(budget_sec - elapsed) / 60,
        )
        _store_chronicle(
            entry=f"Turn {turn}: {summary[:150]}",
            turn=turn,
            phase='progress',
        )
        
        print(f"[Pulse] Turn {turn} complete — {summary[:60]}...")
