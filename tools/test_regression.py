#!/usr/bin/env python3
"""
rmqtt 系统回归测试
检查: broker健康 / Web UI API / MariaDB 持久化 / agent任务
返回: JSON格式结果，exit code=0 全部通过
"""
import sys, os, json, time, urllib.request, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MQTT_HOST"] = "127.0.0.1"; os.environ["MQTT_PORT"] = "1883"

def http_get(url, timeout=5):
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.status, json.loads(resp.read().decode()) if resp.status == 200 else resp.read().decode()
    except Exception as e:
        return None, str(e)

results = {"passed": 0, "failed": 0, "tests": []}

def test(name, ok, detail=""):
    results["tests"].append({"name": name, "passed": ok, "detail": detail})
    if ok: results["passed"] += 1
    else: results["failed"] += 1
    print(f"  {'[OK]' if ok else '[FAIL]'} {name}" + (f": {detail}" if detail else ""))

print("=" * 50)
print("rmqtt 回归测试")
print("=" * 50)

# 1. Broker 端口检查
print("\n[1] Broker 健康")
import socket
for port, name in [(1883, "MQTT"), (6060, "HTTP API"), (3306, "MariaDB")]:
    s = socket.socket()
    s.settimeout(3)
    ok = s.connect_ex(('127.0.0.1', port)) == 0
    test(f"{name} ({port})", ok)
    s.close()

# 2. rmqtt HTTP API 检查
print("\n[2] rmqtt HTTP API")
status, data = http_get("http://127.0.0.1:6060/api/v1/brokers")
test("brokers endpoint", status == 200, f"status={status}")

status, data = http_get("http://127.0.0.1:6060/api/v1/clients")
test("clients endpoint", status == 200, f"{len(data) if isinstance(data,list) else 0} clients")

# 3. Web UI API 检查
print("\n[3] Web UI API")
try:
    resp = urllib.request.urlopen("http://127.0.0.1:8100/", timeout=5)
    body = resp.read().decode()
    test("/ (主页)", resp.status == 200 and len(body) > 500, f"{len(body)} bytes")
except Exception as e:
    test("/ (主页)", False, str(e))

status, data = http_get("http://127.0.0.1:8100/api/broker")
test("/api/broker", status == 200 and isinstance(data, dict) and "info" in data)

status, data = http_get("http://127.0.0.1:8100/api/clients")
test("/api/clients", status == 200 and isinstance(data, list))

status, data = http_get("http://127.0.0.1:8100/api/tasks")
task_count = len(data) if isinstance(data, dict) else 0
test("/api/tasks", status == 200, f"{task_count} tasks")

status, data = http_get("http://127.0.0.1:8100/api/logs")
test("/api/logs", status == 200)

# 4. MariaDB 检查
print("\n[4] MariaDB 持久化")
try:
    import pymysql
    conn = pymysql.connect(host='127.0.0.1',port=3306,user='root',password='mariadb',database='mqtt_bbs',connect_timeout=3)
    with conn.cursor() as cur:
        for table in ['agent_sessions', 'retained_messages', 'session_queue']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cur.fetchone()[0]
            test(f"table {table}", True, f"{cnt} rows")
    conn.close()
except Exception as e:
    test("MariaDB connection", False, str(e))

# 5. 发布任务 + 验证 agent 认领
print("\n[5] Agent 任务测试")
try:
    from mqtt_bbs import AgentBoard
    with AgentBoard("regression_test") as board:
        tid = board.post_task("analyse_log", {"path": "/var/log/nginx", "pattern": "error"}, timeout=10)
        output = board.wait_task(tid, timeout=30)
        ok = output.status == "completed" and output.agent_id is not None
        test(f"agent {output.agent_id} claims {tid}", ok, f"status={output.status}")
except Exception as e:
    test("Agent task publish", False, str(e))

# 结果
print(f"\n{'='*50}")
total = results["passed"] + results["failed"]
print(f"结果: {results['passed']}/{total} 通过, {results['failed']} 失败")
print(f"{'='*50}")

# 写入报告
report_path = sys.argv[1] if len(sys.argv) > 1 else None
if report_path:
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"报告写入: {report_path}")

sys.exit(0 if results["failed"] == 0 else 1)
