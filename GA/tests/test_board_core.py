"""BoardService Core unit tests."""
import sys
from pathlib import Path
from unittest.mock import patch
_proj = Path(__file__).resolve().parent.parent.parent.parent
_beneh = _proj.parent
for p in [str(_proj), str(_beneh)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import unittest

class TestBoardServiceInit(unittest.TestCase):
    @patch("Mqtt_bbs_server.board_core.cfg")
    def test_init_defaults(self, mock_cfg):
        mock_cfg.BROKER_HOST = "localhost"
        mock_cfg.BROKER_PORT = 1883
        from Mqtt_bbs_server.board_core import BoardService
        svc = BoardService(agent_id="test-agent")
        self.assertEqual(svc.agent_id, "test-agent")
        self.assertEqual(svc._host, "localhost")
    
    def test_init_custom_host(self):
        from Mqtt_bbs_server.board_core import BoardService
        svc = BoardService(agent_id="custom", host="10.0.0.1", port=9000)
        self.assertEqual(svc._host, "10.0.0.1")
        self.assertEqual(svc._port, 9000)
