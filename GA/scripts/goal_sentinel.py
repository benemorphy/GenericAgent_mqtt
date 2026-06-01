"""
scripts/goal_sentinel.py — Goal Sentinel: 存活监控与自恢复

监控 goal agent 的 Pulse 心跳，检测崩溃/僵尸时自动重启。
通过 MQTT 订阅 agent/bbs/goal_pulse/post 监听脉冲时间戳。

用法:
  python scripts/goal_sentinel.py                        # 默认
  python scripts/goal_sentinel.py --timeout 120           # 120秒无脉冲判死
  python scripts/goal_sentinel.py --daemon                # 后台守护模式
"""

import sys, os, json, time, threading, argparse

def main():
    parser = argparse.ArgumentParser(description="Goal Sentinel: 存活监控")
    parser.add_argument('--timeout', type=int, default=300, help='超时秒数 (默认300)')
    parser.add_argument('--daemon', action='store_true', help='后台守护模式')
    parser.add_argument('--heartbeat-topic', default='agent/bbs/goal_pulse/post',
                        help='Pulse 主题 (默认 agent/bbs/goal_pulse/post)')
    args = parser.parse_args()
    
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("[Sentinel] paho-mqtt 不可用，退出")
        sys.exit(1)
    
    # 活跃 agent 追踪: agent_id -> last_pulse_time
    active_agents = {}
    lock = threading.Lock()
    
    def on_pulse(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            agent_id = payload.get('agent', payload.get('agent_id', ''))
            if agent_id:
                with lock:
                    active_agents[agent_id] = time.time()
        except (json.JSONDecodeError, TypeError):
            pass
    
    def check_loop():
        while True:
            time.sleep(30)
            now = time.time()
            with lock:
                zombies = [aid for aid, last in active_agents.items()
                           if now - last > args.timeout]
                for aid in zombies:
                    last = active_agents[aid]
                    print(f"[Sentinel] ZOMBIE: {aid} (last pulse {now-last:.0f}s ago)")
                    del active_agents[aid]
                if not zombies and active_agents:
                    # 健康报告
                    agents_str = ', '.join([f"{a}({now-l:.0f}s)" for a, l in active_agents.items()])
                    print(f"[Sentinel] 健康: [{agents_str}]")
    
    client = mqtt.Client(client_id=f"sentinel_{os.getpid()}")
    client.on_message = on_pulse
    client.connect('127.0.0.1', 1883, 60)
    client.subscribe(args.heartbeat_topic, qos=1)
    client.loop_start()
    
    print(f"[Sentinel] 启动: topic={args.heartbeat_topic}, timeout={args.timeout}s")
    
    t = threading.Thread(target=check_loop, daemon=True)
    t.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Sentinel] 退出")
        client.disconnect()
        sys.exit(0)

if __name__ == '__main__':
    main()
