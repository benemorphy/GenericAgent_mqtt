# reflect/goal_nexus.py — Goal Nexus: 人机协作反射模式
# agent 自主执行，关键决策点通过飞书等待人类回复
#
# 用法:
#   python agentmain.py --reflect reflect/goal_nexus.py
#
# 配置: 环境变量 GOAL_STATE 指向 goal_state.json
#   goal_state.json objective 中的 {decision_points} 定义哪些点需要人类决策
#
# 继承 goal_mode.py 的 check/on_done 模式，额外增加:
#   - ask_human(): 发布决策到 Board → 阻塞等待飞书回复 (程序化API)
#   - send_feishu(): 通过 Board 推送消息到飞书
#   - suspend/resume(): 挂起/恢复执行状态
#   - 人机协作标记解析: agent 回复中 [ASK_HUMAN] / [SEND_FEISHU] 标记

import os, sys, json, time, threading, uuid, json as _json
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))
_ga_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _ga_dir)

# 共享 goal_mode 的基础设施
from reflect import goal_bbs
from Mqtt_bbs_client.board_client import BoardClient

_STATE_FILE = os.environ.get("GOAL_STATE", os.path.join(_ga_dir, "temp", "goal_state.json"))

_INTERVAL = 5       # check 间隔秒数
_ONCE = False        # 非一次性
_HUMAN_WAIT_TIMEOUT = 3600  # 人类决策等待超时（秒）

_nexus = {
    "bbs": None,
    "agent_id": None,
    "pulse_initialized": False,
    "_human_responses": {},  # corr_id -> choice (由MQTT回调线程写入)
    "_human_responses_lock": threading.Lock(),
}

