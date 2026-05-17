"""Standalone agent runner: python agent_runner.py name cap1,cap2"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MQTT_HOST"] = "127.0.0.1"
os.environ["MQTT_PORT"] = "1883"
import logging
logging.basicConfig(level=logging.WARN)

from mqtt_bbs import WorkerAgent

NAME = sys.argv[1]
CAPS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["test"]

def handler(task):
    return {"agent": NAME, "result": f"done_{task.type}"}

print(f"[{NAME}] starting caps={CAPS}...")
a = WorkerAgent(NAME, capabilities=CAPS)
a.on_task(handler)
a.start(block=True)
