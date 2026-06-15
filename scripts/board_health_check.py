"""
BoardService 增强型健康检测脚本

检测维度:
1. MQTT Broker 连通性 (ping + echo)
2. BoardService 响应性 (topic 请求/响应)
3. 速率限制器状态 (如果 BBSClient 可用)
4. 插件管理器状态 (如果已加载)
5. 审计日志状态

用法:
    python scripts/board_health_check.py          # 基础健康检查
    python scripts/board_health_check.py --full   # 全面检查（含限流统计）
    python scripts/board_health_check.py --json   # 输出 JSON
"""

import paho.mqtt.client as mqtt
import time, json, uuid, sys, os, argparse

# 确保能导入 Mqtt_bbs_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

HEALTH_TOPIC = "system/health/check"
HEALTH_RESP_TOPIC = "system/health/response"
CHECK_TIMEOUT = 5.0


def check_broker_connectivity(host="127.0.0.1", port=1883, timeout=5):
    """检查 MQTT Broker 连通性"""
    results = {"ok": False, "detail": ""}
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                             f"health_check_{uuid.uuid4().hex[:8]}",
                             protocol=mqtt.MQTTv311)
        client.connect(host, port, timeout)
        client.loop_start()
        time.sleep(0.5)
        if client.is_connected():
            results["ok"] = True
            results["detail"] = f"Broker reachable at {host}:{port}"
        else:
            results["detail"] = f"Broker {host}:{port} connect failed"
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        results["detail"] = f"Broker unreachable: {e}"
    return results


def check_board_service(host="127.0.0.1", port=1883, timeout=5):
    """检查 BoardService 响应性"""
    results = {"ok": False, "detail": ""}
    corr_id = str(uuid.uuid4())
    msgs = []

    def on_msg(c, u, msg):
        msgs.append((msg.topic, msg.payload.decode('utf-8', errors='replace')))

    client_id = f"health_check_{uuid.uuid4().hex[:8]}"
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id,
                             protocol=mqtt.MQTTv311)
        client.on_message = on_msg
        client.connect(host, port, timeout)
        client.loop_start()
        client.subscribe(HEALTH_RESP_TOPIC, qos=1)
        time.sleep(0.3)

        payload = json.dumps({
            "v": 1, "action": "health_check", "corr_id": corr_id,
            "source": "health_check", "timestamp": time.time(),
        })
        client.publish(HEALTH_TOPIC, payload, qos=1)
        time.sleep(timeout)

        found = any(corr_id in topic for topic, payload in msgs)
        results["ok"] = found
        results["detail"] = "BoardService 正常响应" if found else "BoardService 无响应"
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        results["detail"] = f"BoardService check failed: {e}"
    return results


def check_mqtt_bbs_library():
    """检查 Mqtt_bbs_client 各模块加载状态"""
    results = {"modules": {}, "ok": True}
    try:
        from Mqtt_bbs_client import config
        results["modules"]["config"] = "ok"
        results["broker"] = f"{config.BROKER_HOST}:{config.BROKER_PORT}"
        results["tls"] = config.MQTT_TLS_ENABLED
        results["rate_limiting"] = config.RATE_LIMIT_ENABLED
        results["audit_log"] = config.AUDIT_LOG_ENABLED
    except Exception as e:
        results["modules"]["config"] = f"error: {e}"
        results["ok"] = False

    try:
        from Mqtt_bbs_client.rate_limiter import RateLimiter
        rl = RateLimiter(enabled=False)
        results["modules"]["rate_limiter"] = "ok"
    except Exception as e:
        results["modules"]["rate_limiter"] = f"error: {e}"
        results["ok"] = False

    try:
        from Mqtt_bbs_client.audit_log import AuditLogger
        results["modules"]["audit_log"] = "ok"
    except Exception as e:
        results["modules"]["audit_log"] = f"error: {e}"
        results["ok"] = False

    try:
        from Mqtt_bbs_client.plugin import PluginManager
        results["modules"]["plugin"] = "ok"
    except Exception as e:
        results["modules"]["plugin"] = f"error: {e}"
        results["ok"] = False

    return results


def full_health_check():
    """执行全面健康检查"""
    result = {
        "timestamp": time.time(),
        "broker": check_broker_connectivity(),
        "board_service": check_board_service(),
        "library": check_mqtt_bbs_library(),
    }
    result["overall"] = all(
        v.get("ok", False) if isinstance(v, dict) and "ok" in v
        else v.get("modules", {}).get("config", "") == "ok"
        for v in result.values()
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT BBS 健康检查")
    parser.add_argument("--full", action="store_true", help="全面检查")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = parser.parse_args()

    if args.full:
        result = full_health_check()
    else:
        result = {
            "timestamp": time.time(),
            "broker": check_broker_connectivity(),
            "board_service": check_board_service(),
            "library": check_mqtt_bbs_library(),
        }
        result["overall"] = result["broker"]["ok"] and result["board_service"]["ok"]

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== MQTT BBS 健康检查 ({time.strftime('%Y-%m-%d %H:%M:%S')}) ===")
        print(f"[Broker] {result['broker']['detail']}")
        print(f"[BoardService] {result['board_service']['detail']}")
        print(f"[Library] {'OK' if result['library'].get('ok') else 'ISSUE'}")
        for mod, status in result['library'].get('modules', {}).items():
            print(f"  - {mod}: {status}")
        if 'rate_limiting' in result['library']:
            print(f"[RateLimit] 状态: {'enabled' if result['library']['rate_limiting'] else 'disabled'}")
        if 'audit_log' in result['library']:
            print(f"[AuditLog] 状态: {'enabled' if result['library']['audit_log'] else 'disabled'}")
        if 'tls' in result['library']:
            print(f"[TLS] 状态: {'enabled' if result['library']['tls'] else 'disabled'}")
        print(f"[Overall] {'PASS' if result.get('overall') else 'FAIL'}")

    sys.exit(0 if result.get('overall') else 1)