def _load():
    if not os.path.isfile(_STATE_FILE):
        return None
    with open(_STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save(state):
    with open(_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def _pulse(**kwargs):
    """安全的 pulse 发送（封装 _send_pulse，处理未初始化）"""
    try:
        _send_pulse(**kwargs)
    except Exception:
        pass

# ── init (agentmain 反射入口) ──

def init(a):
    """初始化 Nexus 环境（agentmain --reflect 入口）"""
    global _STATE_FILE, _INTERVAL
    _STATE_FILE = a.get('goal_state') or os.environ.get('GOAL_STATE') or os.path.join(_ga_dir, 'temp', 'goal_state.json')
    if not os.path.isabs(_STATE_FILE):
        _STATE_FILE = os.path.join(_ga_dir, _STATE_FILE)
    
    # 发送启动脉冲
    state = _load()
    if state:
        _pulse(msg_type='goal_started', turn=0, focus='Nexus init', progress='0%',
               remaining_min=state.get('budget_seconds', 1800) / 60)
        _store_chronicle(
            entry=f"Nexus started: {state['objective'][:100]}...",
            turn=0, phase='start',
        )

# ── 主逻辑: check / on_done ──

def check():
    """Nexus check — 继承 goal_mode 的 check 逻辑，增加人类决策等待检测"""
    state = _load()
    if state is None:
        return '/exit'
    
    status = state.get('status', 'running')
    
    # 非 running 状态处理
    if status == 'done' or status == 'done_budget':
        return '/exit'
    
    if status == 'wrapping_up':
        return '/exit'
    
    # --- waiting_human: 非阻塞等待人类决策 ---
    if status == 'waiting_human':
        return _check_human_response(state)
    
    # --- 正常 running 状态 ---
    elapsed = time.time() - state.get('start_time', time.time())
    budget_sec = state.get('budget_seconds', 1800)
    remaining = budget_sec - elapsed
    turn = state.get('turns_used', 0) + 1
    
    # 预算耗尽或满轮次 → 收口
    if remaining <= 0 or turn > state.get('max_turns', 200):
        state['status'] = 'wrapping_up'
        state['end_time'] = time.time()
        _save(state)
        _pulse(msg_type='wrapping_up', turn=turn, focus='Budget exhausted',
               progress='100%', remaining_min=max(0, remaining/60))
        return BUDGET_LIMIT_PROMPT.format(
            objective=state['objective'],
            elapsed_min=elapsed / 60,
            remaining_min=max(0, remaining) / 60,
            turn=turn,
        )
    
    state['turns_used'] = turn
    _save(state)
    
    # Pulse: 发新一轮开始信号
    _pulse(msg_type='turn_start', turn=turn,
           progress=f"{elapsed/budget_sec*100:.0f}%",
           remaining_min=remaining/60)
    
    # 检查是否有挂起的决策等待恢复（从 waiting_human 恢复后）
    pending_response = state.pop('_nexus_human_response', None)
    if pending_response:
        # 有恢复的响应，注入到 prompt
        resume_note = (
            f"\n\n[人类决策恢复] 刚才的决策 '{state.get('_last_decision', '')}' "
            f"已获得人类回复: {pending_response}\n请根据此回复继续推进。"
        )
    else:
        resume_note = ""
    
    return CONTINUATION_PROMPT.format(
        objective=state['objective'],
        elapsed_min=elapsed / 60,
        remaining_min=remaining / 60,
        turn=turn,
    ) + resume_note


def _check_human_response(state):
    """检查等待人类决策的状态（非阻塞）"""
    pending = state.get('_pending_decision', {})
    if not pending:
        # 没有挂起决策但状态为 waiting_human → 异常恢复
        state['status'] = 'running'
        _save(state)
        return CONTINUATION_PROMPT.format(
            objective=state['objective'],
            elapsed_min=(time.time() - state.get('start_time', time.time())) / 60,
            remaining_min=0, turn=state.get('turns_used', 0) + 1,
        )
    
    corr_id = pending.get('corr_id', '')
    expires = pending.get('expires_at', 0)
    recommendation = pending.get('recommendation', '')
    
    # 1. 检查 MQTT 回调是否收到了回复（内存缓存）
    response = None
    with _nexus['_human_responses_lock']:
        if corr_id in _nexus['_human_responses']:
            response = _nexus['_human_responses'].pop(corr_id)
    
    # 1b. 也检查 state 文件中的持久化响应（模块重载后仍可恢复）
    if response is None:
        persisted = state.get('_nexus_human_responses', {})
        if corr_id in persisted:
            response = persisted.pop(corr_id)
            state['_nexus_human_responses'] = persisted
    
    if response:
        # 收到人类回复
        state['status'] = 'running'
        state['_nexus_human_response'] = response
        state['_last_decision'] = pending.get('decision', '')
        state.pop('_pending_decision', None)
        _save(state)
        _pulse(msg_type='human_responded', turn=state.get('turns_used', 0),
               focus=f"Human: {response[:60]}", progress='...')
        # 立即返回 None 让下一轮 check 产生带回复通知的 prompt
        return None  # agentmain 处理: None 表示继续等下一轮 check
    
    # 2. 检查超时
    if expires > 0 and time.time() > expires:
        state['status'] = 'running'
        state['_nexus_human_response'] = f"[TIMEOUT] 自动使用推荐: {recommendation}"
        state['_last_decision'] = pending.get('decision', '')
        state.pop('_pending_decision', None)
        _save(state)
        _store_chronicle(entry=f"ask_human TIMEOUT for '{pending.get('decision','')[:60]}', use: {recommendation}",
                         turn=state.get('turns_used', 0), phase='human_timeout')
        return None  # 下一轮 check 带超时通知
    
    # 3. 仍在等待 → 返回等待 prompt (简短，节省 token)
    wait_prompt = WAITING_PROMPT.format(
        decision=pending.get('decision', '等待人类决策'),
        elapsed_min=(time.time() - state.get('start_time', time.time())) / 60,
        remaining_min=max(0, expires - time.time()) / 60 if expires else 0,
        recommendation=recommendation,
    )
    return wait_prompt


def on_done(result):
    """Nexus on_done — 继承 goal_mode 的 on_done，增加飞书通知和标记解析"""
    state = _load()
    if state is None:
        return
    
    turn = state.get('turns_used', 0)
    
    result_text = ""
    if isinstance(result, dict):
        result_text = result.get('response', '') or result.get('result', '') or str(result)
    else:
        result_text = str(result)
    summary = result_text[:200].replace('\n', ' ').strip()
    
    # 解析 agent 回复中的操作标记
    markers = _parse_agent_markers(result_text)
    
    # 处理 [SEND_FEISHU] 标记：推送到飞书
    for feishu_msg in markers.get('send_feishu', []):
        _do_send_feishu(feishu_msg)
        _store_chronicle(entry=f"[Nexus] send_feishu: {feishu_msg[:80]}", turn=turn, phase='feishu')
    
    # 处理 [ASK_HUMAN] 标记：发布决策请求，状态置 waiting_human
    for decision_info in markers.get('ask_human', []):
        decision_point = decision_info.get('decision', '')
        options = decision_info.get('options', [])
        recommendation = decision_info.get('recommendation', '')
        _publish_human_decision(decision_point, options, recommendation, state, turn)
        # 状态已改为 waiting_human, 保存并返回（不再继续其他处理）
        return
    
    # done_prompt 检测
    done_marker = state.get('done_prompt', '')
    if done_marker and done_marker in result_text:
        _pulse(msg_type='goal_complete', turn=turn, focus=summary[:80], progress='100%', remaining_min=0)
        _store_chronicle(entry=f"Nexus done: {summary[:150]}", turn=turn, phase='complete')
        state['status'] = 'done'
        state['end_time'] = time.time()
        _save(state)
        _close_bbs()
        return
    
    if state.get('status') == 'wrapping_up':
        _pulse(msg_type='goal_complete', turn=turn, focus=summary[:80], progress='100%', remaining_min=0)
        _store_chronicle(entry=f"Nexus completed: {summary[:150]}", turn=turn, phase='complete')
        state['status'] = 'done_budget'
        state['end_time'] = time.time()
        _save(state)
        _close_bbs()
        return
    
    # 正常轮次 → Pulse + Chronicle
    _pulse(msg_type='turn_done', turn=turn, focus=summary[:80],
           progress=f"{turn/state.get('max_turns', 200)*100:.0f}%")
    _store_chronicle(entry=f"Turn {turn}: {summary[:150]}", turn=turn, phase='progress')


# ── Agent 标记解析 ──

def _parse_agent_markers(text):
    """从 agent 回复中解析操作标记
    
    支持格式:
        [ASK_HUMAN] decision | option1,option2,option3 | recommendation
        [SEND_FEISHU] 消息内容
    
    Returns:
        dict: {"ask_human": [...], "send_feishu": [...]}
    """
    result = {"ask_human": [], "send_feishu": []}
    if not text:
        return result
    
    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        
        # [ASK_HUMAN] 格式: decision | option1,option2 | recommendation
        if stripped.startswith('[ASK_HUMAN]') or stripped.startswith('[ask_human]'):
            content = stripped.split(']', 1)[1].strip()
            parts = [p.strip() for p in content.split('|', 2)]
            decision = parts[0] if len(parts) > 0 else ''
            options_str = parts[1] if len(parts) > 1 else ''
            recommendation = parts[2] if len(parts) > 2 else ''
            options = [o.strip() for o in options_str.split(',') if o.strip()]
            result['ask_human'].append({
                'decision': decision,
                'options': options,
                'recommendation': recommendation,
            })
        
        # [SEND_FEISHU] 格式: 消息内容
        elif stripped.startswith('[SEND_FEISHU]') or stripped.startswith('[send_feishu]'):
            content = stripped.split(']', 1)[1].strip()
            if content:
                result['send_feishu'].append(content)
    
    return result


# ── 非阻塞决策发布 (用于 on_done 标记解析) ──

def _publish_human_decision(decision_point, options, recommendation, state, turn):
    """发布人类决策请求到 MQTT（非阻塞），状态置 waiting_human"""
    _init_bbs()
    bbs = _nexus['bbs']
    corr_id = f"nexus_{uuid.uuid4().hex[:8]}"
    
    payload = {
        'v': 1,
        'action': 'post',
        'corr_id': corr_id,
        'content': {
            'type': 'human_review',
            'decision': decision_point,
            'options': options or [],
            'recommendation': recommendation,
            'corr_id': corr_id,
        }
    }
    
    # 发布到 Nexus Board (fsapp.py 订阅此主题推送到飞书)
    bbs.publish('bbs/goal_nexus/review', _json.dumps(payload, ensure_ascii=False), qos=1)
    
    # 保存挂起决策到 state
    state['status'] = 'waiting_human'
    state['_pending_decision'] = {
        'corr_id': corr_id,
        'decision': decision_point,
        'options': options,
        'recommendation': recommendation,
        'expires_at': time.time() + _HUMAN_WAIT_TIMEOUT,
        'turn': turn,
    }
    state['_last_decision'] = decision_point
    _save(state)
    
    _store_chronicle(entry=f"[Nexus] ask_human: {decision_point[:80]}",
                     turn=turn, phase='human_wait')
    _pulse(msg_type='ask_human', turn=turn,
           focus=f"Waiting human: {decision_point[:60]}", progress='...')


# ── Nexus 特有功能 (程序化 API) ──

def ask_human(decision_point, options=None, recommendation="", timeout=3600):
    """发布决策到 Board → 阻塞等待飞书回复 (程序化API，用于非reflect场景)
    
    参数:
        decision_point: 决策描述
        options: 选项列表 (如 ["确认执行", "跳过"])
        recommendation: 推荐选项
        timeout: 超时秒数 (默认1小时), 超时自动用推荐方案
    
    返回:
        str — 人类选择的选项, 超时返回 recommendation
    """
    _init_bbs()
    bbs = _nexus["bbs"]
    corr_id = f"nexus_{uuid.uuid4().hex[:8]}"
    
    payload = {
        "v": 1,
        "action": "post",
        "corr_id": corr_id,
        "content": {
            "type": "human_review",
            "decision": decision_point,
            "options": options or [],
            "recommendation": recommendation,
            "corr_id": corr_id,
        }
    }
    
    # 发布到 Nexus Board
    bbs.publish("bbs/goal_nexus/review", _json.dumps(payload, ensure_ascii=False), qos=1)
    _store_chronicle(entry=f"ask_human: {decision_point[:80]}", turn=_load().get('turns_used', 0), phase='human_wait')
    
    # 阻塞等待回复（通过 Board 订阅）
    result = _wait_human_response(corr_id, timeout)
    
    if result is None:
        _store_chronicle(entry=f"ask_human TIMEOUT, using recommendation", turn=_load().get('turns_used', 0), phase='human_timeout')
        return recommendation
    return result


def _wait_human_response(corr_id, timeout):
    """阻塞等待人类回复（简化版：线程Event等待，外部通过 set_human_response() 触发）"""
    result_container = []
    event = threading.Event()
    
    # 注册外部可调用的回调
    _nexus["_pending_callbacks"] = _nexus.get("_pending_callbacks", {})
    def on_choice(choice):
        result_container.append(choice)
        event.set()
    _nexus["_pending_callbacks"][corr_id] = on_choice
    
    event.wait(timeout)
    
    # 清理
    _nexus["_pending_callbacks"].pop(corr_id, None)
    return result_container[0] if result_container else None


def set_human_response(corr_id, choice):
    """外部设置人类回复（由飞书桥接或测试调用）"""
    # 1. 尝试阻塞式回调
    cb = _nexus.get("_pending_callbacks", {}).get(corr_id)
    if cb:
        cb(choice)
    
    # 2. 也存入非阻塞响应池（供 check() 轮询使用）
    with _nexus['_human_responses_lock']:
        _nexus['_human_responses'][corr_id] = choice
    
    # 3. 持久化到 state 文件（防止模块重载后丢失）
    try:
        state = _load()
        if state:
            if '_nexus_human_responses' not in state:
                state['_nexus_human_responses'] = {}
            state['_nexus_human_responses'][corr_id] = choice
            _save(state)
    except Exception:
        pass


def send_feishu(message, msg_type="text"):
    """通过 Board → 飞书桥接发送消息到飞书群聊"""
    _do_send_feishu(message, msg_type)


def _do_send_feishu(message, msg_type="text"):
    """内部: 发送消息到飞书 (不依赖 state)"""
    _init_bbs()
    bbs = _nexus["bbs"]
    payload = {
        "v": 1,
        "action": "post",
        "content": message,
        "msg_type": msg_type,
    }
    bbs.publish("bbs/goal_nexus/response", _json.dumps(payload, ensure_ascii=False), qos=1)


# ── 挂起 / 恢复 ──

def suspend(reason="manual"):
    """挂起执行状态（支持 running 和 waiting_human 状态）"""
    state = _load()
    if state and state.get('status') in ('running', 'waiting_human'):
        state['_suspended'] = True
        state['_suspend_reason'] = reason
        state['_suspend_time'] = time.time()
        _save(state)
        _pulse(msg_type='suspended', turn=state.get('turns_used', 0),
               focus=f"Suspended: {reason}", progress='...')
        return True
    return False


def resume():
    """恢复执行状态"""
    state = _load()
    if state and state.get('_suspended'):
        state['_suspended'] = False
        state.pop('_suspend_reason', None)
        state.pop('_suspend_time', None)
        # 恢复为 running
        if state.get('status') == 'waiting_human':
            state['status'] = 'running'
        _save(state)
        _pulse(msg_type='resumed', turn=state.get('turns_used', 0),
               focus="Resumed", progress='...')
        return True
    return False


# ── BBS 连接管理 ──

def _init_bbs():
    """初始化 MQTT 连接，订阅 Nexus 响应主题"""
    if _nexus["bbs"] is None:
        import socket
        agent_id = f"nexus_{socket.gethostname()}_{os.getpid()}"
        _nexus["agent_id"] = agent_id
        import paho.mqtt.client as mqtt
        
        def _on_message(client, userdata, msg):
            """处理收到的 MQTT 消息"""
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
                topic = msg.topic
                _on_nexus_response(topic, payload)
            except Exception as e:
                print(f"[Nexus] MQTT message parse error: {e}")
        
        client = mqtt.Client(client_id=agent_id)
        client.on_message = _on_message
        client.connect('127.0.0.1', 1883, 60)
        
        # 订阅人类回复主题
        client.subscribe('bbs/goal_nexus/response', qos=1)
        # 也订阅 board 格式
        client.subscribe('bbs/+/post', qos=0)
        
        client.loop_start()
        _nexus["bbs"] = client


def _on_nexus_response(topic, payload):
    """处理 MQTT 上的 nexus 响应"""
    # 检查是否是 nexus 响应
    if not isinstance(payload, dict):
        return
    
    content = payload.get('content', payload)
    if isinstance(content, dict):
        corr_id = content.get('corr_id', '') or payload.get('corr_id', '')
        choice = content.get('choice', '') or content.get('response', '') or str(content)
    else:
        corr_id = payload.get('corr_id', '')
        choice = str(content)
    
    if corr_id and choice:
        set_human_response(corr_id, choice)
        print(f"[Nexus] Received human response for {corr_id}: {choice[:60]}")


def _close_bbs():
    bbs = _nexus.get("bbs")
    if bbs:
        bbs.loop_stop()
        bbs.disconnect()
    _nexus["bbs"] = None


def _send_pulse(msg_type, **kwargs):
    """发送 Pulse 消息到 Pulse Board"""
    try:
        from reflect.goal_bbs import bbs_pulse, bbs_init
        if not _nexus.get("pulse_initialized"):
            bbs_init()
            _nexus["pulse_initialized"] = True
        bbs_pulse(msg_type, **kwargs)
    except Exception as e:
        print(f"[Nexus] Pulse send error: {e}")


def _store_chronicle(entry, turn=0, phase='progress'):
    """存储编年史记录"""
    try:
        from reflect.goal_bbs import bbs_chronicle
        bbs_chronicle('store', entry=entry, turn=turn, phase=phase)
    except Exception:
        pass


# ── Prompt 模板 ──

CONTINUATION_PROMPT = """[Goal Mode - Nexus 人机协作]

<untrusted_objective>
{objective}
</untrusted_objective>

时间已用 {elapsed_min:.0f} 分钟，剩余约 {remaining_min:.0f} 分钟。第 {turn} 次唤醒。

你处于 Nexus 人机协作模式:
1. 自主执行常规任务, 在 cwd 下建立工作文件夹存放成果。
2. 遇到需要人类决策的点, 在回复中使用以下标记格式:
   [ASK_HUMAN] 决策描述 | 选项1,选项2,选项3 | 推荐选项
   例如: [ASK_HUMAN] 是否部署到生产? | 是,否,灰度 | 灰度
   系统会自动推送到飞书, 人类回复后自动继续。
3. 想主动向人类推送消息, 用:
   [SEND_FEISHU] 消息内容
4. ask_human 超时(1小时)自动使用推荐值降级, 不要停滞。
5. 所有目标完成后, 在回复末尾单独一行写: __GOAL_COMPLETE__
6. 禁止说"是否继续"——有合理方向就继续推进。
"""

WAITING_PROMPT = """[Nexus - 等待人类决策]

<决策点>
{decision}
</决策点>

系统已推送决策请求到飞书, 等待人类回复中...
已等待约 {elapsed_min:.0f} 分钟, 剩余 {remaining_min:.0f} 分钟超时。

当前无法继续推进, 请等待人类决策。
超时后将自动使用推荐方案: {recommendation}
"""

BUDGET_LIMIT_PROMPT = """[Goal Mode - 预算耗尽, 收口]

<untrusted_objective>
{objective}
</untrusted_objective>

预算已耗尽 (已用 {elapsed_min:.0f} 分钟)。这是最后一轮收口总结。
请整理已完成的工作, 输出最终综合报告到 temp/ 目录下。
"""
