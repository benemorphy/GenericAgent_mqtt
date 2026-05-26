"""Master - 发布任务并等待结果"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print("[MASTER] 启动...", flush=True)

from Mqtt_bbs.bbs import AgentBoard

print("[MASTER] 已导入AgentBoard", flush=True)
board = AgentBoard("test_master", host="127.0.0.1", port=1883)
board._client.connect()
print("[MASTER] connect() 完成", flush=True)
board._client.wait_connected(5)
print("[MASTER] 已连接MQTT", flush=True)

task_ids = []
for w in range(2):
    for t in range(3):
        tid = board.post_task_routed(
            "stress_test",
            {"msg": f"w{w}_t{t}", "seq": t},
            target_agent_id=f"stress_worker_{w:02d}",
        )
        task_ids.append(tid)
        print(f"[MASTER] 发布: {tid}", flush=True)

print(f"[MASTER] 共 {len(task_ids)} 个任务", flush=True)

for idx, tid in enumerate(task_ids):
    out = board.wait_task(tid, timeout=30)
    print(f"[MASTER] [{idx+1}/{len(task_ids)}] {tid[:12]}... status={out.status}", flush=True)

print("[MASTER] 完成!", flush=True)
board._client.disconnect()
