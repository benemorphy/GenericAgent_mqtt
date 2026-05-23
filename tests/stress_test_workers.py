"""
Worker Agent 压力测试
启动5个worker agent，由AgentBoard发布任务，统计吞吐量和延迟
"""
import sys, os, time, json, logging, subprocess, multiprocessing, threading, signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 配置 ──
WORKER_COUNT = 5
TASK_COUNT = 30          # 每个worker处理的任务数（共150任务）
TASK_WORK_DELAY = 0.1    # 每个任务模拟处理时间（秒）
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883

# ── Worker 进程函数 ──

def run_worker(worker_id: int, task_count: int):
    """在独立进程中运行一个worker agent"""
    import logging
    logging.basicConfig(level=logging.WARN, format=f"[W{worker_id}] %(message)s")
    
    from mqtt_bbs.bbs import WorkerAgent, TaskMessage
    
    def handle_task(task: TaskMessage) -> dict:
        """任务处理器 — 模拟工作负载"""
        if TASK_WORK_DELAY > 0:
            time.sleep(TASK_WORK_DELAY)
        return {"result": "ok", "worker_id": worker_id, "echo": task.input.get("msg", "")}
    
    worker = WorkerAgent(
        f"stress_worker_{worker_id:02d}",
        capabilities=["stress_test"],
        host=BROKER_HOST, port=BROKER_PORT,
    )
    worker.on_task(handle_task)
    worker.start(block=True)


# ── 主测试流程 ──

def run_stress_test():
    from mqtt_bbs.bbs import AgentBoard
    from mqtt_bbs.board_client import BoardClient
    
    print("=" * 60)
    print("WORKER AGENT 压力测试")
    print(f"    Workers: {WORKER_COUNT}")
    print(f"    任务/Worker: {TASK_COUNT}")
    print(f"    模拟耗时/任务: {TASK_WORK_DELAY}s")
    print(f"    总任务: {WORKER_COUNT * TASK_COUNT}")
    print("=" * 60)
    
    # 1. 验证基础设施
    print("\n[1/5] 验证基础设施...")
    import socket
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect((BROKER_HOST, BROKER_PORT))
        s.close()
        print(f"  [OK] MQTT Broker 在线 ({BROKER_HOST}:{BROKER_PORT})")
    except Exception as e:
        print(f"  [FAIL] MQTT Broker 不可用: {e}")
        return None
    
    # 2. 启动5个Worker
    print(f"\n[2/5] 启动 {WORKER_COUNT} 个 Worker...")
    processes = []
    for i in range(WORKER_COUNT):
        p = multiprocessing.Process(
            target=run_worker,
            args=(i, TASK_COUNT),
            name=f"worker_{i:02d}",
        )
        p.daemon = True
        p.start()
        processes.append(p)
        print(f"  [START] Worker[{i:02d}] PID={p.pid}")
        time.sleep(0.3)
    
    print("  等待workers就绪...")
    time.sleep(2)
    
    # 3. 创建AgentBoard并定向发布任务
    print(f"\n[3/5] 定向发布 {WORKER_COUNT * TASK_COUNT} 个任务...")
    
    board = AgentBoard("stress_master", host=BROKER_HOST, port=BROKER_PORT)
    board._client.connect()
    board._client.wait_connected(5)
    
    if not board._client.is_connected:
        print("  [FAIL] Master AgentBoard 连接失败")
        return None
    
    directed_task_ids = []
    pub_errors = 0
    pub_start = time.time()
    
    for w in range(WORKER_COUNT):
        for t in range(TASK_COUNT):
            try:
                tid = board.post_task_routed(
                    "stress_test",
                    {"msg": f"w{w:02d}_n{t:03d}", "seq": t, "worker": w},
                    target_agent_id=f"stress_worker_{w:02d}",
                )
                directed_task_ids.append(tid)
            except Exception as e:
                pub_errors += 1
    
    pub_time = time.time() - pub_start
    print(f"  发布完成: {len(directed_task_ids)} 任务, {pub_errors} 错误, {pub_time:.2f}s")
    
    # 4. 等待任务完成
    print(f"\n[4/5] 等待任务完成...")
    start_wait = time.time()
    timeout = max(60, TASK_COUNT * (TASK_WORK_DELAY + 0.3) * WORKER_COUNT + 10)
    print(f"  超时: {timeout:.0f}s")
    
    completed = board.wait_all(directed_task_ids, timeout=timeout)
    wait_time = time.time() - start_wait
    
    # 统计
    total_done = sum(1 for o in completed if o.status in ("completed", "done"))
    total_failed = sum(1 for o in completed if o.status in ("failed", "timeout"))
    total_lost = sum(1 for o in completed if o.status == "lost" or o.status == "pending")
    
    print(f"\n[5/5] 结果汇总")
    print("=" * 60)
    print(f"  总任务:     {len(completed)}")
    print(f"  完成:       {total_done} [OK]")
    print(f"  失败:       {total_failed}")
    print(f"  丢失:       {total_lost}")
    print(f"  发布耗时:   {pub_time:.2f}s")
    print(f"  等待耗时:   {wait_time:.2f}s")
    print(f"  总耗时:     {pub_time + wait_time:.2f}s")
    
    throughput = total_done / wait_time if wait_time > 0 else 0
    print(f"  吞吐量:     {throughput:.1f} tasks/s")
    print(f"  延迟均值:   {wait_time/total_done*1000:.1f}ms/task" if total_done > 0 else "")
    
    # 清理workers
    print("\n  清理workers...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.join(timeout=3)
    board._client.disconnect()
    
    # 发布测试报告到BBS
    print("\n  发布测试报告...")
    try:
        with BoardClient("stress_tester", board="agent-bbs-test") as bbs:
            reg = bbs.register("stress_tester", timeout=3)
            token = reg.get("token", "")
            if token:
                report = (
                    f"[压力测试] {WORKER_COUNT}workers*{TASK_COUNT}tasks "
                    f"| 完成={total_done}/{len(completed)} "
                    f"| {wait_time:.1f}s "
                    f"| {throughput:.1f}t/s"
                )
                bbs.post(report, token)
                print(f"  [OK] {report}")
    except Exception as e:
        print(f"  [WARN] 发布报告失败: {e}")
    
    print("\n[OK] 压力测试完成!")
    
    return {
        "total": len(completed),
        "done": total_done,
        "failed": total_failed,
        "lost": total_lost,
        "pub_time": round(pub_time, 2),
        "wait_time": round(wait_time, 2),
        "throughput": round(throughput, 1),
    }


if __name__ == "__main__":
    result = run_stress_test()
    if result:
        print(f"\n>>> 最终结果: {json.dumps(result, indent=2)}")
