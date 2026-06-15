"""board_config unit tests."""
import sys
from pathlib import Path
from unittest.mock import patch
_proj = Path(__file__).resolve().parent.parent.parent.parent
_beneh = _proj.parent
for p in [str(_proj), str(_beneh)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import unittest

class TestBoardConfig(unittest.TestCase):
    def test_has_boards_file_constant(self):
        import Mqtt_bbs_server.board_config as cfg
        self.assertTrue(hasattr(cfg, "BOARDS_FILE"))
        self.assertTrue(hasattr(cfg, "TOPIC_BBS"))
        self.assertEqual(cfg.TOPIC_BBS, "bbs")

    def test_has_default_boards(self):
        import Mqtt_bbs_server.board_config as cfg
        self.assertTrue(hasattr(cfg, "DEFAULT_BOARDS"))
        self.assertIsInstance(cfg.DEFAULT_BOARDS, dict)

    @patch("requests.post")
    def test_webhook_send(self, mock_post):
        from Mqtt_bbs_server.board_config import webhook_send
        mock_post.return_value.status_code = 200
        webhook_send("http://test.url", {"key": "value"})
        mock_post.assert_called_once_with("http://test.url", json={"key": "value"}, timeout=5)

    @patch("requests.post", side_effect=Exception("timeout"))
    def test_webhook_send_handles_error(self, mock_post):
        from Mqtt_bbs_server.board_config import webhook_send
        webhook_send("http://test.url", {})  # should not raise
        self.assertTrue(True)  # reached without exception
