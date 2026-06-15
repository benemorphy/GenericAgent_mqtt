"""
MQTT 优先级标记模块 — P0: 为关键 topic 设置 socket 优先级
基于 VLAN 802.1Q PCP / DSCP 映射，零硬件成本

用法:
    from mqtt_priority import apply_priority_to_client
    apply_priority_to_client(mqtt_client)
"""
import socket, re
from typing import List

# 优先级 topic 模式列表 (re 模式匹配)
# 级别 0-2 (默认=0, 高=1, 紧急=2)
PRIORITY_RULES: List[tuple] = [
    # (re_pattern, priority_level, description)
    (r"agent/[-\w]+/command/",     2, "Agent 命令 — 最高"),
    (r"board/global/signal",        2, "全局信号 — 最高"),
    (r"agent/[-\w]+/inject",        2, "Agent 注入指令 — 最高"),
    (r"bbs/[-\w]+/register",        1, "BBS 注册 — 高"),
    (r"bbs/[-\w]+/heartbeat",       1, "BBS 心跳 — 高"),
    (r"agent/[-\w]+/task/",         1, "Agent 任务 — 高"),
    (r"bbs/[-\w]+/log/",            0, "日志 — 普通"),
    (r".*/response/",               0, "响应 — 普通"),
]

# SO_PRIORITY 值 (Windows 支持)
# 0=Best Effort, 1=Background, 2=Excellent Effort, 3=Critical, 4=Video, 5=Voice, 6=Interative, 7=Network Control
PCP_MAP = {0: 0, 1: 3, 2: 7}

def get_topic_priority(topic: str) -> int:
    """返回 topic 的优先级等级 (0/1/2)"""
    for pattern, level, _ in PRIORITY_RULES:
        if re.match(pattern, topic):
            return level
    return 0

def apply_priority_to_sock(sock, level: int):
    """在 socket 上设置优先级"""
    if sock is None:
        return
    try:
        pcp = PCP_MAP.get(level, 0)
        # SO_PRIORITY on Windows
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, pcp)
        # IP_TOS / DSCP (跨平台)
        dscp = pcp << 5  # Simple DSCP mapping
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp)
    except (OSError, AttributeError):
        pass  # 静默降级，不影响业务

def apply_priority_to_client(client):
    """为 paho MQTT 客户端添加优先级发布能力"""
    original_publish = client.publish

    def prioritized_publish(topic, payload=None, qos=0, retain=False, **kwargs):
        level = get_topic_priority(topic)
        if level > 0:
            try:
                apply_priority_to_sock(client._sock, level)
            except AttributeError:
                pass
        return original_publish(topic, payload, qos=qos, retain=retain, **kwargs)

    client.publish = prioritized_publish
    
    # 重连后自动恢复
    original_connect = client.connect
    def connect_and_set(*args, **kwargs):
        result = original_connect(*args, **kwargs)
        try:
            apply_priority_to_sock(client._sock, 0)  # 默认 Best Effort
        except AttributeError:
            pass
        return result
    client.connect = connect_and_set

    return client
