"""
Worker Agent 压力测试 v2 — 基于subprocess + wait_task
5 workers, 每worker 30个任务，测吞吐量和延迟
"""
import sys, os, time, json, subprocess, signal, socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WORKER_COUNT = 5
TASK_PER_WORKER = 30
TASK_WORK_DELAY = 0.1
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883

python_exe = r'D:\open_claw_agent\GenericAgent_mqtt\.venv\Scripts\python.exe'
workdir = r'D:\open_claw_agent\GenericAgent_mqtt'

# ── Worker 启动脚本 ──
WORKER_CODE = r"""
import sys, os, time, logging
sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')
logging.basicConfig(level=logging.WARN, format="[W{id}] %(message)s")
from mqtt_bbs.bbs import WorkerAgent, TaskMessage

def handler(task):
    time.sleep({delay})
    return {{"result": "ok", "worker_id": {id}, "echo": task.input.get("msg","")}}

w = WorkerAgent("stress_worker_{id:02d}", capabilities=["stress_test"], host="{host}", port={port})
w.on_task(handler)
w.start(block=True)
"""

def start_worker(worker_id: int) -> subprocess.Popen:
    code = WORKER_CODE.format(
        id=worker_id, delay=TASK_WORK_DELAY,
        host=BROKER_HOST, port=BROKER_PORT
    )
    return subprocess.Popen(
        [python_exe, '-u', '-c', code],
        cwd=workdir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def run_test():
    print("=" * 60)
    print("WORKER AGENT 压力测试 v2")
    print(f"    Workers: {WORKER_COUNT}")
    print(f"    任务/Worker: {TASK_PER_WORKER}")
    print(f"    总任务: {WORKER_COUNT * TASK_PER_WORKER}")
    print(f"    模拟耗时/任务: {TASK_WORK_DELAY}s")
    print("=" * 60)

    # 1. 验证服务
    print("\n[1/5] 验证基础设施...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((BROKER_HOST, BROKER_PORT))
        s.close()
        print(f"  [OK] MQTT Broker 在线")
    except Exception as e:
        print(f"  [FAIL] MQTT Broker: {e}")
        return

    # 2. 启动 Workers
    print(f"\n[2/5] 启动 {WORKER_COUNT} 个 Worker...")
    workers = []
    for i in range(WORKER_COUNT):
        p = start_worker(i)
        workers.append(p)
        print(f"  [START] Worker[{i:02d}] PID={p.pid}")
        time.sleep(0.5)

    time.sleep(2)  # 等待完全就绪
    alive = sum(1 for p in workers if p.poll() is None)
    print(f"  Workers 存活: {alive}/{WORKER_COUNT}")

    # 3. 发布任务
    print(f"\n[3/5] 发布任务...")
    from mqtt_bbs.bbs import AgentBoard

    board = AgentBoard("stress_master", host=BROKER_HOST, port=BROKER_PORT)
    board._client.connect()
    board._client.wait_connected(5)

    task_ids = []
    pub_start = time.time()
    pub_errors = 0

    for w in range(WORKER_COUNT):
        for t in range(TASK_PER_WORKER):
            try:
                tid = board.post_task_routed(
                    "stress_test",
                    {"msg": f"w{w:02d}_task{t:03d}", "seq": t},
                    target_agent_id=f"stress_worker_{w:02d}",
                )
                task_ids.append(tid)
            except Exception as e:
                pub_errors += 1

    pub_time = time.time() - pub_start
    print(f"  发布: {len(task_ids)} 任务, {pub_errors} 错误, {pub_time:.2f}s")

    # 4. 等待结果（逐个wait_task）
    print(f"\n[4/5] 等待任务完成...")
    start_wait = time.time()
    per_task_timeout = TASK_PER_WORKER * (TASK_WORK_DELAY + 0.5) + 10
    completed = []
    failed = []
    timed_out = []

    for idx, tid in enumerate(task_ids):
        out = board.wait_task(tid, timeout=per_task_timeout)
        if out.status in ("completed", "done"):
            completed.append(out)
        elif out.status == "timeout":
            timed_out.append(out)
        else:
            failed.append(out)

        if (idx + 1) % 20 == 0:
            print(f"   进度: {idx+1}/{len(task_ids)} (完成{len(completed)}, 失败{len(failed)}, 超时{len(timed_out)})")

    wait_time = time.time() - start_wait

    # 5. 汇总
    print(f"\n[5/5] 结果汇总")
    print("=" * 60)
    print(f"  总任务:     {len(task_ids)}")
    print(f"  完成:       {len(completed)} [OK]")
    print(f"  失败:       {len(failed)}")
    print(f"  超时:       {len(timed_out)}")
    print(f"  发布耗时:   {pub_time:.2f}s")
    print(f"  等待耗时:   {wait_time:.2f}s")
    print(f"  总耗时:     {pub_time + wait_time:.2f}s")

    throughput = len(completed) / wait_time if wait_time > 0 else 0
    print(f"  吞吐量:     {throughput:.1f} tasks/s")

    avg_latency = wait_time / len(completed) * 1000 if completed else 0
    print(f"  平均延迟:   {avg_latency:.1f} ms/task")

    # 清理
    print(f"\n  清理 {len(workers)} Workers...")
    for p in workers:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            try:
                p.kill()
            except:
                pass
    board._client.disconnect()

    # 发布报告到BBS
    try:
        from mqtt_bbs.board_client import BoardClient
        with BoardClient("stress_tester", board="agent-bbs-test") as bbs:
            reg = bbs.register("stress_tester", timeout=3)
            token = reg.get("token", "")
            if token:
                report = (
                    f"[压力测试v2] {WORKER_COUNT}w*{TASK_PER_WORKER}t "
                    f"| 完成={len(completed)}/{len(task_ids)} "
                    f"| {wait_time:.1f}s "
                    f"| {throughput:.1f}t/s"
                )
                bbs.post(report, token)
                print(f"  [OK] 报告已发布: {report}")
    except Exception as e:
        print(f"  [WARN] 发布报告失败: {e}")

    return {
        "total": len(task_ids),
        "completed": len(completed),
        "failed": len(failed),
        "timeout": len(timed_out),
        "pub_time": round(pub_time, 2),
        "wait_time": round(wait_time, 2),
        "throughput": round(throughput, 1),
        "avg_latency_ms": round(avg_latency, 1),
    }


if __name__ == "__main__":
    result = run_test()
    if result:
        print(f"\n>>> {json.dumps(result, indent=2)}")
