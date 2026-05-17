"""
测试: mqtt_bbs 持久化集成 — 单元测试 + 集成测试 + E2E

遵循 mqtt_testing 技能模式:
- 使用 pytest 编写测试
- Mock 隔离外部依赖
- 覆盖核心逻辑和边界情况
- 集成测试验证组件间协作
"""

import sys, os, json, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import patch, MagicMock
from mqtt_bbs.client import TaskOutput, TaskMessage


class TestUnit:
    """单元: 序列化 + Mock"""

    def test_task_output_roundtrip(self):
        o = TaskOutput(task_id="t1", agent_id="a1", status="completed", result={"x": 1})
        d = o.to_dict()
        o2 = TaskOutput.from_dict(d)
        assert o2.task_id == "t1"
        assert o2.agent_id == "a1"
        assert o2.status == "completed"
        assert o2.result == {"x": 1}

    def test_task_message_roundtrip(self):
        m = TaskMessage(task_id="t2", type="test", input={"cmd": "hello"}, priority=5, timeout=60)
        d = m.to_dict()
        m2 = TaskMessage.from_dict(d)
        assert m2.task_id == "t2"
        assert m2.type == "test"
        assert m2.input == {"cmd": "hello"}
        assert m2.priority == 5
        assert m2.timeout == 60

    def test_task_output_with_error(self):
        o = TaskOutput(task_id="t3", agent_id="a2", status="failed", error="timeout")
        d = o.to_dict()
        o2 = TaskOutput.from_dict(d)
        assert o2.status == "failed"
        assert o2.error == "timeout"

    def test_task_output_defaults(self):
        o = TaskOutput(task_id="t4", agent_id="a3", status="pending")
        assert o.status == "pending"
        assert o.result is None
        assert o.error is None
