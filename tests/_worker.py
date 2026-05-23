# -*- coding: utf-8 -*-
import sys, time, json, os
sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')
from mqtt_bbs.client import BBSClient
import logging
logging.basicConfig(level=logging.WARN)

import sys
wid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
wname = f"sw_{wid}"
log = open(r'D:\open_claw_agent\GenericAgent_mqtt\temp\log_' + str(wid) + '.txt', 'w', encoding='utf-8', buffering=1)

log.write(f"[{wname}] 启动\n")
log.flush()

c = BBSClient(wname, host="127.0.0.1", port=1883, mqtt_version=5)
c.connect()
c.wait_connected(5)
log.write(f"[{wname}] 已连接\n")
log.flush()

count = [0]
def on_task(topic, payload):
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode())
    count[0] += 1
    n = count[0]
    task_id = payload.get("task_id", "")
    task_input = payload.get("input", {})
    log.write(f"[{wname}] #{n} task={task_id[:12]} seq={task_input.get('seq','?')}\n")
    log.flush()
    time.sleep(delay)
    output = {
        "task_id": task_id,
        "status": "completed",
        "result": {"worker_id": wname, "echo": task_input.get("msg","")},
    }
    c.publish("board/task/" + task_id + "/output", output, retain=True, qos=1)
    log.write(f"[{wname}] #{n} done\n")
    log.flush()

c.subscribe("node/" + wname + "/task/input", on_task)
log.write(f"[{wname}] 就绪\n")
log.flush()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
c.disconnect()
log.close()
