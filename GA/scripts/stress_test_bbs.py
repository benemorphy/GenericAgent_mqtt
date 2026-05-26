"""
BBS 分布式压测 — 吞吐量 / 并发 Worker / 断连风暴 / 长时间运行

用法:
    python scripts/stress_test_bbs.py               # 全场景
    python scripts/stress_test_bbs.py --scenario throughput  # 仅吞吐
    python scripts/stress_test_bbs.py --dry-run              # 只打印不执行

协议参考: memory/board_stress_sop.md
"""

import os, sys, json, time, uuid, threading, argparse, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
log = logging.getLogger("stress")

# ── 配置 ──
BROKER_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "1883"))
TEST_BOARD = "agent-stress-test"
TIMEOUT = 10  # 等待响应超时(秒)

# ── 指标收集 ──
_metrics = {"register": [], "post": [], "query": []}
_metrics_lock = threading.Lock()


def _record(op, duration_ms, ok=True):
    with _metrics_lock:
        _metrics.setdefault(op, []).append({"ok": ok, "ms": duration_ms})


def _report(op):
    """输出 P50 / P95 / P99"""
    data = _metrics.get(op, [])
    if not data:
        return "no data"
    import statistics as _s
    vals = sorted(d["ms"] for d in data if d["ok"])
    ok_rate = sum(1 for d in data if d["ok"]) / len(data) * 100
    return f"ok={ok_rate:.0f}%  count={len(vals)}  P50={_s.median(vals):.1f}ms  P95={vals[int(len(vals)*0.95)]:.1f}ms" if vals else "all failed"


def _corr():
    return f"s{uuid.uuid4().hex[:8]}"


class StressClient:
    """压测客户端 — 直接MQTT操作（遵循 board_stress_sop.md 协议）"""

    def __init__(self, agent_id: str):
        import paho.mqtt.client as mqtt
        self.agent_id = agent_id
        self._client = mqtt.Client(client_id=agent_id, protocol=mqtt.MQTTv5 if hasattr(mqtt, 'MQTTv5') else mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._pending = {}
        self._lock = threading.Lock()
        self._connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self._connected = True

    def connect(self):
        self._client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        self._client.loop_start()
        deadline = time.time() + 5
        while time.time() < deadline and not self._connected:
            time.sleep(0.05)
        return self._connected

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    def subscribe(self, topic, callback):
        self._client.subscribe(topic)
        self._client.message_callback_add(topic, callback)

    def publish(self, topic, payload):
        self._client.publish(topic, json.dumps(payload) if isinstance(payload, dict) else payload, qos=1)

    def register(self) -> tuple[bool, dict]:
        """注册 → (ok, response)  耗时瓶颈在 sub+wait"""
        corr_id = _corr()
        resp_topic = f"bbs/{TEST_BOARD}/register/response/{corr_id}"
        result = {"data": None}

        def on_resp(client, userdata, msg):
            try:
                result["data"] = json.loads(msg.payload)
            except Exception:
                result["data"] = {"error": "parse fail"}

        self.subscribe(resp_topic, on_resp)
        t0 = time.perf_counter()
        self.publish(f"bbs/{TEST_BOARD}/register", {"agent_id": self.agent_id, "name": self.agent_id, "corr_id": corr_id})

        deadline = time.time() + TIMEOUT
        while time.time() < deadline and result["data"] is None:
            time.sleep(0.01)

        ms = (time.perf_counter() - t0) * 1000
        ok = bool(result["data"] and "token" in result["data"])
        _record("register", ms, ok)
        return ok, result["data"]

    def post(self, token: str, content: str) -> bool:
        """发帖 → bool"""
        corr_id = _corr()
        resp_topic = f"bbs/{TEST_BOARD}/post/response/{corr_id}"
        result = {"ok": False}

        def on_resp(client, userdata, msg):
            result["ok"] = True

        self.subscribe(resp_topic, on_resp)
        t0 = time.perf_counter()
        self.publish(f"bbs/{TEST_BOARD}/post", {"agent_id": self.agent_id, "token": token, "content": content, "corr_id": corr_id})

        deadline = time.time() + TIMEOUT
        while time.time() < deadline and not result["ok"]:
            time.sleep(0.01)

        ms = (time.perf_counter() - t0) * 1000
        _record("post", ms, result["ok"])
        return result["ok"]


# ══════════════════════════════════════
# 测试场景
# ══════════════════════════════════════

def scenario_throughput(count: int = 500):
    """吞吐量测试: 注册 → 连续发帖"""
    log.info(f"── 吞吐量测试: {count} 条帖子 ──")
    c = StressClient(f"stress_throughput")
    if not c.connect():
        log.error("Broker 连接失败"); return
    ok, info = c.register()
    if not ok:
        log.error("注册失败"); c.disconnect(); return
    token = info.get("token", "")
    log.info(f"注册成功, token={token[:8]}...")

    batch_size = 50
    for i in range(0, count, batch_size):
        end = min(i + batch_size, count)
        batch = list(range(i, end))
        for j in batch:
            c.post(token, f"stress_test_msg_{j}")
        log.info(f"  发布 {end}/{count}")
        time.sleep(0.01)  # 限速

    c.disconnect()
    log.info(f"  吞吐报告: {_report('post')}")


def scenario_concurrent(clients: int = 50, posts_per_client: int = 10):
    """并发 Worker: N 个客户端同时注册+发帖"""
    log.info(f"── 并发测试: {clients} 客户端 × {posts_per_client} 帖 ──")
    threads, results = [], [{} for _ in range(clients)]

    def worker(idx):
        c = StressClient(f"stress_w{idx}")
        if not c.connect():
            results[idx] = {"error": "connect fail"}; return
        ok, info = c.register()
        if not ok:
            results[idx] = {"error": "register fail"}; c.disconnect(); return
        token = info.get("token", "")
        for j in range(posts_per_client):
            c.post(token, f"concurrent_msg_{idx}_{j}")
        c.disconnect()
        results[idx] = {"ok": True, "agent_id": f"stress_w{idx}"}

    t0 = time.perf_counter()
    for i in range(clients):
        t = threading.Thread(target=worker, args=(i,))
        t.start(); threads.append(t)
    for t in threads:
        t.join()

    elapsed = time.perf_counter() - t0
    ok_count = sum(1 for r in results if r.get("ok"))
    log.info(f"  完成: {ok_count}/{clients} clients in {elapsed:.1f}s")
    log.info(f"  注册报告: {_report('register')}")
    log.info(f"  发帖报告: {_report('post')}")


def scenario_disconnect_storm(clients: int = 50):
    """断连风暴: N 客户端同时断连"""
    log.info(f"── 断连风暴: {clients} 客户端同时断连 ──")
    # 先注册
    clients_list = []
    for i in range(clients):
        c = StressClient(f"storm_c{i}")
        if c.connect():
            c.register()
            clients_list.append(c)
    log.info(f"  已注册 {len(clients_list)}/{clients}")

    # 同时断连
    t0 = time.perf_counter()
    threads = []
    for c in clients_list:
        t = threading.Thread(target=c.disconnect)
        t.start(); threads.append(t)
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    log.info(f"  断连完成: {len(clients_list)} clients in {elapsed:.3f}s")


def scenario_long_run(duration_minutes: int = 5):
    """长时间运行: 持续注册/发帖"""
    log.info(f"── 长时间运行: {duration_minutes} 分钟 ──")
    c = StressClient("stress_longrun")
    if not c.connect():
        log.error("Broker 连接失败"); return
    ok, info = c.register()
    if not ok:
        log.error("注册失败"); c.disconnect(); return
    token = info.get("token", "")

    deadline = time.time() + duration_minutes * 60
    count = 0
    while time.time() < deadline:
        c.post(token, f"longrun_msg_{count}")
        count += 1
        if count % 100 == 0:
            log.info(f"  已发 {count} 帖，剩余 {int(deadline - time.time())}s")

    c.disconnect()
    log.info(f"  长时间运行报告: {_report('post')}")


# ══════════════════════════════════════
# 清理
# ══════════════════════════════════════

def cleanup():
    """清理测试数据"""
    try:
        import pymysql
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='mariadb', database='mqtt_bbs',
                               charset='utf8mb4', connect_timeout=3)
        cur = conn.cursor()
        cur.execute("DELETE FROM bbs_posts WHERE board=%s", (TEST_BOARD,))
        cur.execute("DELETE FROM bbs_users WHERE board=%s", (TEST_BOARD,))
        conn.commit(); conn.close()
        log.info(f"  清理: {TEST_BOARD} 数据已删除")
    except Exception as e:
        log.warning(f"  清理失败(DB可能不在本地): {e}")


