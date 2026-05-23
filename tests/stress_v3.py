"""
压力测试 v3 — 完全绕过MariaDB，纯BBSClient直连MQTT
Master直接BBSClient publish, Workers订阅处理，无需AgentBoard/WorkerAgent
"""
import sys, os, time, json, subprocess, uuid, threading

sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')

WORKER_COUNT = 5
TASK_PER_WORKER = 30
TASK_WORK_DELAY = 0.1
workdir = r'D:\open_claw_agent\GenericAgent_mqtt'
python_exe = r'D:\open_claw_agent\GenericAgent_mqtt\.venv\Scripts\python.exe'

# Worker代码 - 纯BBSClient
WORKER_CODE = r"""
import sys, time, json, os, uuid
sys.path.insert(0, r'{workdir}')
from mqtt_bbs.client import BBSClient
import logging
logging.basicConfig(level=logging.WARN)

wid = {wid}
wname = f"stress_worker_{wid:02d}"

c = BBSClient(wname, host="127.0.0.1", port=1883)
c.connect()
c.wait_connected(5)

results = {{}}

def on_task(topic, payload):
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode())
    task_id = payload.get("task_id", "")
    if not task_id or task_id in results:
        return
    results[task_id] = True
    
    time.sleep({delay})
    
    output = {{
        "task_id": task_id,
        "status": "completed",
        "result": {{"worker_id": wname, "msg": payload.get("input", {{}}).get("msg","")}},
        "agent_id": wname,
    }}
    c.publish(f"board/task/{{task_id}}/output", output, retain=True, qos=1)

c.subscribe(f"node/{{wname}}/task/input", on_task)
print(f"[{{wname}}] 就绪", flush=True)
try:
    while True:
        time.sleep(1)
except:
    c.disconnect()
"""

# ==== 启动 Workers ====
print(f"[1] 启动 {WORKER_COUNT} Workers...", flush=True)
workers = []
for i in range(WORKER_COUNT):
    code = WORKER_CODE.format(wid=i, delay=TASK_WORK_DELAY, workdir=workdir)
    p = subprocess.Popen(
        [python_exe, '-u', '-c', code],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    workers.append(p)
    print(f"  Worker[{i}] PID={p.pid}", flush=True)

time.sleep(3)
alive = sum(1 for p in workers if p.poll() is None)
print(f"  存活: {alive}/{WORKER_COUNT}", flush=True)

# ==== Master: 纯BBSClient发布任务 ====
print(f"\n[2] 发布任务 {WORKER_COUNT}*{TASK_PER_WORKER}...", flush=True)
from mqtt_bbs.client import BBSClient

master = BBSClient("stress_master", host="127.0.0.1", port=1883)
master.connect()
master.wait_connected(5)
print("  已连接MQTT", flush=True)

# 准备结果收集
results = {}
results_lock = threading.Lock()

def on_result(topic, payload):
    if isinstance(payload, bytes):
        payload = json.loads(payload.decode())
    tid = payload.get("task_id", "")
    status = payload.get("status", "")
    with results_lock:
        if tid not in results:
            results[tid] = payload

# 订阅所有board/task/+/output
master.subscribe("board/task/+/output", on_result)
# 也需要订阅node/+/task/output
master.subscribe("node/+/task/output", on_result)

time.sleep(1)

# 发布任务
task_ids = []
pub_start = time.time()
for w in range(WORKER_COUNT):
    for t in range(TASK_PER_WORKER):
        tid = f"task_{uuid.uuid4().hex[:8]}"
        msg = {
            "task_id": tid,
            "type": "stress_test",
            "input": {"msg": f"w{w:02d}_t{t:03d}", "seq": t},
        }
        # 同时发布到定向topic和board topic
        master.publish(f"node/stress_worker_{w:02d}/task/input", msg, qos=1)
        master.publish(f"board/task/{tid}/input", msg, qos=1)
        task_ids.append(tid)
pub_time = time.time() - pub_start
print(f"  发布: {len(task_ids)} 任务, {pub_time:.2f}s", flush=True)

# ==== 等待结果 ====
print(f"\n[3] 等待结果...", flush=True)
start_wait = time.time()
completed = 0
timeout_c = 0
poll_interval = 30  # 每30秒检查一次

for round_num in range(10):  # 最多等5分钟
    time.sleep(poll_interval)
    with results_lock:
        completed = sum(1 for tid in task_ids if tid in results and results[tid].get("status") == "completed")
    elapsed = time.time() - start_wait
    print(f"  第{round_num+1}轮: {completed}/{len(task_ids)} 完成, {elapsed:.0f}s", flush=True)
    if completed == len(task_ids):
        break

wait_time = time.time() - start_wait
timeout_c = len(task_ids) - completed

# ==== 清理 ====
print(f"\n[4] 清理...", flush=True)
for p in workers:
    try: p.terminate(); p.wait(3)
    except: 
        try: p.kill()
        except: pass
master.disconnect()

# ==== 报告 ====
print(f"\n[5] 结果", flush=True)
tput = completed/wait_time if wait_time > 0 else 0
print(f"  总任务: {len(task_ids)}", flush=True)
print(f"  完成:   {completed}", flush=True)
print(f"  超时:   {timeout_c}", flush=True)
print(f"  发布耗时: {pub_time:.2f}s", flush=True)
print(f"  等待耗时: {wait_time:.2f}s", flush=True)
print(f"  吞吐量:  {tput:.1f} tasks/s", flush=True)
if completed > 0:
    print(f"  平均延迟: {wait_time/completed*1000:.0f} ms/task", flush=True)

# 在BBS上报告
try:
    from mqtt_bbs.board_client import BoardClient
    import logging
    logging.getLogger('mqtt_bbs').setLevel(logging.ERROR)
    bc = BoardClient("stress_tester", board="agent-bbs-test")
    bc.connect()
    bc.wait_connected(5)
    reg = bc.register("stress_tester", timeout=5)
    token = reg.get("token", "")
    if token:
        report = f"[压力测试] {WORKER_COUNT}w*{TASK_PER_WORKER}t 完成={completed}/{len(task_ids)} {wait_time:.1f}s {tput:.1f}t/s"
        bc.post(report, token)
        print(f"  BBS报告: {report}", flush=True)
    bc.disconnect()
except Exception as e:
    print(f"  BBS报告跳过: {e}", flush=True)

print(f"\n{'='*50}", flush=True)
print(f">>> 完成!", flush=True)
