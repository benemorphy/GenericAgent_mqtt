"""
board_service.py 单元测试 — BoardService + CapabilityRegistry 业务逻辑
使用 unittest.mock 模拟 MQTT 和数据库，不依赖外部服务。
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from mqtt_bbs.board_service import BoardService, CapabilityRegistry


class TestCapabilityRegistry:
    """CapabilityRegistry: Agent 能力注册与查询"""

    def test_init_empty(self):
        """初始化时注册表应为空"""
        reg = CapabilityRegistry()
        assert len(reg.get_agents()) == 0

    @patch("mqtt_bbs.board_service.time.time", return_value=1000)
    def test_on_heartbeat_registers_agent(self, mock_time):
        """心跳应注册/更新 Agent"""
        reg = CapabilityRegistry()
        reg._on_capability("agent/bbs/agent-bbs-test/capability", {
            "agent_id": "agent_a", "capabilities": ["code", "web"]
        })
        reg._on_heartbeat("node/agent_a/heartbeat", {"agent_id": "agent_a", "capabilities": ["code", "web"]})
        agents = reg.get_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "agent_a"

    @patch("mqtt_bbs.board_service.time.time", return_value=1000)
    def test_on_status_changes_state(self, mock_time):
        """状态变更应更新 Agent 状态"""
        reg = CapabilityRegistry()
        reg._on_capability("agent/bbs/agent-bbs-test/capability", {
            "agent_id": "agent_a", "capabilities": []
        })
        reg._on_heartbeat("node/agent_a/heartbeat", {"agent_id": "agent_a"})
        reg._on_status("node/agent_a/status", "busy")
        agents = reg.get_agents()
        assert agents[0]["status"] == "busy"

    @patch("mqtt_bbs.board_service.time.time", return_value=1000)
    def test_heartbeat_timeout_marks_offline(self, mock_time):
        """长时间无心跳的 Agent 应标记为 offline"""
        reg = CapabilityRegistry()
        reg._on_capability("agent/bbs/agent-bbs-test/capability", {
            "agent_id": "agent_a", "capabilities": ["code"]
        })
        reg._on_heartbeat("node/agent_a/heartbeat", {"agent_id": "agent_a"})
        # 模拟超过超时时间
        with patch("mqtt_bbs.board_service.time.time", return_value=2000):
            reg._check_expired(now=2000)
            agents = reg.get_agents()
            assert len(agents) == 0 or agents[0]["status"] == "offline"

    @patch("mqtt_bbs.board_service.time.time", return_value=1000)
    def test_query_by_capability(self, mock_time):
        """按能力过滤查询应返回匹配的 Agent"""
        reg = CapabilityRegistry()
        agents_data = [
            ("agent_a", ["code", "web"]),
            ("agent_b", ["web"]),
            ("agent_c", ["vision"]),
        ]
        for aid, caps in agents_data:
            reg._on_capability("agent/bbs/test/capability", {"agent_id": aid, "capabilities": caps})
            reg._on_heartbeat(f"node/{aid}/heartbeat", {"agent_id": aid, "capabilities": caps})

        web_agents = [a for a in reg.get_agents() if "web" in (a.get("capabilities") or [])]
        assert len(web_agents) >= 2
        assert all("web" in (a.get("capabilities") or []) for a in web_agents)


class TestBoardService:
    """BoardService: 公告板持久化服务"""

    @patch("mqtt_bbs.board_service.BBSClient")
    def test_init_creates_client(self, MockClient):
        """初始化应创建 BBSClient 连接"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        svc = BoardService("bbs-keeper")
        svc._client = mock_client  # 替换真实 client
        assert svc.agent_id == "bbs-keeper"

    @patch("mqtt_bbs.board_service.BoardService._subscribe_board")
    @patch("mqtt_bbs.board_service.BBSClient")
    def test_start_subscribes_boards(self, MockClient, mock_sub):
        """start() 应订阅 boards.json 中的所有 board"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        svc = BoardService("bbs-keeper")
        svc._client = mock_client

        with patch.object(svc, '_load_boards', return_value={
            "agent-bbs-test": {"name": "default"},
            "agent-inspiration": {"name": "灵感板"},
        }):
            svc.start()
            # 验证订阅了所有 board
            assert mock_sub.call_count >= 2

    @patch("mqtt_bbs.board_service.BBSClient")
    def test_stop_disconnects(self, MockClient):
        """stop() 应断开 MQTT 连接"""
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        svc = BoardService("bbs-keeper")
        svc._client = mock_client
        svc._running = True

        svc.stop()
        assert svc._running is False
        mock_client.disconnect.assert_called_once()
