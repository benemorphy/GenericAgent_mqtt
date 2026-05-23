# -*- coding: utf-8 -*-
"""
压力测试最终版 - 5 Workers x 30 Tasks
使用BBSClient直连，写日志文件，顺序启动
"""
import sys, os, time, json, subprocess, uuid, threading

sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')
workdir = r'D:\open_claw_agent\GenericAgent_mqtt'
python_exe = os.path.join(workdir, '.venv', 'Scripts', 'python.exe')
log_dir = os.path.join(workdir, 'temp')

WORKER_COUNT = 5
TASK_PER_WORKER = 30
TASK_DELAY = 0.05

# Worker Python code (no format strings at all)
worker_py = os.path.join(workdir, 'temp', '_worker.py')
with open(worker_py, 'w', encoding='utf-8') as f:
    f.write(r'''# -*- coding: utf-8 -*-
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
''')

# ==== 1. 启动 Workers ====
print("[1] 启动 Workers...")
workers = []
for i in range(WORKER_COUNT):
    p = subprocess.Popen(
        [python_exe, '-u', worker_py, str(i), str(TASK_DELAY)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    workers.append(p)
    print(f"  Worker[{i}] PID={p.pid}")
    time.sleep(0.5)

time.sleep(3)
alive = sum(1 for p in workers if p.poll() is None)
print(f"  存活: {alive}/{WORKER_COUNT}")
if alive == 0:
    print("  [FAIL] 全部失败退出")
    sys.exit(1)

# 验证所有worker日志
for i in range(WORKER_COUNT):
    log_file = os.path.join(log_dir, f'log_{i}.txt')
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            print(f"  Worker[{i}] 日志: {lines[-1] if lines else '空'}")

# ==== 2. 发布任务 ====
print(f"\n[2] 发布 {WORKER_COUNT}*{TASK_PER_WORKER}={WORKER_COUNT*TASK_PER_WORKER} 任务...")
from mqtt_bbs.client import BBSClient

master = BBSClient("master", host="127.0.0.1", port=1883, mqtt_version=5)
master.connect()
master.wait_connected(5)
print("  Master 已连接")

# 收集结果
results = {}
lock = threading.Lock()

def on_result(topic, payload):
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode())
    tid = payload.get("task_id", "")
    if tid:
        with lock:
            results[tid] = payload

master.subscribe("board/task/+/output", on_result)
time.sleep(1)

# 发布
task_ids = []
pub_start = time.time()
for w in range(WORKER_COUNT):
    for t in range(TASK_PER_WORKER):
        tid = "t_" + uuid.uuid4().hex[:8]
        msg = {
            "task_id": tid,
            "type": "stress",
            "input": {"msg": f"w{w}_t{t}", "seq": t},
        }
        master.publish("node/sw_" + str(w) + "/task/input", msg, qos=1)
        task_ids.append(tid)
pub_time = time.time() - pub_start
print(f"  发布耗时: {pub_time:.2f}s")

# ==== 3. 等待 ====
print(f"\n[3] 等待结果...")
start_wait = time.time()
total = len(task_ids)

for round_num in range(20):  # 最多等100秒
    time.sleep(5)
    with lock:
        completed = sum(1 for tid in task_ids if tid in results and results[tid].get("status") == "completed")
    elapsed = time.time() - start_wait
    print(f"  {elapsed:.0f}s: {completed}/{total}")
    if completed == total:
        print("  全部完成!")
        break

wait_time = time.time() - start_wait
timeout_c = total - completed

# ==== 4. 读取worker日志 ====
print(f"\n[4] Worker处理统计:")
total_processed = 0
for i in range(WORKER_COUNT):
    log_file = os.path.join(log_dir, f'log_{i}.txt')
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            done_count = content.count("done")
            total_processed += done_count
            print(f"  Worker[{i}]: 处理 {done_count} 任务")
    else:
        print(f"  Worker[{i}]: 无日志")

# ==== 5. 清理 ====
print(f"\n[5] 清理...")
for p in workers:
    try: p.terminate(); p.wait(timeout=3)
    except:
        try: p.kill()
        except: pass
master.disconnect()

# ==== 6. 报告 ====
print(f"\n[6] 结果报告")
tput = completed/wait_time if wait_time > 0 else 0
print(f"  {'='*40}")
print(f"  总任务: {total}")
print(f"  完成:   {completed}")
print(f"  超时:   {timeout_c}")
print(f"  Worker处理总数: {total_processed}")
print(f"  发布耗时: {pub_time:.2f}s")
print(f"  等待耗时: {wait_time:.1f}s")
print(f"  吞吐量:  {tput:.1f} tasks/s")
if completed > 0:
    print(f"  平均延迟: {wait_time/completed*1000:.0f} ms/task")
print(f"  {'='*40}")
