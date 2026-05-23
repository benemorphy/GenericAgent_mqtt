# -*- coding: utf-8 -*-
"""Debug: Worker#1 收不到消息根因"""
import sys, os, time, json, subprocess, uuid, threading

sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')
workdir = r'D:\open_claw_agent\GenericAgent_mqtt'
python_exe = os.path.join(workdir, '.venv', 'Scripts', 'python.exe')
log_dir = os.path.join(workdir, 'temp')

worker_py = os.path.join(workdir, 'tests', '_worker_debug.py')
with open(worker_py, 'w', encoding='utf-8') as f:
    f.write(r'''# -*- coding: utf-8 -*-
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
    log.write("[" + wname + "] #" + str(count[0]) + "RECV " + task_id[:12] + " seq=" + str(seq) + "\n")
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
''')


def run_test(test_name, worker_names):
    print(f"\n{'='*50}")
    print(f"TEST: {test_name}")
    print(f"Workers: {worker_names}")
    
    for n in worker_names:
        lf = os.path.join(log_dir, f'wd_{n}.txt')
        if os.path.exists(lf): os.remove(lf)
    
    workers = []
    for name in worker_names:
        p = subprocess.Popen(
            [python_exe, '-u', worker_py, name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        workers.append(p)
        time.sleep(0.5)
    
    time.sleep(3)
    
    all_ready = True
    for name in worker_names:
        lf = os.path.join(log_dir, f'wd_{name}.txt')
        if os.path.exists(lf):
            with open(lf, 'r', encoding='utf-8') as f:
                if 'READY' not in f.read():
                    all_ready = False
                    print(f"  WARN: {name} NOT READY")
    
    if not all_ready:
        print("  [SKIP] workers not ready")
        for p in workers:
            try: p.terminate()
            except: pass
        return None
    
    print("  OK: all ready")
    
    from mqtt_bbs.client import BBSClient
    master = BBSClient("dm", host="127.0.0.1", port=1883, mqtt_version=5)
    master.connect()
    master.wait_connected(5)
    
    results = {}
    lock = threading.Lock()
    def on_result(t, p):
        if isinstance(p, bytes): p = json.loads(p.decode())
        with lock: results[p.get("task_id","")] = p
    master.subscribe("board/task/+/output", on_result)
    time.sleep(1)
    
    task_ids = []
    for name in worker_names:
        for t in range(5):
            tid = f"t_{uuid.uuid4().hex[:8]}"
            msg = {"task_id": tid, "type": "test", "input": {"seq": t, "msg": f"{name}_t{t}"}}
            master.publish("node/" + name + "/task/input", msg, qos=1)
            task_ids.append(tid)
    
    total = len(task_ids)
    print(f"  Published {total} tasks")
    
    for i in range(10):
        time.sleep(1)
        with lock:
            done = sum(1 for tid in task_ids if tid in results)
        if done == total:
            print(f"  {i+1}s: {done}/{total} ALL DONE")
            break
        print(f"  {i+1}s: {done}/{total}")
    
    master.disconnect()
    
    stats = {}
    for name in worker_names:
        lf = os.path.join(log_dir, f'wd_{name}.txt')
        if os.path.exists(lf):
            with open(lf, 'r', encoding='utf-8') as f:
                content = f.read()
            received = content.count("RECV")
            done = content.count("DONE")
            stats[name] = {"recv": received, "done": done}
        else:
            stats[name] = {"recv": 0, "done": 0}
    
    for p in workers:
        try: p.terminate(); p.wait(timeout=3)
        except: pass
    
    return stats


# === Test sequence ===
results = []

s = run_test("sw_0 -> sw_1 (original)", ["sw_0", "sw_1"])
if s: results.append(("sw_0->sw_1", s))

s = run_test("sw_1 -> sw_0 (reversed)", ["sw_1", "sw_0"])
if s: results.append(("sw_1->sw_0", s))

s = run_test("wa -> wb (different names)", ["wa", "wb"])
if s: results.append(("wa->wb", s))

s = run_test("w0 -> w1 -> w2 (3 workers)", ["w0", "w1", "w2"])
if s: results.append(("w0->w1->w2", s))

s = run_test("w5 -> w4 -> w3 (3 reversed)", ["w5", "w4", "w3"])
if s: results.append(("w5->w4->w3", s))

s = run_test("xa -> xb (single worker each)", ["xa", "xb"])
if s: results.append(("xa->xb", s))

print(f"\n\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
for name, stats in results.items() if hasattr(results, 'items') else []:
    pass

for name, stats in results:
    parts = [f"{k}:{v['recv']}/{v['done']}" for k,v in stats.items()]
    print(f"  {name:20} | {' | '.join(parts)}")
