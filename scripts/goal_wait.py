# scripts/goal_wait.py — 阻塞等待 Goal Mode 完成
# 用法:
#   python scripts/goal_wait.py                     # 等当前 goal_state.json
#   python scripts/goal_wait.py --timeout 7200      # 超时秒数
#   python scripts/goal_wait.py --pulse-only        # 只用 Pulse，不读 state
#
# 返回码:
#   0 - goal_complete (done_prompt)
#   0 - budget_exhausted
#   1 - timeout
#   2 - error

import sys, os, json, time, argparse

_script_dir = os.path.dirname(os.path.abspath(__file__))
_state_path = os.path.join(_script_dir, '..', 'temp', 'goal_state.json')

def wait_via_state(timeout=0):
    """轮询 goal_state.json"""
    deadline = time.time() + timeout if timeout > 0 else float('inf')
    while time.time() < deadline:
        if os.path.exists(_state_path):
            with open(_state_path, 'r') as f:
                state = json.load(f)
            status = state.get('status', '')
            if status == 'done':
                print(f"[Goal] 完成 (done_prompt 触发), 运行 {state.get('turns_used', 0)} 轮")
                return 0
            if status == 'done_budget':
                print(f"[Goal] 完成 (预算耗尽), 运行 {state.get('turns_used', 0)} 轮")
                return 0
        time.sleep(3)
    print("[Goal] 超时")
    return 1

def wait_via_pulse(timeout=0):
    """通过 MQTT Pulse 等待 goal_complete"""
    import paho.mqtt.client as mqtt
    finished = {'flag': False, 'data': None}
    
    def on_msg(client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            if data.get('type') == 'goal_complete':
                finished['data'] = data
                finished['flag'] = True
                client.disconnect()
        except:
            pass
    
    c = mqtt.Client(client_id="goal_waiter")
    c.on_message = on_msg
    c.connect('127.0.0.1', 1883, 60)
    c.subscribe("agent/bbs/goal_pulse/post", qos=1)
    c.loop_start()
    
    deadline = time.time() + timeout if timeout > 0 else float('inf')
    while time.time() < deadline and not finished['flag']:
        time.sleep(0.5)
    
    c.loop_stop()
    c.disconnect()
    
    if finished['flag']:
        d = finished['data']
        print(f"[Goal] Pulse 收到 goal_complete: turn={d.get('turn')}, focus={str(d.get('focus',''))[:60]}")
        return 0
    print("[Goal] 超时 (未收到 Pulse)")
    return 1

def main():
    parser = argparse.ArgumentParser(description="等待 Goal Mode 完成")
    parser.add_argument('--timeout', type=int, default=0, help='超时秒数 (0=无限)')
    parser.add_argument('--pulse-only', action='store_true', help='仅用 Pulse 检测')
    args = parser.parse_args()
    
    if args.pulse_only:
        return wait_via_pulse(args.timeout)
    
    # 双通道: 先 Pulse, 3s 无响应则轮询 state
    import threading
    result = [None]
    def pulse_thread():
        result[0] = wait_via_pulse(args.timeout)
    t = threading.Thread(target=pulse_thread, daemon=True)
    t.start()
    
    # 同时轮询 state
    deadline = time.time() + args.timeout if args.timeout > 0 else float('inf')
    while time.time() < deadline:
        if result[0] is not None:
            sys.exit(result[0])
        if os.path.exists(_state_path):
            with open(_state_path, 'r') as f:
                state = json.load(f)
            if state.get('status') in ('done', 'done_budget'):
                print(f"[Goal] 检测到 status={state['status']}")
                sys.exit(0)
        time.sleep(3)
    
    print("[Goal] 超时")
    sys.exit(1)

if __name__ == '__main__':
    main()
