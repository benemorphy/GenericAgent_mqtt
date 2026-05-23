"""
pytest conftest — 全局 mock，防止测试导入触发 DB 连接或 MQTT Broker 连接

bbs.py 的 AgentBoard/WorkerAgent 在 __init__ 中导入 BBSClientWithPersistence，
该模块在导入时会尝试连接 MariaDB。这里在导入前 mock 掉它。
"""

import sys, os, types

# 在 bbs 被 import 之前，先插入 mock 的 persistence 模块
mock_persistence = types.ModuleType("mqtt_bbs.persistence")

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

mock_persistence.BBSClientWithPersistence = MockBBSClientWithPersistence
sys.modules["mqtt_bbs.persistence"] = mock_persistence
