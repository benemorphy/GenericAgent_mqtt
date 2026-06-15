import webview, threading, subprocess, sys, time, os, ctypes, atexit, socket, random, tempfile, signal, traceback
from datetime import datetime

# ── 强制显示控制台窗口 (launch.pyw 默认被 pythonw.exe 静默启动) ──
_CONSOLE_WAS_ALLOCATED = False  # 跟踪是否由本脚本自行分配控制台
if os.name == 'nt' and not ctypes.windll.kernel32.GetConsoleWindow():
    ctypes.windll.kernel32.AllocConsole()
    _CONSOLE_WAS_ALLOCATED = True
    sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
    sys.stderr = open('CONOUT$', 'w', encoding='utf-8')

# ═══════════════════════════════════════════════════════
# 日志系统 — Tee 输出: print → 控制台 + 日志文件
# ═══════════════════════════════════════════════════════
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_FILE = os.path.join(_LOG_DIR, f"launch_{datetime.now().strftime('%Y%m%d')}.log")
class _TeeLogger:
    def __init__(self):
        self.terminal = sys.stdout
        self.logfile = open(_LOG_FILE, 'a', encoding='utf-8')
    def write(self, msg):
        if msg.strip():
            self.terminal.write(msg)
            self.logfile.write(msg)
            self.logfile.flush()
    def flush(self):
        self.terminal.flush()
        self.logfile.flush()
sys.stdout = _TeeLogger()
sys.stderr = _TeeLogger()

# ═══════════════════════════════════════════════════════
# 控制台隐藏 — .pyw 模式自动隐藏控制台窗口
# ═══════════════════════════════════════════════════════
try:
    # 仅当由 pythonw.exe 启动(本脚本自行分配了控制台)时才隐藏,
    # 避免用 python.exe 启动时把父级 PowerShell 窗口也隐藏掉
    if _CONSOLE_WAS_ALLOCATED and os.name == 'nt':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except Exception:
    pass

# ═══════════════════════════════════════════════════════
# 三重单实例锁: 互斥体 + TCP端口 + PID文件
# ═══════════════════════════════════════════════════════

# 1) Windows 命名互斥体 (Local\ 无需管理员权限)
LAUNCH_MUTEX_NAME = "Local\\GA_Launch_Mutex_V2"
_kernel32 = ctypes.windll.kernel32
_launch_mutex = _kernel32.CreateMutexW(None, True, LAUNCH_MUTEX_NAME)
if not _launch_mutex:
    print(f"[Launch] 创建互斥体失败 (error={ctypes.get_last_error()})")
    sys.exit(1)
_last_err = ctypes.get_last_error()
if _last_err == 183:  # ERROR_ALREADY_EXISTS
    print(f"[Launch] launch.pyw 已在运行 (互斥体), 退出")
    sys.exit(0)

# 2) TCP 端口锁 (二级防护, 兼容跨互斥体场景)
LOCK_PORT = 19734
_lock_sock = None
try:
    _lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _lock_sock.bind(('127.0.0.1', LOCK_PORT))
    _lock_sock.listen(1)
except OSError:
    print(f"[Launch] launch.pyw 已在运行 (端口 {LOCK_PORT} 被占用), 退出")
    sys.exit(0)

# 3) PID 文件 (防进程残留)
_PID_FILE = os.path.join(tempfile.gettempdir(), "GA_launch.pid")
def _check_pid_file():
    if os.path.isfile(_PID_FILE):
        try:
            with open(_PID_FILE) as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 0)  # 检查进程是否存在
                print(f"[Launch] PID文件显示旧进程({old_pid})仍在运行, 退出")
                sys.exit(0)
            except OSError:
                pass  # 旧进程已死, 覆盖PID文件
        except (ValueError, OSError):
            pass
_check_pid_file()
with open(_PID_FILE, 'w') as f:
    f.write(str(os.getpid()))
atexit.register(lambda: os.remove(_PID_FILE) if os.path.isfile(_PID_FILE) else None)

# ═══════════════════════════════════════════════════════
# 优雅退出处理器 — Ctrl+C / 崩溃时清理全部子进程
# ═══════════════════════════════════════════════════════
_ALL_PROCS: list[subprocess.Popen] = []  # 全局子进程列表
_EXITING = False

def _cleanup_all_procs():
    global _EXITING
    if _EXITING:
        return
    _EXITING = True
    print('[Shutdown] 正在清理所有子进程...')
    for proc in _ALL_PROCS[:]:
        if proc and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=3)
                print(f'[Shutdown] 已终止 PID={proc.pid}')
            except Exception as e:
                print(f'[Shutdown] 终止 PID={proc.pid} 失败: {e}')
    _ALL_PROCS.clear()
    print('[Shutdown] 清理完成')

