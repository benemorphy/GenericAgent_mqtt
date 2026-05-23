# -*- coding: utf-8 -*-
import sys, time, json, os
sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')
from mqtt_bbs.client import BBSClient
import logging
logging.basicConfig(level=logging.WARN)
wname = sys.argv[1]
log = open(r'D:\open_claw_agent\GenericAgent_mqtt\temp\wd_' + wname + '.txt', 'w', encoding='utf-8', buffering=1)
log.write("[" + wname + "] START\n")
log.flush()
c = BBSClient(wname, host="127.0.0.1", port=1883, mqtt_version=5)
c.connect()
c.wait_connected(5)
log.write("[" + wname + "] CONNECTED\n")
log.flush()
count = [0]
def on_task(topic, payload):
    if isinstance(payload, bytes): payload = json.loads(payload.decode())
    count[0] += 1
    task_id = payload.get("task_id", "")
    seq = payload.get("input", {}).get("seq","?")
    log.write("[" + wname + "] #" + str(count[0]) + " RECV " + task_id[:12] + " seq=" + str(seq) + "\n")
    log.flush()
    time.sleep(0.05)
    output = {"task_id": task_id, "status": "completed", "result": {"worker_id": wname}}
    c.publish("board/task/" + task_id + "/output", output, retain=True, qos=1)
    log.write("[" + wname + "] #" + str(count[0]) + " DONE\n")
    log.flush()
c.subscribe("node/" + wname + "/task/input", on_task)
log.write("[" + wname + "] SUB node/" + wname + "/task/input\n")
log.flush()
log.write("[" + wname + "] READY\n")
log.flush()
try:
    while True: time.sleep(1)
except: pass
c.disconnect()
log.close()