# ══════════════════════════════════════
# 入口
# ══════════════════════════════════════

SCENARIOS = {
    "throughput": scenario_throughput,
    "concurrent": scenario_concurrent,
    "disconnect": scenario_disconnect_storm,
    "longrun": scenario_long_run,
}


def main():
    parser = argparse.ArgumentParser(description="BBS 分布式压测")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()) + ["all"], default="all")
    parser.add_argument("--count", type=int, default=500, help="吞吐量测试消息数")
    parser.add_argument("--clients", type=int, default=50, help="并发/断连客户端数")
    parser.add_argument("--posts-per-client", type=int, default=10, help="每客户端发帖数")
    parser.add_argument("--duration", type=int, default=5, help="长时间运行(分钟)")
    parser.add_argument("--dry-run", action="store_true", help="只打印不执行")
    parser.add_argument("--no-cleanup", action="store_true", help="不清理测试数据")
    args = parser.parse_args()

    log.info(f"BBS 分布式压测 — broker={BROKER_HOST}:{BROKER_PORT} board={TEST_BOARD}")
    log.info(f"  场景数: {'all' if args.scenario == 'all' else args.scenario}")

    if args.dry_run:
        log.info("  [dry-run] 模式，不执行实际测试")
        return

    scenarios = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    for name in scenarios:
        if name == "throughput":
            SCENARIOS[name](count=args.count)
        elif name == "concurrent":
            SCENARIOS[name](clients=args.clients, posts_per_client=args.posts_per_client)
        elif name == "disconnect":
            SCENARIOS[name](clients=args.clients)
        elif name == "longrun":
            SCENARIOS[name](duration_minutes=args.duration)
        log.info("")

    # 清理
    if not args.no_cleanup:
        cleanup()

    # 总报告
    log.info("═" * 50)
    log.info("压测报告")
    for op in ["register", "post", "query"]:
        log.info(f"  {op:<10} {_report(op)}")
    log.info("═" * 50)


if __name__ == "__main__":
    main()
