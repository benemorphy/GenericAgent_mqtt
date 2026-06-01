# reflect/goal_bbs.py — Goal Pulse + Goal Chronicle: MQTT BBS 集成
# 可选依赖: Mqtt_bbs_client (通过 paho-mqtt 连接 Mosquitto)
# 不可用时静默降级为文件模式，不影响原 goal_mode 流程
#
# 用法 (在 goal_mode.py 中):
#   from goal_bbs import bbs_init, bbs_pulse, bbs_chronicle, bbs_close

import os, sys, time, json, socket, logging

_dir = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger('goal_bbs')

# ---- 全局状态 ----
_bbs = None          # BoardClient 实例
_bbs_client = None   # paho mqtt 客户端 (直接 publish 用)
_agent_id = ""       # 唯一 agent 标识
_token = ""          # register 返回的 token
_enabled = False     # BBS 是否可用
_pulse_board = "goal_pulse"
_chronicle_board = "goal_chronicle"

def bbs_init(pulse_board: str = "goal_pulse", chronicle_board: str = "goal_chronicle") -> bool:
    """初始化 BBS 连接。
    
    尝试连接 MQTT Broker 并注册到 Board。
    失败时静默降级 (返回 False)。
    
    Args:
        pulse_board: Pulse 模式使用的 Board 名称
        chronicle_board: Chronicle 模式使用的 Board 名称
    
    Returns:
        True if BBS 连接成功, False if 降级
    """
    global _bbs, _bbs_client, _agent_id, _token, _enabled, _pulse_board, _chronicle_board
    
    if _bbs is not None:
        return True
    
    _pulse_board = pulse_board
    _chronicle_board = chronicle_board
    
    try:
        # 确保 Mqtt_bbs_client 在 sys.path 上
        # 从 reflect/ -> GA/ -> Beneh/
        ga_dir = os.path.abspath(os.path.join(_dir, '..'))
        beneh_dir = os.path.abspath(os.path.join(_dir, '..', '..'))
        for p in [ga_dir, beneh_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)
        
        from Mqtt_bbs_client.board_client import BoardClient
        
        _agent_id = f"goal_{socket.gethostname()}_{os.getpid()}_{int(time.time())}"
        
        # 连接 Pulse Board
        _bbs = BoardClient(_agent_id, board=_pulse_board)
        _bbs.connect()
        
        # 注册获取 token (超时也不影响后续直接 publish)
        reg = _bbs.register("goal_mode_agent")
        _token = reg.get("token", "")
        
        # 保存 paho 客户端的引用，用于直接 publish (fire-and-forget)
        _bbs_client = _bbs._client
        
        _enabled = True
        print(f"[GoalBBS] Connected: agent={_agent_id} board={_pulse_board}")
        return True
        
    except Exception as e:
        _enabled = False
        print(f"[GoalBBS] Unavailable (fallback to file-only): {e}")
        return False

def bbs_pulse(msg_type: str, **kwargs):
    """发送脉冲消息到 Pulse Board (fire-and-forget, 不等待响应).
    
    每轮 goal 执行完毕后调用，广播当前状态。
    BBS 不可用时静默跳过。
    
    Args:
        msg_type: 脉冲类型 (如 'turn_done', 'wrapping_up', 'goal_complete')
        **kwargs: 自定义字段 (如 turn=5, focus="审计代码", progress="30%")
    """
    if not _enabled or _bbs_client is None:
        return
    
    try:
        import json
        payload = {
            "v": 1,
            "action": "post",
            "source": _agent_id,
            "type": msg_type,
            "agent_id": _agent_id,
            "token": _token,
            "timestamp": time.time(),
        }
        payload.update(kwargs)
        
        topic = f"bbs/{_pulse_board}/post"
        _bbs_client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
        log.debug(f"[Pulse] fire-and-forget: {msg_type} -> {topic}")
    except Exception as e:
        log.warning(f"[Pulse] publish error: {e}")

def bbs_chronicle(action: str = "query", **kwargs):
    """操作 Chronicle Board。
    
    Chronicles:
        query: 查询历史编年记录 (返回 posts 列表)
        store: 存储一条编年记录
        summary: 存储目标完成摘要
    
    Args:
        action: 'query' | 'store' | 'summary'
        **kwargs: 与 action 相关的参数
    
    Returns:
        query 时返回 posts 列表, 否则返回 None
    """
    if not _enabled or _bbs is None:
        return [] if action == 'query' else None
    
    try:
        if action == 'query':
            limit = kwargs.get('limit', 20)
            # 查询当前 Board 的历史
            posts = _bbs.query_posts(limit=limit)
            return posts
            
        elif action == 'store':
            payload = {
                "v": 1,
                "action": "post",
                "source": _agent_id,
                "type": "chronicle_entry",
                "agent_id": _agent_id,
                "token": _token,
                "timestamp": time.time(),
                "entry": kwargs.get('entry', ''),
                "turn": kwargs.get('turn', 0),
                "phase": kwargs.get('phase', 'progress'),
            }
            topic = f"bbs/{_chronicle_board}/post"
            _bbs_client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
            
        elif action == 'summary':
            payload = {
                "v": 1,
                "action": "post",
                "source": _agent_id,
                "type": "goal_summary",
                "agent_id": _agent_id,
                "token": _token,
                "timestamp": time.time(),
                "summary": kwargs.get('summary', ''),
                "total_turns": kwargs.get('total_turns', 0),
                "duration_sec": kwargs.get('duration_sec', 0),
                "findings": kwargs.get('findings', []),
            }
            topic = f"bbs/{_chronicle_board}/post"
            _bbs_client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
            
    except Exception as e:
        log.warning(f"[Chronicle] {action} error: {e}")
    
    return [] if action == 'query' else None

def bbs_close():
    """关闭 BBS 连接"""
    global _bbs, _bbs_client, _enabled
    if _bbs_client:
        try:
            _bbs_client.disconnect()
        except Exception:
            pass
        _bbs_client = None
    if _bbs:
        try:
            _bbs.disconnect()
        except Exception:
            pass
        _bbs = None
    _enabled = False
    print("[GoalBBS] Disconnected")

# ── 简便单行调用 ──
def quick_pulse(turn: int, focus: str, progress: str = "", remaining_min: float = 0):
    """快速发送一轮 Pulse 状态"""
    bbs_pulse(
        'turn_complete',
        turn=turn,
        focus=focus,
        progress=progress,
        remaining_min=round(remaining_min, 1),
    )