def _signal_handler(sig, frame):
    print(f'[Shutdown] 收到信号 {sig}, 准备退出...')
    _cleanup_all_procs()
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
atexit.register(_cleanup_all_procs)

# ── 手动加载 .env（无需 python-dotenv） ──
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.isfile(_env_path):
    with open(_env_path, encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

WINDOW_WIDTH, WINDOW_HEIGHT, RIGHT_PADDING, TOP_PADDING = 600, 900, 0, 100

script_dir = os.path.dirname(os.path.abspath(__file__))
frontends_dir = os.path.join(script_dir, "frontends")
scripts_dir = os.path.join(script_dir, "scripts")

def find_free_port(lo=18501, hi=18599):
    ports = list(range(lo, hi+1)); random.shuffle(ports)
    for p in ports:
        try: s = socket.socket(); s.bind(('127.0.0.1', p)); s.close(); return p
        except OSError: continue
    raise RuntimeError(f'No free port in {lo}-{hi}')

def get_screen_width():
    try: return ctypes.windll.user32.GetSystemMetrics(0)
    except: return 1920

def start_streamlit(port):
    """启动 Streamlit 前端 (production模式, 注册到全局进程列表)"""
    cmd = [sys.executable, "-m", "streamlit", "run",
           os.path.join(frontends_dir, "stapp.py"),
           "--server.port", str(port),
           "--server.address", "localhost",
           "--server.headless", "true",
           "--client.toolbarMode", "viewer",
           "--global.developmentMode", "false",
           "--server.enableCORS", "false",
           "--server.enableXsrfProtection", "false"]
    try:
        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        _ALL_PROCS.append(proc)
        print(f'[Streamlit] 已启动 (PID={proc.pid}, port={port})')
        return proc
    except Exception as e:
        print(f'[Streamlit] 启动失败: {e}')
        traceback.print_exc()
        return None

def inject(text):
    window.evaluate_js(f"""
        const textarea = document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (textarea) {{
            // 1. 用原生 setter 设置值（绕过 React）
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeTextAreaValueSetter.call(textarea, {repr(text)});
            // 2. 触发 React 的 input 事件
            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            // 3. 触发 change 事件（有些组件需要）
            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
            // 4. 延迟提交
            setTimeout(() => {{
                const btn = document.querySelector('[data-testid="stChatInputSubmitButton"]');
                if (btn) {{btn.click();console.log('Submitted:', {repr(text)});}}
            }}, 200);
        }}""")

def get_last_reply_time():
    last = window.evaluate_js("""
        const el = document.getElementById('last-reply-time');
        el ? parseInt(el.textContent) : 0;
    """) or 0
    return last or int(time.time())

PASTE_HOOK_JS = """if (!window._pasteHooked) { window._pasteHooked = true;
    document.addEventListener('paste', e => {
        const items = e.clipboardData?.items; if (!items) return;
        let t = null, hasText = false;
        for (const item of items) {
            if (item.kind === 'string' && (item.type === 'text/plain' || item.type === 'text/html')) hasText = true;
            if (item.kind === 'file') { t = item.type.startsWith('image/') ? 'image in clipboard, ' : 'file in clipboard, '; }
        }
        if (!t || hasText) return;
        e.preventDefault(); e.stopImmediatePropagation();
        const el = document.querySelector('textarea[data-testid="stChatInputTextArea"]') || document.activeElement;
        if (el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')) {
            const s = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
            s.call(el, el.value + t); el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }, true);
}"""

def idle_monitor():
    """后台线程: 30秒轮询检测用户空闲, 触发自主任务"""
    _paste_injected = False
    last_trigger_time = 0
    while True:
        time.sleep(30)
        try:
            # PASTE_HOOK_JS 仅注入一次 (避免 bridge 资源泄漏)
            if not _paste_injected:
                window.evaluate_js(PASTE_HOOK_JS)
                _paste_injected = True
            # 空闲检测
            now = time.time()
            if now - last_trigger_time < 120:
                continue
            last_reply = get_last_reply_time()
            if now - last_reply > 1800:
                print('[Idle Monitor] Detected idle state, injecting task...')
                inject("[AUTO]🤖 用户已经离开超过30分钟，作为自主智能体，请阅读自动化sop，执行自动任务。")
                last_trigger_time = now
        except Exception as e:
            print(f'[Idle Monitor] Error: {e}')

# ── LLM Cache Daemon 已移除 (llm_cache_rs 不再使用) ──

# ── 子进程崩溃监测已移除 (原Watchdog) ──

# ═══════════════════════════════════════════════════════
# 依赖预检 — 启动前检查关键模块
# ═══════════════════════════════════════════════════════
def _check_dependencies():
    """检查启动所需的关键文件和模块"""
    checks = [
        ('frontends/stapp.py', os.path.join(frontends_dir, 'stapp.py')),
    ]
    missing = [name for name, path in checks if not os.path.isfile(path)]
    if missing:
        print(f'[Dependency] ⚠ 缺少关键文件: {", ".join(missing)}')
        return False
    try:
        import importlib
        importlib.import_module('streamlit')
    except ImportError:
        print('[Dependency] ⚠ streamlit 未安装, 请执行: pip install streamlit')
        return False
    print('[Dependency] 依赖检查通过')
    return True

def _start_bot(app_path: str, name: str, enabled: bool) -> subprocess.Popen | None:
    """通用 bot 启动器: 注册到 _ALL_PROCS 并返回进程"""
    if not enabled:
        print(f'[Launch] {name} Bot not enabled')
        return None
    if not os.path.isfile(app_path):
        print(f'[Launch] ⚠ {name} Bot 文件不存在: {app_path}')
        return None
    try:
        proc = subprocess.Popen(
            [sys.executable, app_path],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        _ALL_PROCS.append(proc)
        print(f'[Launch] {name} Bot started (PID={proc.pid})')
        return proc
    except Exception as e:
        print(f'[Launch] ⚠ {name} Bot 启动失败: {e}')
        return None

if __name__ == '__main__':
    # ── 依赖预检 ──
    if not _check_dependencies():
        print('[Launch] ⚠ 依赖检查失败, 退出')
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('port', nargs='?', default='0'); 
    parser.add_argument('--tg', action='store_true', help='启动 Telegram Bot')
    parser.add_argument('--qq', action='store_true', help='启动 QQ Bot')
    parser.add_argument('--feishu', '--fs', dest='feishu', action='store_true', help='启动 Feishu Bot')
    parser.add_argument('--wechat', '--wx', dest='wechat', action='store_true', help='启动 WeChat Bot')
    parser.add_argument('--wecom', action='store_true', help='启动 WeCom Bot')
    parser.add_argument('--dingtalk', '--dt', dest='dingtalk', action='store_true', help='启动 DingTalk Bot')
    parser.add_argument('--sched', action='store_true', help='启动计划任务调度器')
    parser.add_argument('--llm_no', type=int, default=0, help='LLM编号')
    args = parser.parse_args()
    port = str(find_free_port()) if args.port == '0' else args.port
    print(f'[Launch] Using port {port}')

    # ── 启动 Streamlit ──
    threading.Thread(target=start_streamlit, args=(port,), daemon=True).start()

    # ── 启动 Bot 前端 (使用通用启动器) ──
    _start_bot(os.path.join(frontends_dir, "tgapp.py"), "Telegram", args.tg)
    _start_bot(os.path.join(frontends_dir, "qqapp.py"), "QQ", args.qq)
    _start_bot(os.path.join(scripts_dir, "fsapp.py"), "Feishu", args.feishu)
    _start_bot(os.path.join(frontends_dir, 'wechatapp.py'), "WeChat", args.wechat)
    _start_bot(os.path.join(frontends_dir, "wecomapp.py"), "WeCom", args.wecom)
    _start_bot(os.path.join(frontends_dir, "dingtalkapp.py"), "DingTalk", args.dingtalk)

    if args.sched:
        scheduler_path = os.path.join(script_dir, "agentmain.py")
        if os.path.isfile(scheduler_path):
            try:
                proc = subprocess.Popen(
                    [sys.executable, scheduler_path, "--reflect",
                     os.path.join(script_dir, "reflect", "scheduler.py"),
                     "--llm_no", str(args.llm_no)],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                _ALL_PROCS.append(proc)
                print(f'[Launch] Task Scheduler started (PID={proc.pid})')
            except Exception as e:
                print(f'[Launch] ⚠ Task Scheduler 启动失败: {e}')
        else:
            print(f'[Launch] ⚠ Task Scheduler 文件不存在: {scheduler_path}')
    else:
        print('[Launch] Task Scheduler not enabled (--sched)')

    # ── Idle Monitor ──
    threading.Thread(target=idle_monitor, daemon=True).start()

    # ── 计算窗口位置并启动 Webview ──
    if os.name == 'nt':
        screen_width = get_screen_width()
        x_pos = screen_width - WINDOW_WIDTH - RIGHT_PADDING
    else:
        x_pos = 100

    try:
        window = webview.create_window(
            title='GenericAgent', url=f'http://localhost:{port}',
            width=WINDOW_WIDTH, height=WINDOW_HEIGHT, x=x_pos, y=TOP_PADDING,
            resizable=True, text_select=True)
        webview.start()
    except Exception as e:
        print(f'[Launch] ⚠ Webview 启动失败: {e}')
        traceback.print_exc()
        _cleanup_all_procs()
        sys.exit(1)
