"""独立 broker stats 采集器 - 每10秒写入 MariaDB"""
import sys, os, time, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MQTT_HOST", "127.0.0.1")

BROKER_API = f"http://127.0.0.1:6060"

import pymysql

def write_stats():
    try:
        # Fetch from rmqtt HTTP API
        resp = urllib.request.urlopen(f"{BROKER_API}/api/v1/stats", timeout=3)
        data = json.loads(resp.read().decode())
        if not data or not isinstance(data[0], dict):
            return
        s = da
...[Truncated]...
oad().decode())
        print(f"Web UI confirmed: {len(data)} records")

    print(f"\n=== Done ===")
    print(f"Total rows collected: {cnt} in {(time.time()-t0)/60:.1f} minutes")
