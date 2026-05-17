"""
mqtt_bbs Dashboard 数据源

订阅 MQTT 主题 → 本地缓存 → get_tasks()/get_agents() 统一接口
"""

import json, time, threading, logging
from mqtt_bbs import BBSClient

class MQTTDataSource:
    """MQTT 数据源：订阅所有 task/agent 主题，维护本地缓存"""

    def __init__(self, host="127.0.0.1", port=1883):
        self._lock = threading.Lock()
        self._tasks = {}       # task_id -> dict
        self._agents = {}      # agent_id -> dict
        self._client = BBSClient("dashboard", host=host)
        self._client.connect()
        self._client.wait_connected(3)
        # 订阅所有任务相关主题
        self._client.subscribe("board/task/+/input", self._on_task_input)
        self._client.subscribe("board/task/+/output", self._on_task_output)
        self._client.subscribe("board/task/+/status", self._on_task_status)
        self._client.subscribe("board/task/+/stdout", self._on_task_stdout)
        self._client.subscribe("board/task/+/stderr", self._on_task_stderr)
        self._client.subscribe("node/+/status", self._on_agent_status)
        self._client.subscribe("node/+/capability", self._on_agent_cap)
        log.info(f"MQTT数据源就绪 (host={host})")

    def _on_task_input(self, topic, payload):
        # topic: board/task/{id}/input
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            t["task_id"] = task_id
            t["input"] = payload
            t["type"] = payload.get("type","?") if isinstance(payload,dict) else "?"
            t["updated_at"] = time.time()

    def _on_task_output(self, topic, payload):
        parts = topic.split("/"); task_id = parts[2] if len(parts)>=3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            t["output"] = payload
            if isinstance(payload, dict):
                if "status" in payload: t["status"] = payload["status"]
                if "result" in payload: t["result"] = payload["result"]
            t["updated_at"] = time.time()

    def _on_task_status(self, topic, payload):
        parts = topic.split("/"); task_id = parts[2] if len(parts)>=3 else "?"
        status = payload.get("status", payload) if isinstance(payload, dict) else (payload.decode() if isinstance(payload, bytes) else str(payload))
        with self._lock:
            self._tasks.setdefault(task_id, {})["status"] = status
            self._tasks[task_id]["updated_at"] = time.time()

    def _on_task_stdout(self, topic, payload):
        parts = topic.split("/"); task_id = parts[2] if len(parts)>=3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            logs = t.setdefault("stdout", [])
            text = payload.get("data","") if isinstance(payload,dict) else str(payload)
            logs.append(text)
            if len(logs) > 100: logs.pop(0)

    def _on_task_stderr(self, topic, payload):
        parts = topic.split("/"); task_id = parts[2] if len(parts)>=3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            errs = t.setdefault("stderr", [])
            text = payload.get("data","") if isinstance(payload,dict) else str(payload)
            errs.append(text)
            if len(errs) > 100: errs.pop(0)

    def _on_agent_status(self, topic, payload):
        parts = topic.split("/"); agent_id = parts[1] if len(parts)>=2 else "?"
        status = payload.get("status", payload) if isinstance(payload, dict) else (payload.decode() if isinstance(payload, bytes) else str(payload))
        with self._lock:
            self._agents.setdefault(agent_id, {})["status"] = status
            self._agents[agent_id]["updated_at"] = time.time()

    def _on_agent_cap(self, topic, payload):
        parts = topic.split("/"); agent_id = parts[1] if len(parts)>=2 else "?"
        with self._lock:
            self._agents.setdefault(agent_id, {})["capabilities"] = payload

    def get_tasks(self):
        with self._lock: return dict(self._tasks)

    def get_agents(self):
        with self._lock: return dict(self._agents)

    def cancel_task(self, task_id):
        self._client.publish(f"board/task/{task_id}/signal", "[CANCEL]", retain=True, qos=2)

    def close(self):
        self._client.disconnect()

log = logging.getLogger("mqtt_dash")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ds = MQTTDataSource(host="127.0.0.1")
    time.sleep(5)
    tasks = ds.get_tasks()
    agents = ds.get_agents()
    print(f"发现 {len(tasks)} 个任务, {len(agents)} 个Agent")
    for tid, t in tasks.items():
        print(f"  {tid}: type={t.get('type','?')}, status={t.get('status','?')}")
    for aid, a in agents.items():
        print(f"  Agent {aid}: status={a.get('status','?')}")
    print("\n" + "="*50)
    print("  测试通过!" if tasks else "  无数据(发布任务后重试)")
    ds.close()
