# reflect/supervisor_monitor.py — 系统健康监控
# 用法: agentmain --reflect reflect/supervisor_monitor.py
# 每300秒检查一次核心服务，发现异常时生成修复任务

import os, json, socket, time as _time, logging
from datetime import datetime

# 端口锁：防止重复启动
try: _lock
except NameError:
    _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _lock.bind(('127.0.0.1', 45763)); _lock.listen(1)

INTERVAL = 300  # 每5分钟检查一次
ONCE = False

_dir = os.path.dirname(os.path.abspath(__file__))
_LOG = os.path.join(_dir, '../temp/supervisor_monitor.log')
_HEALTH = {}  # 缓存上次健康状态

# 日志
_logger = logging.getLogger('supervisor')
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _fh = logging.FileHandler(_LOG, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M'))
    _logger.addHandler(_fh)

def port_open(host, port, timeout=3):
    """检查TCP端口是否可达"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except:
        return False

def check():
    now = _time.time()
    issues = []

    # 1. MariaDB (3306)
    mariadb_ok = port_open('127.0.0.1', 3306)
    _state_change('mariadb', mariadb_ok)
    if not mariadb_ok:
        issues.append('MariaDB (3306) 不可达')

    # 2. Mosquitto (1883)
    mqtt_ok = port_open('127.0.0.1', 1883)
    _state_change('mosquitto', mqtt_ok)
    if not mqtt_ok:
        issues.append('Mosquitto (1883) 不可达')

    # 3. BoardService RS (9100 metrics)
    bs_ok = port_open('127.0.0.1', 9100)
    _state_change('board_service_rs', bs_ok)
    if not bs_ok:
        issues.append('BoardService RS (9100) 不可达')

    # 4. Gateway (8000)
    gw_ok = port_open('127.0.0.1', 8000)
    _state_change('gateway', gw_ok)
    if not gw_ok:
        issues.append('Gateway (8000) 不可达')

    # 汇总
    if issues:
        msg = '; '.join(issues)
        _logger.warning(f'异常: {msg}')
        return (
            f'[Supervisor] 系统健康检查发现异常\n'
            f'异常服务: {msg}\n\n'
            f'请根据异常情况执行修复：\n'
            f'- 若 MariaDB 不可达: 执行 `Start-Service MariaDB`\n'
            f'- 若 Mosquitto 不可达: 执行 start_all.ps1 或手动启动 mosquitto\n'
            f'- 若 BoardService RS 不可达: 执行 start_all.ps1 中的 BoardService 启动步骤\n'
            f'- 若 Gateway 不可达: 执行 `python -m frontends.gateway.main`\n\n'
            f'修复后确认所有服务可用。'
        )

    _logger.info('所有服务正常')
    return None

def _state_change(name, ok):
    """检测状态变化，仅第一次异常时记录"""
    prev = _HEALTH.get(name)
    _HEALTH[name] = ok
    if prev is None and not ok:
        _logger.warning(f'[INIT] {name} 初始状态=异常')
    elif prev is True and not ok:
        _logger.warning(f'[DOWN] {name} 从正常转为异常')
    elif prev is False and ok:
        _logger.info(f'[UP] {name} 从异常恢复')
