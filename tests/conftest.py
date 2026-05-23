"""
pytest conftest — 全局 mock，防止测试导入触发 DB 连接或 MQTT Broker 连接

bbs.py → persistence.py → pymysql.connect() 在无 MariaDB 环境崩溃。
这里在导入链的根部（pymysql）mock 掉。
"""

import sys, types

# ── 1. 在 persistence.py 被 import 之前 mock pymysql ──
# persistence.py 在模块顶层 `import pymysql`，如果 pymysql 可用但 DB 不可达就会崩溃。
# 直接注入一个静默的 mock 模块。
mock_pymysql = types.ModuleType("pymysql")
mock_pymysql.connect = lambda **kw: types.SimpleNamespace(
    cursor=lambda **kw: types.SimpleNamespace(
        execute=lambda *a, **kw: None,
        fetchall=lambda: [],
        fetchone=lambda: None,
        close=lambda: None,
    ),
    close=lambda: None,
    commit=lambda: None,
)
mock_pymysql.err = types.SimpleNamespace(
    OperationalError=type("OperationalError", (Exception,), {}),
)
mock_pymysql.cursors = types.SimpleNamespace(
    DictCursor=type("DictCursor", (), {}),
)
sys.modules["pymysql"] = mock_pymysql

# ── 2. Mock persistence.py 模块 ──
class MockBBSClientWithPersistence:
    """Mock 持久化 BBS 客户端，不连接任何外部服务"""
    def __init__(self, *args, **kwargs):
        self.agent_id = args[0] if args else "test"
        self._connected = True
    def connect(self, *args, **kwargs): pass
    def disconnect(self, *args, **kwargs): pass
    def publish(self, *args, **kwargs): pass
    def subscribe(self, *args, **kwargs): pass
    def wait_connected(self, *args, **kwargs): return True
    def wait_response(self, *args, **kwargs): return {}
    @property
    def is_connected(self): return True

mock_persistence = types.ModuleType("mqtt_bbs.persistence")
mock_persistence.BBSClientWithPersistence = MockBBSClientWithPersistence
sys.modules["mqtt_bbs.persistence"] = mock_persistence

# CI: mock pymysql + persistence for MariaDB-free test environment
