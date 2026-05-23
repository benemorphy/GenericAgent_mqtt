"""
一体化压力测试：启动5 workers → 发布任务 → 等待结果 → 报告
"""
import sys, os, time, json, subprocess, socket

sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')

WORKER_COUNT = 5
TASK_PER_WORKER = 10
TASK_WORK_DELAY = 0.1
workdir = r'D:\open_claw_agent\GenericAgent_mqtt'
python_exe = r'D:\open_claw_agent\GenericAgent_mqtt\.venv\Scripts\python.exe'

# ==== 1. 启动 Workers ====
print("[1] 启动 Workers...", flush=True)
workers = []
worker_code_tpl = r"""
import sys, time, logging
sys.path.insert(0, r'{workdir}')
logging.basicConfig(level=logging.WARN)
from mqtt_bbs.bbs import WorkerAgent, TaskMessage
def handler(task):
    time.sleep({delay})
    return {{"result": "ok", "worker_id": {wid}, "echo": task.input.get("msg","")}}
w = WorkerAgent("stress_worker_{wid:02d}", capabilities=["stress_test"], host="127.0.0.1", port=1883)
w.on_task(handler)
w.start(block=True)
"""

for i in range(WORKER_COUNT):
    code = worker_code_tpl.format(wid=i, delay=TASK_WORK_DELAY, workdir=workdir)
    p = subprocess.Popen(
        [python_exe, '-u', '-c', code],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    workers.append(p)
    print(f"  Worker[{i}] PID={p.pid}", flush=True)
    time.sleep(0.5)

time.sleep(3)
alive = sum(1 for p in workers if p.poll() is None)
print(f"  存活: {alive}/{WORKER_COUNT}", flush=True)

if alive < WORKER_COUNT:
    print("[FAIL] Workers 启动不足! 清理退出", flush=True)
    for p in workers:
        try: p.terminate(); p.wait(2)
        except: pass
    sys.exit(1)

# ==== 2. 发布任务 ====
print(f"\n[2] 发布任务 ({WORKER_COUNT}*{TASK_PER_WORKER}={WORKER_COUNT*TASK_PER_WORKER})...", flush=True)
from mqtt_bbs.bbs import AgentBoard

board = AgentBoard("stress_master", host="127.0.0.1", port=1883)
board._client.connect()
board._client.wait_connected(5)
print(f"  已连接MQTT", flush=True)

task_ids = []
pub_start = time.time()
for w in range(WORKER_COUNT):
    for t in range(TASK_PER_WORKER):
        tid = board.post_task_routed(
            "stress_test",
            {"msg": f"w{w:02d}_t{t:03d}", "seq": t},
            target_agent_id=f"stress_worker_{w:02d}",
        )
        task_ids.append(tid)
pub_time = time.time() - pub_start
print(f"  发布: {len(task_ids)} 任务, {pub_time:.2f}s", flush=True)

# ==== 3. 等待结果 ====
print(f"\n[3] 等待结果 (超时每任务30s)...", flush=True)
start_wait = time.time()
completed = 0
failed = 0
timeout = 0

for idx, tid in enumerate(task_ids):
    out = board.wait_task(tid, timeout=30)
    if out.status in ("completed", "done"):
        completed += 1
    elif out.status == "timeout":
        timeout += 1
    else:
        failed += 1
    
    if (idx+1) % 10 == 0:
        print(f"  进度: {idx+1}/{len(task_ids)} (完成{completed}, 失败{failed}, 超时{timeout})", flush=True)

wait_time = time.time() - start_wait

# ==== 4. 报告 ====
print(f"\n[4] 结果", flush=True)
print(f"  总任务: {len(task_ids)}", flush=True)
print(f"  完成:   {completed}", flush=True)
print(f"  失败:   {failed}", flush=True)
print(f"  超时:   {timeout}", flush=True)
print(f"  发布:   {pub_time:.2f}s", flush=True)
print(f"  等待:   {wait_time:.2f}s", flush=True)
tput = completed/wait_time if wait_time > 0 else 0
print(f"  吞吐:   {tput:.1f} tasks/s", flush=True)

# ==== 5. 清理 ====
print(f"\n[5] 清理 {len(workers)} Workers...", flush=True)
for p in workers:
    try: p.terminate(); p.wait(timeout=3)
    except:
        try: p.kill()
        except: pass
board._client.disconnect()

# ==== 6. 发布BBS报告 ====
try:
    from mqtt_bbs.board_client import BoardClient
    with BoardClient("stress_tester", board="agent-bbs-test") as bbs:
        reg = bbs.register("stress_tester", timeout=3)
        token = reg.get("token", "")
        if token:
            report = (
                f"[压力测试] {WORKER_COUNT}w*{TASK_PER_WORKER}t "
                f"| 完成={completed}/{len(task_ids)} "
                f"| {wait_time:.1f}s | {tput:.1f}t/s"
            )
            bbs.post(report, token)
            print(f"  BBS报告: {report}", flush=True)
except Exception as e:
    print(f"  BBS报告失败: {e}", flush=True)

print(f"\n>>> 完成!", flush=True)
