import paho.mqtt.client as mqtt
import time, json, uuid, sys, os

def health_check():
    """BoardService event_loop健康检测"""
    results = {"ok": False, "detail": ""}
    corr_id = str(uuid.uuid4())
    msgs = []
    
    def on_msg(c, u, msg):
        msgs.append((msg.topic, msg.payload.decode('utf-8', errors='replace')))
    
    client = mqtt.Client(client_id=f"health_{int(time.time())}")
    client.on_message = on_msg
    client.connect("127.0.0.1", 1883, 5)
    client.subscribe(f"agent/bbs/health-check-{int(time.time())}/register/response/#")
    client.subscribe("#", qos=0)
    client.loop_start()
    time.sleep(0.5)
    
    board = f"health-check-{int(time.time())}"
    client.publish(f"agent/bbs/{board}/register", json.dumps({
        "name": "health_monitor",
        "corr_id": corr_id
    }), qos=1)
    time.sleep(3)
    
    found = any(corr_id in topic for topic, payload in msgs)
    client.loop_stop()
    client.disconnect()
    
    results["ok"] = found
    results["detail"] = "BoardService正常响应" if found else "BoardService无响应"
    return results

if __name__ == "__main__":
    result = health_check()
    print(json.dumps(result))
    sys.exit(0 if result["ok"] else 1)
