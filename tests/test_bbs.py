"""
bbs.py 单元测试 — AgentBoard + WorkerAgent 业务逻辑
使用 unittest.mock 模拟 MQTT，不依赖外部 Broker 或 MariaDB。
"""

import sys, os, json, hmac, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock, call
import pytest

from mqtt_bbs.bbs import AgentBoard, WorkerAgent, TaskStatus, _calc_hmac, _verify_task


# ── HMAC 签名验证 ──

class TestHMAC:
    """HMAC 签名机制的单元测试"""

    def test_calc_hmac_produces_valid_signature(self):
        """正常签名"""
        sig = _calc_hmac("task_001", "test", {})
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_verify_valid_signature(self):
        """正确签名应通过验证"""
        tid, tp, inp = "task_001", "test", {"x": 1}
        sig = _calc_hmac(tid, tp, inp)
        assert _verify_task({"task_id": tid, "type": tp, "input": inp, "_sig": sig})

    def test_verify_tampered_payload(self):
        """篡改后的 payload 应被拒绝"""
        tid, tp, inp = "task_001", "test", {"x": 1}
        sig = _calc_hmac(tid, tp, inp)
        tampered = {"task_id": tid, "type": "EVIL", "input": inp, "_sig": sig}
        assert not _verify_task(tampered)

    def test_verify_missing_signature(self):
        """缺少 _sig 的 payload 应被拒绝"""
        assert not _verify_task({"task_id": "t1", "type": "test", "input": {}})

    def test_verify_wrong_signature(self):
        """错误的签名应被拒绝"""
        assert not _verify_task({"task_id": "t1", "type": "test", "input": {}, "_sig": "bad"})


# ── AgentBoard — 任务发布 ──

class TestAgentBoard:
    """AgentBoard: 主智能体接口（任务创建/查询/取消）"""

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_post_task_returns_task_id(self, MockClient):
        """post_task 应返回有效的 task_id"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        board = AgentBoard("test_agent")
        board._client = mock_client

        tid = board.post_task("test_type", {"key": "val"}, task_id=None)
        assert tid.startswith("task_")
        assert len(tid) > 10

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_post_task_publishes_input_and_status(self, MockClient):
        """post_task 应 publish input (retain=True) 和 status (retain=True)"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        board = AgentBoard("test_agent")
        board._client = mock_client

        tid = board.post_task("test_type", {"key": "val"})

        # 检查 publish 调用
        publish_calls = [c for c in mock_client.publish.call_args_list if "board/task" in str(c)]
        assert len(publish_calls) >= 2

        # 检查 input 发布
        input_topics = [c[0][0] for c in publish_calls if "input" in str(c)]
        assert len(input_topics) >= 1
        assert tid in str(input_topics)

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_post_task_with_hmac_signature(self, MockClient):
        """post_task 发布的 payload 应包含 _sig 签名"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        board = AgentBoard("test_agent")
        board._client = mock_client

        board.post_task("test_type", {"key": "val"})

        # 找到 input publish 的 payload 并验证 _sig
        for args, kwargs in mock_client.publish.call_args_list:
            topic, payload = args[0], args[1]
            if "input" in topic and isinstance(payload, dict):
                assert "_sig" in payload
                assert len(payload["_sig"]) > 0

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_cancel_task_publishes_cancel_status(self, MockClient):
        """cancel_task 应 publish CANCELED 状态"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        board = AgentBoard("test_agent")
        board._client = mock_client

        board.cancel_task("task_001")

        # 检查 publish 了 CANCELED 状态
        found = False
        for args, kwargs in mock_client.publish.call_args_list:
            topic, payload = args[0], args[1]
            if "status" in str(topic) and (payload == TaskStatus.CANCELED.value or payload == "canceled"):
                found = True
                break
        assert found, "cancel_task should publish CANCELED status"


# ── WorkerAgent — 任务执行 ──

class TestWorkerAgent:
    """WorkerAgent: 工作智能体（任务认领/执行）"""

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_agent_initialization(self, MockClient):
        """WorkerAgent 初始化应设置 agent_id 和 board"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        worker = WorkerAgent("worker_1")
        worker._client = mock_client
        assert worker.agent_id == "worker_1"

    @patch("mqtt_bbs.bbs.BBSClient")
    def test_start_registers_topics(self, MockClient):
        """WorkerAgent.start() 应 subscribe 必要的 topic"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        worker = WorkerAgent("worker_1")
        worker._client = mock_client

        worker.start()

        # 检查 subscribe 了 open/task 等 topic
        subscribe_calls = [c[0][0] for c in mock_client.subscribe.call_args_list]
        assert any("board/open" in t for t in subscribe_calls), "should subscribe to board/open"
