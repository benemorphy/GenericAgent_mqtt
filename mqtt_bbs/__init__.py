"""
MQTT Agent BBS — 智能体协作消息总线

对标当前 subagent 文件协议 (input.txt / output.txt / [ROUND END])，
用 MQTT 主题树实现任务分发、流式反馈、结果收集。

公共测试 Broker: broker.emqx.io:1883（无需注册）

快速开始:
    from mqtt_bbs import AgentBoard, WorkerAgent

    # 主智能体：发布任务
    master = AgentBoard("master_alpha")
    task_id = master.post_task("analyse_log", {"path": "/var/log"})
    result = master.wait_task(task_id)

    # 工作智能体：认领并执行
    worker = WorkerAgent("worker_01")
    worker.start()  # 自动认领匹配能力的任务
"""

from .client import BBSClient
from .bbs import AgentBoard, WorkerAgent, TaskStatus
from .persistence import BBSClientWithPersistence, MariaDBConn, AgentBoardWithPersistence, WorkerAgentWithPersistence
from .board_client import BoardClient
from .board_service import BoardService

# 预定义测试板块
DEFAULT_BOARD = "agent-bbs-test"

__version__ = "0.1.0"
