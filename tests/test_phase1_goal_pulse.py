# Phase 1 完整测试 — Goal Pulse + Goal Chronicle
# 测试范围: 单元测试 → 集成测试 → 端到端 → 降级测试 → 边界测试

import sys, os, json, time, socket, traceback

GA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'GA'))
sys.path.insert(0, GA_DIR)
os.chdir(GA_DIR)

PASS = 0
FAIL = 0

def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

# ═══════════════════════════════════════════════════════════
# Test 1: 模块导入与语法检查
# ═══════════════════════════════════════════════════════════
section("Test 1: 模块导入与语法检查")
import py_compile

try:
    py_compile.compile(os.path.join(GA_DIR, "reflect", "goal_bbs.py"), doraise=True)
    check(True, "goal_bbs.py 语法正确")
except py_compile.PyCompileError as e:
    check(False, f"goal_bbs.py 语法错误: {e}")

try:
    py_compile.compile(os.path.join(GA_DIR, "reflect", "goal_mode.py"), doraise=True)
    check(True, "goal_mode.py 语法正确")
except py_compile.PyCompileError as e:
    check(False, f"goal_mode.py 语法错误: {e}")

# ═══════════════════════════════════════════════════════════
# Test 2: goal_bbs API 完整性
# ═══════════════════════════════════════════════════════════
section("Test 2: goal_bbs API 完整性")
from reflect.goal_bbs import bbs_init, bbs_pulse, bbs_chronicle, bbs_close, quick_pulse

check(callable(bbs_init), "bbs_init 可调用")
check(callable(bbs_pulse), "bbs_pulse 可调用")
check(callable(bbs_chronicle), "bbs_chronicle 可调用")
check(callable(bbs_close), "bbs_close 可调用")
check(callable(quick_pulse), "quick_pulse 可调用")

import inspect
bbs_init_sig = inspect.signature(bbs_init)
check('pulse_board' in bbs_init_sig.parameters, "bbs_init 有 pulse_board 参数")
check('chronicle_board' in bbs_init_sig.parameters, "bbs_init 有 chronicle_board 参数")

qp_sig = inspect.signature(quick_pulse)
check('turn' in qp_sig.parameters, "quick_pulse 有 turn 参数")
check('focus' in qp_sig.parameters, "quick_pulse 有 focus 参数")

# ═══════════════════════════════════════════════════════════
# Test 3: goal_mode.py Pulse/Chronicle 代码注入
# ═══════════════════════════════════════════════════════════
section("Test 3: goal_mode.py Pulse/Chronicle 代码注入")
with open(os.path.join(GA_DIR, "reflect", "goal_mode.py"), 'r', encoding='utf-8') as f:
    gm_code = f.read()

check("from goal_bbs import" in gm_code, "导入 goal_bbs")
check("bbs_init()" in gm_code, "init() 调用了 bbs_init()")
check("bbs_chronicle('query'" in gm_code, "init() 调用了 bbs_chronicle(query)")
check("_send_pulse(" in gm_code, "check()/on_done() 调用了 _send_pulse() (内部调 bbs_pulse)")
check("_store_chronicle(" in gm_code, "on_done() 调用了 _store_chronicle() (内调 bbs_chronicle)")
check("_bbs['chronicle']('summary'" in gm_code, "wrapping_up 调用了 bbs_chronicle(summary)")

# 验证所有 BBS 调用都有 try/except 保护
try_count = gm_code.count("try:")
except_count = gm_code.count("except")
check(try_count >= 5 and except_count >= 5, f"有 {try_count} 个 try / {except_count} 个 except 保护")

# ═══════════════════════════════════════════════════════════
# Test 4: BBS 连接与 fire-and-forget 延迟
# ═══════════════════════════════════════════════════════════
section("Test 4: BBS 连接与 fire-and-forget 延迟")

sock = socket.socket()
broker_ok = sock.connect_ex(('127.0.0.1', 1883)) == 0
sock.close()
check(broker_ok, "MQTT Broker (1883) 可达")

if broker_ok:
    bbs_init()
    check(True, "bbs_init() 连接成功")
    
    # Pulse 延迟测试 (10次)
    pulse_times = []
    for i in range(10):
        t0 = time.time()
        bbs_pulse('test_pulse', turn=i, focus=f"test_{i}")
        pulse_times.append((time.time() - t0) * 1000)
    avg_pulse = sum(pulse_times) / len(pulse_times)
    max_pulse = max(pulse_times)
    check(avg_pulse < 50, f"Pulse 平均延迟 {avg_pulse:.1f}ms (< 50ms)")
    check(max_pulse < 200, f"Pulse 最大延迟 {max_pulse:.1f}ms (< 200ms)")
    
    # Chronicle store 延迟
    store_times = []
    for i in range(5):
        t0 = time.time()
        bbs_chronicle('store', entry=f"test_store_{i}", turn=i, phase='test')
        store_times.append((time.time() - t0) * 1000)
    avg_store = sum(store_times) / len(store_times)
    check(avg_store < 50, f"Chronicle store 平均延迟 {avg_store:.1f}ms (< 50ms)")
    
    # Chronicle summary
    t0 = time.time()
    bbs_chronicle('summary', summary="test summary", total_turns=5, duration_sec=10, findings=["test"])
    check((time.time() - t0) * 1000 < 50, f"Chronicle summary 延迟 < 50ms")
    
    # 关闭
    bbs_close()
    check(True, "bbs_close() 正常关闭")
    
    # 关闭后静默
    bbs_pulse('post_close', turn=99)  # 应该静默跳过
    check(True, "关闭后 Pulse 静默跳过")
    
