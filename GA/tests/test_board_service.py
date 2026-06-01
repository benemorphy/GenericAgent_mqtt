"""Board Service unit tests."""
import sys
from pathlib import Path
_proj = Path(__file__).resolve().parent.parent.parent.parent
_beneh = _proj.parent
for p in [str(_proj), str(_beneh)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import unittest
from unittest.mock import MagicMock, patch

class TestCapabilityRegistry(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
    
    def test_methods_exist(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        self.assertTrue(hasattr(reg, "start"))
        self.assertTrue(hasattr(reg, "stop"))
        self.assertTrue(hasattr(reg, "get_agents"))
        self.assertTrue(hasattr(reg, "get_agent"))
    
    def test_get_agents_returns_list(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        result = reg.get_agents()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_agents_with_capability(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        result = reg.get_agents(capability="python")
        self.assertIsInstance(result, list)

    def test_get_agent_returns_none_for_missing(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        self.assertIsNone(reg.get_agent("nonexistent"))

    def test_start_subscribes(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        reg.start()
        self.assertTrue(self.mock_client.subscribe.called)
        self.assertTrue(reg._running)

    def test_stop_sets_running_false(self):
        from Mqtt_bbs_server.board_db import CapabilityRegistry
        reg = CapabilityRegistry(self.mock_client)
        reg.start()
        reg.stop()
        self.assertFalse(reg._running)


class TestMariaDBWrapper(unittest.TestCase):
    def test_init_with_connection(self):
        from Mqtt_bbs_server.board_db import MariaDBWrapper
        mock_conn = MagicMock()
        wrapper = MariaDBWrapper(mock_conn)
        self.assertTrue(hasattr(wrapper, "execute"))
        self.assertTrue(hasattr(wrapper, "commit"))
        self.assertTrue(hasattr(wrapper, "close"))

    def test_execute_calls_cursor(self):
        from Mqtt_bbs_server.board_db import MariaDBWrapper
        mock_conn = MagicMock()
        wrapper = MariaDBWrapper(mock_conn)
        wrapper.execute("SELECT 1")
        self.assertTrue(mock_conn.cursor.called)
