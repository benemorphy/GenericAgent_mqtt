"""
5 Agent 并发测试 - 每个 agent 不同能力，发布任务验证
"""
import sys, os, time, json, threading, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MQTT_HOST"] = "127.0.0.1"
os.environ["MQTT_PORT"] = "1883"

logging.basicConfig(level=logging.WARN, format="%(name)s | %(message)s")

from mqtt_bbs import WorkerAgentWithPersistence as WorkerAgent, AgentBoardWithPersistence as AgentBoard

agents = []
results = {}

def make_handler(name):
    def handler(task):
        print(f"  [{name}] ✅ 认领: {task.type}")
        time.sleep(0.5)
        return {"agent": name, "result": f"done_{task.type}", "ts": time.time()}
    return handler

# Agent 配置
agent_configs = [
    ("agent_alpha", ["analyse_log", "scan"]),
    ("agent_beta",  ["scan", "backup"]),
    ("agent_gamma", ["analyse_log", "monitor"]),
    ("agent_delta", ["backup", "cleanup"]),
    ("agent_epsilon",["monitor", "report"]),
]

print("=" * 60)
print("🚀 启动 5 个 WorkerAgent")
print("=" * 60)

for name, caps in agent_configs:
    a = WorkerAgent(name, capabilities=caps)
    a.on_task(make_handler(name))
    a.start()
    agents.append(a)
    print(f"  ✅ {name}: caps={caps}")

time.sleep(2)

# 发布任务
print("\n📋 发布 6 个任务...")
tasks_data = [
    ("analyse_log", {"path": "/var/log"}),
    ("scan", {"target": "10.0.0.0/24"}),
    ("backup", {"path": "/data", "type": "incremental"}),
    ("monitor", {"service": "nginx", "check": "health"}),
    ("cleanup", {"path": "/tmp", "older_than": "7d"}),
    ("report", {"format": "pdf", "period": "daily"}),
]

with AgentBoard("load_test_master") as board:
    task_ids = []
    for task_type, payload in tasks_data:
        tid = board.post_task(task_type, payload)
        task_ids.append(tid)
        print(f"  📌 [{tid}] {task_type}")
    
    print("\n⏳ 等待任务完成...")
    for tid in task_ids:
        output = board.wait_task(tid, timeout=20)
        print(f"  {'✅' if output.status=='completed' else '❌'} {tid[:12]}... → {output.agent_id}: {output.status}")

# 收尾
for a in agents:
    a.stop()

print(f"\n{'='*60}")
print("✅ 5 Agent 并发测试完成！")
print(f"{'='*60}")

# DB 验证
try:
    import pymysql
    c = pymysql.connect(host='127.0.0.1',port=3306,user='root',password='mariadb',database='mqtt_bbs')
    with c.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM agent_sessions WHERE agent_id LIKE 'agent_%'")
        new_sessions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM retained_messages WHERE source_agent LIKE 'agent_%'")
        new_retained = cur.fetchone()[0]
        print(f"\n📊 持久化写入: sessions={new_sessions} 条, retained={new_retained} 条")
    c.close()
except Exception as e:
    print(f"  DB 检查跳过: {e}")
