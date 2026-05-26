"""
MQTT Worker Agent 启动器

启动多个 Worker Agent 实例，通过 MQTT 连接 AgentBoard。

用法:
    python frontends/launcher_mqtt.py                     # 启动 3 个Worker（默认）
    python frontends/launcher_mqtt.py --workers 5         # 启动 5 个Worker
    python frontends/launcher_mqtt.py --names alpha,beta  # 指定名称
    python frontends/launcher_mqtt.py --list-capabilities # 显示所有可用Worker能力
"""

import argparse, json, logging, os, signal, subprocess, sys, threading, time, uuid

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s %(message)s")
log = logging.getLogger("launcher")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 预定义 Worker 能力池
DEFAULT_WORKER_PROFILES = [
    {"name": "worker_scanner",  "capabilities": ["scan_network", "port_scan", "vuln_check"]},
    {"name": "worker_analyzer", "capabilities": ["data_analysis", "log_analysis", "text_mining"]},
    {"name": "worker_reporter", "capabilities": ["report_gen", "summary", "format_output"]},
    {"name": "worker_monitor",  "capabilities": ["health_check", "ping", "status_collect"]},
    {"name": "worker_helper",   "capabilities": ["shell_exec", "file_ops", "code_review"]},
]

PROCESSES = []


def launch_worker(name: str, capabilities: list, broker_host: str = "127.0.0.1", broker_port: int = 1883):
    """通过子进程启动一个 Worker Agent（使用 worker_factory）"""
    env = os.environ.copy()
    env["WORKER_ID"] = name
    env["WORKER_CAPS"] = ",".join(capabilities)
    # Optional broker overrides
    env["MQTT_HOST"] = broker_host
    env["MQTT_PORT"] = str(broker_port)

    cmd = [sys.executable, "-m", "mqtt_bbs.examples.worker_factory"]
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    PROCESSES.append(proc)
    log.info(f"🟢 启动 Worker: {name} (PID {proc.pid}) — 能力: {capabilities}")
    return proc


def launch_workers(count: int = 3, names: list = None):
    """启动多个 Worker"""
    if names:
        # 按给定名称和能力启动
        for i, name in enumerate(names):
            profile = DEFAULT_WORKER_PROFILES[i % len(DEFAULT_WORKER_PROFILES)]
            launch_worker(name, profile["capabilities"])
    else:
        # 循环使用能力池
        for i in range(count):
            profile = DEFAULT_WORKER_PROFILES[i % len(DEFAULT_WORKER_PROFILES)]
            launch_worker(profile["name"], profile["capabilities"])


def cleanup(signum=None, frame=None):
    """清理所有子进程"""
    log.info(f"🛑 正在停止 {len(PROCESSES)} 个 Worker...")
    for proc in PROCESSES:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    log.info("✅ 所有 Worker 已停止")
    sys.exit(0)


def list_capabilities():
    """列出所有可用的 Worker 能力"""
    print("\n可用的 Worker 能力配置:")
    print("=" * 60)
    for p in DEFAULT_WORKER_PROFILES:
        caps_str = ", ".join(p["capabilities"])
        print(f"  {p['name']:20s} → {caps_str}")
    print()


def main():
    parser = argparse.ArgumentParser(description="MQTT Worker Agent 启动器")
    parser.add_argument("--workers", type=int, default=3, help="Worker 数量（默认 3）")
    parser.add_argument("--names", type=str, help="Worker 名称列表（逗号分隔，覆盖 --workers）")
    parser.add_argument("--broker-host", default="127.0.0.1", help="MQTT Broker 地址")
    parser.add_argument("--broker-port", type=int, default=1883, help="MQTT Broker 端口")
    parser.add_argument("--list-capabilities", action="store_true", help="列出可用 Worker 能力")
    args = parser.parse_args()

    if args.list_capabilities:
        list_capabilities()
        return

    log.info(f"🚀 启动 {args.workers} 个 Worker Agent (Broker: {args.broker_host}:{args.broker_port})")

    names = args.names.split(",") if args.names else None
    launch_workers(args.workers, names)

    # 注册信号处理
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    log.info("✅ 所有 Worker 已启动，按 Ctrl+C 停止")
    try:
        # 等待所有子进程
        for proc in PROCESSES:
            proc.wait()
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
