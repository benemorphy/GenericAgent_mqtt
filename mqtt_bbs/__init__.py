"""
MQTT Agent BBS — 智能体协作消息总线 (Rust BoardService + Mosquitto + MariaDB)

快速开始:
    from mqtt_bbs.board_client import BoardClient

    bbs = BoardClient("agent_alpha")
    bbs.connect()
    info = bbs.register("agent_alpha")

依赖:
    Python 客户端 → MQTT (Mosquitto) → Rust BoardService RS → MariaDB
    Rust 无运行时可部署
"""

from .board_client import BoardClient
from .client import BBSClient
from .bbs import AgentBoard, WorkerAgent
from .whiteboard import WhiteboardKV
from .persistence import AgentBoardWithPersistence, BBSClientWithPersistence, WorkerAgentWithPersistence

__version__ = "0.3.0"
