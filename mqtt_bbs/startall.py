"""
startall.py — 一键启动所有服务

用法: python startall.py
"""

import os, sys, subprocess, time, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

# 加载 .env
env_path = ROOT / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

# 默认路径: 优先从环境变量读取，fallback到本地硬编码
_DEFAULT_MOSQUITTO_HOME = r'D:\tools\mosquitto'
os.environ.setdefault('MOSQUITTO_HOME', _DEFAULT_MOSQUITTO_HOME)
os.environ.setdefault('MOSQUITTO_EXE', 'mosquitto.exe')
os.environ.setdefault('MOSQUITTO_CONF', 'mosquitto.conf')
os.environ.setdefault('MOSQUITTO_PASSWD', 'mosquitto_passwd')

PYTHON = sys.executable  # or str(ROOT / '.venv' / 'Scripts' / 'python.exe')


def port_free(port):
    """检查端口是否可用"""
    r = subprocess.run(
        ['powershell', '-Command',
         f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty State'],
        capture_output=True, text=True, timeout=5
    )
    return r.stdout.strip() != 'Listen'


def start_proc(cmd_args, name, timeout=3):
    """启动后台进程"""
    p = subprocess.Popen(
        cmd_args,
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=ROOT
    )
    time.sleep(timeout)
    if p.poll() is None:
        print(f'  [OK] {name} (PID={p.pid})')
    else:
        print(f'  [!] {name} FAILED (exit={p.returncode})')
    return p


def check_port(port, name, url=''):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    ok = s.connect_ex(('127.0.0.1', port)) == 0
    s.close()
    state = 'Listen' if ok else 'OFF'
    print(f'  [{"OK" if ok else " "}] {name:20} port {port:5} {url}')
    return ok


def main():
    print('=' * 50)
    print('  GenericAgent MQTT - 全服务启动')
    print('=' * 50)
    print()

    procs = []

    # 1. MariaDB
    r = subprocess.run(['sc', 'query', 'MariaDB'], capture_output=True, text=True, timeout=5)
    if 'RUNNING' in r.stdout:
        print('  [OK] MariaDB (3306) 已在运行')
    else:
        r2 = subprocess.run(['net', 'start', 'MariaDB'], capture_output=True, text=True, timeout=10)
        if r2.returncode == 0:
            print('  [OK] MariaDB 已启动')
        else:
            print('  [!] MariaDB 启动失败')

    # 2. Mosquitto (1883)
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq mosquitto.exe', '/FO', 'CSV'],
                       capture_output=True, text=True, timeout=5)
    if 'mosquitto.exe' in r.stdout:
        print('  [OK] Mosquitto (1883) 已在运行')
    else:
        mosq = os.path.join(os.environ['MOSQUITTO_HOME'], os.environ['MOSQUITTO_EXE'])
        if os.path.exists(mosq):
            p = start_proc([mosq, '-c', os.path.join(os.environ['MOSQUITTO_HOME'], os.environ['MOSQUITTO_CONF'])], 'Mosquitto', timeout=3)
            if p.poll() is None:
                procs.append(p)
        else:
            print('  [!] Mosquitto not found')

    # 3. simphtml_rs (8901)
    check_port(8901, 'simphtml_rs', 'http://localhost:8901')

    # 4. rmqtt_webui_rs (8900)
    check_port(8900, 'rmqtt Web UI', 'http://localhost:8900')

    # 5. md_server_rs (8899)
    check_port(8899, 'MD Server', 'http://localhost:8899')

    # 6. BoardService RS
    exe = ROOT / 'tools' / 'board_service_rs' / 'target' / 'release' / 'board_service_rs.exe'
    if exe.exists():
        dbpw = os.environ.get('DB_PASSWORD', 'mariadb')
        p = subprocess.Popen(
            [str(exe), '--db-url', f'mysql://root:{dbpw}@127.0.0.1/mqtt_bbs'],
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=ROOT
        )
        time.sleep(3)
        if p.poll() is None:
            print('  [OK] BoardService RS (PID=%d)' % p.pid)
            procs.append(p)
        else:
            print('  [!] BoardService RS FAILED')
    else:
        print('  [ ] BoardService RS 未编译')

    # 7. Gateway (8000)
    if port_free(8000):
        py = str(ROOT / '.venv' / 'Scripts' / 'python.exe')
        p = subprocess.Popen(
            [py, '-m', 'frontends.gateway.main'],
            creationflags=subprocess.CREATE_NO_WINDOW,
            cwd=ROOT
        )
        time.sleep(5)
        if p.poll() is None:
            print('  [OK] Gateway (8000) http://localhost:8000 (PID=%d)' % p.pid)
            procs.append(p)
        else:
            print('  [!] Gateway FAILED')
    else:
        print('  [OK] Gateway (8000) 已在运行')

    print()
    print('=' * 50)
    print('  Service Summary')
    print('=' * 50)
    for port, name, url in [
        (8000, 'Gateway', 'http://localhost:8000'),
        (1883, 'Mosquitto', 'mqtt://127.0.0.1:1883'),
        (3306, 'MariaDB', 'mysql://127.0.0.1:3306'),
        (8901, 'simphtml_rs', 'http://localhost:8901'),
        (8900, 'rmqtt Web UI', 'http://localhost:8900'),
        (8899, 'MD Server', 'http://localhost:8899'),
    ]:
        check_port(port, name, url)
    print()
    print('  fsapp.py: python frontends\fsapp.py')
    print('=' * 50)

    # Keep running
    print()
    print('  Ctrl+C 退出所有服务')
    try:
        while True:
            time.sleep(10)
            for p in procs[:]:
                if p.poll() is not None:
                    procs.remove(p)
    except KeyboardInterrupt:
        print('\n正在停止...')
        for p in procs:
            p.terminate()
        print('已停止所有服务')


if __name__ == '__main__':
    main()
