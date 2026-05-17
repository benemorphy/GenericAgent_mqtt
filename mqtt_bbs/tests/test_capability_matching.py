"""
测试: WorkerAgent 能力匹配逻辑

业务规则:
- capabilities=[] 或 None → 接受所有任务
- capabilities=["scan"] → 只接受 type=scan 的任务
- capabilities=["scan","analyse"] → 接受 scan 或 analyse
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import MagicMock, patch
from mqtt_bbs.client import TaskMessage, TaskOutput
import logging


class TestCapabilityMatching:
    """能力匹配单元测试 — 隔离MQTT网络"""

    def _make_worker(self, capabilities):
        """创建一个 mock 的 WorkerAgent（不连 MQTT）"""
        from mqtt_bbs.bbs import WorkerAgent
        worker = WorkerAgent.__new__(WorkerAgent)
        worker.agent_id = "test_worker"
        worker.capabilities = capabilities or []
        worker._task_handler = None
        worker._client = MagicMock()
        worker._current_task_id = None
        worker._seq = 0
        worker.stream_out = MagicMock()
        worker.stream_err = MagicMock()
        worker.claim_task = MagicMock(return_value=True)
        worker.complete = MagicMock()
        return worker

    def test_empty_capabilities_accepts_all(self):
        """能力列表为空 → 接受所有任务"""
        worker = self._make_worker([])
        worker._task_handler = MagicMock(return_value={"ok": True})

        msg = TaskMessage(task_id="t1", type="scan", input={"x": 1})
        worker._on_task_input("board/task/t1/input", msg.to_dict())

        worker.claim_task.assert_called_once_with("t1")
        worker._task_handler.assert_called_once()

    def test_matching_capability(self):
        """能力匹配 → 认领并执行"""
        worker = self._make_worker(["scan"])
        worker._task_handler = MagicMock(return_value={"ok": True})

        msg = TaskMessage(task_id="t2", type="scan", input={"target": "test"})
        worker._on_task_input("board/task/t2/input", msg.to_dict())

        worker.claim_task.assert_called_once_with("t2")

    def test_non_matching_capability_skips(self):
        """能力不匹配 → 跳过（不认领、不执行）"""
        worker = self._make_worker(["analyse"])
        worker._task_handler = MagicMock()

        msg = TaskMessage(task_id="t3", type="scan", input={"x": 1})
        worker._on_task_input("board/task/t3/input", msg.to_dict())

        worker.claim_task.assert_not_called()
        worker._task_handler.assert_not_called()

    def test_multi_capability_match(self):
        """多能力 → 任一匹配即可"""
        worker = self._make_worker(["scan", "analyse", "report"])
        worker._task_handler = MagicMock(return_value={"ok": True})

        msg = TaskMessage(task_id="t4", type="analyse", input={"x": 1})
        worker._on_task_input("board/task/t4/input", msg.to_dict())

        worker.claim_task.assert_called_once_with("t4")

    def test_skip_on_no_handler(self):
        """未注册 handler → 直接返回，不认领"""
        worker = self._make_worker(["scan"])
        worker._task_handler = None  # 没有handler

        msg = TaskMessage(task_id="t5", type="scan", input={"x": 1})
        worker._on_task_input("board/task/t5/input", msg.to_dict())

        worker.claim_task.assert_not_called()

    def test_skip_on_invalid_payload(self):
        """非法 payload（非 dict） → 直接返回"""
        worker = self._make_worker([])
        worker._task_handler = MagicMock()

        worker._on_task_input("board/task/t6/input", "not_a_dict")

        worker._task_handler.assert_not_called()
