"""goal_bbs unit tests."""
import sys
from pathlib import Path
from unittest.mock import patch
_proj = Path(__file__).resolve().parent.parent.parent.parent
if str(_proj) not in sys.path:
    sys.path.insert(0, str(_proj))



class TestGoalBbsInit:
    @patch("reflect.goal_bbs.bbs_init")
    def test_bbs_init_called(self, mock_init):
        from reflect.goal_bbs import bbs_init
        bbs_init("test_board")
        mock_init.assert_called_once_with("test_board")

    @patch("reflect.goal_bbs.bbs_pulse", return_value=None)
    def test_quick_pulse_format(self, mock_pulse):
        from reflect.goal_bbs import quick_pulse
        msg = quick_pulse(5, "testing", "done", 10.0)
        assert msg is None or isinstance(msg, dict)

    @patch("reflect.goal_bbs.bbs_chronicle")
    def test_chronicle_query(self, mock_chron):
        from reflect.goal_bbs import bbs_chronicle
        bbs_chronicle(action="query")
        mock_chron.assert_called_once_with(action="query")

    @patch("reflect.goal_bbs.bbs_chronicle")
    def test_chronicle_store(self, mock_chron):
        from reflect.goal_bbs import bbs_chronicle
        bbs_chronicle(action="store", text="test entry")
        mock_chron.assert_called_once_with(action="store", text="test entry")
