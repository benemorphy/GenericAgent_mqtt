"""
ga_watchdog — GA 智能体守护进程

功能: 封装 launch.pyw，崩溃后自动重启，防止 GA 智能体因偶发崩溃长时间离线。

用法:
    python GA/tools/ga_watchdog.py --feishu          # 启动飞书 Bot + 自动重启
    python GA/tools/ga_watchdog.py --feishu --sched   # 启动飞书 + 调度器
    python GA/tools/ga_watchdog.py --help             # 查看完整参数

设计:
  - 命名互斥体锁防止重复启动 (Global\GA_Watchdog_Mutex)
  - 轮询子进程状态，异常退出时自动重启
  - 最大重启频率限制（默认 10 次/分钟），超过则停止防止死循环
  - 重启日志记录到 temp/ga_watchdog.log
  - 所有未识别的参数透传给 launch.pyw
"""

import os, sys, time, subprocess, argparse, logging, signal, ctypes

# ── 命名互斥体锁 (比 socket bind 更可靠, 跨不同 python 解释器生效) ──
MUTEX_NAME = "Global\\GA_Watchdog_Mutex"
kernel32 = ctypes.windll.kernel32
_mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
if not _mutex:
    print(f"[Watchdog] 创建互斥体失败 (error={ctypes.get_last_error()})")
    sys.exit(1)
if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
    print(f"[Watchdog] 互斥体 '{MUTEX_NAME}' 已存在 — 看门狗已在运行，退出")
    sys.exit(0)

# ── 路径 ──
# 文件位于 GA/tools/observability/ga_watchdog.py，需上3层到 GA/
_GA_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROJECT_ROOT = os.path.dirname(_GA_ROOT)
_LOG_DIR = os.path.join(_GA_ROOT, "temp")
_LOG_FILE = os.path.join(_LOG_DIR, "ga_watchdog.log")
_PID_FILE = os.path.join(_GA_ROOT, "run", "ga_watchdog.pid")
_LAUNCH_SCRIPT = os.path.join(_GA_ROOT, "launch.pyw")

os.makedirs(_LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(_PID_FILE), exist_ok=True)

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Watchdog] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("watchdog")

# ── 配置 ──
MAX_RESTARTS_PER_MINUTE = 10  # 每分钟最大重启次数
POLL_INTERVAL = 2.0           # 进程轮询间隔（秒）
GRACEFUL_EXIT_CODES = {0, -1, 1}  # 正常退出的返回码（不计入崩溃计数）

# ── LLM Cache 守护进程 (已移除, llm_cache_rs 不再使用) ──


def parse_args():
    """解析参数：只提取看门狗自己的参数，其余透传给 launch.pyw"""
    parser = argparse.ArgumentParser(
        description="GA 智能体守护进程 — 崩溃自动重启",
        add_help=False,
    )
    parser.add_argument("--max-restarts", type=int, default=MAX_RESTARTS_PER_MINUTE,
                        help=f"每分钟最大重启次数 (默认 {MAX_RESTARTS_PER_MINUTE})")
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL,
                        help=f"进程轮询间隔秒数 (默认 {POLL_INTERVAL})")
    parser.add_argument("--help", action="store_true", help="显示帮助")

    # 只解析已知参数，剩余留给 launch.pyw
    args, remaining = parser.parse_known_args()

    if args.help:
        # 显示合并帮助
        parser.print_help()
        print("\n--- launch.pyw 参数透传 ---")
        subprocess.run([sys.executable, _LAUNCH_SCRIPT, "--help"], cwd=_PROJECT_ROOT)
        sys.exit(0)

    args.launch_args = remaining  # 透传给 launch.pyw
    return args


def launch_ga(launch_args: list) -> subprocess.Popen:
    """启动 GA 进程，返回 Popen 对象"""
    cmd = [sys.executable, _LAUNCH_SCRIPT] + launch_args
    log.info(f"启动 GA: {' '.join(cmd)}")
    log.info(f"工作目录: {_PROJECT_ROOT}")

    proc = subprocess.Popen(
        cmd,
        cwd=_PROJECT_ROOT,
        stdout=None,   # 继承看门狗的 stdout
        stderr=None,   # 继承看门狗的 stderr
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    log.info(f"GA 进程已启动 (PID {proc.pid})")
    return proc


def is_normal_exit(return_code: int) -> bool:
    """判断退出码是否为正常退出"""
    return return_code in GRACEFUL_EXIT_CODES or return_code is None


def main():
    args = parse_args()

    log.info("=" * 60)
    log.info("GA 看门狗启动")

    log.info(f"透传参数: {' '.join(args.launch_args)}")
    log.info(f"最大重启/分钟: {args.max_restarts}")
    log.info(f"轮询间隔: {args.poll_interval}s")
    log.info(f"日志文件: {_LOG_FILE}")

    # 写入 PID 文件
    with open(_PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    log.info(f"看门狗 PID: {os.getpid()} (已写入 {_PID_FILE})")

    restart_counts = []  # 记录重启时间戳
    launch_attempt = 0

    try:
        while True:
            launch_attempt += 1
            log.info(f"[第 {launch_attempt} 次启动]")

            proc = launch_ga(args.launch_args)

            # 等待进程结束
            proc.wait()

            exit_code = proc.returncode
            uptime = time.time() - proc.pid  # 粗略 uptime（pid 复用不精确，用时间记录替代）
            log.warning(f"GA 进程退出 (PID {proc.pid}, exit code {exit_code})")

            # 判断是否正常退出
            if is_normal_exit(exit_code):
                log.info("进程正常退出 — 看门狗停止")
                break

            # 清理当前时间窗的旧记录
            now = time.time()
            restart_counts = [t for t in restart_counts if now - t < 60]

            # 检查重启频率限制
            if len(restart_counts) >= args.max_restarts:
                log.error(f"每分钟重启次数超过阈值 ({args.max_restarts})，停止看门狗防止无限重启")
                log.error("请检查 GA 是否遇到持续崩溃的 bug")
                break

            restart_counts.append(now)
            log.info(f"当前重启频率: {len(restart_counts)}/{args.max_restarts} 每分钟")

            # 指数退避：连续重启时逐渐增加等待时间
            backoff = min(30, launch_attempt * 2)  # 最多等 30 秒
            log.info(f"等待 {backoff}s 后重启...")
            time.sleep(backoff)

    except KeyboardInterrupt:
        log.info("收到 Ctrl+C，看门狗停止")

    finally:
        # 清理 PID 文件
        if os.path.isfile(_PID_FILE):
            os.remove(_PID_FILE)
            log.info("PID 文件已清理")

        # 如果 GA 进程还在运行，尝试终止
        if 'proc' in locals() and proc.poll() is None:
            log.info("终止 GA 进程...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                log.warning("GA 进程已强制终止")

        log.info("看门狗退出")


if __name__ == "__main__":
    main()
