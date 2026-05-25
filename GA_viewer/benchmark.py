"""
BoardService 基准压测脚本

测试场景:
  1. register: 创建 N 个 agent
  2. post: 每人发 M 条帖子
  3. query: 批量查询帖子

用法:
    python scripts/stress_test_bbs.py --count 100 --clients 10

输出:
    P50/P95/P99 延迟, 总吞吐量
"""
import subprocess, sys, os, time, json, argparse, statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def benchmark(count=100, clients=5):
    from mqtt_bbs.board_client import BoardClient
    
    # Load JWT
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'mqtt_bbs', 'agent.env'
    )
    jwt = None
    with open(env_path) as f:
        for line in f:
            if 'AGENT_GPT_PASSWORD' in line:
                jwt = line.split('=', 1)[1].strip()
    
    if jwt:
        os.environ['MQTT_USERNAME'] = 'agent_gpt'
        os.environ['MQTT_PASSWORD'] = jwt

    latencies = {"register": [], "post": [], "query": []}

    print(f"Benchmark: {clients} clients x {count} posts each")
    print(f"{'Operation':<12} {'Count':>8} {'P50':>10} {'P95':>10} {'P99':>10} {'TPS':>10}")
    print("-" * 60)

    for cid in range(clients):
        name = f"bench_{cid}"
        bbs = BoardClient(name, board="agent-bbs-test")
        bbs.connect()
        
        t0 = time.perf_counter()
        info = bbs.register(name)
        t1 = time.perf_counter()
        if info and info.get('token'):
            latencies["register"].append((t1-t0)*1000)
            token = info['token']
            
            for i in range(count):
                t0 = time.perf_counter()
                r = bbs.post(f"bench post {cid}_{i}", token)
                t1 = time.perf_counter()
                if r and r.get('id'):
                    latencies["post"].append((t1-t0)*1000)
            
            # query
            t0 = time.perf_counter()
            posts = bbs.query_posts(author=name)
            t1 = time.perf_counter()
            latencies["query"].append((t1-t0)*1000)
        
        bbs.disconnect()

    for op, vals in latencies.items():
        if not vals:
            print(f"{op:<12} {'0':>8} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
            continue
        vals.sort()
        p50 = vals[int(len(vals)*0.5)]
        p95 = vals[int(len(vals)*0.95)]
        p99 = vals[int(len(vals)*0.99)]
        tps = 1000.0 / (sum(vals)/len(vals)) if vals else 0
        print(f"{op:<12} {len(vals):>8} {p50:>8.1f}ms {p95:>8.1f}ms {p99:>8.1f}ms {tps:>8.0f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--clients', type=int, default=5)
    args = parser.parse_args()
    benchmark(args.count, args.clients)