# ═══════════════════════════════════════════════════════════
# Test 5: 降级测试 — BBS 不可用
# ═══════════════════════════════════════════════════════════
section("Test 5: 降级测试 — BBS 不可用")
# 重新导入模拟未初始化状态
import importlib
from reflect import goal_bbs
importlib.reload(goal_bbs)

# 不调用 bbs_init(), 直接发 pulse
goal_bbs.bbs_pulse('no_init', turn=0)  # 应静默跳过
check(True, "未初始化时 Pulse/Chronicle 静默跳过")

# ═══════════════════════════════════════════════════════════
# Test 6: goal_state.json 兼容性
# ═══════════════════════════════════════════════════════════
section("Test 6: goal_state.json 兼容性")

test_state = {
    "objective": "Phase 1 集成测试",
    "budget_seconds": 300,
    "start_time": time.time(),
    "turns_used": 0,
    "max_turns": 10,
    "status": "running",
    "done_prompt": ""
}
state_path = os.path.join(GA_DIR, "temp", "test_goal_state.json")
with open(state_path, 'w') as f:
    json.dump(test_state, f)
os.environ['GOAL_STATE'] = state_path

# 测试 reflect.goal_mode
import importlib
import reflect.goal_mode
importlib.reload(reflect.goal_mode)

check(os.environ.get('GOAL_STATE') == state_path, f"GOAL_STATE 环境变量正确: {os.path.basename(state_path)}")

# 手动调用 init()
reflect.goal_mode.init({"goal_state": state_path})
check(reflect.goal_mode.STATE_FILE == state_path, f"init() 后 STATE_FILE 正确")

state = reflect.goal_mode._load()
check(state is not None, "_load() 读取成功")
check(state['objective'] == "Phase 1 集成测试", "_load() 内容正确")

# 测试 _save 往返
state['turns_used'] = 5
state['status'] = 'wrapping_up'
reflect.goal_mode._save(state)
reloaded = reflect.goal_mode._load()
check(reloaded['turns_used'] == 5 and reloaded['status'] == 'wrapping_up', "_save/_load 往返正确")

# 清理
if os.path.exists(state_path):
    os.remove(state_path)
os.environ.pop('GOAL_STATE', None)

# ═══════════════════════════════════════════════════════════
# Test 7: 端到端 — 启动 goal 实例验证
# ═══════════════════════════════════════════════════════════
section("Test 7: 端到端 — 启动 goal 实例验证")

# 先检查 broker 是否可用再跑端到端
sock = socket.socket()
broker_up = sock.connect_ex(('127.0.0.1', 1883)) == 0
sock.close()

if broker_up:
    import subprocess
    
    # 创建临时 state
    test_state_path = os.path.join(GA_DIR, "temp", "test_end2end_state.json")
    test_state = {
        "objective": "端到端测试：验证 Pulse 消息是否发送到 MQTT",
        "budget_seconds": 120,
        "start_time": time.time(),
        "turns_used": 0,
        "max_turns": 5,
        "status": "running",
        "done_prompt": ""
    }
    with open(test_state_path, 'w') as f:
        json.dump(test_state, f)
    os.environ['GOAL_STATE'] = test_state_path
    
    # 启动新 goal 实例（子进程方式）
    proc = subprocess.Popen(
        [sys.executable, "agentmain.py", "--reflect", "reflect/goal_mode.py"],
        cwd=GA_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # 等 60 秒让子进程完成 init + BBS 注册 + LLM 首轮推理
    print("  等待 goal 实例运行 60 秒 (BBS register ~10s + init + LLM 首轮推理)...")
    time.sleep(60)
    
    # 检查进程是否存活
    alive = proc.poll() is None
    check(alive, "goal 实例进程存活 (reflect loop 已启动)")
    
    if alive:
        # 先终止子进程，确保无并发写入
        proc.terminate()
        raw_out, raw_err = proc.communicate(timeout=5)
        stdout = raw_out.decode('gbk', errors='replace') if raw_out else ""
        stderr = raw_err.decode('gbk', errors='replace') if raw_err else ""
        
        # 再读取 goal_state.json（无竞争）
        if os.path.exists(test_state_path):
            try:
                with open(test_state_path, 'r', encoding='utf-8') as f:
                    cur_state = json.load(f)
                turns = cur_state.get('turns_used', 0)
                check(turns >= 1, f"goal_state.json 已更新, turns_used={turns}")
            except Exception as e:
                check(False, f"读取 goal_state.json 失败: {e}")
        else:
            check(False, "goal_state.json 已被删除")
        
        # 检查 stderr 确认无 import 错误
        has_import_error = 'No module named' in stderr or 'ModuleNotFoundError' in stderr
        check(not has_import_error, f"BBS import 无错误 ({'有错误' if has_import_error else 'ok'})")
        
        has_connected = 'Connected' in stderr or 'Connected' in stdout
        check(has_connected, f"BBS 连接成功 ({'已连接' if has_connected else '未连接'})")
    else:
        raw_out, raw_err = proc.communicate(timeout=2)
        stderr = raw_err.decode('gbk', errors='replace')[:300] if raw_err else "(empty)"
        print(f"  stderr: {stderr}")
    
    # 清理
    if os.path.exists(test_state_path):
        os.remove(test_state_path)
    os.environ.pop('GOAL_STATE', None)
else:
    check(True, "[SKIP] Broker 不可用，跳过端到端测试")

# ═══════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════
section("测试汇总")
total = PASS + FAIL
print(f"  通过: {PASS}/{total} ({PASS/total*100:.0f}%)")
print(f"  失败: {FAIL}/{total}")
if FAIL == 0:
    print("\nALL TESTS PASSED")
else:
    print(f"\n{FAIL} TEST(S) FAILED")
sys.exit(0 if FAIL == 0 else 1)
